# Using it with other MCP clients (including GPT)

**One package. Same files for everyone. Still offline.**

This is a plain MCP server that talks over **stdio** — a local pipe between the
client and the server on the same machine. There is no separate build for Claude
and another for GPT: it is the *same* `server.py` and the *same* bundled
libraries. The only thing that differs per client is one small step that tells
the client where the server lives.

The one-click `.mcpb` is just Claude Desktop's installer format. Every other
client points at the exact same server directly.

---

## Step 1 — get the files (once)

**Fastest way — one command does both steps:**

```
python scripts/unpack-for-any-client.py pc-screen-control.mcpb C:\Tools\psc
```

It extracts the package and prints the exact config block with your real path
already in it. No network, nothing installed.

Or by hand, two ways — both leave you with a `server.py` that has its libraries
beside it:

- **From the release (offline, nothing to install).** The `.mcpb` is an ordinary
  ZIP. Rename it to `.zip` or open it with any archive tool and extract it to a
  folder, e.g. `C:\Tools\pc-screen-control\`. Inside you get `server.py`,
  `overlay.py` and a `lib/` folder with `uiautomation`, `comtypes` and `pillow`
  already in it. Nothing to install, no network.
- **From source.** Clone the repo and run `python src\server.py --install` once.
  That installs the two libraries into your own Python. Then point at
  `src\server.py`.

Either way you end up with a full path to a `server.py`. Keep it handy — every
client below just needs that path.

> Tip: run `python scripts\print-config.py` and it prints the ready-to-paste
> config below with your actual path already filled in.

---

## Step 2 — point your client at it

### Config-file clients — Claude Code, Cursor, VS Code, Cline, Continue, Zed, Windsurf

All of these read a JSON block. Add this to the client's MCP config (the menu is
usually *Settings → MCP* or an `mcp.json` the client tells you about):

```json
{
  "mcpServers": {
    "pc-screen-control": {
      "command": "python",
      "args": ["C:/Tools/pc-screen-control/server.py"]
    }
  }
}
```

Replace the path with yours. Use forward slashes, or doubled backslashes
(`C:\\Tools\\...`). If `python` is not on your PATH, put the full path to
`python.exe` in `command`.

### GPT — the OpenAI Agents SDK / Codex

OpenAI's **Agents SDK** runs local MCP servers the same way Claude does — it
launches the process and talks over stdio. In your Python agent:

```python
from agents import Agent, Runner
from agents.mcp import MCPServerStdio

async def main():
    async with MCPServerStdio(
        params={"command": "python",
                "args": ["C:/Tools/pc-screen-control/server.py"]}
    ) as pc:
        agent = Agent(
            name="Desktop assistant",
            instructions="Use the PC Screen Control tools to operate Windows. "
                         "Start every task with describe_screen.",
            mcp_servers=[pc],
        )
        result = await Runner.run(agent, "List my open windows.")
        print(result.final_output)
```

That is the "install" for GPT: a few lines of code, pointing at the same
`server.py`. Nothing is hosted, nothing is exposed.

**`scripts/gpt_example.py` is that, complete and runnable:**

```
pip install openai-agents
set OPENAI_API_KEY=sk-...
python scripts/gpt_example.py "list my open windows"
```

It finds the server itself, starts it locally, hands GPT the 34 tools, and
instructs it to work down the cost ladder and to bracket its work in blocks so
you keep your screen.

---

## What about the ChatGPT app itself?

**Deliberately not supported, and it should stay that way.** The consumer
ChatGPT app (Developer Mode "apps") only connects to **remote** MCP servers over
an HTTPS **URL** — it cannot launch a local one. To use this tool there you would
have to run your PC-control server as a public web endpoint and let a cloud
service reach into your machine through it. That throws away the entire point of
this project — the server that drives your mouse never touches the network.

So the rule is simple: **anything that runs the server locally (stdio) is
welcome and stays offline. Anything that needs it on a URL is out of scope by
design.** The OpenAI Agents SDK above is the offline way to use GPT with it.

---

## None of this adds a network connection

Every client on this page runs the server as a local process and speaks to it
over a pipe. The server has no network code (see `SECURITY.md` and
`tests/test_offline.py`), and the bundled `lib/` means it does not even reach out
to install anything. Adding a new *local* client changes none of that.
