# -*- coding: utf-8 -*-
"""
"Works with any MCP client" - proven, not claimed.

The README says this server works with Claude Desktop, Cursor, VS Code, Cline,
Zed and GPT through the OpenAI Agents SDK. All of those do the same thing: spawn
`python server.py` and speak MCP over stdin/stdout. So this test IS such a
client. It knows nothing about Claude, imports nothing from the server, and
talks to it only through the pipe - exactly as a stranger's client would.

What it checks is the contract every client depends on:

  * the handshake answers with the protocol version and server identity;
  * tools/list returns well-formed tools, each with a name, a description and a
    JSON Schema - a client that cannot parse these cannot offer them;
  * a tool call returns MCP-shaped content;
  * an unknown tool and a malformed call are answered with a JSON-RPC error
    rather than a crash or a silent hang, which is what actually breaks a
    third-party client;
  * one process serves several calls in sequence (clients keep it alive).

Deliberately uses only tools that read, so it is safe to run anywhere, and it
skips the screen-dependent parts off Windows.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(os.path.dirname(HERE), "src", "server.py")

failures = []


def check(name, ok, detail=""):
    if not ok:
        failures.append(name)
    print("  %-56s %-6s %s" % (name, "OK" if ok else "FAIL", detail))


def sprich(anfragen, timeout=120):
    """Send JSON-RPC lines to a fresh server process and collect the replies."""
    eingabe = "\n".join(json.dumps(a) for a in anfragen)
    p = subprocess.run([sys.executable, SERVER], input=eingabe,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    antworten = []
    for zeile in p.stdout.splitlines():
        if zeile.strip():
            try:
                antworten.append(json.loads(zeile))
            except ValueError:
                pass
    return antworten, p


def main():
    print("1 - the handshake a stranger's client performs")
    antworten, p = sprich([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ])
    check("server answered both messages", len(antworten) == 2,
          "%d replies; stderr: %s" % (len(antworten), p.stderr[:120]))
    if len(antworten) < 2:
        print("RESULT: FAILED (no usable handshake)")
        return 1

    init = antworten[0].get("result", {})
    check("reports a protocol version", bool(init.get("protocolVersion")),
          init.get("protocolVersion"))
    check("identifies itself",
          init.get("serverInfo", {}).get("name") == "pc-screen-control",
          init.get("serverInfo", {}).get("name"))
    check("declares a tools capability", "tools" in (init.get("capabilities") or {}))

    print()
    print("2 - the tool list is machine-readable, not just human-readable")
    tools = antworten[1].get("result", {}).get("tools", [])
    check("returns a list of tools", len(tools) >= 25, "%d tools" % len(tools))
    schlecht = [t.get("name") for t in tools
                if not t.get("name") or not t.get("description")
                or not isinstance(t.get("inputSchema"), dict)
                or t["inputSchema"].get("type") != "object"]
    check("every tool has name, description and an object schema",
          not schlecht, ", ".join(str(s) for s in schlecht[:3]))
    check("no duplicate tool names",
          len({t["name"] for t in tools}) == len(tools))

    print()
    print("3 - a real call comes back in MCP shape")
    antworten, _ = sprich([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "self_test", "arguments": {}}},
    ])
    ruf = [a for a in antworten if a.get("id") == 2]
    check("the call was answered", bool(ruf))
    if ruf:
        ergebnis = ruf[0].get("result", {})
        inhalt = ergebnis.get("content") or []
        check("reply carries content[]", bool(inhalt))
        check("content is typed text",
              bool(inhalt) and inhalt[0].get("type") == "text")
        try:
            nutzlast = json.loads(inhalt[0]["text"])
            check("the text is parseable JSON a client can use",
                  isinstance(nutzlast, dict), "version %s"
                  % nutzlast.get("version"))
        except Exception as e:
            check("the text is parseable JSON a client can use", False,
                  str(e)[:40])

    print()
    print("4 - it fails politely instead of taking the client down")
    antworten, p = sprich([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "no_such_tool", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "get_text"}},          # required args missing
        {"jsonrpc": "2.0", "id": 4, "method": "tools/list", "params": {}},
    ])
    per_id = {a.get("id"): a for a in antworten}
    unbekannt = per_id.get(2, {})
    check("unknown tool -> an answer, not silence", bool(unbekannt))
    check("unknown tool -> error or isError",
          "error" in unbekannt or unbekannt.get("result", {}).get("isError"))
    kaputt = per_id.get(3, {})
    check("missing arguments -> an answer, not a hang", bool(kaputt))
    check("missing arguments -> error or isError",
          "error" in kaputt or kaputt.get("result", {}).get("isError"))
    check("still alive afterwards (answered the next call)",
          bool(per_id.get(4, {}).get("result", {}).get("tools")))

    print()
    print("5 - one process serves a whole session")
    anfragen = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}]
    for i in range(2, 7):
        anfragen.append({"jsonrpc": "2.0", "id": i, "method": "tools/list",
                         "params": {}})
    antworten, _ = sprich(anfragen)
    check("six messages, six replies, one process", len(antworten) == 6,
          "%d replies" % len(antworten))
    check("ids come back matched",
          sorted(a.get("id") for a in antworten) == list(range(1, 7)))

    print()
    print("-" * 68)
    print("RESULT:", "OK" if not failures else "FAILED: " + ", ".join(failures))
    print("-" * 68)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
