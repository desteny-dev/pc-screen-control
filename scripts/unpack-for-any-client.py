# -*- coding: utf-8 -*-
"""
Unpack the .mcpb so any MCP client can run it, and print the config.

The .mcpb is not a different build and not a different language. It is a ZIP
with a manifest, which is how Claude Desktop installs things. Every other client
- Cursor, VS Code, Cline, Zed, GPT through the OpenAI Agents SDK - wants the
same file inside it: server.py, started locally and spoken to over a pipe.

So this does the two boring steps for you: extract, then print the exact block
to paste. No network, nothing installed, nothing changed outside the folder you
name.

    python scripts/unpack-for-any-client.py pc-screen-control.mcpb C:\\Tools\\psc
"""
import json
import os
import sys
import zipfile


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    paket = os.path.abspath(sys.argv[1])
    ziel = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else \
        os.path.join(os.path.dirname(paket), "pc-screen-control")

    if not os.path.isfile(paket):
        print("Not found: %s" % paket)
        return 1
    if not zipfile.is_zipfile(paket):
        print("%s is not a ZIP. A real .mcpb is one - is this the right file?"
              % paket)
        return 1

    with zipfile.ZipFile(paket) as z:
        namen = z.namelist()
        if "server.py" not in namen:
            print("No server.py inside - this does not look like this package.")
            return 1
        os.makedirs(ziel, exist_ok=True)
        z.extractall(ziel)
        try:
            version = json.loads(z.read("manifest.json"))["version"]
        except Exception:
            version = "?"

    server = os.path.join(ziel, "server.py")
    lib = os.path.isdir(os.path.join(ziel, "lib"))
    forward = server.replace("\\", "/")

    print("=" * 70)
    print("Unpacked version %s to:" % version)
    print("  %s" % ziel)
    print("  libraries bundled alongside: %s" % ("yes" if lib else
                                                 "NO - install uiautomation and pillow yourself"))
    print("=" * 70)
    print()
    print("-- Cursor, VS Code, Cline, Continue, Zed: paste into the MCP config")
    print(json.dumps({"mcpServers": {"pc-screen-control": {
        "command": "python", "args": [forward]}}}, indent=2))
    print()
    print("-- GPT, with the OpenAI Agents SDK")
    print('    from agents.mcp import MCPServerStdio')
    print('    MCPServerStdio(params={"command": "python",')
    print('                           "args": ["%s"]})' % forward)
    print("    (scripts/gpt_example.py is a complete runnable version)")
    print()
    print("-- Claude Desktop does not need any of this: install the .mcpb itself.")
    print()
    print("If 'python' is not on your PATH, put the full path to python.exe in")
    print("'command'. Full walkthrough: docs/OTHER_CLIENTS.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
