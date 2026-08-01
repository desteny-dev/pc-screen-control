# -*- coding: utf-8 -*-
"""
Register this server with GPT (ChatGPT desktop / Codex), and check that it works.

This is the GPT counterpart of installing the .mcpb in Claude. Claude reads a
packaged extension; GPT reads a line in a config file. Same server, same file on
disk, different way of being told about it.

    python scripts/install-for-gpt.py

What it does, and nothing more:
  1. finds server.py - the installed copy, this checkout, or an unpacked .mcpb;
  2. checks it actually answers before writing anything anywhere;
  3. backs up ~/.codex/config.toml, once, and never overwrites that backup;
  4. adds or updates one [mcp_servers.pc-screen-control] block, leaving every
     other line of the file exactly as it was;
  5. reads the file back and says what to do next.

No network. Nothing installed. Undo is one line: delete that block, or restore
the .backup file next to it.
"""
import json
import os
import shutil
import subprocess
import sys

NAME = "pc-screen-control"
HIER = os.path.dirname(os.path.abspath(__file__))


def sag(zeile=""):
    print(zeile)


def server_finden():
    """An explicit path wins over any guess - pass it as the first argument.
    Otherwise prefer a copy that has its libraries beside it, because that one
    runs with no further setup; a bare source checkout only works if the Python
    it will be started with already has uiautomation."""
    if len(sys.argv) > 1:
        p = os.path.abspath(sys.argv[1])
        if os.path.isdir(p):
            p = os.path.join(p, "server.py")
        if not os.path.isfile(p):
            sag("No server.py at: %s" % p)
            return None
        return p

    kandidaten = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), NAME, "server.py"),
        os.path.join(HIER, "server.py"),
        os.path.join(os.path.dirname(HIER), "server.py"),
        os.path.join(HIER, "..", "src", "server.py"),
    ]
    gefunden = [os.path.abspath(k) for k in kandidaten
                if k and os.path.isfile(k)]
    if not gefunden:
        return None
    mit_lib = [g for g in gefunden
               if os.path.isdir(os.path.join(os.path.dirname(g), "lib"))]
    return (mit_lib or gefunden)[0]


def python_finden():
    """The interpreter that will actually run it. sys.executable is the one
    running this script, which is the honest answer - but never the launcher
    stub, which cannot run anything."""
    exe = sys.executable or ""
    if exe and "WindowsApps" not in exe:
        return exe
    fuer = shutil.which("python") or shutil.which("python3")
    return fuer or exe


def server_pruefen(python, server):
    """Start it once and count the tools. Writing config for a server that does
    not answer is how someone spends an evening on the wrong problem."""
    anfrage = "\n".join([
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {}}),
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list",
                    "params": {}}),
    ])
    try:
        p = subprocess.run([python, server], input=anfrage, capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           timeout=180)
    except Exception as e:
        return None, "could not start it: %s" % e
    zeilen = []
    for z in p.stdout.splitlines():
        if z.strip():
            try:
                zeilen.append(json.loads(z))
            except ValueError:
                pass
    for m in zeilen:
        if m.get("id") == 2 and "result" in m:
            return len(m["result"].get("tools") or []), None
    return None, (p.stderr or "no usable reply").strip()[:200]


def toml_wert(s):
    """TOML basic string: backslashes and quotes escaped. Windows paths are
    full of backslashes, and getting this wrong writes a config that parses to
    a different path than the one on screen."""
    return '"%s"' % s.replace("\\", "\\\\").replace('"', '\\"')


def block_bauen(python, server):
    return "\n".join([
        "[mcp_servers.%s]" % NAME,
        "command = %s" % toml_wert(python),
        "args = [%s]" % toml_wert(server),
        "startup_timeout_sec = 30",
        "tool_timeout_sec = 120",
        "",
    ])


def config_schreiben(pfad, block):
    """Replace our block if it is there, append it if it is not, and touch
    nothing else. Returns 'added' or 'updated'."""
    kopf = "[mcp_servers.%s]" % NAME
    alt = ""
    if os.path.isfile(pfad):
        with open(pfad, encoding="utf-8") as fh:
            alt = fh.read()

    if kopf in alt:
        zeilen = alt.splitlines(True)
        neu, drin = [], False
        for z in zeilen:
            if z.strip() == kopf:
                drin = True
                neu.append(block)
                continue
            if drin:
                # our block ends at the next table header
                if z.lstrip().startswith("["):
                    drin = False
                    neu.append(z)
                continue
            neu.append(z)
        inhalt = "".join(neu)
        zustand = "updated"
    else:
        trenner = "" if (not alt or alt.endswith("\n\n")) else \
            ("\n" if alt.endswith("\n") else "\n\n")
        inhalt = alt + trenner + block
        zustand = "added"

    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    if alt and not os.path.exists(pfad + ".backup"):
        shutil.copyfile(pfad, pfad + ".backup")
    tmp = pfad + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(inhalt)
    os.replace(tmp, pfad)
    return zustand


def main():
    sag("=" * 70)
    sag("PC Screen Control - register with GPT (ChatGPT desktop / Codex)")
    sag("=" * 70)

    server = server_finden()
    if not server:
        sag("Could not find server.py.")
        sag("Unpack the .mcpb first (it is a ZIP):")
        sag("  python scripts/unpack-for-any-client.py pc-screen-control.mcpb "
            "C:\\Tools\\psc")
        sag("then run this again from beside it.")
        return 1
    python = python_finden()
    sag("server:  %s" % server)
    sag("python:  %s" % python)
    if not os.path.isdir(os.path.join(os.path.dirname(server), "lib")):
        sag("note:    no lib/ beside it - this is a source checkout, so "
            "uiautomation and pillow must be installed in that Python.")

    sag()
    sag("Checking it answers before writing anything...")
    anzahl, fehler = server_pruefen(python, server)
    if anzahl is None:
        sag("  FAILED: %s" % fehler)
        sag("  Nothing was written. Run 'python %s' by hand to see why."
            % server)
        return 1
    sag("  OK - %d tools" % anzahl)

    pfad = os.path.join(os.path.expanduser("~"), ".codex", "config.toml")
    zustand = config_schreiben(pfad, block_bauen(python, server))
    sag()
    sag("%s [mcp_servers.%s] in:" % (zustand, NAME))
    sag("  %s" % pfad)
    if os.path.exists(pfad + ".backup"):
        sag("  (previous version kept as config.toml.backup)")

    with open(pfad, encoding="utf-8") as fh:
        zurueck = fh.read()
    if ("[mcp_servers.%s]" % NAME) not in zurueck:
        sag("  ...but reading it back does not show the block. Check the file.")
        return 1

    sag()
    sag("-" * 70)
    sag("Now restart ChatGPT / Codex, then ask it:")
    sag('  "Use describe_screen and tell me which windows are open."')
    sag()
    sag("To undo: delete that block from the file above, or restore the")
    sag("backup next to it. Nothing else on your machine was touched.")
    sag("-" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
