# -*- coding: utf-8 -*-
"""
Stress test - not whether it works, but whether it holds.

The other tests ask "can it do this?". This one asks the questions that come
after: how expensive is each call, what happens when it is fed nonsense, is the
server still usable after an error, does it fall apart under repetition. A
server that dies on the twentieth call is worse in practice than one that never
started, because it dies in the middle of something.

Everything goes over real JSON-RPC against the server process. It found three
bugs the feature tests did not: describe_screen costing 11.4 seconds,
element_from_point claiming success for coordinates on no screen at all, and
empty table cells printing their column heading.

    python tests/stress.py

Exit code 0 when everything passes. Takes about a minute.
"""
import json
import os
import statistics
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(HERE, os.pardir, "src", "server.py")

_failures = []


def head(t):
    print()
    print("=" * 66)
    print(t)
    print("=" * 66)


def check(name, ok, detail=""):
    if not ok:
        _failures.append(name)
    print("  %-46s %-7s %s" % (name, "ok" if ok else "FAIL", str(detail)[:60]))


class Client(object):
    def __init__(self):
        self.p = subprocess.Popen(
            [sys.executable, SERVER], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding="utf-8", errors="replace", bufsize=1)
        self.id = 0
        self.junk = []
        self.stderr = []
        threading.Thread(target=self._err, daemon=True).start()
        self.raw({"jsonrpc": "2.0", "id": 0, "method": "initialize",
                  "params": {}})

    def _err(self):
        for z in self.p.stderr:
            self.stderr.append(z.rstrip())

    def raw(self, message, timeout=90):
        """Sends exactly what it is given - including nonsense."""
        if isinstance(message, dict):
            line = json.dumps(message)
            expect = message.get("id")
        else:
            line, expect = message, None
        self.p.stdin.write(line + "\n")
        self.p.stdin.flush()
        if expect is None:
            return None
        deadline = time.time() + timeout
        while time.time() < deadline:
            z = self.p.stdout.readline()
            if not z:
                raise RuntimeError("server closed the pipe")
            z = z.strip()
            if not z:
                continue
            try:
                m = json.loads(z)
            except Exception:
                self.junk.append(z)
                continue
            if m.get("id") == expect:
                return m
        raise RuntimeError("timeout")

    def tool(self, name, args=None, timeout=90):
        self.id += 1
        a = self.raw({"jsonrpc": "2.0", "id": self.id, "method": "tools/call",
                      "params": {"name": name, "arguments": args or {}}},
                     timeout)
        if a is None:
            return {"_error": "no answer"}
        if "error" in a:
            return {"_error": a["error"].get("message", "?")}
        for part in a.get("result", {}).get("content", []):
            if part.get("type") == "text":
                try:
                    return json.loads(part["text"])
                except Exception:
                    return {"_text": part["text"][:200]}
            if part.get("type") == "image":
                return {"_image": len(part.get("data", ""))}
        return a.get("result", {})

    def alive(self):
        try:
            self.id += 1
            a = self.raw({"jsonrpc": "2.0", "id": self.id,
                          "method": "tools/list", "params": {}}, 30)
            return bool(a and a.get("result", {}).get("tools"))
        except Exception:
            return False

    def close(self):
        try:
            self.p.stdin.close()
            self.p.wait(timeout=5)
        except Exception:
            self.p.kill()


c = Client()
started = time.time()

head("1 - Cost: how expensive is each call?")
d = c.tool("describe_screen")
windows = d.get("windows", [])
if not windows:
    print("no window - stopping")
    sys.exit(1)
big = max(windows, key=lambda w: w["probe_nodes"])
h = big["handle"]
print("  test window: %s (%d nodes)" % (big["title"][:40], big["probe_nodes"]))
print()

MEASURED = [
    ("describe_screen", "describe_screen", {}),
    ("list_windows", "list_windows", {}),
    ("read_ui_tree 400", "read_ui_tree", {"window_handle": h,
                                          "max_nodes": 400}),
    ("find_elements", "find_elements", {"window_handle": h, "query": "e",
                                        "limit": 10}),
    ("get_focus", "get_focus", {}),
    ("read_table", "read_table", {"window_handle": h, "max_rows": 20}),
]
times = {}
for label, tool, args in MEASURED:
    runs = []
    for _ in range(5):
        t0 = time.time()
        c.tool(tool, args)
        runs.append(time.time() - t0)
    times[label] = runs
    print("  %-22s min %5.2fs   median %5.2fs   max %5.2fs"
          % (label, min(runs), statistics.median(runs), max(runs)))

slow = [n for n, t in times.items() if statistics.median(t) > 8]
check("nothing slower than 8s at the median", not slow, slow)

head("2 - Repetition: 60 calls in a row")
t0 = time.time()
bad = 0
for _ in range(60):
    if "_error" in c.tool("find_elements", {"window_handle": h, "query": "a",
                                            "limit": 5}):
        bad += 1
total = time.time() - t0
print("  60 calls in %.1fs  (%.2fs each)" % (total, total / 60))
check("all 60 answered", bad == 0, "%d failed" % bad)
check("server still alive", c.alive())

head("3 - Limits: the largest tree it will build")
t0 = time.time()
r = c.tool("read_ui_tree", {"window_handle": h, "max_nodes": 6000,
                            "max_depth": 40})
print("  %s nodes in %.1fs" % (r.get("nodes_returned"), time.time() - t0))
check("full tree returned", r.get("nodes_returned", 0) > 0, r.get("_error", ""))
check("budget respected", r.get("nodes_returned", 0) <= 6000,
      r.get("nodes_returned"))
r = c.tool("read_ui_tree", {"window_handle": h, "max_nodes": 999999})
check("absurd budget is capped", r.get("nodes_returned", 0) <= 6000,
      r.get("nodes_returned"))

head("4 - Nonsense: every case must be refused cleanly")
NONSENSE = [
    ("window does not exist", "read_ui_tree", {"window_handle": 999999999}),
    ("ref is gibberish", "get_text", {"ref": "not-even-a-number"}),
    ("ref points nowhere", "get_text", {"ref": "%d:99.99.99" % h}),
    ("required field missing", "find_elements", {"window_handle": h}),
    ("coordinates off every screen", "element_from_point",
     {"x": -99999, "y": -99999}),
    ("value without a ref", "set_value", {"value": 50}),
    ("window title does not exist", "read_table",
     {"window_title": "this-window-certainly-does-not-exist"}),
    ("invented window state", "window", {"window_handle": h,
                                         "state": "floating"}),
    ("clipboard, wrong mode", "clipboard", {"mode": "delete"}),
    ("wait for nothing", "wait_for", {"timeout": 1}),
    ("batch with unknown tool", "batch",
     {"steps": [{"tool": "does-not-exist", "args": {}}]}),
    ("text where a number belongs", "read_ui_tree",
     {"window_handle": "twelve"}),
]
WORDS = ("Error", "error", "Exception", "must be", "required", "outside",
         "no longer", "stale", "not installed")


def refused(r):
    """
    A refusal is anything that does not pass for a usable result. Tool errors
    come back as text content, which is protocol-conformant and more readable
    for a model than a bare error code - but it has to count as a refusal here.
    """
    if "_error" in r or r.get("ok") is False or r.get("aborted") is True:
        return True
    t = r.get("_text")
    return bool(t and any(w in t for w in WORDS))


clean = 0
for label, tool, args in NONSENSE:
    try:
        r = c.tool(tool, args, timeout=45)
        ok = refused(r)
        clean += 1 if ok else 0
        print("  %-32s %s" % (label, ("refused: " + str(
            r.get("_text") or r.get("_error") or "cleanly")[:44])
            if ok else "LET THROUGH: %s" % str(r)[:44]))
    except Exception as e:
        print("  %-32s SERVER DIED: %s" % (label, e))
        _failures.append(label)
        break
check("all %d nonsense cases caught" % len(NONSENSE), clean == len(NONSENSE),
      "%d of %d" % (clean, len(NONSENSE)))
check("server alive after the nonsense", c.alive())

head("5 - Protocol: broken messages")
c.raw("this is not json at all")
c.raw("{\"incomplete\": ")
c.raw(json.dumps({"jsonrpc": "2.0", "id": 9001, "method": "no/such/method"}))
c.raw(json.dumps({"jsonrpc": "2.0", "method": "notifications/whatever"}))
c.raw("")
time.sleep(0.5)
check("server alive after broken messages", c.alive())
a = c.raw({"jsonrpc": "2.0", "id": 9002, "method": "no/such/method"}, 20)
check("unknown method returns an error object", bool(a and "error" in a),
      str(a)[:60])

head("6 - Repeatability: does the same call give the same answer?")
counts = [c.tool("read_ui_tree", {"window_handle": h, "max_nodes": 300}
                 ).get("nodes_returned") for _ in range(5)]
print("  node counts: %s" % counts)
check("result does not drift", len(set(counts)) == 1, counts)
# This used to require the window COUNT to be identical across three reads,
# which is not a property of the server - it is a claim that nobody opened or
# closed anything for a second and a half. Notifications appear, tooltips come
# and go, an installer finishes, our own overlay shows and hides. It failed
# intermittently on a different Python each time, and a test that fails at
# random gets ignored - and then it is not there on the day it matters, which
# is the same argument this project makes about a guard that refuses correct
# work.
#
# The real property is narrower and actually about the server: a window that
# is there in every read must be described the SAME WAY every time. Churn is
# reported, not failed on.
lesungen = [c.tool("describe_screen").get("windows", []) for _ in range(3)]
print("  window counts: %s" % [len(x) for x in lesungen])

bleibend = set.intersection(*[{w["handle"] for w in x} for x in lesungen])
gewandert = max(len(x) for x in lesungen) - len(bleibend)
if gewandert:
    print("  %d window(s) came or went during the reads - that is the desktop, "
          "not the server" % gewandert)

beschreibungen = {}
for lesung in lesungen:
    for w in lesung:
        if w["handle"] in bleibend:
            beschreibungen.setdefault(w["handle"], set()).add(
                (w.get("title"), w.get("verdict"), w.get("framework")))
uneins = [h for h, s in beschreibungen.items() if len(s) > 1]
check("windows that stayed are described identically", not uneins,
      "%d of %d differed" % (len(uneins), len(bleibend)))
check("something was seen at all", bool(bleibend), len(bleibend))

head("7 - Hygiene")
check("nothing but JSON-RPC on the protocol line", not c.junk, c.junk[:2])
check("stderr is just the ready line", len(c.stderr) <= 2, c.stderr[:3])
memory = None
try:
    import ctypes
    import ctypes.wintypes as wt

    class PMC(ctypes.Structure):
        _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t)]
    hp = ctypes.windll.kernel32.OpenProcess(0x0410, False, c.p.pid)
    pmc = PMC()
    pmc.cb = ctypes.sizeof(PMC)
    if ctypes.windll.psapi.GetProcessMemoryInfo(hp, ctypes.byref(pmc), pmc.cb):
        memory = pmc.WorkingSetSize / (1024.0 * 1024.0)
    ctypes.windll.kernel32.CloseHandle(hp)
except Exception:
    pass
if memory:
    print("  working set after ~120 calls: %.0f MB" % memory)
    check("memory under 400 MB", memory < 400, "%.0f MB" % memory)

c.close()
print()
print("total: %.0fs" % (time.time() - started))
print()
print("=" * 66)
print("STRESS TEST: %s" % ("passed" if not _failures else
                           "FAILED: " + ", ".join(_failures)))
print("=" * 66)
sys.exit(1 if _failures else 0)
