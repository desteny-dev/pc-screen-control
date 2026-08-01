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


# ---------------------------------------------------------------------------
print()
print("8 - ending a block says what actually came back")
#
# _RUECKGABE was written on every release and read by nobody: the server
# measured whether it had given the screen back and then never said so. The
# claim "your focus is restored is a measurement, not a promise" was true of
# the measurement and false of the reporting, which is how a foreground that
# never came back could keep happening without producing a single signal.

g = quelle(server.t_set_guard)
pruefe("block:'end' reads the measurement", "_RUECKGABE" in g)
pruefe("... and reports it", "handed_back" in g)
for feld in ("foreground_restored", "their_window", "in_front_now",
             "caret_restored", "attempts"):
    pruefe("  ... reports %s" % feld, feld in g)
pruefe("says what to do when it did not come back",
       "focus_window before doing anything else" in g)
pruefe("watch mode is reported as deliberate, not as failure",
       "watch_mode" in g and "deliberately" in g)
pruefe("the window in front is measured, not deduced",
       "foreground_now" in quelle(server._session_schliessen))


# ---------------------------------------------------------------------------
print()
print("9 - the input hold is installed on the thread that can receive it")
#
# A low-level hook is delivered to the message queue of the thread that
# INSTALLED it. The commands from the server arrive on the stdin thread, which
# sits blocked in a read with no message loop - so hooks installed from there
# are never dispatched and the person keeps their mouse and keyboard while the
# server is certain it is holding them. Nothing fails and nothing is logged.
#
# Reported as "I could still move my mouse and type while you had my window".

ov = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                  "src", "overlay.py")
with open(ov, encoding="utf-8") as fh:
    o = fh.read()

pruefe("_haken_an only records a wish",
       re.search(r"def _haken_an\(self\):\s*\n\s*self\.haken_wunsch = True", o)
       is not None)
pruefe("_haken_aus only records a wish",
       re.search(r"def _haken_aus\(self\):\s*\n\s*self\.haken_wunsch = False", o)
       is not None)
pruefe("the hooks are applied from tick(), the message-loop thread",
       re.search(r"def tick\(self\):\s*\n(\s*#[^\n]*\n)*\s*self\._haken_anwenden\(\)",
                 o) is not None)
anwenden = o[o.index("def _haken_anwenden"):]
anwenden = anwenden[:anwenden.index("\n    def ", 10)]
pruefe("both hooks are installed inside _haken_anwenden and nowhere else",
       anwenden.count("SetWindowsHookExW(") == 2
       and o.count("SetWindowsHookExW(") == 2,
       "%d im Ganzen" % o.count("SetWindowsHookExW("))
pruefe("a refused hook is written to stderr",
       "input hooks REFUSED by Windows" in o)
pruefe("the overlay reports the truth back to the server",
       '_sende("hooks:1" if haelt else "hooks:0")' in o)
pruefe("the hooks are taken down on the loop thread at exit",
       re.search(r"guard\.off\(\)\s*\n(\s*#[^\n]*\n)*\s*guard\._haken_anwenden\(\)",
                 o) is not None)

pruefe("the server reads that report",
       'wort.startswith("hooks:")' in quelle(server._overlay_lesen))
g = quelle(server.t_set_guard)
pruefe("block:'start' reports input_held", "input_held" in g)
pruefe("... and warns loudly when it is not held",
       "input_warning" in g and "NOT held" in g)


# ---------------------------------------------------------------------------
print()
print("10 - every acting reply carries the state the model cannot remember")
#
# The reader here is a model with no memory of the machine between turns. Only
# set_guard reported whether a block was open, so after two turns the assistant
# is guessing - and a block held by a forgotten start is how somebody ends up
# locked out of their own desk. Swallowed errors had the same shape: recorded
# faithfully, and only visible in self_test, which nobody runs mid-task.

server._SESSION["offen"] = True
server._SESSION["geoeffnet"] = 0.0
server._ZIEL["titel"] = "Notepad"
server._OVERLAY["haelt"] = True

aus = server._lagebericht("send_keys", server._FEHLER_ZAEHLER["total"])
lage = aus[0] if aus else {}
pruefe("an acting tool is told the block is open", lage.get("block_open") is True)
pruefe("... and how long it has been held", "seconds_held" in lage)
pruefe("... and whether the input is really held",
       lage.get("input_held") is True)
pruefe("... and which window it is working in", lage.get("working_in") == "Notepad")
pruefe("... and reminded to end it", "block:'end'" in (lage.get("reminder") or ""))

server._OVERLAY["haelt"] = False
lage = server._lagebericht("click", server._FEHLER_ZAEHLER["total"])[0]
pruefe("a shared screen is called a shared screen",
       "shared" in (lage.get("input_warning") or ""))
server._OVERLAY["haelt"] = True

pruefe("a reader is not nagged about the block",
       server._lagebericht("describe_screen",
                           server._FEHLER_ZAEHLER["total"]) == [])
server._SESSION["offen"] = False
pruefe("no block, no state block", server._lagebericht("click", 0) == [])

vorher = server._FEHLER_ZAEHLER["total"]
server._safe(lambda: 1 / 0)
server._safe(lambda: {}["nope"])
aus = server._lagebericht("click", vorher)
schluck = [a for a in aus if "swallowed_during_this_call" in a]
pruefe("errors swallowed during the call are reported", len(schluck) == 1)
if schluck:
    pruefe("  ... with the count", schluck[0]["swallowed_during_this_call"] == 2)
    pruefe("  ... with type and line",
           all("type" in e and "where" in e for e in schluck[0]["errors"]))
    pruefe("  ... and what it means for the result",
           "emptier or stranger" in schluck[0]["what_this_means"])
pruefe("a clean call says nothing",
       server._lagebericht("click", server._FEHLER_ZAEHLER["total"]) == [])

pruefe("the dispatcher attaches it to every reply",
       "_lagebericht(" in quelle(server._handle))


# ---------------------------------------------------------------------------
print()
print("11 - the guard cannot go missing, and cannot linger")

q = quelle(server._overlay_starten)
pruefe("a dead overlay is restarted, not returned as if alive",
       "p.poll() is None" in q and 'gestorben' in q)
pruefe("... and 'held' is forgotten when it dies", '"haelt"] = None' in q)
pruefe("... and a restart loop gives up honestly",
       '_OVERLAY["off"] = True' in q)

with open(ov, encoding="utf-8") as fh:
    o = fh.read()
pruefe("nothing may be on screen when nothing is held",
       'self.zustand == "off" and self.sichtbar' in o)
pruefe("each monitor gets its own frame",
       "def monitore(" in o and "Bar(s, m) for m in self.monitore" in o)
pruefe("the held bar is redrawn, not drawn once and trusted",
       "self.zuletzt_gemalt" in o)
pruefe("topmost is re-asserted, because it does not stay",
       "SetWindowPos(self.hwnd" in o and "HWND_TOPMOST" in o)
pruefe("the pixels are cached so the redraw is cheap",
       "zwischenspeicher" in o)


# ---------------------------------------------------------------------------
print()
print("12 - nobody sits through a wait inside a batch")

lang = server.t_batch({"steps": [{"tool": "wait", "args": {"seconds": 10}}]})
pruefe("a 10s wait inside a batch is refused", lang["aborted"] is True)
fehlertext = lang["results"][0].get("error", "")
pruefe("... and says how long it would have cost them",
       "10.0s of the person" in fehlertext)
pruefe("... and says what to do instead", "set_guard block:'end'" in fehlertext)
pruefe("the limit is short but not zero",
       0 < server.WARTEN_IM_BATCH_MAX_S <= 3)


# ---------------------------------------------------------------------------
print()
print("13 - the stale-ref rescue measures itself")

vorher = dict(server._SPUR_KOSTEN)
server._spur_messen(1200, 0.42, False)
server._spur_messen(4000, 1.10, True)
k = server._SPUR_KOSTEN
pruefe("runs are counted", k["laeufe"] == vorher["laeufe"] + 2)
pruefe("nodes are counted", k["knoten"] == vorher["knoten"] + 5200)
pruefe("the worst single run is kept", k["schlimmster_lauf_s"] >= 1.1)
pruefe("hitting the 4000 limit is counted",
       k["grenze_erreicht"] == vorher["grenze_erreicht"] + 1)
pruefe("self_test hands the numbers back",
       "stale_ref_rescue" in quelle(server.t_self_test))


print()
print("=" * 74)
print("NUTZERFENSTER:", "ALLES GRUEN" if not fehler
      else "FEHLER -> " + ", ".join(fehler))
print("=" * 74)
sys.exit(1 if fehler else 0)
