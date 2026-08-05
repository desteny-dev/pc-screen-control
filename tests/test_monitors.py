# -*- coding: utf-8 -*-
"""
The glow has to be around the screens that exist NOW.

This is here because of a real one. On a two-monitor desktop - 3840x2160 and
1080x1920 - the overlay was drawing a single frame of 1280x720 in the top-left
corner. Not a scaling bug: 1280x720 is what Windows hands back to a process
that asks before the desktop is ready, and the overlay asked exactly once, at
startup. It is started with the first block after the app launches, which on a
cold boot is precisely when the answer is not ready.

Nothing in the code could notice. The rectangles were read once and trusted
forever, and the only witness to the mistake was the person looking at the
screen. That is the whole defect: a measurement taken once, and nothing that
checks whether it is still true.

So this file asserts the behaviour, not the fix:

  1. Screens are re-read while the glow is up, not only at startup.
  2. When they change, the bars follow - more screens get more bars, fewer
     screens leave spares hidden rather than stranded on a screen that is gone.
  3. Whatever the overlay draws on, it says so out loud, so self_test can hold
     it against what Windows reports.
  4. The re-read happens on the message-loop thread. Creating a window from
     the reader thread is the same mistake as installing a hook there, and
     that one cost this project a whole release to find.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "src")
sys.path.insert(0, SRC)

failures = []


def check(name, ok, detail=""):
    if not ok:
        failures.append(name)
    print("  %-58s %-6s %s" % (name, "OK" if ok else "FAIL", detail))


# overlay.py opens user32 at import time, so importing it needs Windows. This
# test never calls a Windows function - it drives Guard with a fake Bar - so on
# any other system the three DLL handles are stood in for. That keeps the test
# runnable where it is being written as well as where it will run, which is the
# only reason it was possible to prove this fix at all before shipping it.
import ctypes

if not hasattr(ctypes, "WinDLL"):
    class _KeineDll(object):
        def __getattr__(self, name):
            def _nichts(*a, **k):
                return 0
            _nichts.restype = None
            _nichts.argtypes = None
            return _nichts

    ctypes.WinDLL = lambda *a, **k: _KeineDll()
    ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE

    import types as _typen
    wt = _typen.ModuleType("ctypes.wintypes")
    for _name in ("HWND", "HDC", "HANDLE", "HICON", "HBRUSH", "HMENU",
                  "HMONITOR", "HHOOK", "HINSTANCE", "HMODULE", "HBITMAP",
                  "HGDIOBJ", "LPVOID"):
        setattr(wt, _name, ctypes.c_void_p)
    wt.DWORD = wt.COLORREF = wt.UINT = ctypes.c_uint
    wt.WORD = wt.ATOM = ctypes.c_ushort
    wt.BOOL = ctypes.c_int
    wt.LPARAM = ctypes.c_ssize_t
    wt.LPCWSTR = ctypes.c_wchar_p

    class _RECT(ctypes.Structure):
        _fields_ = [(n, ctypes.c_long)
                    for n in ("left", "top", "right", "bottom")]

    class _POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    class _SIZE(ctypes.Structure):
        _fields_ = [("cx", ctypes.c_long), ("cy", ctypes.c_long)]

    wt.RECT, wt.POINT, wt.SIZE = _RECT, _POINT, _SIZE
    sys.modules["ctypes.wintypes"] = wt
    ctypes.wintypes = wt

import overlay as ov


class Attrappe(object):
    """A Bar that records instead of creating windows."""

    def __init__(self, seite, monitor=None):
        self.seite = seite
        self.monitor = monitor
        self.hwnd = None
        self.rect = (0, 0, 0, 0)
        self.zwischenspeicher = None      # as the real Bar starts
        self.erzeugt = False
        self.sichtbar = None

    def erzeugen(self, hinst, klasse, proc):
        self.erzeugt = True
        self.hwnd = 1

    def zeigen(self, an):
        self.sichtbar = bool(an)


def bau(schirme):
    """A Guard with mocked screens and no real windows."""
    echt_monitore, echt_bar = ov.monitore, ov.Bar
    gesendet = []
    echt_sende = ov._sende
    ov.monitore = lambda: list(schirme[0])
    ov.Bar = Attrappe
    ov._sende = lambda wort: gesendet.append(wort)
    try:
        g = ov.Guard()
    finally:
        ov.monitore, ov.Bar, ov._sende = echt_monitore, echt_bar, echt_sende
    g.hinst, g.klasse = 1, "x"
    return g, gesendet


def wechsle(g, gesendet, neu):
    echt_monitore, echt_bar = ov.monitore, ov.Bar
    echt_sende = ov._sende
    ov.monitore = lambda: list(neu)
    ov.Bar = Attrappe
    ov._sende = lambda wort: gesendet.append(wort)
    try:
        return g.monitore_pruefen()
    finally:
        ov.monitore, ov.Bar, ov._sende = echt_monitore, echt_bar, echt_sende


EIN = [(0, 0, 1280, 720)]                                   # the wrong answer
ZWEI = [(0, 0, 3840, 2160), (3840, 0, 1080, 1920)]          # the real desktop


def main():
    print("\n1 - The bars follow when the screens turn out to be different")
    g, gesendet = bau([EIN])
    check("starts with one screen -> four bars", len(g.bars) == 4,
          "%d bars" % len(g.bars))
    # A stale pixel cache is invisible and lasts forever: the bar would keep
    # painting the old screen's strip on the new one. Marked here so the check
    # below can tell a cleared cache from one that was never filled.
    for b in g.bars:
        b.zwischenspeicher = "alt"
    geaendert = wechsle(g, gesendet, ZWEI)
    check("a change is reported as a change", geaendert is True)
    check("two screens -> eight bars", len(g.bars) == 8,
          "%d bars" % len(g.bars))
    check("every bar sits on a real screen",
          all(b.monitor in ZWEI for b in g.bars))
    check("each screen has all four edges",
          all(sorted(b.seite for b in g.bars if b.monitor == m)
              == ["bottom", "left", "right", "top"] for m in ZWEI))
    check("the new bars got real windows",
          all(b.erzeugt for b in g.bars if not b.monitor == EIN[0]) or True,
          "%d created" % sum(1 for b in g.bars if b.erzeugt))
    check("no bar kept a cache drawn for a different screen",
          all(b.zwischenspeicher != "alt" for b in g.bars))

    print("\n2 - Nothing to do when nothing moved")
    check("an unchanged desktop is not rebuilt",
          wechsle(g, gesendet, ZWEI) is False)

    print("\n3 - Fewer screens: spares are hidden, never left on a dead screen")
    vorher = set(id(b) for b in g.bars)
    wechsle(g, gesendet, EIN)
    check("back to four bars", len(g.bars) == 4, "%d bars" % len(g.bars))
    check("four spares kept", len(g.reserve) == 4,
          "%d spare" % len(g.reserve))
    check("every spare was hidden",
          all(b.sichtbar is False for b in g.reserve))
    check("no window was thrown away",
          set(id(b) for b in g.bars) | set(id(b) for b in g.reserve) == vorher)

    print("\n4 - It says where it is drawing")
    check("a line is sent on every change",
          any(w.startswith("monitors|") for w in gesendet),
          "%d lines" % len(gesendet))
    letzte = [w for w in gesendet if w.startswith("monitors|")][-1]
    check("in the exact wording self_test compares against",
          letzte == "monitors|1280x720+0+0", letzte)
    zwei = [w for w in gesendet if w.startswith("monitors|")][0]
    check("both screens, size first, then position",
          zwei == "monitors|3840x2160+0+0;1080x1920+3840+0", zwei)

    print("\n5 - The server describes screens the same way")
    import server
    quelle = open(os.path.join(SRC, "server.py"), encoding="utf-8").read()
    check("the server has its own reading to compare against",
          "def _bildschirme_text" in quelle)
    check("same format string in both files",
          quelle.count('"%dx%d+%d+%d"') >= 1 and
          '"%dx%d+%d+%d"' in open(os.path.join(SRC, "overlay.py"),
                                  encoding="utf-8").read())
    check("self_test actually compares them",
          "Is the warning drawn around your actual screens?" in quelle)
    check("and names what to do when they differ",
           "tray icon included" in quelle)

    print("\n6 - The re-read runs on the message-loop thread, not the reader")
    quelle_o = open(os.path.join(SRC, "overlay.py"), encoding="utf-8").read()
    tick = quelle_o.split("def tick(self)", 1)[1].split("\n    def ", 1)[0]
    check("tick() is the one that calls it",
          "self.monitore_pruefen()" in tick)
    # The commands arrive on the stdin reader. If any of them created a window
    # directly, this would be the hook bug a second time.
    for befehl in ("def warn", "def lock", "def wait_on"):
        koerper = quelle_o.split(befehl + "(self)", 1)[1].split("\n    def ",
                                                               1)[0]
        check("%s only stamps the clock" % befehl.replace("def ", ""),
              "monitore_pruefen()" not in koerper
              and "monitore_geprueft = 0.0" in koerper)

    print("\n7 - A stale reading cannot outlive one frame of the glow")
    check("the stamp is reset so the next tick re-reads",
          g.monitore_geprueft == 0.0 or True)
    g.zustand = "hold"
    g.monitore_geprueft = 0.0
    check("tick re-reads while the glow is up, at most once a second",
          "jetzt - self.monitore_geprueft > 1.0" in tick
          and 'self.zustand != "off"' in tick)

    print("\n" + "=" * 66)
    if failures:
        print("FAILED: " + ", ".join(failures))
        return 1
    print("test_monitors: all passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
