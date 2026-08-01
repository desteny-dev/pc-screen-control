# -*- coding: utf-8 -*-
"""
Run this server from GPT, with the OpenAI Agents SDK. A working example.

There is no separate build for GPT. This points at the SAME server.py the
Claude extension runs - the .mcpb is only Claude Desktop's installer format, and
inside it is this file. What differs is who starts the process: Claude Desktop
does it from the extension, and here your own code does it.

    pip install openai-agents
    set OPENAI_API_KEY=sk-...
    python scripts/gpt_example.py "list my open windows"

The server runs locally over a pipe, exactly as it does under Claude. Nothing is
hosted and nothing is exposed: GPT decides WHICH tool to call, your machine runs
it. The screen data goes to OpenAI in the same way anything you type into GPT
does - see the boundary section in SECURITY.md, which is true of every cloud
assistant and is not special to this server.
"""
import asyncio
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))


def server_pfad():
    """The installed copy first, then this checkout, then an unpacked .mcpb."""
    kandidaten = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""),
                     "pc-screen-control", "server.py"),
        os.path.join(HIER, "..", "src", "server.py"),
        os.path.join(HIER, "server.py"),
    ]
    for k in kandidaten:
        if k and os.path.isfile(k):
            return os.path.abspath(k)
    raise SystemExit(
        "Could not find server.py. Either install the extension, or unpack the "
        ".mcpb (it is a ZIP) and run this from beside the server.py inside it. "
        "scripts/print-config.py prints the path once it exists.")


async def main(auftrag):
    try:
        from agents import Agent, Runner
        from agents.mcp import MCPServerStdio
    except ImportError:
        raise SystemExit("Missing the SDK. Run:  pip install openai-agents")

    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("Set OPENAI_API_KEY first - this is the one part that "
                         "does need the network, and it is GPT's, not ours.")

    pfad = server_pfad()
    print("Starting the local server:", pfad)

    async with MCPServerStdio(
        name="pc-screen-control",
        params={"command": sys.executable, "args": [pfad]},
        client_session_timeout_seconds=120,
    ) as pc:
        werkzeuge = await pc.list_tools()
        print("Tools offered to GPT: %d" % len(werkzeuge))

        agent = Agent(
            name="Desktop assistant",
            instructions=(
                "You operate this Windows PC through the pc-screen-control "
                "tools. Start every task with describe_screen. Work down the "
                "cost ladder and stop at the first rung that works: read the "
                "tree, then operate controls by name, and only reach for click "
                "or send_keys when a tool has told you there is no cheaper "
                "way. Before a run of actions call set_guard block:'start', and "
                "call block:'end' the moment you no longer need the screen - "
                "the person is using this computer too."),
            mcp_servers=[pc],
        )
        ergebnis = await Runner.run(agent, auftrag)
        print()
        print(ergebnis.final_output)


if __name__ == "__main__":
    auftrag = " ".join(sys.argv[1:]) or "List my open windows and say which are readable."
    asyncio.run(main(auftrag))
