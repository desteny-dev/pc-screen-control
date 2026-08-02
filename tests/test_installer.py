# -*- coding: utf-8 -*-
"""
Tests for the setup logic in src/server.py.

These run against a simulated machine in a temporary directory and never touch
a real config file, so they are safe to run anywhere - including CI on a
machine that has no MCP client installed at all.

    python tests/test_installer.py

Exit code 0 when everything passes.
"""
import importlib.util
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(HERE, os.pardir, "src", "server.py")

spec = importlib.util.spec_from_file_location("uia_srv", SERVER)
srv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(srv)

_failures = []


def check(name, condition, detail=""):
    passed = bool(condition)
    if not passed:
        _failures.append(name)
    print("  %-58s %s%s" % (name, "ok" if passed else "FAIL",
                            ("   " + str(detail)) if detail and not passed else ""))


FOREIGN = {
    "some-other-server": {"command": "node", "args": ["x.js"]},
    "and-another": {"command": "python", "args": ["y.py"]},
}
ENTRY_NAME = srv.SERVER_NAME


print()
print("1 - fresh machine, no config file yet")
with tempfile.TemporaryDirectory() as t:
    p = os.path.join(t, "claude_desktop_config.json")
    state, _ = srv._install_write_config("Test", p, os.path.join(t, "server.py"))
    check("entry is created", state == "added", state)
    check("file is valid JSON", json.load(open(p, encoding="utf-8")))
    check("no backup needed", not os.path.exists(p + ".backup"))

print()
print("2 - machine that already has other MCP servers configured")
with tempfile.TemporaryDirectory() as t:
    p = os.path.join(t, "claude_desktop_config.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump({"mcpServers": dict(FOREIGN), "globalShortcut": "Alt+Space"}, fh)

    state, _ = srv._install_write_config("Test", p, os.path.join(t, "server.py"))
    d = json.load(open(p, encoding="utf-8"))
    check("reports 'added'", state == "added", state)
    check("foreign entries survive", all(k in d["mcpServers"] for k in FOREIGN))
    check("foreign entries unmodified",
          all(d["mcpServers"][k] == v for k, v in FOREIGN.items()))
    check("unrelated settings survive", d.get("globalShortcut") == "Alt+Space")
    check("backup was created", os.path.exists(p + ".backup"))
    b = json.load(open(p + ".backup", encoding="utf-8"))
    check("backup holds the state from BEFORE", ENTRY_NAME not in b["mcpServers"])

    print()
    print("3 - the same install run three times in a row")
    for _ in range(3):
        state, _ = srv._install_write_config("Test", p, os.path.join(t, "server.py"))
    d = json.load(open(p, encoding="utf-8"))
    b = json.load(open(p + ".backup", encoding="utf-8"))
    check("reports 'updated' from the second run on", state == "updated", state)
    check("exactly one entry, no duplicates",
          len([k for k in d["mcpServers"] if k == ENTRY_NAME]) == 1)
    check("foreign entries still present",
          all(k in d["mcpServers"] for k in FOREIGN))
    check("backup was NOT overwritten", ENTRY_NAME not in b["mcpServers"])
    check("no leftover .tmp file", not os.path.exists(p + ".tmp"))

print()
print("4 - config file is corrupt (not valid JSON)")
with tempfile.TemporaryDirectory() as t:
    p = os.path.join(t, "claude_desktop_config.json")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("{ this is not json ,,, ")
    state, _ = srv._install_write_config("Test", p, os.path.join(t, "server.py"))
    check("refuses instead of overwriting", state == "failed", state)
    check("file left untouched",
          open(p, encoding="utf-8").read().startswith("{ this is not json"))

print()
print("5 - mcpServers exists but is the wrong type")
with tempfile.TemporaryDirectory() as t:
    p = os.path.join(t, "claude_desktop_config.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump({"mcpServers": ["not", "an", "object"]}, fh)
    state, _ = srv._install_write_config("Test", p, os.path.join(t, "server.py"))
    check("refuses instead of guessing", state == "failed", state)

print()
print("6 - client is not installed at all (directory missing)")
with tempfile.TemporaryDirectory() as t:
    p = os.path.join(t, "does-not-exist", "claude_desktop_config.json")
    state, _ = srv._install_write_config("Test", p, os.path.join(t, "server.py"))
    check("skipped, no crash", state == "skipped", state)

print()
print("7 - non-ASCII user name and spaces in the path")
with tempfile.TemporaryDirectory() as t:
    d2 = os.path.join(t, u"Jörg Müller", "App Data")
    os.makedirs(d2)
    p = os.path.join(d2, "claude_desktop_config.json")
    target = os.path.join(d2, "pc-screen-control", "server.py")
    state, _ = srv._install_write_config("Test", p, target)
    d = json.load(open(p, encoding="utf-8"))
    check("entry created", state == "added", state)
    check("path round-trips unchanged",
          d["mcpServers"][ENTRY_NAME]["args"][0] == target)

print()
print("8 - install locations come from the environment, not from constants")
source = open(SERVER, encoding="utf-8").read()
check("install dir derived from LOCALAPPDATA", "LOCALAPPDATA" in source)
check("config dir derived from APPDATA", "APPDATA" in source)
# Both separators, always - not os.sep. Using the running platform's separator
# meant a hard-coded C:\... slipped through every local run on Linux and only
# turned CI red, which is the slowest possible way to find a one-line mistake.
# A Windows path is wrong in this file whatever machine is reading it.
check("no hard-coded install path",
      not re.search(r"[A-Za-z]:[\\/](?!Users.you)\w", source))

print()
print("-" * 68)
if _failures:
    print("FAILED (%d): %s" % (len(_failures), ", ".join(_failures)))
else:
    print("all checks passed")
print("-" * 68)
if __name__ == "__main__":          # never on import
    sys.exit(1 if _failures else 0)
