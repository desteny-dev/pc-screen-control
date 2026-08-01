# -*- coding: utf-8 -*-
"""
Keystrokes meant for one window must never land in another. Reported from use.

The setup: a terminal on one screen, the person's own chat window on the other.
The assistant was told to drive the terminal. It brought that window forward,
then spent a few seconds working out what to type. The block went idle, the
guard did exactly what it is built to do and handed the screen back - restoring
the person's window, where they were mid-sentence. Then the assistant sent its
keystrokes, and a command meant for a terminal was typed into their chat.

Every step was individually correct, which is what makes it worth a test. The
takeover check asks "has anything moved since the last call". Nothing had: the
restore was ours, so the baseline agreed with the screen. The question nobody
was asking is "is this the window we said we were working in".

So there are now two checks with different jobs:

  * _LAGE  - did the screen move under us (the user clicked somewhere)
  * _ZIEL  - is the foreground still the window we declared

This test drives the second one, including the exact sequence above, and checks
that it does not fire when it should not.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
import server  # noqa: E402

failures = []

TERMINAL = 111111          # what the assistant was told to drive
CHAT = 222222              # the person's own window, other screen


def check(name, ok, detail=""):
    if not ok:
        failures.append(name)
    print("  %-58s %-6s %s" % (name, "OK" if ok else "FAIL", detail))


def erlaubt(was="send these keystrokes", args=None):
    """Would blind input be allowed right now?"""
    try:
        server._lage_pruefen(args or {}, was)
        return True
    except RuntimeError:
        return False


def grund():
    try:
        server._lage_pruefen({}, "send these keystrokes")
        return ""
    except RuntimeError as e:
        return str(e)


def main():
    # Windows-only leaves, replaced so the state machine can be driven here.
    vordergrund = {"h": TERMINAL}
    server._vordergrund = lambda: vordergrund["h"]
    server._fenstertitel = lambda h: {TERMINAL: "PowerShell",
                                      CHAT: "Claude"}.get(int(h or 0), "?")
    server._fokus_kennung = lambda: ("EditControl", "", "prompt")

    print("1 - the reported failure, step by step")
    server._ziel_vergessen()
    server._LAGE.update({"hwnd": 0, "fokus": None, "gesetzt": 0.0})

    # a) the assistant brings the terminal forward - a declaration of intent
    server._ziel_setzen(TERMINAL, "PowerShell")
    check("target recorded when the assistant chose a window",
          server._ZIEL["hwnd"] == TERMINAL)

    # b) it types once while that window is still in front: fine
    server._lage_merken()
    check("typing into the declared window is allowed", erlaubt())

    # c) the block goes idle, the guard restores the person's window, and
    #    refreshes the baseline to the restored state - both correct
    vordergrund["h"] = CHAT
    server._lage_merken()

    # d) the assistant, still mid-task, sends its keystrokes
    check("typing after the screen was handed back is REFUSED", not erlaubt(),
          "this is the bug")
    text = grund()
    check("the refusal names the window it should have gone to",
          "PowerShell" in text, text[:60])
    check("the refusal names the window that is in front instead",
          "Claude" in text)
    check("it explains why this happens", "handed back" in text)
    check("it says what to do about it", "focus_window" in text)

    print()
    print("2 - it does not fire when it should not")
    server._ziel_vergessen()
    vordergrund["h"] = CHAT
    server._lage_merken()
    check("no declared target -> no refusal (nothing to contradict)", erlaubt())

    server._ziel_setzen(CHAT, "Claude")
    check("target matches the foreground -> allowed", erlaubt())

    server._ziel_setzen(TERMINAL, "PowerShell")
    vordergrund["h"] = TERMINAL
    server._lage_merken()
    check("assistant re-focused its window -> allowed again", erlaubt())

    print()
    print("3 - force still overrides, because sometimes it is right")
    vordergrund["h"] = CHAT
    check("force=true goes ahead", erlaubt(args={"force": True}))

    print()
    print("4 - the target is taken from the call, not from memory")
    server._ziel_vergessen()
    h = server._ziel_aus_args({"ref": "%d:1.2.3" % TERMINAL})
    check("a ref carries its window handle", h == TERMINAL, str(h))
    h = server._ziel_aus_args({"window_handle": CHAT})
    check("window_handle is taken as the target", h == CHAT, str(h))
    check("a call about nothing in particular sets no target",
          server._ziel_aus_args({"x": 5, "y": 5}) == 0)

    print()
    print("5 - reading a window is not a declaration of intent")
    # Only acting tools record a target. Reading the person's chat to see what
    # is on screen must not make it the place to type.
    src = open(os.path.join(os.path.dirname(HERE), "src", "server.py"),
               encoding="utf-8").read()
    vor = src[src.index("def _vor_dem_werkzeug"):]
    vor = vor[:vor.index("\ndef ", 1)]
    check("the reader list is checked before the target is set",
          vor.index("LESENDE_WERKZEUGE") < vor.index("_ziel_setzen"))
    check("and it returns for readers", "return" in vor.split("LESENDE_WERKZEUGE")[1][:60])

    print()
    print("6 - ending the block forgets the target")
    sg = server.t_set_guard
    import inspect
    q = inspect.getsource(sg)
    check("block:'end' clears it", "_ziel_vergessen" in q)

    print()
    print("-" * 68)
    print("RESULT:", "OK" if not failures else "FAILED: " + ", ".join(failures))
    print("-" * 68)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
