# -*- coding: utf-8 -*-
"""
Regression test for the failure that made this check exist.

An assistant read a form, the person watching clicked into a chat window, and
the assistant then sent Enter. The keystroke went to the chat, because a
keystroke with no target goes wherever focus happens to be. The tool had always
returned a note saying "confirm this landed where you intended" - which is read
after the damage, not before it, and is therefore not a safeguard at all.

Telling "the user moved the focus" apart from "we moved it" looks like it needs
to know who generated an event, and Windows will not say: GetLastInputInfo
counts injected input as input. The question can be answered without that. The
foreground window is recorded after every tool call, so anything the server did
is already in the baseline; a change that shows up between calls came from
outside. That is the person, or a window that stole focus by itself, and
neither is somewhere to type blindly.

Checked here:
  1. Nothing moved  -> blind keystrokes go through.
  2. Foreground moved between calls -> refused, with both windows named.
  3. force=true     -> goes through anyway, because sometimes it is right.
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

failures = []


def check(name, ok, detail=""):
    if not ok:
        failures.append(name)
    print("  %-54s %-6s %s" % (name, "OK" if ok else "FAIL", detail))


def main():
    try:
        import uiautomation  # noqa: F401
    except ImportError:
        print("SKIP: uiautomation is not installed")
        return 0

    import server

    print("1 - baseline matches the foreground: blind input is allowed")
    server._lage_merken()
    if not server._LAGE.get("hwnd"):
        print("SKIP: no foreground window in this session")
        return 0
    try:
        server._lage_pruefen({}, "type")
        check("allowed while nothing has moved", True)
    except RuntimeError as e:
        check("allowed while nothing has moved", False, str(e)[:60])

    print()
    print("2 - something else took the foreground: refused")
    # Simulated rather than acted out: forcing a real focus change from a test
    # would need a second window and a race with the window manager. What the
    # check actually compares is the recorded handle against the live one, so
    # a baseline pointing at a different window reproduces it exactly.
    echt = server._LAGE["hwnd"]
    server._LAGE["hwnd"] = echt + 12345          # a handle that is not in front
    server._LAGE["gesetzt"] = time.time() - 3.0
    try:
        server._lage_pruefen({}, "send these keystrokes")
        check("refused after the foreground changed", False,
              "it went ahead anyway")
    except RuntimeError as e:
        text = str(e)
        check("refused after the foreground changed", True)
        check("the refusal names both windows and says what to do",
              "Expected" in text and "found" in text
              and "focus_window" in text and "force=true" in text)

    server._LAGE["hwnd"] = echt

    print()
    print("2b - same window, focus moved inside it: refused")
    # The window-level check missed this one, twice. A person clicks another
    # field in the window that is already in front; the foreground handle never
    # changes, and the keystroke follows the focus into the wrong box.
    server._LAGE["fokus"] = ("EditControl", "some-other-field", "Somewhere else")
    server._LAGE["gesetzt"] = time.time() - 2.0
    jetzt = server._fokus_kennung()
    if jetzt is None:
        print("     (nothing holds focus in this session; cannot check here)")
    elif jetzt == server._LAGE["fokus"]:
        print("     (focus happens to match the decoy; cannot check here)")
    else:
        try:
            server._lage_pruefen({}, "send these keystrokes")
            check("refused after focus moved within the window", False,
                  "it went ahead anyway")
        except RuntimeError as e:
            text = str(e)
            check("refused after focus moved within the window", True)
            check("the refusal explains that typing follows the focus",
                  "follows the focus" in text and "force=true" in text)

    print()
    print("3 - force=true still works, for when it really is right")
    try:
        server._lage_pruefen({"force": True}, "send these keystrokes")
        check("force=true overrides the check", True)
    except RuntimeError:
        check("force=true overrides the check", False)

    server._lage_merken()

    print()
    print("4 - the check runs inside the lock, not before it")
    # Order is the whole point. Checking first and locking afterwards leaves a
    # gap in which a click still lands, and a check that only works sometimes
    # is worse than none, because it gets trusted.
    import inspect
    verdrahtet = {
        "t_send_keys": "send these keystrokes",
        "t_click": "click at these coordinates",
        "t_drag": "drag across these coordinates",
        "t_hold_key": "hold this key down",
    }
    for name, marke in verdrahtet.items():
        quelle = inspect.getsource(getattr(server, name))
        # Not %r: that quotes with apostrophes and the source uses double
        # quotes, which made this fail on correct code the first time round.
        uebergeben = ("_eingabe_laeuft((args," in quelle and marke in quelle
                      ) or "_eingabe_laeuft(wache)" in quelle
        check("%s hands the check to _eingabe_laeuft" % name, uebergeben)
        check("%s does not check before locking" % name,
              "_lage_pruefen" not in quelle)

    # Since the guard became a session, the lock is taken once per block rather
    # than once per action: the settle now lives where the block opens, and the
    # screen is handed back by the session when a check refuses. Same order,
    # different home - so look where it actually is.
    oeffnen = inspect.getsource(server._session_oeffnen)
    check("the block settles before reading", "BERUHIGEN_MS" in oeffnen)
    check("it locks before it saves",
          oeffnen.index("_warnen_und_sperren") < oeffnen.index("_fokus_sichern"))
    betreten = inspect.getsource(server._eingabe_laeuft.__enter__)
    check("the screen is handed back if the check refuses",
          "_session_schliessen" in betreten and "raise" in betreten)
    check("a settle delay exists and is small",
          0 < server.BERUHIGEN_MS <= 200, "%d ms" % server.BERUHIGEN_MS)

    print()
    print("-" * 64)
    print("RESULT:", "OK" if not failures else "FAILED: " + ", ".join(failures))
    print("-" * 64)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
