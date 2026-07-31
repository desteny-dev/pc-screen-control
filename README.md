<p align="center">
  <img src="assets/banner.svg" alt="PC Screen Control" width="680">
</p>

<h3 align="center">A screenshot is a picture made for human eyes.<br>This hands your AI the screen as data instead.</h3>

<p align="center"><sub>An MCP server for Windows · one-click install for Claude Desktop · works with any MCP client</sub></p>

<p align="center">
  <a href="../../releases/latest"><img alt="Download" src="https://img.shields.io/badge/⬇%20Download%20for%20Windows-22d3ee?style=for-the-badge&labelColor=0f172a"></a>
  <a href="docs/GUIDE.md"><img alt="Guide" src="https://img.shields.io/badge/📖%205--minute%20guide-0f172a?style=for-the-badge"></a>
</p>

<p align="center">
  <img alt="MIT" src="https://img.shields.io/badge/license-MIT-0f172a?style=flat-square">
  <img alt="Windows" src="https://img.shields.io/badge/platform-Windows-0f172a?style=flat-square">
  <img alt="Python 3.9+" src="https://img.shields.io/badge/python-3.9%2B-0f172a?style=flat-square">
  <img alt="34 tools" src="https://img.shields.io/badge/tools-34-22d3ee?style=flat-square">
  <a href="../../actions/workflows/ci.yml"><img alt="CI" src="../../actions/workflows/ci.yml/badge.svg"></a>
</p>

---

## Install

This is a plain MCP server, so **any MCP client can use it** — Claude Desktop,
Claude Code, Cursor, VS Code, Cline, Zed, or **GPT through the OpenAI Agents
SDK**. It is one package, not one per client: the same `server.py` for all of
them, each running it locally and offline. The one-click `.mcpb` below is Claude
Desktop's bundle format; for everything else there is a small config —
see **[docs/OTHER_CLIENTS.md](docs/OTHER_CLIENTS.md)**.

Needs Windows and [Python 3.9+](https://www.python.org/downloads/) — tick **"Add
python.exe to PATH"** during its setup.

**1.** Download **[`pc-screen-control.mcpb`](../../releases/latest)**

**2.** In Claude: `Settings → Extensions → Advanced → Install extension…` and
pick the file

> **Do not double-click the file.** Windows has no handler for `.mcpb` and will
> ask you which program to open it with. There is no right answer to that.

**3.** Close Claude completely — tray icon included — and start it again

There is no fourth step and nothing to switch on. To check, ask Claude to run
`describe_screen`; you should get a list of your open windows.

<sub>**[Full guide →](docs/GUIDE.md)** · From source instead: download this
repository as a ZIP and run `scripts\INSTALL.bat` · Remove: *Settings →
Extensions*, or `scripts\UNINSTALL.bat`</sub>

---

## Why this is better than a screenshot

Ask an AI to click something and it normally photographs your screen, squints at
it, and guesses a coordinate — then has no way of knowing whether the click
landed.

Windows already publishes what is on screen as structured data: every button,
field and list with its name and its state. That is how screen readers work.
This server hands Claude the same thing.

```
with a screenshot:   "click at 847, 312"      guessing, and no way to check
with this:           invoke(ref of "Save")    by name, and it comes back proven
```

| | |
|---|---|
| **It presses the right thing** | Controls are found by name, not by pixel. Nothing drifts when a window moves or the resolution changes. |
| **It knows whether it worked** | Every action returns the element's state before and after. Success is shown, not assumed. |
| **Your mouse stays yours** | Most of it goes through the accessibility interface rather than the pointer, so you can keep working while it works. |

---

## The cost ladder

Start at the top, stop at the first rung that works.

| | | cost to you |
|---|---|---|
| **1** | `read_ui_tree` `find_elements` `read_text` `read_table` | nothing |
| **2** | `invoke` `set_text` `set_value` `toggle` `select` `window` | **your cursor is never touched** |
| **3** | `capture` | nothing, but tells you less |
| **4** | `click` `drag` `send_keys` | **takes your mouse or keyboard** |

Rungs 1–3 cover almost everything. A screenshot loop lives on rung 4 every time.

**`claim_window` gets out of your way for a long job.** It parks the window just
past every monitor's edge — still running, still operable by name, but you can't
see or click it, because Windows won't let the pointer leave the monitors.
*(Measured: monitors end at x=4920, window parks at x=5120, `SetCursorPos(5170)`
lands at 4919.)* `release_window` and the exit handler put it back to the pixel —
even after a crash, since the position is saved to disk before the window moves.

**It won't type into a window you moved to.** The foreground window *and the
focused control* are recorded after every call. If either moved before the next
blind keystroke or click, the move came from you — the tool refuses and names
what changed. `force: true` overrides.

**Order: freeze, look, act.** Input is held first, the screen gets 40 ms for the
last keystroke to land, then the target is verified. Checking before locking
leaves a gap a click slips through.

**No tool steps down a rung silently.** `invoke` on an unpressable control
refuses and hands you the exact `click(x, y)` — never a click behind your back.
Cheaper routes inside a tool come first (`close_window` asks before Alt+F4;
`menu` tries expand, then the menu key, then right-click), and any step-down is
named in the reply (`"how"`, `"took_input": true`).

**Rung 4 is the exception** — only where an app paints its own interface:
canvases, timelines, games.

**And it warns you first — on the screen, not in the chat.** The edge breathes
**red** and deep — your moment to finish typing — then snaps back and fades to
blue; that snap is when your input is held. A **Windows notification** says what
Claude is doing, and how long if it will take a while (`~3 min`), because when
you are working you are in another window, not reading a chat.

**A burst is one interruption, not ten.** Everything Claude does in one go is a
single held block; your window, focus, text cursor and mouse come back once, at
the end. **Pause**, **Stop** and **Watch the work** sit in a tray icon and work
even while your input is held. Escape is not an abort — a stray key can't cancel
a task. `set_guard priority:"me"` makes Claude wait for your go and refuse
rather than take over.

<p align="center">
  <img src="docs/img/edge-glow.png" alt="The screen edge while input is taken" width="560">
</p>

Measured live, ten windows open: `describe_screen` 3.4s, everything else
0.07–0.86s, 60 calls at 0.09s each. `tests/stress.py` reproduces it.

---

## What a session actually looks like

Unedited output from a real desktop.

```jsonc
describe_screen()
// 7 windows, none of them a screenshot:
//   Claude                 219 nodes   readable   "woken": true
//   tools – File Explorer  207 nodes   readable
//   Edge, 17 tabs          182 nodes   readable
//   Taskbar                 53 nodes   readable
```

`"woken": true` is the Chromium fix at work — that window measures 13 nodes on a
first shallow look and 219 once asked properly.

```jsonc
read_table({ window_handle: 2100558 })
// { "headers": ["Name", "Änderungsdatum", "Typ", "Größe"],
//   "rows": [["audit",     "21.07.2026 09:42", "Python File", "7 KB"],
//            ["build",     "21.07.2026 09:42", "Batchdatei",  "2 KB"],
//            ["build_log", "21.07.2026 09:51", "Textdokument","1 KB"]] }
```

```jsonc
find_elements({ window_handle: 2100558, query: "Aktualisieren" })
// { "ref": "2100558:2.0.1.3", "role": "ButtonControl",
//   "name": "\"tools\" aktualisieren (F5)",
//   "automation_id": "refreshButton", "matched_on": "name",
//   "note": "Matched on the display name, which is language-dependent.
//            Where an automation_id is shown, prefer it." }
```

That is a German Windows. `refreshButton` is the same on every machine on earth;
`"tools" aktualisieren (F5)` is not — and the tool says so rather than letting
you write something that breaks abroad.

---

## The 34 tools

| | |
|---|---|
| **`describe_screen`** | Every window, classified `readable` / `shallow` / `canvas-only`. Start here. |
| `list_windows` `read_ui_tree` `find_elements` | The control tree, searchable, each node with a `ref` |
| `element_from_point` `get_focus` `get_text` `read_text` | What is where, what has focus, what it says |
| **`read_table`** | A grid or details list as rows, columns and headers |
| **`capture`** | Image of the screen, a window, or **a single element** |
| `invoke` `toggle` `expand` `select` `set_text` | Operate controls — all return before/after |
| **`set_value`** | A slider, spinner or scroll position to an exact number |
| **`window`** | Move, resize, minimise, maximise — without the mouse |
| **`clipboard`** | Read or write it. One call instead of hundreds of keystrokes |
| **`menu`** | Open a context menu and read it — menus do not exist until opened |
| `click` `drag` `scroll` | Coordinate input, last resort for self-drawn surfaces |
| `send_keys` `hold_key` | Keyboard, for shortcuts |
| **`wait_for`** `wait` | Wait for a condition, not for the clock |
| **`batch`** | Several verified steps in one call |
| `launch_app` `close_window` `focus_window` | Processes and windows |
| **`self_test`** | Checks everything and says in plain words what is wrong and what to do |
| **`claim_window`** `release_window` | Park a window where your mouse cannot reach, and put it back to the pixel |
| **`set_guard`** | Who has priority while Claude uses the mouse — `claude` or `me` |

---

## What it can and cannot reach

Measured with `tests/measure_desktop.py`, which ships here so you can contradict
these numbers on your own machine.

| | actionable nodes | |
|---|---:|---|
| File Explorer | 220 | full control, file list as a real table |
| Chrome / Electron | 207–398 | full page content, after waking them |
| DaVinci Resolve (Project Manager) | 53 | buttons and checkboxes by name |

**Chromium needed a fix, not an excuse.** Browsers and Electron apps build their
accessibility tree only once something asks. A first shallow look reports 13
nodes for a Claude window; after waking it, 207. That covers VS Code, Slack,
Discord, Teams, Notion and every web app.

**Self-drawn surfaces cost more, they are not off limits.** Editing canvases,
timelines and games expose no controls — nothing can read what was never
published. `capture` shows them and `click` / `drag` operate them, in the same
server. You lose precision and proof, not access.

---

## Before you rely on it

- **Windows only.** `docs/PORTING.md` maps every pattern used here onto the
  macOS Accessibility API. That map is not an implementation.
- **Control names follow the window's language.** On a German Windows the save
  button is *Speichern*. About half of all elements also carry an
  `automation_id`, which does not translate; `find_elements` searches both and
  says which matched.
- **Your antivirus may object.** A program that reads other applications and
  moves the mouse is structurally indistinguishable from spyware. There is no
  signature and no company here — but the whole server is one readable Python
  file, which is a better basis for trust than a signature would be.
  [docs/ANTIVIRUS.md](docs/ANTIVIRUS.md) has the full explanation and how to
  make the warning stop without disabling your protection.
- **Administrator processes are invisible.** Windows blocks input across
  integrity levels by design.
- **No undo of its own.** `send_keys {Ctrl}z` reaches the application's undo.
  Closing a window or sending a message is not something any tool takes back.

---

## Design notes

**Actions prove themselves.** `ok: true` only means the call did not throw.
Every action re-reads the element and reports what changed — or says plainly
that nothing did.

**Tools refuse the expensive path.** `drag` on a slider points at `set_value`;
`send_keys` at a text field points at `set_text`. Both take `force: true`.

**Waiting on state, not on the clock.** Fixed sleeps are the main reason screen
automation is flaky.

---

## Repository layout

```
src/      the server — one readable Python file, plus the screen-edge overlay
tests/    run these yourself: setup logic, a desktop measurement, a stress test
docs/     the install guide, using it with other clients (GPT etc.), macOS map
scripts/  install from source, print a client config, check for updates
```

<details>
<summary>Other MCP clients — Claude Code, Cursor, VS Code, Cline, Zed, and GPT via the OpenAI Agents SDK</summary>

Same server, same files — only the pointer differs. The `.mcpb` is a ZIP:
unzip it and its libraries are already in `lib/` beside `server.py`, so it runs
with nothing to install. Point a config-file client at that path:

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

**GPT** runs it the same way through the OpenAI Agents SDK (`MCPServerStdio`,
pointing at the same `server.py`) — local, offline, no hosting. The ChatGPT
consumer app is deliberately not supported, because it only connects to remote
URL servers and this one never goes on the network.

Run `scripts\print-config.py` to print the block above with your real path
filled in. Full walkthrough, GPT snippet included: **[docs/OTHER_CLIENTS.md](docs/OTHER_CLIENTS.md)**.

</details>

---

## Disclaimer

**This software controls your computer** — buttons, typing, closing windows,
dragging, including in apps holding unsaved work.

**As is**, no warranty ([LICENSE](LICENSE)). You are responsible for what you
automate; test on something you can afford to lose. It collects no data and sends
none: none of the 34 tools makes an outbound connection, and the server installs
nothing at startup — its libraries ship in the package; version checks are a
separate program you run by hand. Automating third-party software may breach its
terms. Threat model: [SECURITY.md](.github/SECURITY.md).

Early software, one person, spare time — no support, no SLA, no maintenance
promise.

MIT — [LICENSE](LICENSE). © 2026 NATHAN Development.
