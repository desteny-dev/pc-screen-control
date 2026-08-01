# -*- coding: utf-8 -*-
"""
The edge overlay and the input guard.

Two jobs in one small always-on process:

  1. The edge glow that shows when Claude is taking the physical mouse or
     keyboard - and, on request, the rubber-band pulse that announces it is
     about to.
  2. The input guard itself: low-level hooks that swallow the user's keystrokes
     and clicks while Claude works, and let Claude's own (injected) input
     through. Escape is no longer an abort - a stray Esc must not cancel the
     assistant; pause and stop live in the tray icon.

Why a separate process: hooks and a layered window both need a running message
loop, and that loop must not share a thread with the protocol. If it dies, the
server carries on and Windows tears the hooks down automatically - the user can
never be locked out by a crash.

Why four edge bars instead of one full-screen window: a full-screen layered
window is ~36 MB per frame and cannot be animated. Four thin bars are ~0.6 ms
per frame (measured), so the pulse is smooth.

Protocol, one word per line.
  in  (stdin):  warn | lock | keepalive | release | wait_on | wait_off | off | quit
                notify|<text>   (show a Windows notification with this text)
  out (stdout): go      (user clicked the wait card)
"""
import ctypes
import ctypes.wintypes as w
import sys
import threading
import time

BLUE = (34, 211, 238)         # settled / idle glow
RED = (239, 68, 68)           # active user: attention, a takeover is starting
THICKNESS = 46                # resting inward reach, px
PEAK_ALPHA = 165
INHALE_MS = 900               # slow build inward
EXHALE_MS = 180               # fast snap back - the "now" instant
RELEASE_MS = 420              # gentle fade at the end
MAX_DEPTH = 260               # idle inhale reach
MAX_DEPTH_WARN = 360          # active user: reach deeper - "stronger into the screen"
WATCHDOG_MS = 10000           # hard auto-unlock

# The current glow colour, mutated in place during the pulse. When the user is
# active the warn breathes RED and reaches deeper, then fades RED -> BLUE as it
# snaps to a hold; an idle takeover stays quietly BLUE.
_FARBE = list(BLUE)


def _mix(a, b, f):
    f = max(0.0, min(1.0, f))
    return (a[0] + (b[0] - a[0]) * f,
            a[1] + (b[1] - a[1]) * f,
            a[2] + (b[2] - a[2]) * f)


def _set_farbe(rgb):
    _FARBE[:] = [int(rgb[0]), int(rgb[1]), int(rgb[2])]

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
WPARAM, LPARAM = ctypes.c_size_t, ctypes.c_ssize_t
ULONG_PTR = ctypes.c_size_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, w.HWND, ctypes.c_uint, WPARAM, LPARAM)
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, WPARAM, LPARAM)

WS_POPUP = 0x80000000
WS_EX = (0x00080000 | 0x00000020 | 0x00000080 | 0x08000000 | 0x00000008)
ULW_ALPHA = 0x02
HWND_TOPMOST = -1
SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x0001, 0x0002, 0x0010
SW_HIDE, SW_SHOWNA = 0, 8
WH_KEYBOARD_LL, WH_MOUSE_LL = 13, 14
LLKHF_INJECTED, LLMHF_INJECTED = 0x10, 0x01
VK_ESCAPE = 0x1B
WM_TIMER, WM_QUIT = 0x0113, 0x0012
WM_KEYDOWN, WM_SYSKEYDOWN = 0x0100, 0x0104
WM_LBUTTONDOWN = 0x0201


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", w.DWORD), ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long), ("biPlanes", w.WORD),
                ("biBitCount", w.WORD), ("biCompression", w.DWORD),
                ("biSizeImage", w.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", w.DWORD),
                ("biClrImportant", w.DWORD)]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [("BlendOp", ctypes.c_ubyte), ("BlendFlags", ctypes.c_ubyte),
                ("SourceConstantAlpha", ctypes.c_ubyte),
                ("AlphaFormat", ctypes.c_ubyte)]


class WNDCLASS(ctypes.Structure):
    _fields_ = [("style", ctypes.c_uint), ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                ("hInstance", w.HINSTANCE), ("hIcon", w.HICON),
                ("hCursor", w.HANDLE), ("hbrBackground", w.HBRUSH),
                ("lpszMenuName", w.LPCWSTR), ("lpszClassName", w.LPCWSTR)]


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", w.DWORD), ("scanCode", w.DWORD), ("flags", w.DWORD),
                ("time", w.DWORD), ("dwExtraInfo", ULONG_PTR)]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("pt", w.POINT), ("mouseData", w.DWORD), ("flags", w.DWORD),
                ("time", w.DWORD), ("dwExtraInfo", ULONG_PTR)]


def _declare():
    user32.RegisterClassW.restype = w.ATOM
    user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASS)]
    user32.CreateWindowExW.restype = w.HWND
    user32.CreateWindowExW.argtypes = [
        w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, w.HWND, w.HMENU, w.HINSTANCE, w.LPVOID]
    user32.DefWindowProcW.restype = LRESULT
    user32.DefWindowProcW.argtypes = [w.HWND, ctypes.c_uint, WPARAM, LPARAM]
    user32.GetDC.restype = w.HDC
    user32.GetDC.argtypes = [w.HWND]
    user32.ReleaseDC.argtypes = [w.HWND, w.HDC]
    user32.ShowWindow.argtypes = [w.HWND, ctypes.c_int]
    user32.MoveWindow.argtypes = [w.HWND, ctypes.c_int, ctypes.c_int,
                                  ctypes.c_int, ctypes.c_int, w.BOOL]
    user32.GetSystemMetrics.restype = ctypes.c_int
    user32.UpdateLayeredWindow.restype = w.BOOL
    user32.UpdateLayeredWindow.argtypes = [
        w.HWND, w.HDC, ctypes.POINTER(w.POINT), ctypes.POINTER(w.SIZE),
        w.HDC, ctypes.POINTER(w.POINT), w.COLORREF,
        ctypes.POINTER(BLENDFUNCTION), w.DWORD]
    user32.SetWindowsHookExW.restype = w.HHOOK
    user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, w.HINSTANCE,
                                         w.DWORD]
    user32.CallNextHookEx.restype = LRESULT
    user32.CallNextHookEx.argtypes = [w.HHOOK, ctypes.c_int, WPARAM, LPARAM]
    user32.UnhookWindowsHookEx.argtypes = [w.HHOOK]
    user32.UnhookWindowsHookEx.restype = w.BOOL
    user32.SetTimer.restype = ctypes.c_void_p
    user32.SetTimer.argtypes = [w.HWND, ctypes.c_void_p, w.UINT, ctypes.c_void_p]
    user32.KillTimer.argtypes = [w.HWND, ctypes.c_void_p]
    user32.SetWindowPos.argtypes = [w.HWND, w.HWND, ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    user32.SetWindowPos.restype = w.BOOL
    user32.GetCursorPos.argtypes = [ctypes.POINTER(w.POINT)]
    user32.FindWindowW.restype = w.HWND
    user32.FindWindowW.argtypes = [w.LPCWSTR, w.LPCWSTR]
    user32.GetWindowRect.argtypes = [w.HWND, ctypes.POINTER(w.RECT)]
    user32.GetWindowRect.restype = w.BOOL
    gdi32.CreateCompatibleDC.restype = w.HDC
    gdi32.CreateCompatibleDC.argtypes = [w.HDC]
    gdi32.CreateDIBSection.restype = w.HBITMAP
    gdi32.CreateDIBSection.argtypes = [
        w.HDC, ctypes.POINTER(BITMAPINFOHEADER), w.UINT,
        ctypes.POINTER(ctypes.c_void_p), w.HANDLE, w.DWORD]
    gdi32.SelectObject.restype = w.HGDIOBJ
    gdi32.SelectObject.argtypes = [w.HDC, w.HGDIOBJ]
    gdi32.DeleteObject.argtypes = [w.HGDIOBJ]
    gdi32.DeleteDC.argtypes = [w.HDC]
    kernel32.GetModuleHandleW.restype = w.HMODULE
    kernel32.GetModuleHandleW.argtypes = [w.LPCWSTR]
    kernel32.GetCurrentThreadId.restype = w.DWORD
    user32.PostThreadMessageW.argtypes = [w.DWORD, ctypes.c_uint, WPARAM, LPARAM]


def _dpi_bewusst():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


def virtueller_bildschirm():
    g = user32.GetSystemMetrics
    x, y, cx, cy = g(76), g(77), g(78), g(79)
    if cx <= 0 or cy <= 0:
        x, y, cx, cy = 0, 0, g(0), g(1)
    return int(x), int(y), int(cx), int(cy)


def _bar_pixels(breite, hoehe, seite, tiefe, staerke):
    """
    Premultiplied BGRA for one edge bar, bottom-up.

    'seite' is which edge (top/bottom/left/right). The glow is brightest at the
    screen edge and fades to nothing at depth 'tiefe'. 'staerke' scales the
    whole thing 0..1 for the fade in and out.
    """
    r, g, b = _FARBE
    tiefe = max(1, int(tiefe))

    def farbe(d):
        t = 1.0 - (d / float(tiefe))
        a = int(PEAK_ALPHA * t * t * staerke)
        return bytes((b * a // 255, g * a // 255, r * a // 255, a))

    if seite in ("top", "bottom"):
        # each row is one colour across the full width; distance = row from edge
        reihen = []
        for y in range(hoehe):
            d = y if seite == "bottom" else (hoehe - 1 - y)
            reihen.append(farbe(d) * breite if d < tiefe
                          else b"\x00\x00\x00\x00" * breite)
        return b"".join(reihen)      # already bottom-up for our purpose
    else:
        # each row identical; within the row, distance = column from edge
        zeile = bytearray(b"\x00\x00\x00\x00" * breite)
        for x in range(breite):
            d = x if seite == "left" else (breite - 1 - x)
            if d < tiefe:
                zeile[x * 4:(x + 1) * 4] = farbe(d)
        return bytes(zeile) * hoehe


def monitore():
    """Every monitor's own rectangle.

    The bars used to follow the virtual desktop - one box around ALL screens.
    That looks right on a single monitor and is wrong on every other setup:
    measured here on two screens of different height, the bottom edge of the
    desktop sat 240px BELOW the smaller monitor, so somebody working on that
    screen got a top edge, a right edge, and nothing else. Half a frame does
    not read as a warning; it reads as a glitch.

    So each monitor gets its own complete frame. Whichever screen the person is
    looking at, the whole thing is around it.
    """
    gefunden = []
    PROC = ctypes.WINFUNCTYPE(ctypes.c_int, w.HMONITOR, w.HDC,
                              ctypes.POINTER(w.RECT), w.LPARAM)

    def _cb(hmon, hdc, lprc, lp):
        r = lprc.contents
        gefunden.append((int(r.left), int(r.top),
                         int(r.right - r.left), int(r.bottom - r.top)))
        return 1

    try:
        user32.EnumDisplayMonitors(0, None, PROC(_cb), 0)
    except Exception:
        pass
    return gefunden or [virtueller_bildschirm()]


class Bar(object):
    """One edge strip of one monitor, as its own click-through layered window."""

    def __init__(self, seite, monitor=None):
        self.seite = seite
        self.monitor = monitor          # (x, y, breite, hoehe) of ONE screen
        self.hwnd = None
        self.rect = (0, 0, 0, 0)
        self.zwischenspeicher = None    # (schluessel, pixel)

    def erzeugen(self, hinst, klasse, proc):
        self.hwnd = user32.CreateWindowExW(
            WS_EX, klasse, "psc-%s" % self.seite, WS_POPUP,
            0, 0, 10, 10, None, None, hinst, None)

    def platzieren_und_zeichnen(self, tiefe, staerke):
        vx, vy, vw, vh = self.monitor or virtueller_bildschirm()
        dick = max(1, int(min(tiefe, MAX_DEPTH_WARN)))
        if self.seite == "top":
            x, y, cx, cy = vx, vy, vw, dick
        elif self.seite == "bottom":
            x, y, cx, cy = vx, vy + vh - dick, vw, dick
        elif self.seite == "left":
            x, y, cx, cy = vx, vy, dick, vh
        else:
            x, y, cx, cy = vx + vw - dick, vy, dick, vh
        self.rect = (x, y, cx, cy)
        # Building the pixels is the expensive part - the top bar of a 4K
        # screen is nearly a megabyte, assembled in Python. During the one
        # second of animation every frame differs and there is nothing to
        # reuse; while the block is HELD nothing changes at all, and the same
        # buffer is re-applied several times a second to keep the bar on
        # screen. Without this cache that redraw would cost more than the
        # animation it follows.
        schluessel = (cx, cy, self.seite, int(tiefe), round(staerke, 3), _FARBE)
        if self.zwischenspeicher and self.zwischenspeicher[0] == schluessel:
            pixel = self.zwischenspeicher[1]
        else:
            pixel = _bar_pixels(cx, cy, self.seite, tiefe, staerke)
            self.zwischenspeicher = (schluessel, pixel)

        kopf = BITMAPINFOHEADER()
        kopf.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        kopf.biWidth, kopf.biHeight = cx, cy
        kopf.biPlanes, kopf.biBitCount, kopf.biCompression = 1, 32, 0

        sdc = user32.GetDC(None)
        mdc = gdi32.CreateCompatibleDC(sdc)
        bits = ctypes.c_void_p()
        bmp = gdi32.CreateDIBSection(mdc, ctypes.byref(kopf), 0,
                                     ctypes.byref(bits), None, 0)
        if bmp:
            ctypes.memmove(bits, pixel, len(pixel))
            alt = gdi32.SelectObject(mdc, bmp)
            # Being TOPMOST once is not being TOPMOST. Any other window that
            # asks for topmost - a browser, a media player, an installer - is
            # put above whoever asked earlier, and from then on the bar is
            # behind a maximised window and invisible. Measured: the glow was
            # there when the block began and gone a second or two later, which
            # is worse than no glow at all, because the person learns the
            # warning is unreliable. So the position is re-asserted on every
            # redraw. NOACTIVATE and NOMOVE/NOSIZE: this changes z-order only,
            # it never takes the foreground and never moves anything.
            user32.SetWindowPos(self.hwnd, w.HWND(HWND_TOPMOST), 0, 0, 0, 0,
                                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
            blend = BLENDFUNCTION(0, 0, 255, 1)
            user32.UpdateLayeredWindow(
                self.hwnd, sdc, ctypes.byref(w.POINT(x, y)),
                ctypes.byref(w.SIZE(cx, cy)), mdc,
                ctypes.byref(w.POINT(0, 0)), 0, ctypes.byref(blend), ULW_ALPHA)
            gdi32.SelectObject(mdc, alt)
            gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(mdc)
        user32.ReleaseDC(None, sdc)

    def zeigen(self, an):
        if self.hwnd:
            user32.ShowWindow(self.hwnd, SW_SHOWNA if an else SW_HIDE)


# ---------------------------------------------------------------------------
# The Windows notification.
#
# A message in the chat is not a warning: when the user is working they are in
# another window, not reading it. This is the on-screen half - a real Windows
# notification, shown together with the edge pulse whenever the screen is taken
# while the user is active, so it reaches them where their attention actually is.
# It rides on a tray icon, which is also where pause/stop will live.
shell32 = ctypes.WinDLL("shell32", use_last_error=True)

NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP, NIF_INFO = 0x01, 0x02, 0x04, 0x10
NIIF_INFO = 0x01
IDI_INFORMATION = 32516
WM_TRAY = 0x8000 + 1        # WM_APP+1: tray callback (used by the menu later)


class NOTIFYICONDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", w.DWORD),
        ("hWnd", w.HWND),
        ("uID", ctypes.c_uint),
        ("uFlags", ctypes.c_uint),
        ("uCallbackMessage", ctypes.c_uint),
        ("hIcon", w.HICON),
        ("szTip", ctypes.c_wchar * 128),
        ("dwState", w.DWORD),
        ("dwStateMask", w.DWORD),
        ("szInfo", ctypes.c_wchar * 256),
        ("uVersion", ctypes.c_uint),
        ("szInfoTitle", ctypes.c_wchar * 64),
        ("dwInfoFlags", w.DWORD),
        ("guidItem", ctypes.c_byte * 16),
        ("hBalloonIcon", w.HICON),
    ]


_TRAY = {"nid": None, "da": False}


def _tray_hinzufuegen(hwnd):
    """Add the tray icon once. Balloons are shown on it; the menu comes later."""
    if _TRAY["da"]:
        return
    try:
        user32.LoadIconW.restype = w.HICON
        icon = user32.LoadIconW(None, ctypes.c_void_p(IDI_INFORMATION))
        nid = NOTIFYICONDATA()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
        nid.hWnd = hwnd
        nid.uID = 1
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = WM_TRAY
        nid.hIcon = icon
        nid.szTip = "PC Screen Control"
        if shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid)):
            _TRAY["nid"] = nid
            _TRAY["da"] = True
    except Exception:
        pass


def _tray_benachrichtigen(text):
    """Show a Windows balloon - the notification that reaches the user even when
    they are working in another window."""
    nid = _TRAY["nid"]
    if not nid:
        return
    try:
        nid.uFlags = NIF_INFO
        nid.szInfoTitle = "Claude needs the screen for a moment"
        nid.szInfo = (text or "working")[:250]
        nid.dwInfoFlags = NIIF_INFO
        shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid))
    except Exception:
        pass


def _tray_entfernen():
    nid = _TRAY["nid"]
    if nid:
        try:
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
        except Exception:
            pass
    _TRAY["nid"] = None
    _TRAY["da"] = False


# ---- tray menu: pause / stop, written to mode.json for the server ----------
# Right-clicking the tray icon opens a tiny menu. Its choices are written to
# mode.json, which the server reads before every action - so pause and stop
# reach the assistant through a plain local file, no socket.
#
# This used to end with "and that is why a takeover cannot lock the user out of
# the controls: the tray icon and its menu are a normal window, not part of the
# swallowed input." That reasoning was wrong, and wrong in the worst possible
# place. A low-level mouse hook intercepts input BEFORE any window sees it -
# being a normal window has nothing to do with it. So while a block was held,
# a real click on the tray icon was swallowed like every other click, and Pause
# and Stop were unreachable during the only moments they exist for. The
# emergency brake did not work while the car was moving.
#
# Now the taskbar is carved out of the swallowing, and so is the whole screen
# while the menu is open. The risk is small and worth it by a wide margin: the
# taskbar is not where the assistant works, and someone reaching for the tray
# during a takeover is trying to stop it.
_TASKLEISTE = {"rect": None, "geprueft": 0.0}
_MENUE = {"offen": False}


def _im_rect(rect, x, y):
    return bool(rect) and rect[0] <= x < rect[2] and rect[1] <= y < rect[3]


def _taskleiste_rect():
    """Where the taskbar is, refreshed now and then - it can move or hide."""
    import time as _t
    jetzt = _t.time()
    if _TASKLEISTE["rect"] is not None and jetzt - _TASKLEISTE["geprueft"] < 1.0:
        return _TASKLEISTE["rect"]
    _TASKLEISTE["geprueft"] = jetzt
    try:
        h = user32.FindWindowW("Shell_TrayWnd", None)
        if h:
            r = w.RECT()
            if user32.GetWindowRect(h, ctypes.byref(r)):
                _TASKLEISTE["rect"] = (r.left, r.top, r.right, r.bottom)
                return _TASKLEISTE["rect"]
    except Exception:
        pass
    _TASKLEISTE["rect"] = None
    return None
WM_RBUTTONUP = 0x0205
WM_CONTEXTMENU = 0x007B
MF_STRING = 0x0000
TPM_RIGHTBUTTON, TPM_RETURNCMD = 0x0002, 0x0100
ID_PAUSE, ID_STOP, ID_VISIBLE = 1001, 1002, 1003

_TRAY_STATE = {"pause": False, "stop": False, "visible": False}


def _mode_schreiben():
    """Write the controls to mode.json; the server reads it before acting."""
    import json
    import os
    try:
        pfad = os.path.join(os.environ.get("LOCALAPPDATA", ""),
                            "pc-screen-control", "mode.json")
        os.makedirs(os.path.dirname(pfad), exist_ok=True)
        with open(pfad, "w", encoding="utf-8") as fh:
            json.dump(_TRAY_STATE, fh)
    except Exception:
        pass


def _menu_zeigen(hwnd):
    try:
        menu = user32.CreatePopupMenu()
        if not menu:
            return
        p = _TRAY_STATE
        user32.AppendMenuW(menu, MF_STRING, ID_VISIBLE,
                           "Work hidden" if p["visible"] else "Watch the work")
        user32.AppendMenuW(menu, MF_STRING, ID_PAUSE,
                           "Resume" if p["pause"] else "Pause")
        user32.AppendMenuW(menu, MF_STRING, ID_STOP,
                           "Let me work" if p["stop"] else "Stop")
        pt = w.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        user32.SetForegroundWindow(hwnd)     # so the menu closes on an outside click
        # TrackPopupMenu does not return until the menu closes, and it runs its
        # own message loop. Real input has to reach it for that whole time.
        _MENUE["offen"] = True
        try:
            cmd = user32.TrackPopupMenu(menu, TPM_RIGHTBUTTON | TPM_RETURNCMD,
                                        pt.x, pt.y, 0, hwnd, None)
        finally:
            _MENUE["offen"] = False
        user32.DestroyMenu(menu)
        if cmd == ID_PAUSE:
            p["pause"] = not p["pause"]
            _mode_schreiben()
        elif cmd == ID_STOP:
            p["stop"] = not p["stop"]
            _mode_schreiben()
        elif cmd == ID_VISIBLE:
            p["visible"] = not p["visible"]
            _mode_schreiben()
    except Exception:
        pass


def _tray_wndproc(hwnd, msg, wparam, lparam):
    if msg == WM_TRAY:
        if (lparam & 0xFFFF) in (WM_RBUTTONUP, WM_CONTEXTMENU):
            _menu_zeigen(hwnd)
        return 0
    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)


class Guard(object):
    """The whole overlay: bars, animation, hooks, wait card."""

    def __init__(self):
        self.monitore = monitore()
        self.bars = [Bar(s, m) for m in self.monitore
                     for s in ("top", "bottom", "left", "right")]
        self.zustand = "off"          # off warn hold release wait
        self.start = 0.0
        self.lock_seit = 0.0
        self.k_hook = None
        self.m_hook = None
        self.haken_wunsch = False     # what the protocol thread asked for
        self.zuletzt_gemalt = 0.0     # when the held bar was last re-applied
        self.sichtbar = False         # are the bars on screen at all
        self.haken_gemeldet = None    # what was last reported to the server
        self._kp = HOOKPROC(self._tasten)
        self._mp = HOOKPROC(self._maus)
        self._wndproc = WNDPROC(_tray_wndproc)
        self.timer_hwnd = None
        self.thread_id = 0

    # ---- hooks -----------------------------------------------------------
    def _gesperrt(self):
        return self.zustand == "hold"

    def _tasten(self, code, wparam, lparam):
        if code >= 0:
            d = ctypes.cast(lparam,
                            ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            eigen = bool(d.flags & LLKHF_INJECTED)
            # Escape is no longer special. A stray Esc must not cancel the
            # assistant, so while input is held it is swallowed like any other
            # real key; the assistant's own injected keys still pass. Pause and
            # stop live in the tray icon, not on a keystroke - but once that
            # menu is open it has to be usable, arrow keys and Enter included.
            if self._gesperrt() and not eigen and not _MENUE["offen"]:
                return 1                            # swallow real keystroke
        return user32.CallNextHookEx(None, code, wparam, lparam)

    def _maus(self, code, wparam, lparam):
        if code >= 0:
            d = ctypes.cast(lparam,
                            ctypes.POINTER(MSLLHOOKSTRUCT)).contents
            eigen = bool(d.flags & LLMHF_INJECTED)
            if self.zustand == "wait" and not eigen and \
                    wparam == WM_LBUTTONDOWN and self._auf_karte(d.pt.x, d.pt.y):
                _sende("go")
                return 1
            if self._gesperrt() and not eigen:
                # The way out stays open. Everything else on screen is held,
                # but the taskbar - and the whole screen while the tray menu is
                # up - has to keep taking real clicks, or Pause and Stop exist
                # only on paper.
                if _MENUE["offen"] or _im_rect(_taskleiste_rect(),
                                               d.pt.x, d.pt.y):
                    return user32.CallNextHookEx(None, code, wparam, lparam)
                return 1                            # swallow real click/move
        return user32.CallNextHookEx(None, code, wparam, lparam)

    # A low-level hook is delivered to the message queue of the thread that
    # INSTALLED it. The commands from the server arrive on the stdin thread,
    # and that thread sits blocked in a read with no message loop at all - so
    # hooks installed from there are never dispatched, Windows drops them after
    # LowLevelHooksTimeout, and the person keeps their mouse and keyboard while
    # the server is certain it is holding them. Nothing fails, nothing is
    # logged: the guard simply is not there.
    #
    # Reported as "I could still move my mouse and type while you had my
    # window", and it is the reason that report was possible at all.
    #
    # So these two only record a wish. The message loop applies it in tick(),
    # which is the one thread with a loop - and that is also the thread the
    # callbacks have to arrive on.
    def _haken_an(self):
        self.haken_wunsch = True

    def _haken_aus(self):
        self.haken_wunsch = False

    def _haken_anwenden(self):
        """Runs on the message-loop thread only. Installs or removes the hooks
        and tells the server what really happened - a guard that cannot say
        whether it is on is a guard nobody can trust."""
        if self.haken_wunsch and not self.k_hook:
            hmod = kernel32.GetModuleHandleW(None)
            self.k_hook = user32.SetWindowsHookExW(
                WH_KEYBOARD_LL, self._kp, hmod, 0) or None
            self.m_hook = user32.SetWindowsHookExW(
                WH_MOUSE_LL, self._mp, hmod, 0) or None
        elif not self.haken_wunsch and (self.k_hook or self.m_hook):
            if self.k_hook:
                user32.UnhookWindowsHookEx(self.k_hook)
                self.k_hook = None
            if self.m_hook:
                user32.UnhookWindowsHookEx(self.m_hook)
                self.m_hook = None

        haelt = bool(self.k_hook and self.m_hook)
        if haelt != self.haken_gemeldet:
            self.haken_gemeldet = haelt
            _sende("hooks:1" if haelt else "hooks:0")
            if self.haken_wunsch and not haelt:
                sys.stderr.write(
                    "[overlay] input hooks REFUSED by Windows - the user's "
                    "input is NOT held\n")
                sys.stderr.flush()

    # ---- wait card (drawn on the bottom bar area) ------------------------
    def _karte_rect(self):
        vx, vy, vw, vh = virtueller_bildschirm()
        b, h = 300, 68
        return (vx + vw - b - 40, vy + vh - h - 40, b, h)

    def _auf_karte(self, x, y):
        cx, cy, cw, ch = self._karte_rect()
        return cx <= x <= cx + cw and cy <= y <= cy + ch

    # ---- animation -------------------------------------------------------
    def _alle_zeigen(self, an):
        self.sichtbar = bool(an)
        for b in self.bars:
            b.zeigen(an)

    def _zeichne(self, tiefe, staerke):
        for b in self.bars:
            b.platzieren_und_zeichnen(tiefe, staerke)

    def tick(self):
        # First, always: this is the message-loop thread, so it is the only
        # place a low-level hook may be installed or removed.
        self._haken_anwenden()
        jetzt = time.time()
        # Nothing held, nothing announced - so nothing may be on screen. Found
        # on a real desktop: an overlay left over from an earlier server sat
        # with all four bars glowing and nothing holding. A glow that means
        # nothing is worse than no glow, because the next real one means
        # nothing either. Whatever path led there, this closes it.
        if self.zustand == "off" and self.sichtbar:
            self._alle_zeigen(False)
        t = (jetzt - self.start) * 1000.0

        if self.zustand == "warn":
            if t < INHALE_MS:
                # deep, slow inhale: RED and reaching deeper while the user is
                # active - the "you are being interrupted" cue.
                f = t / INHALE_MS
                f = 1 - (1 - f) * (1 - f)
                _set_farbe(RED)
                self._zeichne(THICKNESS + (MAX_DEPTH_WARN - THICKNESS) * f,
                              0.40 + 0.45 * f)
            elif t < INHALE_MS + EXHALE_MS:
                # fast exhale: snap back, fading RED -> BLUE as it settles.
                f = (t - INHALE_MS) / EXHALE_MS
                _set_farbe(_mix(RED, BLUE, f))
                self._zeichne(MAX_DEPTH_WARN - (MAX_DEPTH_WARN - THICKNESS) * f,
                              0.85 + 0.15 * f)
            else:
                _set_farbe(BLUE)
                self._zustand("hold")

        elif self.zustand == "release":
            f = t / RELEASE_MS
            if f >= 1.0:
                self._alle_zeigen(False)
                self._zustand("off")
            else:
                self._zeichne(THICKNESS, 1.0 - f)

        elif self.zustand == "hold":
            # Redraw, steadily, instead of drawing once and trusting it to
            # stay. Measured on a real desktop: the bar appears when the block
            # starts and is gone again within a second or two - the layered
            # content does not survive whatever else is composing the screen.
            # So for the entire time the person was actually locked out, there
            # was nothing on screen at all: a red flash, then silence. That is
            # the report "no blue fade came", and it was right.
            #
            # Every 200ms is invisible to a person and, with the pixel cache,
            # costs four UpdateLayeredWindow calls - far less than one frame of
            # the animation that precedes it.
            if jetzt - self.zuletzt_gemalt > 0.2:
                self.zuletzt_gemalt = jetzt
                self._zeichne(THICKNESS, 1.0)
            # crash-watchdog. If the server has gone silent - no
            # keepalive - for this long it has likely died, so release rather
            # than leave the user locked out. During real work the server's
            # keepalive keeps resetting lock_seit, so a long block is safe.
            if (jetzt - self.lock_seit) * 1000.0 > WATCHDOG_MS:
                self.release()

    def _zustand(self, neu):
        self.zustand = neu
        if neu == "hold":
            self.lock_seit = time.time()
            self._haken_an()
            self._zeichne(THICKNESS, 1.0)
        elif neu == "off":
            self._haken_aus()

    # ---- commands from the server ---------------------------------------
    def warn(self):
        _set_farbe(RED)                 # active user: the pulse starts red
        self._alle_zeigen(True)
        self.start = time.time()
        self._zustand("warn")

    def lock(self):
        """No announcement - user is idle. Straight to hold, quietly blue."""
        _set_farbe(BLUE)
        self._alle_zeigen(True)
        self._zustand("hold")

    def keepalive(self):
        """The server is still working: reset the crash-watchdog so a long but
        legitimate block is not force-released at the 10s mark. When the server
        dies the keepalives stop and the watchdog fires as intended."""
        if self.zustand == "hold":
            self.lock_seit = time.time()

    def wait_on(self):
        self._alle_zeigen(True)
        self.zustand = "wait"
        self._zeichne(THICKNESS, 0.5)
        # card is part of the bottom bar's redraw region; kept simple: the
        # glow signals waiting, the click area is the card rectangle.
        self._haken_an()          # need the mouse hook to catch the GO click

    def wait_off(self):
        self._haken_aus()
        self.zustand = "off"
        self._alle_zeigen(False)

    def release(self):
        if self.zustand in ("hold", "wait", "warn"):
            self._haken_aus()
            self.start = time.time()
            self.zustand = "release"

    def off(self):
        self._haken_aus()
        self.zustand = "off"
        self._alle_zeigen(False)


_STDOUT_LOCK = threading.Lock()


def _sende(wort):
    with _STDOUT_LOCK:
        try:
            sys.stdout.write(wort + "\n")
            sys.stdout.flush()
        except Exception:
            pass


def main():
    _declare()
    _dpi_bewusst()
    hinst = kernel32.GetModuleHandleW(None)
    klasse = "PcScreenControlEdge"
    guard = Guard()

    wc = WNDCLASS()
    wc.lpfnWndProc = guard._wndproc
    wc.hInstance = hinst
    wc.lpszClassName = klasse
    if not user32.RegisterClassW(ctypes.byref(wc)):
        fehler = ctypes.get_last_error()
        if fehler not in (0, 1410):
            raise ctypes.WinError(fehler)
    for b in guard.bars:
        b.erzeugen(hinst, klasse, guard._wndproc)
    _tray_hinzufuegen(guard.bars[0].hwnd)     # tray icon hosts the notifications

    guard.thread_id = kernel32.GetCurrentThreadId()
    # a hidden helper window would be cleaner, but a thread timer is enough:
    user32.SetTimer(None, None, 16, None)     # ~60 Hz WM_TIMER
    sys.stderr.write("[overlay] ready %s\n" % (virtueller_bildschirm(),))
    sys.stderr.flush()

    def lesen():
        try:
            for zeile in sys.stdin:
                roh = zeile.rstrip("\r\n")
                if roh.startswith("notify|"):
                    _tray_benachrichtigen(roh[7:])   # the message text, as sent
                    continue
                b = roh.strip().lower()
                if b == "warn":
                    guard.warn()
                elif b == "lock":
                    guard.lock()
                elif b == "keepalive":
                    guard.keepalive()
                elif b == "release":
                    guard.release()
                elif b == "wait_on":
                    guard.wait_on()
                elif b == "wait_off":
                    guard.wait_off()
                elif b == "off":
                    guard.off()
                elif b in ("quit", "exit"):
                    break
        except Exception:
            pass
        user32.PostThreadMessageW(guard.thread_id, WM_QUIT, 0, 0)

    threading.Thread(target=lesen, daemon=True).start()

    msg = w.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        if msg.message == WM_TIMER:
            guard.tick()
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))
    guard.off()
    # Still on the message-loop thread here, so this is the right place - and
    # the only place - to actually take the hooks down before exiting.
    guard._haken_anwenden()
    _tray_entfernen()


if __name__ == "__main__":
    main()
