# -*- coding: utf-8 -*-
"""
A ref survives the page moving underneath it.

A ref is a path of child indexes: exact, cheap, and wrong the moment something
is inserted above the target. On a desktop application that is rare. On a modern
web page it happens constantly, because the page re-renders between two calls -
measured on a GitHub form, where a ref read one call earlier was already stale.
The consequence is worse than an error message: the tool can name a field and
not fill it, so the only route left is the mouse, which is the step down the
ladder this whole server exists to avoid.

So a stale ref is now looked up again by what it WAS - automation id, type, name
and class, recorded when the ref was handed out.

Simulated with a fake tree rather than a real browser: what is being tested is
the recovery logic, and a fake tree can be made to shift on demand, which a
browser cannot.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
import server  # noqa: E402

failures = []


def check(name, ok, detail=""):
    if not ok:
        failures.append(name)
    print("  %-58s %-6s %s" % (name, "OK" if ok else "FAIL", detail))


class Fake(object):
    """The few properties _resolve and the fingerprint actually read."""

    def __init__(self, art="EditControl", aid="", name="", cls="", kinder=None):
        self.ControlTypeName = art
        self.AutomationId = aid
        self.Name = name
        self.ClassName = cls
        self._kinder = kinder or []

    def GetChildren(self):
        return list(self._kinder)


def main():
    ziel = Fake(aid="release_body", name="Release description", cls="textarea")
    anderer = Fake(art="ButtonControl", aid="publish", name="Publish")

    # A page with the target as the second child of the root.
    wurzel = Fake(art="WindowControl", kinder=[anderer, ziel])
    server.auto = type("A", (), {"ControlFromHandle": staticmethod(
        lambda h: wurzel)})()

    print("1 - a ref that still fits is resolved by its path, untouched")
    server._REF_SPUR.clear()
    server._spur_merken("42:1", ziel)
    check("resolves to the same element", server._resolve("42:1") is ziel)

    print()
    print("2 - the page inserts a banner: the old path now points elsewhere")
    banner = Fake(art="TextControl", name="Cookie banner")
    wurzel._kinder = [banner, anderer, ziel]        # target moved 1 -> 2
    gefunden = server._resolve("42:1")
    check("did NOT return the wrong control", gefunden is not anderer,
          "would have typed into %r" % _name(gefunden))
    check("found the real target again by its id", gefunden is ziel)

    print()
    print("3 - the whole path is gone: still found, still the right one")
    wurzel._kinder = [Fake(art="GroupControl", name="wrapper",
                           kinder=[banner, anderer, ziel])]
    gefunden = server._resolve("42:1")
    check("found it nested one level deeper", gefunden is ziel)

    print()
    print("4 - without an id, type+name+class identify it")
    ohne_id = Fake(art="EditControl", aid="", name="Search", cls="omnibox")
    wurzel._kinder = [ohne_id]
    server._spur_merken("42:0", ohne_id)
    wurzel._kinder = [banner, ohne_id]              # shifted again
    check("found by type, name and class", server._resolve("42:0") is ohne_id)

    print()
    print("5 - a control that is really gone still fails, loudly")
    wurzel._kinder = [banner]
    try:
        server._resolve("42:0")
        check("raises when it truly cannot be found", False, "returned something")
    except ValueError as e:
        check("raises when it truly cannot be found", "stale" in str(e))

    print()
    print("6 - the fingerprint store cannot grow without limit")
    server._REF_SPUR.clear()
    for i in range(server.REF_SPUR_MAX + 50):
        server._spur_merken("42:%d" % i, ziel)
    check("bounded", len(server._REF_SPUR) <= server.REF_SPUR_MAX,
          "%d entries" % len(server._REF_SPUR))

    print()
    print("-" * 68)
    print("RESULT:", "OK" if not failures else "FAILED: " + ", ".join(failures))
    print("-" * 68)
    return 1 if failures else 0


def _name(el):
    return getattr(el, "Name", "?")


if __name__ == "__main__":
    sys.exit(main())
