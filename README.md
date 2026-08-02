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

Then ask your AI to run **`self_test`**. It answers in plain words, and every
failure carries its own fix.

<sub>Upgrading: remove the old version first and quit the app completely,
including its tray icon. · [Full guide](docs/GUIDE.md) ·
[Other clients](docs/OTHER_CLIENTS.md) · [If your antivirus objects](docs/ANTIVIRUS.md)</sub>

---

## What it does

Windows already publishes what is on screen as structured data — every button,
field and list, with its name and state. It is the same thing screen readers
use. This hands that to your AI instead of a picture.

|  | screenshot + coordinates | this |
|---|---|---|
| find a button | guess a pixel | ask for it by name |
| the window moved | coordinates are wrong | nothing changes |
| did it work? | take another screenshot | the reply carries before / after |
| your mouse | taken | usually untouched |

---

## Does it use *your* screen?

Worth being exact about, because the honest answer is "mostly not".

**30 of the 34 tools never touch your mouse or keyboard.** Reading the window
tree is pure data. Pressing a button, filling a field, setting a slider — all of
that goes through the accessibility interface and works on a window that is
behind others, or not visible at all.

**Four tools do take the hardware:** `click`, `drag`, `send_keys`, `hold_key`.
They are for surfaces that paint themselves and publish nothing — editing
canvases, timelines, games. While one runs, the screen edge pulses red, a
Windows notification says what is happening and for how long, and your input is
held so your keystrokes cannot land inside the work. It is handed back when the
block ends — window, focus and text cursor — and the reply says whether that
actually happened, measured.

**And there is a way out of your sight entirely.** `claim_window` moves a window
just past the edge of every monitor. It keeps running and stays fully operable
by name, but you cannot see it, and Windows will not let your mouse pointer
leave the monitors, so you cannot click it by accident either. Work on a parked
window **costs you nothing**: no pulse, no held input, no interruption. Park it
once and the AI works beside you instead of instead of you.

What this is **not**: a private virtual display. Windows does not let a normal
program create a second screen for an application. Parking off-monitor is the
closest thing that genuinely works — and it is real, not a trick.

*The tray icon's Pause / Stop / Watch stay clickable even while your input is
held; the taskbar is deliberately left out of the hold.*

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
| **`self_test`** | Checks everything and says what is wrong and what to do about it |
| **`claim_window`** `release_window` | Park a window out of your reach, and put it back to the pixel |
| **`set_guard`** | Who has priority while the AI works — `claude` or `me` |

---

## Reach, measured

From `tests/measure_desktop.py`, which ships here so you can contradict these
numbers on your own machine.

| | actionable nodes |
|---|---:|
| File Explorer | 220 |
| Chrome / Electron — VS Code, Slack, Discord, Teams, Notion | 207–398 |
| DaVinci Resolve, Project Manager | 53 |

Browsers and Electron build their tree only once something asks: a first look
reports 13 nodes, after waking it 207. Self-drawn surfaces publish nothing and
are reached with `capture` + `click` — you lose precision and proof, not access.

---

## Before you rely on it

- **Windows only, and there is no macOS version.** `docs/PORTING.md` maps the
  patterns onto the macOS Accessibility API, but that is a map and nobody has
  compiled a line of it. Treat macOS as **not available**, not as coming.
- **No network at all.** The server opens no socket — no update check, no
  telemetry. Two files here *do* use the network and neither ships: the updater
  you start by hand, and a workflow on GitHub's machines that verifies every
  release against its source. [SECURITY.md](.github/SECURITY.md)
- **Control names follow the window's language** — *Speichern*, not *Save*.
  About half of all elements also carry an `automation_id`, which does not
  translate; `find_elements` searches both and says which matched.
- **Your antivirus may object.** A program that reads other applications and
  moves the mouse looks structurally like spyware. No signature, no company
  here — but the whole server is one readable Python file.
  [docs/ANTIVIRUS.md](docs/ANTIVIRUS.md)
- **Administrator processes are invisible.** Windows blocks input across
  integrity levels by design.
- **No undo of its own.** Closing a window or sending a message is not something
  any tool takes back.
- **Early software, one person, spare time.** No support, no SLA.

---

## The rule this is built on

> **Measure before you claim. A function that does not report whether it worked
> will eventually stop working, and nobody will notice.**

Most of the code exists because of that sentence. Several defects here survived
for weeks while looking complete and doing nothing: a focus restore that Windows
had never once granted, input hooks installed on a thread that could not receive
them, a measurement written on every block and read by nobody. Every claim on
this page has a test behind it, and every number came from a measurement that
has been wrong before.

<sub>[Changelog](CHANGELOG.md) · [Security](.github/SECURITY.md) ·
[Contributing](.github/CONTRIBUTING.md) · [Other clients](docs/OTHER_CLIENTS.md)
· MIT © 2026 NATHAN Development</sub>

---

<sub>**Disclaimer.** This software controls your computer — buttons, typing,
closing windows, dragging, including in apps holding unsaved work. Provided
**as is**, no warranty ([LICENSE](LICENSE)). You are responsible for what you
automate; test on something you can afford to lose. Automating third-party
software may breach its terms.</sub>
