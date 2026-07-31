# -*- coding: utf-8 -*-
"""
Every tool that can change the screen goes through the guard. No exceptions.

This exists because of a specific failure, and the shape of that failure is the
whole point. The guard used to protect "tools that take the mouse or keyboard" -
click, drag, send_keys, hold_key. Operating a control through the accessibility
interface takes no pointer, so invoke was treated as harmless.

It is not. The application on the other end is free to raise itself when one of
its buttons is pressed, and it usually does. A button was pressed in a chat
window; the window came to the front; the caret went with it; and the person
typing a report at that moment sent their next sentence into someone else's
message box. No pulse, no hold, nothing put back - because the tool that did it
was on the safe list.

The boundary is not "does this use the pointer". It is "can this change what is
on screen". So the server keeps a list of READERS, and everything else is
guarded. A tool added later is protected by default; forgetting to think about
it fails safe.

This test walks the real tool list and checks both halves of that: nothing
outside the reader list is unguarded, and nothing on the reader list secretly
acts. It needs no desktop - it reads the declarations.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "src")
sys.path.insert(0, SRC)
import server  # noqa: E402

failures = []


def check(name, ok, detail=""):
    if not ok:
        failures.append(name)
    print("  %-58s %-6s %s" % (name, "OK" if ok else "FAIL", detail))


def quelle_von(fn):
    import inspect
    try:
        return inspect.getsource(fn)
    except Exception:
        return ""


def main():
    namen = [t["name"] for t in server.TOOLS]
    leser = set(server.LESENDE_WERKZEUGE)

    print("1 - the dispatcher guards everything that is not a reader")
    versand = quelle_von(server._vor_dem_werkzeug)
    check("it checks the reader list", "LESENDE_WERKZEUGE" in versand)
    check("and guards the rest", "_session_beruehren" in versand)
    # The call has to actually be wired into the request path, not just defined.
    src = open(os.path.join(SRC, "server.py"), encoding="utf-8").read()
    check("wired in before every tool call",
          "_vor_dem_werkzeug(t[\"name\"]" in src)
    # Compare inside the dispatcher block only: batch dispatches tools too, and
    # matching its source instead would compare two unrelated places.
    block = src[src.index('if method == "tools/call"'):]
    ruf = block.index("_vor_dem_werkzeug(t[\"name\"]")
    aufruf = block.index('out = t["_fn"]')
    check("guard runs BEFORE the tool, not after", ruf < aufruf)

    print()
    print("2 - the reader list only contains tools that really read")
    # A reader must not operate anything. These are the verbs that change the
    # screen; finding one inside a tool that claims to be a reader is the bug
    # this section exists to catch.
    handelnd = ("SetFocus()", "Invoke()", "Toggle()", "SetValue(",
                "auto.Click", "auto.SendKeys", "auto.RightClick", "SetActive",
                "os.startfile", "subprocess.Popen", "ShowWindow", "MoveWindow",
                "SetWindowPos", "keybd_event")
    for t in server.TOOLS:
        if t["name"] not in leser:
            continue
        q = quelle_von(t["_fn"])
        # capture takes a picture and may focus a window first: it declares that
        # in its own schema and is the one documented exception.
        erlaubt = {"capture": ("SetActive", "SetFocus()")}.get(t["name"], ())
        treffer = [h for h in handelnd if h in q and h not in erlaubt]
        check("reader %r does not act" % t["name"], not treffer,
              ", ".join(treffer))

    print()
    print("3 - every acting tool is covered")
    ungeschuetzt = [n for n in namen if n not in leser]
    check("acting tools exist and are all outside the reader list",
          len(ungeschuetzt) >= 15, "%d acting, %d readers"
          % (len(ungeschuetzt), len(leser)))
    # Nothing may be on the reader list that is not a real tool - a typo there
    # would silently unguard nothing, or worse, guard nothing.
    unbekannt = sorted(leser - set(namen))
    check("no unknown names on the reader list", not unbekannt,
          ", ".join(unbekannt))

    print()
    print("4 - the tools that caused this are guarded now")
    for name in ("invoke", "set_text", "toggle", "select", "expand",
                 "set_value", "menu", "window", "close_window", "focus_window",
                 "launch_app", "click", "drag", "send_keys", "hold_key",
                 "scroll", "batch", "claim_window", "release_window"):
        check("%s is guarded" % name, name in namen and name not in leser)

    print()
    print("5 - the guard says in plain words what is about to happen")
    satz = server._werkzeug_satz("invoke", {})
    check("invoke reads as an action, not a tool name",
          satz and not satz.startswith("invoke"), satz)
    satz2 = server._werkzeug_satz("launch_app", {"command": "notepad.exe"})
    check("it names the target when there is one", "notepad.exe" in satz2, satz2)

    print()
    print("6 - the reader list is declared once, not scattered")
    stellen = len(re.findall(r"LESENDE_WERKZEUGE\s*=", src))
    check("declared exactly once", stellen == 1, "%d declarations" % stellen)

    print()
    print("-" * 68)
    print("RESULT:", "OK" if not failures else "FAILED: " + ", ".join(failures))
    print("-" * 68)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
