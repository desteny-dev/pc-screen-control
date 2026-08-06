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

**Fastest way: download `pc-screen-control-setup.zip` and extract it.** That is
already `server.py` with its `lib/` beside it — nothing to unpack out of another
format, nothing to install. `INSTALL.bat` in that folder does Step 2 for the
clients that read a config file directly.

If you only have the `.mcpb`, one command does both steps:

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

### ChatGPT desktop / Codex — nothing extra to run

The desktop app runs **local stdio servers**; it does not need a URL and nothing
gets hosted. It reads `~/.codex/config.toml`, and **`INSTALL.bat` already writes
that entry** — the same run that registers Claude. There is no second script and
no GPT-specific download any more.

> This used to be `scripts/install-for-gpt.py`, in a package called
> `pc-screen-control-gpt.zip`. The name was the problem: that package is also the
> only route that still works when Claude refuses to install the extension, and
> every Claude user read "for GPT" and closed it again. One installer now writes
> every client, and the package is called `-setup.zip`.

By hand instead:

```
python server.py --install
```

It backs the config up, adds or updates exactly one
`[mcp_servers.pc-screen-control]` block, reads the file back before calling it
a success, and leaves every other line — your other MCP servers, your model
settings, your keys — untouched. Then restart ChatGPT and ask it:
*"Use describe_screen and tell me which windows are open."*

If `~/.codex` does not exist, it says `skipped` and creates nothing. Start Codex
once so it makes that folder, then run the installer again.

By hand instead: **Settings → MCP servers → Add server → STDIO**, name it, and
give it the full path to `python.exe` and to `server.py`.

Undo is one line: delete that block, or restore `config.toml.backup` beside it.

### GPT in your own code — the OpenAI Agents SDK / Codex

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

## The one route that is out of scope

**ChatGPT in a browser**, via the web plugin workflow, registers an MCP server by
**URL**. That would mean running your PC-control server as a reachable web
endpoint so a cloud service can reach into your machine — which throws away the
whole point, so it is not supported and will not be.

The rule: **anything that starts the server locally over stdio is welcome and
stays offline; anything that needs it on a URL is out of scope by design.** The
ChatGPT *desktop app* is the local kind, which is why it works.

---

## None of this adds a network connection

Every client on this page runs the server as a local process and speaks to it
over a pipe. The server has no network code (see `SECURITY.md` and
`tests/test_offline.py`), and the bundled `lib/` means it does not even reach out
to install anything. Adding a new *local* client changes none of that.
