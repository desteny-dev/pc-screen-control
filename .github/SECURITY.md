# Security

This software controls your computer. That is its purpose and also its threat
model.

## What it can do

It runs with your user account's privileges. Anything you can do by clicking and
typing, it can do: press buttons, enter text, close windows, drag things, read
documents and web pages that are open on screen.

It is driven by an AI. Assume it will occasionally misidentify a control, and
that a web page or document it reads may contain text aimed at redirecting it.
Do not leave it unattended in front of anything irreversible.

### It installs low-level input hooks, and you should know exactly when

The input guard — the thing that pauses your typing while the pointer is being
used — works by installing `WH_KEYBOARD_LL` and `WH_MOUSE_LL` hooks. Those are
system-wide, and they are the same mechanism a keylogger uses. Saying so plainly
is more useful than hoping nobody notices, so:

- **They exist only while a takeover block holds your input** — installed when
  it opens, removed when it ends, not at startup and not between calls.
- **They live in `src/overlay.py`, a separate process** with no file access and
  no network code, joined to the server by one pipe carrying only `warn`,
  `lock`, `keepalive`, `release`, `wait_on`, `wait_off`, `off`, `quit`, and a
  `notify` line for the on-screen message.
- **Nothing is recorded.** The callbacks look at one field — whether Windows
  marked the event as injected — and return "swallow" or "pass on". No key value
  is stored, logged, counted or sent. The whole hook path is about forty lines.
- **Escape is not special.** A stray Esc can't cancel a task; while your input is
  held it is swallowed like any key. Pause and stop live in the tray icon. A
  watchdog releases the hooks if the server goes silent for ten seconds — a crash
  can never lock you out — and Windows removes them anyway if the process dies
  (measured 0.1s after killing the parent).
- **You can switch it all off** with `set_guard enabled:false`; then no hook is
  ever installed and actions run without pausing you.

Your antivirus may object to this, and that is a reasonable thing for it to do.
[docs/ANTIVIRUS.md](../docs/ANTIVIRUS.md) explains exactly why, how to verify
what the hooks do, and how to make the warning stop without disabling your
protection.

## What it cannot do

- **No network. At all.** The server that controls your PC makes no outbound
  connection of any kind — no update check, no telemetry, no background ping,
  no dependency download, nothing. This is not a policy you have to trust; it is
  a fact you can verify three ways, and `tests/test_offline.py` checks all three
  on every push:
    - it imports nothing that can reach the network — grep `src/server.py` for
      `socket`, `urllib`, `http`, `ssl` or `requests` and you will find none;
    - it installs nothing at run time — the two libraries it needs travel
      **inside the extension** in a `lib/` folder, put there when the package is
      built, so the very first start opens no connection and waits on no pip;
    - starting it and driving it opens zero sockets, watched by a tripwire in
      the test.

  Checking for a newer version is a **separate** program,
  `scripts/CHECK-FOR-UPDATES`, which a person runs by hand — the server neither
  offers nor triggers it, so there is no path by which the thing driving your
  mouse can reach the internet on its own. The updater, when *you* run it, asks
  GitHub's public release API, and downloads a new version only after you say
  yes and only after verifying its SHA-256 against the release notes.
- **`launch_app` is not a general shell.** It starts a named program or opens a
  file. A command carrying shell operators (`&`, `|`, `>` …), invoking a
  scripting host (`cmd`, `powershell`, `wscript` …), or opening a URL is
  refused unless you pass `confirm: true`. Running arbitrary commands is the
  main way an AI redirected by something it read on screen could do real harm,
  and this closes that door by default.
- **Password fields are not read back.** Windows marks password boxes, and their
  contents are replaced with a placeholder everywhere a value is returned —
  `describe_screen`, `read_ui_tree`, `find_elements`, `get_text`, `read_text`.
  The label ("Password") is shown; the secret never leaves the process.
- **No elevated processes.** Windows blocks input from a lower-integrity process
  to a higher one. Anything running as administrator is invisible to it.
- **No credentials.** It has no keychain or credential API. Treat logins as out
  of scope.
- **No keystroke logging.** The hooks described above decide swallow-or-pass and
  keep nothing. There is no buffer, no file, no counter of what you typed.
- **No persistence.** No service, no scheduled task, no startup entry, no shell
  extension. It runs only while your MCP client runs it.

## The boundary this cannot cross — and you should know it

The server is offline, but **it does not run alone.** It is driven by an AI
client — Claude Desktop, or another — and that client is very often a cloud
service. So the honest picture is:

> This tool reads your screen and hands that data to the AI client that asked
> for it. If that client is a cloud AI, **the client sends what it received to
> its provider**, exactly as it does with anything else you type into it. The
> local server never makes that connection — but the data can still leave your
> machine through the client above it.

Nothing here can change that; it is the nature of using a cloud assistant. What
this project controls is its own half: the part on your machine is offline,
auditable, and refuses to read passwords. Decide what you point it at with the
same care you would use for anything you paste into a cloud AI.

## What the installer touches

Four operations, all inside your own user profile, none needing administrator
rights:

| | |
|---|---|
| bundles | `uiautomation`, `comtypes` and `pillow` — shipped inside the extension, not fetched at install; the source `INSTALL.bat` installs them via pip instead |
| creates | `%LOCALAPPDATA%\pc-screen-control\` |
| modifies | your Claude config — one entry, existing entries preserved |
| backs up | each config before the first change, never overwriting that backup |

It writes via a temporary file and an atomic replace, then reads the result back
to confirm. No registry key, no system setting, no file association, nothing
outside your user profile. `tests/test_installer.py` covers this and you can run
it yourself.

To remove: `UNINSTALL.bat`. It takes out only its own entry.

## Reporting a problem

Open an issue. If you would rather not post it publicly, open an issue saying
only that and I will follow up.

Be realistic about what you are dealing with: a hobby project maintained by one
person. No security team, no response time, no bounty. If you need those, this
is not the right dependency — and that is a reasonable conclusion to reach.
