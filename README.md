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

Needs Windows and [Python 3.9+](https://www.python.org/downloads/) — tick
**"Add python.exe to PATH"** during its setup. Then take the one download for
your AI. Same server inside both.

**Claude Desktop** — download **`pc-screen-control.mcpb`**, then
Settings → Extensions → Advanced → Install extension → restart Claude.

**ChatGPT desktop, Codex, Cursor, VS Code, Cline, Zed** — download
**`pc-screen-control-gpt.zip`**, extract it, double-click
**`INSTALL-FOR-GPT.bat`**, restart the app.

Then ask your AI to run **`self_test`**. It reports what works, and every
failure names its own fix.

<sub>Upgrading: remove the old version first and quit the app completely,
including its tray icon. · [Full guide](docs/GUIDE.md) ·
[Other clients](docs/OTHER_CLIENTS.md) · [If your antivirus objects](docs/ANTIVIRUS.md)</sub>

---

## What it does

A screenshot is a picture. An AI looking at one has to work out what the shapes
mean and then aim at a pixel.

Windows already publishes the same screen as **structured data** — every button,
field and list, by name, type and state. It is what screen readers read. This
hands your AI that instead of the picture.

And a button is not clicked at a coordinate. **It is asked to press itself:**
the application carries out its own action and reports what changed. Nothing is
aimed at, nothing is guessed, and the confirmation is in the reply rather than
in another screenshot.

|  | screenshot + coordinates | this |
|---|---|---|
| find a button | work out which shape it is, aim at a pixel | ask for it by name |
| press it | move the mouse there and click | tell the application to invoke it |
| the window moved | the coordinates are wrong | nothing changes — the name did not move |
| did it work? | take another screenshot and look | the reply carries the state before and after |
| your mouse | taken | untouched |

---

## Does it use your screen?

Mostly not.

**30 of the 34 tools never touch your mouse or keyboard.** Reading the window
tree is pure data. Pressing a button, filling a field, setting a slider go
through the accessibility interface and work on a window that is behind others,
or not visible at all.

**Four tools do take the hardware:** `click`, `drag`, `send_keys`, `hold_key`.
They are for surfaces that paint themselves and publish no controls: editing
canvases, timelines, games. While one runs, the screen edge pulses red, a
Windows notification states what is happening and for how long, and your input
is held so your keystrokes cannot land inside the work. Window, focus and text
cursor are restored when the block ends, and the reply reports whether that
succeeded.

**A claimed window is outside your view entirely.** `claim_window` moves a
window just past the edge of every monitor. It keeps running and stays fully
operable by name, but it is not visible and Windows will not let your pointer
leave the monitors, so you cannot click it by accident. Work on a parked window
takes no block at all: no pulse, no held input, no interruption.

This is **not** a private virtual display. Windows does not let an ordinary
program create a second screen for an application. Parking off-monitor is the
closest equivalent that works.

The tray icon's Pause, Stop and Watch stay clickable while your input is held;
the taskbar is excluded from the hold.

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
| **`self_test`** | Checks the installation and reports what is wrong and how to fix it |
| **`claim_window`** `release_window` | Park a window out of your reach, and put it back to the pixel |
| **`set_guard`** | Who has priority while the AI works — `claude` or `me` |

---

## Reach, measured

Measured with `tests/measure_desktop.py`, which ships here so the numbers can
be reproduced or contradicted on your own machine.

| | actionable nodes |
|---|---:|
| File Explorer | 220 |
| Chrome / Electron — VS Code, Slack, Discord, Teams, Notion | 207–398 |
| DaVinci Resolve, Project Manager | 53 |

Browsers and Electron build their tree only once something asks: a first look
reports 13 nodes, 207 after waking it. Self-drawn surfaces publish no controls
and are reached with `capture` and `click` instead.

---

## Before you rely on it

- **Windows only.** `docs/PORTING.md` maps the patterns onto the macOS
  Accessibility API, but none of it has been implemented. macOS is **not
  available**.
- **No network at all.** The server opens no socket — no update check, no
  telemetry. Two files here *do* use the network and neither ships: the updater
  you start by hand, and a workflow on GitHub's machines that verifies every
  release against its source. [SECURITY.md](.github/SECURITY.md)
- **Control names follow the window's language** — *Speichern*, not *Save*.
  About half of all elements also carry an `automation_id`, which does not
  translate; `find_elements` searches both and says which matched.
- **Your antivirus may object.** A program that reads other applications and
  moves the mouse is structurally similar to spyware. There is no code signing
  certificate here; the server is a single readable Python file instead.
  [docs/ANTIVIRUS.md](docs/ANTIVIRUS.md)
- **Administrator processes are invisible.** Windows blocks input across
  integrity levels by design.
- **No undo of its own.** Closing a window or sending a message is not something
  any tool takes back.
- **Maintained by one person.** No support contract, no SLA.

---

## Verification

Every claim on this page has a test behind it. 18 test files run in CI on
Python 3.9, 3.11 and 3.13, and each release is checked against its own source
automatically: the published packages are downloaded and compared byte for byte
with the code at their tag.

Run them yourself: `python -m pytest -q`, or any single file directly —
`python tests/test_offline.py`.

<sub>[Changelog](CHANGELOG.md) · [Security](.github/SECURITY.md) ·
[Contributing](.github/CONTRIBUTING.md) · [Other clients](docs/OTHER_CLIENTS.md)
· MIT © 2026 NATHAN Development</sub>

---

<sub>**Disclaimer.** This software controls your computer — buttons, typing,
closing windows, dragging, including in apps holding unsaved work. Provided
**as is**, no warranty ([LICENSE](LICENSE)). You are responsible for what you
automate; test on something you can afford to lose. Automating third-party
software may breach its terms.</sub>
