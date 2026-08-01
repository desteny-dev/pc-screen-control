# -*- coding: utf-8 -*-
"""
The window the person was in must not disappear.

Reported from real use: "when you take control my active window goes to the
background, and now and then it was even closed."

Three tools can make a window vanish and none of them used to know which window
the person was sitting in:

  * close_window closes it
  * claim_window moves it past every monitor, where it looks closed
  * window state:minimized hides it

Plus a fourth path that is not a tool at all: Alt+F4 or Ctrl+W sent blind,
landing on whatever holds the keyboard.

This replays each of them against the real source, and also checks the cases
where nothing may be refused - a guard that blocks correct work gets switched
off, and then it is not there on the day it matters.

Runs anywhere: it reads and executes the guard functions, it does not open
windows.
"""
import inspect
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

os.environ["PSC_NO_UIA"] = "1"
import server  # noqa: E402

fehler = []


def pruefe(name, ok, detail=""):
    if not ok:
        fehler.append(name)
    print("  %-58s %-7s %s" % (name, "OK" if ok else "FEHLER", detail))


def quelle(fn):
    return inspect.getsource(fn)


# ---------------------------------------------------------------------------
print("1 - the person's window is known while a block is open")

server._SESSION["offen"] = True
server._SESSION["gesichert"] = {"hwnd": 4242, "titel": "Report.docx - Word"}

heim = server._heimat()
pruefe("_heimat reports handle and title", heim == (4242, "Report.docx - Word"),
       str(heim))

server._SESSION["offen"] = False
pruefe("no block open means no protected window", server._heimat() is None)
server._SESSION["offen"] = True


# ---------------------------------------------------------------------------
print()
print("2 - it is refused")

for was, args in (
        ("close", {"window_title": "Report"}),
        ("park", {"window_title": "Report"}),
        ("minimize", {"window_handle": 4242}),
        ("close by handle without confirm", {"window_handle": 4242}),
):
    try:
        server._nutzerfenster_schuetzen(4242, args, was)
        pruefe("refuses to %s the person's window" % was, False, "went through")
    except RuntimeError as e:
        text = str(e)
        pruefe("refuses to %s the person's window" % was, True)
        pruefe("  ... names the window, not just a handle",
               "Report.docx - Word" in text)
        pruefe("  ... says to hand the screen back and ask",
               "block:'end'" in text and "ask the person" in text)


# ---------------------------------------------------------------------------
print()
print("3 - it does NOT refuse correct work")

try:
    server._nutzerfenster_schuetzen(9999, {"window_title": "Notepad"}, "close")
    pruefe("another window is closed without complaint", True)
except RuntimeError as e:
    pruefe("another window is closed without complaint", False, str(e)[:50])

try:
    server._nutzerfenster_schuetzen(
        4242, {"window_handle": 4242, "confirm": True}, "close")
    pruefe("named by handle AND confirmed gets through", True)
except RuntimeError as e:
    pruefe("named by handle AND confirmed gets through", False, str(e)[:50])

server._SESSION["offen"] = False
try:
    server._nutzerfenster_schuetzen(4242, {"window_title": "Report"}, "close")
    pruefe("outside a block nothing is protected", True)
except RuntimeError:
    pruefe("outside a block nothing is protected", False)
server._SESSION["offen"] = True


# ---------------------------------------------------------------------------
print()
print("4 - the three tools actually call it")

for name, fn in (("close_window", server.t_close_window),
                 ("claim_window", server.t_claim_window),
                 ("window", server.t_window)):
    pruefe("%s asks before making a window vanish" % name,
           "_nutzerfenster_schuetzen" in quelle(fn))

pruefe("close_window refuses to guess an ambiguous title",
       "streng=True" in quelle(server.t_close_window))
pruefe("claim_window refuses to guess an ambiguous title",
       "streng=True" in quelle(server.t_claim_window))
pruefe("window only protects the minimising case",
       'zustand == "minimized"' in quelle(server.t_window))


# ---------------------------------------------------------------------------
print()
print("5 - an ambiguous title is refused, an exact one is not")

server._top_windows = lambda: [                      # noqa: E731
    {"handle": 1, "title": "Chrome"},
    {"handle": 2, "title": "Report - Chrome"},
    {"handle": 3, "title": "Mail - Chrome"},
]
server.auto = type("A", (), {"ControlFromHandle": staticmethod(lambda h: h)})

try:
    server._window_by(title="Chrome", streng=True)
    # "Chrome" is an exact match for handle 1, so this must NOT refuse
    pruefe("an exact title still wins outright", True)
except ValueError as e:
    pruefe("an exact title still wins outright", False, str(e)[:60])

try:
    server._window_by(title="- Chrome", streng=True)
    pruefe("an ambiguous title is refused", False, "picked one")
except ValueError as e:
    t = str(e)
    pruefe("an ambiguous title is refused", True)
    pruefe("  ... lists the candidates with handles",
           "handle 2" in t and "handle 3" in t)
    pruefe("  ... says to use window_handle instead", "window_handle" in t)

try:
    server._window_by(title="- Chrome")
    pruefe("reading still gets a best guess (streng off)", True)
except ValueError:
    pruefe("reading still gets a best guess (streng off)", False)


# ---------------------------------------------------------------------------
print()
print("6 - blind window-closing keystrokes")

for tasten in ("%{F4}", "{Alt}{F4}", "^w", "^W", "^{F4}"):
    pruefe("%r is recognised as window-closing" % tasten,
           server._fenster_toetende_tasten(tasten) is not None)

for harmlos in ("^s", "{Esc}", "hello world", "^v", "{Enter}"):
    pruefe("%r is not treated as window-closing" % harmlos,
           server._fenster_toetende_tasten(harmlos) is None)

q = quelle(server.t_send_keys)
pruefe("send_keys refuses them without a ref",
       "_fenster_toetende_tasten" in q and 'if not args.get("ref")' in q)
pruefe("... but a ref makes it a normal thing to do",
       re.search(r"Refusing to send.*without a ref", q, re.S) is not None)


# ---------------------------------------------------------------------------
print()
print("7 - a foreground that did not come back is said out loud")

q = quelle(server._session_schliessen)
pruefe("the restore is attempted more than twice",
       "for pause in (0.08, 0.25)" in q)
pruefe("a failed restore is queued for the next call",
       "_NACHHALL" in q and "foreground_not_restored" in q)
pruefe("it says which window should be in front",
       "should_be_in_front" in q and "window_handle" in q)
pruefe("watch mode explains itself once, not never",
       "_WATCH_HINWEIS" in q and "watch_mode" in q)

haupt = quelle(server._handle)
pruefe("the dispatcher delivers it on success", "_NACHHALL" in haupt)
pruefe("the dispatcher delivers it on failure too",
       haupt.count("_NACHHALL.popitem()") >= 2)


print()
print("=" * 74)
print("NUTZERFENSTER:", "ALLES GRUEN" if not fehler
      else "FEHLER -> " + ", ".join(fehler))
print("=" * 74)
sys.exit(1 if fehler else 0)
