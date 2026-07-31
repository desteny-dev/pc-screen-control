# -*- coding: utf-8 -*-
"""
The handover, end to end: freeze, look, act, restore, release. In that order.

Two orderings matter and both were wrong once.

Checking the target and *then* freezing input leaves a gap in which a click
still lands. That was fixed first. Releasing the input and *then* restoring the
screen is the same race mirrored: the keyboard comes back while the screen still
points wherever the action left it, so a keystroke goes into the wrong window at
the exact moment the guard believes it has finished. Both gaps are short, both
fail only sometimes, and a guard that fails only sometimes is worse than none
because it gets trusted.

There is also a quieter one. The state used to be photographed before the lock
closed, so it recorded the screen as it was *before* the user's last keystroke
arrived - and then faithfully restored them to a moment that never finished
happening.

What is asserted here is the order itself, not the presence of the calls. Every
version that was broken had all the calls.
"""
import inspect
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

failures = []


def check(name, ok, detail=""):
    if not ok:
        failures.append(name)
    print("  %-56s %-6s %s" % (name, "OK" if ok else "FAIL", detail))


def ohne_doku(quelle):
    """
    Source without its docstring.

    Order is checked by where things appear in the text, and a docstring that
    explains the order naturally mentions the same names in the same breath -
    which made this fail against correct code the first time it ran.
    """
    marke = '"""'
    erst = quelle.find(marke)
    if erst == -1:
        return quelle
    zweit = quelle.find(marke, erst + 3)
    if zweit == -1:
        return quelle
    return quelle[:erst] + quelle[zweit + 3:]


def vor(text, a, b):
    """Does a appear before b, ignoring the docstring?"""
    text = ohne_doku(text)
    ia, ib = text.find(a), text.find(b)
    return ia != -1 and ib != -1 and ia < ib


def main():
    import server

    print("1 - opening the session: warn/lock, settle, then save")
    src = inspect.getsource(server._session_oeffnen)
    check("locks or warns before saving the state",
          vor(src, "_warnen_und_sperren", "_fokus_sichern"))
    check("settles before saving, so the last keystroke has landed",
          vor(src, "sleep", "_fokus_sichern"))

    enter = inspect.getsource(server._eingabe_laeuft.__enter__)
    check("joins the session before checking the target",
          vor(enter, "_session_beruehren", "_lage_pruefen"))
    check("hands the screen back if the check refuses",
          "_session_schliessen" in enter and "raise" in enter)

    print()
    print("2 - giving it back: restore first, release second")
    frei = inspect.getsource(server._session_schliessen)
    check("restores before releasing the input",
          vor(frei, "_fokus_zurueck", 'sagen("release")'),
          "the mirrored race")
    check("puts the mouse back too", "_maus_zurueck" in frei)
    check("retries once if the window did not come back", "sleep" in frei)
    check("records what was actually restored", "_RUECKGABE" in frei)

    print()
    print("3 - the restore does not fight Windows")
    zur = inspect.getsource(server._fokus_zurueck)
    check("window first", vor(zur, "_vordergrund_setzen", "SetFocus"))
    check("accepts the focus Windows restored by itself",
          vor(zur, "_fokus_kennung", "SetFocus"))
    check("only forces focus when it really has to", "forced" in zur)

    print()
    print("4 - the foreground call is the version that works")
    vg = inspect.getsource(server._vordergrund_setzen)
    check("attaches the input queue", "AttachThreadInput" in vg)
    check("detaches again", vg.count("AttachThreadInput") >= 2)
    check("restores a minimised window first", "IsIconic" in vg)
    check("reports the measured result, not the attempt",
          "GetForegroundWindow" in vg.split("finally")[-1])

    print()
    print("-" * 68)
    print("RESULT:", "OK" if not failures else "FAILED: " + ", ".join(failures))
    print("-" * 68)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
