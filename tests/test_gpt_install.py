# -*- coding: utf-8 -*-
"""
Registering with GPT must not damage a config that is already there.

Claude gets a packaged extension; GPT gets one block in ~/.codex/config.toml.
That file is not ours - it may already hold other MCP servers, model settings
and API keys, written by hand or by another tool. Adding one block to it is easy
to get almost right and ruinous to get wrong, so the same things are checked
here that the Claude installer checks: foreign entries survive untouched, a
second run updates instead of duplicating, a backup is made once and never
overwritten, and Windows paths come out the other side meaning what they said.

Runs against temporary files. Nothing real is read or written.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))

import importlib.util  # noqa: E402
spec = importlib.util.spec_from_file_location(
    "gptinst", os.path.join(os.path.dirname(HERE), "scripts",
                            "install-for-gpt.py"))
gi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gi)

failures = []


def check(name, ok, detail=""):
    if not ok:
        failures.append(name)
    print("  %-58s %-6s %s" % (name, "OK" if ok else "FAIL", detail))


FREMD = """model = "gpt-5"
approval_policy = "on-request"

[mcp_servers.context7]
command = "npx"
args = ["-y", "@upstash/context7-mcp"]

[mcp_servers.other-thing]
command = "node"
args = ["x.js"]
"""

# Deliberately not a path under a real home directory. The consistency checker
# refuses those anywhere in the published tree, and it is right to: a fixture
# that looks like somebody's own machine is how one leaks.
PY = r"X:\Programs\Python311\python.exe"
SRV = r"X:\Tools\pc-screen-control\server.py"


def main():
    print("1 - Windows paths survive being written into TOML")
    w = gi.toml_wert(PY)
    check("backslashes are escaped", "\\\\" in w and w.startswith('"'))
    try:
        import tomllib
        geparst = tomllib.loads("p = %s" % w)["p"]
        check("it parses back to the same path", geparst == PY, geparst)
    except ImportError:
        check("it parses back to the same path", True, "tomllib not in 3.9/3.10")

    print()
    print("2 - a fresh machine with no config at all")
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, ".codex", "config.toml")
        zustand = gi.config_schreiben(p, gi.block_bauen(PY, SRV))
        inhalt = open(p, encoding="utf-8").read()
        check("reports 'added'", zustand == "added", zustand)
        check("the block is there", "[mcp_servers.pc-screen-control]" in inhalt)
        check("no backup needed", not os.path.exists(p + ".backup"))

    print()
    print("3 - a config that already has other servers in it")
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, ".codex", "config.toml")
        os.makedirs(os.path.dirname(p))
        open(p, "w", encoding="utf-8").write(FREMD)
        gi.config_schreiben(p, gi.block_bauen(PY, SRV))
        inhalt = open(p, encoding="utf-8").read()
        check("foreign server context7 survives",
              "[mcp_servers.context7]" in inhalt and "@upstash/context7-mcp" in inhalt)
        check("foreign server other-thing survives",
              "[mcp_servers.other-thing]" in inhalt)
        check("unrelated settings survive",
              'model = "gpt-5"' in inhalt and "approval_policy" in inhalt)
        check("a backup was made", os.path.exists(p + ".backup"))
        sicherung = open(p + ".backup", encoding="utf-8").read()
        check("the backup holds the state from BEFORE",
              "pc-screen-control" not in sicherung)

        print()
        print("4 - running it three times in a row")
        for _ in range(3):
            zustand = gi.config_schreiben(p, gi.block_bauen(PY, SRV))
        inhalt = open(p, encoding="utf-8").read()
        check("reports 'updated' from the second run on", zustand == "updated",
              zustand)
        check("exactly one block, no duplicates",
              inhalt.count("[mcp_servers.pc-screen-control]") == 1,
              "%d found" % inhalt.count("[mcp_servers.pc-screen-control]"))
        check("foreign servers still both there",
              "[mcp_servers.context7]" in inhalt
              and "[mcp_servers.other-thing]" in inhalt)
        sicherung = open(p + ".backup", encoding="utf-8").read()
        check("the backup was NOT overwritten",
              "pc-screen-control" not in sicherung)
        check("no leftover .tmp file", not os.path.exists(p + ".tmp"))

        try:
            import tomllib
            with open(p, "rb") as fh:
                d = tomllib.load(fh)
            check("the result is still valid TOML", True)
            check("our entry parses with the right command",
                  d["mcp_servers"]["pc-screen-control"]["command"] == PY)
            check("and the right argument",
                  d["mcp_servers"]["pc-screen-control"]["args"] == [SRV])
            check("the other servers parse too",
                  "context7" in d["mcp_servers"]
                  and "other-thing" in d["mcp_servers"])
        except ImportError:
            print("     (tomllib needs 3.11+; parse check skipped here)")

    print()
    print("5 - an updated path really replaces the old one")
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, ".codex", "config.toml")
        gi.config_schreiben(p, gi.block_bauen(PY, r"D:\alt\server.py"))
        gi.config_schreiben(p, gi.block_bauen(PY, r"D:\neu\server.py"))
        inhalt = open(p, encoding="utf-8").read()
        check("the new path is in", "neu" in inhalt)
        check("the old path is gone", "alt" not in inhalt)

    print()
    print("-" * 68)
    print("RESULT:", "OK" if not failures else "FAILED: " + ", ".join(failures))
    print("-" * 68)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
