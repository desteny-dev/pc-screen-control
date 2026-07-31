# -*- coding: utf-8 -*-
"""
The handover session: one grab, held across calls, given back once.

This proves the behaviour the user asked for without needing Windows. The
OS-level leaves - the overlay pipe, saving and restoring focus, the idle clock -
are replaced with fakes, so what gets tested is the state machine itself:

  * a burst of actions is ONE takeover, warned once, restored once - not one
    flicker per action;
  * focus_window joins that session instead of stealing the foreground in
    silence (the exact bug that was reported);
  * the block ends on an explicit end_block or, as a safety net, after a short
    idle;
  * stop halts, and pause parks the assistant.
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
import server  # noqa: E402

failures = []


def check(name, ok, detail=""):
    if not ok:
        failures.append(name)
    print("  %-58s %-6s %s" % (name, "OK" if ok else "FAIL", detail))


# --- replace the Windows-only leaves with fakes -----------------------------
signale = []
restore = {"n": 0}
server._overlay_sagen = lambda w: signale.append(w)
server._fokus_sichern = lambda: {"hwnd": 4242}
server._maus_merken = lambda: (7, 7)
server._maus_zurueck = lambda p: True
server._lage_merken = lambda: None
server._leerlauf_ms = lambda: 0            # user is active -> the warn path


def _fake_restore(z):
    restore["n"] += 1
    return {"window": True, "control": True}


server._fokus_zurueck = _fake_restore
server.GUARD["enabled"] = True
server.SESSION_IDLE_S = 100                 # deterministic: no idle-close in 1-3


def reset():
    signale.clear()
    restore["n"] = 0
    server._SESSION.update({"offen": False, "gesichert": None, "maus": None,
                            "letzte": 0.0, "geoeffnet": 0.0, "dauer": None,
                            "nachricht": "", "explizit": False})
    server._STEUER.update({"pause": False, "stop": False, "sichtbar": False})


def main():
    print("1 - a burst of actions is ONE takeover, not one per action")
    reset()
    for i in range(4):
        server._session_beruehren("action %d" % i)
    check("session is open after the burst", server._SESSION["offen"])
    check("warned exactly once, not four times",
          signale.count("warn") == 1, "warn x%d" % signale.count("warn"))
    check("did NOT restore in the middle of the burst", restore["n"] == 0)

    print()
    print("2 - an explicit end gives the screen back exactly once")
    server._session_schliessen()
    check("session is closed", not server._SESSION["offen"])
    check("restored exactly once", restore["n"] == 1)
    check("released the input", "release" in signale)

    print()
    print("3 - focus_window joins the session (no silent foreground steal)")
    reset()

    class _El:
        Name = "GitHub"

        def SetActive(self):
            pass

    server._window_by = lambda h, t: (_El(), 3737708)
    server.t_focus_window({"window_handle": 3737708})
    check("focus_window opened a guarded session", server._SESSION["offen"])
    check("focus_window warned first (no silent steal)", "warn" in signale)
    check("focus_window saved the user's spot",
          server._SESSION["gesichert"].get("hwnd") == 4242)

    print()
    print("3b - launch_app joins the session too (a new window steals focus)")
    # Reported from real use: a console window flashed up for two seconds, took
    # the caret out of the report being written, and the keystrokes typed in
    # those seconds went nowhere - a hole in the text, with no warning first.
    reset()
    gestartet = {"n": 0}
    # A real file, so the "open it with its default handler" branch is the one
    # taken; the handler itself is stubbed so nothing actually starts.
    import tempfile as _tf
    skript = os.path.join(_tf.mkdtemp(), "some-script.bat")
    open(skript, "w").close()
    server.os.startfile = lambda p: gestartet.__setitem__("n", 1)
    server.t_launch_app({"command": skript})
    check("it did start the program", gestartet["n"] == 1)
    check("launch_app opened a guarded session", server._SESSION["offen"])
    check("it warned before the window appeared", "warn" in signale,
          ", ".join(signale))
    check("it saved the user's spot first",
          (server._SESSION["gesichert"] or {}).get("hwnd") == 4242)

    print()
    print("4 - the idle watchdog gives it back if the assistant forgets")
    server.SESSION_IDLE_S = 0.6
    server._session_beruehren("still working")   # refresh, keep it open
    server._watchdog_sicherstellen()
    time.sleep(server.SESSION_IDLE_S + 1.0)
    check("watchdog closed the idle session", not server._SESSION["offen"])
    check("watchdog restored on the way out", restore["n"] >= 1)
    server.SESSION_IDLE_S = 2.0                  # back to the production value

    print()
    print("5 - stop halts, pause parks")
    reset()
    server._STEUER["stop"] = True
    try:
        server._session_beruehren("x")
        check("stop raised and blocked the action", False, "no raise")
    except RuntimeError:
        check("stop raised and blocked the action", True)

    reset()
    server._session_oeffnen("work")
    check("session open before pause", server._SESSION["offen"])
    server._STEUER["pause"] = True
    time.sleep(0.9)                              # watchdog closes on pause
    check("pause handed the screen back", not server._SESSION["offen"])

    print()
    print("6 - a takeover of an active user fires an on-screen notification")
    reset()
    server._session_oeffnen("bring GitHub to the front", dauer=180, explizit=True)
    notifs = [s for s in signale if s.startswith("notify|")]
    check("a notification was sent (not just chat)", bool(notifs),
          notifs[0] if notifs else "none")
    check("it names what is happening", bool(notifs) and "GitHub" in notifs[0])
    check("it announces the duration (~3 min)",
          bool(notifs) and "min" in notifs[0], notifs[0] if notifs else "")

    print()
    print("7 - await_user hands the screen back and asks on screen")
    reset()
    server._session_oeffnen("working")           # take it first
    check("session open before await_user", server._SESSION["offen"])
    server.t_set_guard({"await_user": "log in to GitHub"})
    check("await_user handed the screen back", not server._SESSION["offen"])
    ask = [s for s in signale if s.startswith("notify|") and "Over to you" in s]
    check("asked the user on screen", bool(ask), ask[0] if ask else "none")

    print()
    print("8 - the tray's mode.json controls the server")
    import json
    import tempfile
    d = tempfile.mkdtemp()
    os.environ["LOCALAPPDATA"] = d
    os.makedirs(os.path.join(d, "pc-screen-control"), exist_ok=True)
    with open(os.path.join(d, "pc-screen-control", "mode.json"),
              "w", encoding="utf-8") as fh:
        json.dump({"pause": True, "visible": True}, fh)
    reset()
    server._steuer_lesen()
    check("mode.json pause reached the server", server._STEUER["pause"])
    check("mode.json visible mapped to sichtbar", server._STEUER["sichtbar"])
    # Clear it again: the watchdog thread re-reads this file every 0.3s, which
    # is exactly the behaviour we want in production (a tray click takes effect
    # immediately) but would otherwise leak into the sections below.
    with open(os.path.join(d, "pc-screen-control", "mode.json"),
              "w", encoding="utf-8") as fh:
        json.dump({"pause": False, "stop": False, "visible": False}, fh)
    server._steuer_lesen()

    print()
    print("9 - the server does not mistake its OWN input for the user typing")
    # GetLastInputInfo counts injected input too - our clicks, our SendKeys, and
    # the Alt tap every restore performs. Reading that back as "the user is
    # busy" produced a red pulse and a notification while nobody was at the
    # desk. Only input MORE RECENT than our own may count as the user's.
    reset()
    server.GUARD["idle_ms"] = 1500
    server._leerlauf_ms = lambda: 100          # something touched input 100ms ago
    server._injektion_merken()                 # ...and it was us, just now
    check("our own injection does not read as the user",
          server._nutzer_aktiv() is False)
    server._INJEKTION["zuletzt"] = time.time() - 5.0   # we acted 5s ago
    check("input after ours does read as the user",
          server._nutzer_aktiv() is True)
    server._leerlauf_ms = lambda: 9999         # nobody touched anything
    check("a quiet desk is never 'busy'", server._nutzer_aktiv() is False)

    # and the consequence: a quiet takeover stays quiet - no pulse, no toast
    reset()
    server._leerlauf_ms = lambda: 100
    server._injektion_merken()
    server._session_oeffnen("second action of a burst")
    check("no red pulse when the last input was ours",
          "warn" not in signale, ", ".join(signale))
    check("no notification either",
          not [s for s in signale if s.startswith("notify|")])
    server._leerlauf_ms = lambda: 0            # restore the busy default

    print()
    print("10 - an announced block is not killed by the 2s idle watchdog")
    reset()
    server._session_oeffnen("long job", dauer=180, explizit=True)
    check("announced block gets a long idle allowance",
          server._idle_grenze() >= 60, "%.0fs" % server._idle_grenze())
    server._SESSION["explizit"] = False
    check("an unannounced burst still closes after 2s",
          server._idle_grenze() == server.SESSION_IDLE_S,
          "%.0fs" % server._idle_grenze())
    server._session_schliessen()

    print()
    print("11 - priority 'me' waits, and refuses rather than grabbing")
    import threading
    reset()
    server.GUARD["priority"] = "me"
    server._leerlauf_ms = lambda: 0
    server._INJEKTION["zuletzt"] = 0.0          # the user really is active

    # a) they click go a moment later -> it proceeds
    def _go_gleich():
        time.sleep(0.4)
        server._OVERLAY["go"] = True
    threading.Thread(target=_go_gleich, daemon=True).start()
    server._session_oeffnen("needs the screen")
    check("showed the wait card instead of grabbing", "wait_on" in signale,
          ", ".join(signale))
    check("did not pulse a takeover warning", "warn" not in signale)
    check("locked only after the go", "lock" in signale)

    # b) they never click -> it must REFUSE, not take the screen anyway
    reset()
    server.WARTEN_MAX_S = 0.5                   # keep the test quick
    try:
        server._session_oeffnen("needs the screen")
        check("refuses when no go arrives", False, "it took the screen anyway")
    except RuntimeError as e:
        check("refuses when no go arrives", "priority 'me'" in str(e))
    check("nothing was locked on refusal", "lock" not in signale,
          ", ".join(signale))
    server.WARTEN_MAX_S = 45.0
    server.GUARD["priority"] = "claude"

    print()
    print("12 - watch mode leaves the work on screen instead of restoring")

    def tray_schreibt(**kw):
        """Go through the real path: the tray writes mode.json, the server
        reads it. Setting _STEUER directly would be undone by the watchdog,
        which re-reads the file - and that is the behaviour we want."""
        zustand = {"pause": False, "stop": False, "visible": False}
        zustand.update(kw)
        with open(os.path.join(d, "pc-screen-control", "mode.json"),
                  "w", encoding="utf-8") as fh:
            json.dump(zustand, fh)
        server._steuer_lesen()

    reset()
    tray_schreibt(visible=True)                  # user picks "Watch the work"
    server._session_oeffnen("doing the thing")
    server._session_schliessen()
    check("did not yank the window back while watching", restore["n"] == 0)
    check("still gave the input back", "release" in signale)
    check("said so in the record", server._RUECKGABE.get("watching") is True)

    reset()
    tray_schreibt(visible=False)                 # back to "Work hidden"
    server._session_oeffnen("doing the thing")
    server._session_schliessen()
    check("hidden mode restores as before", restore["n"] == 1)

    print()
    print("-" * 68)
    print("RESULT:", "OK" if not failures else "FAILED: " + ", ".join(failures))
    print("-" * 68)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
