# Changelog

## 1.3.0

### Keystrokes can no longer land in the wrong window

Reported from real use, and the sequence is worth writing down because every
single step in it was correct.

A terminal on one screen, the person's own chat window on the other. The
assistant was told to drive the terminal. It brought that window forward, then
spent a few seconds working out what to type. The block went idle, **the guard
did exactly what it is built to do and handed the screen back** — restoring the
person's window, on the other screen, where they were mid-sentence. Then the
assistant sent its keystrokes, and a command meant for a terminal was typed into
their chat.

Nothing malfunctioned. The takeover check asks *"has anything moved since the
last call"*, and nothing had: the restore was ours, so the baseline agreed with
the screen. **The question nobody was asking is "is this the window we said we
were working in".**

So there are two checks now, with different jobs:

| | asks |
|---|---|
| the existing one | did the screen move under us — did the *user* click somewhere |
| the new one | is the foreground still the window we *declared* |

The window the assistant last acted in is remembered — taken from the call
itself, so no tool can forget to record it — and blind keystrokes or coordinate
clicks are refused when something else is in front. The refusal names both
windows, explains that the block probably ended while it was thinking, and says
to call `focus_window` again rather than force it.

**This is enforced by the extension, not by instructions.** It holds in any
chat, with any client, whether or not anyone thought to ask for it.
`tests/test_wrong_window.py` replays the reported sequence step by step, and
also checks the cases where it must *not* fire — no declared target, target
matches, target re-focused — because a guard that refuses correct work gets
switched off.

## 1.2.2

**A second download, so GPT is not the harder path.** Claude got one file and a
double-click; everyone else got a ZIP and an explanation. Now there are two
packages with the same server inside:

| | |
|---|---|
| `pc-screen-control.mcpb` | Claude Desktop — install it in Settings → Extensions |
| `pc-screen-control-gpt.zip` | ChatGPT desktop, Codex, Cursor, VS Code, Cline, Zed — extract, double-click `INSTALL-FOR-GPT.bat` |

`.mcpb` is Claude Desktop's installer format: a ZIP with a manifest it knows how
to read. Nothing else reads it, so everyone else gets the same contents as a
plain folder with the setup script beside it. Same `server.py`, same bundled
libraries, same 34 tools.

**The ChatGPT desktop app runs local servers, and the docs used to say it
couldn't.** That was true of the browser plugin workflow, which registers a
server by URL — still out of scope, because this one never goes on the network.
It was never true of the desktop app, which reads `~/.codex/config.toml` and
picks the transport from the key it finds: `command` for a local process,
`url` for a hosted one. `scripts/install-for-gpt.py` writes that entry, after
starting the server once and counting its tools, and leaves every other line of
that file alone. `tests/test_gpt_install.py` holds that line in CI.

**Two more faults, both found by using it.** `batch` did not refresh the
takeover baseline between steps, so a click in step one made step two look like
the *user* had moved the focus — a false refusal whose only workaround is
`force: true`, which switches off the check that catches typing into the wrong
window for real. And `send_keys` without a ref now reports the window and
control that actually received the keystrokes, instead of advising the caller to
go and check afterwards.

## 1.2.1

### The guard had a hole, and it was the wrong shape

The guard protected the tools that take the mouse or keyboard. Operating a
control through the accessibility interface takes neither, so `invoke` was
treated as harmless — and it is not. **The application on the other end raises
itself when one of its buttons is pressed.** A button was pressed in a chat
window, the window came to the front, the caret went with it, and the person
typing a report at that moment sent their next sentence into someone else's
message box. No pulse, no hold, nothing put back.

The boundary was wrong. It is not *"does this use the pointer"* — it is
**"can this change what is on screen"**. Reading cannot; everything else can.

So the guard moved to the one place every call passes through, and the server
now keeps a list of **readers**. Anything not on it is guarded: `invoke`,
`set_text`, `toggle`, `select`, `expand`, `set_value`, `menu`, `window`,
`close_window`, `focus_window`, `launch_app`, `scroll`, `batch`,
`claim_window`, `release_window` — as well as the four that always were. **A
tool added later is protected by default**, and forgetting to think about it
fails safe instead of quietly repeating this. `tests/test_guard_coverage.py`
walks the real tool list and holds that line in CI.

**Refs survive the page moving under them.** A ref is a path of child indexes:
exact, and wrong the moment something is inserted above the target — which on a
web page happens between two calls. It is now looked up again by what it *was*
(automation id, type, name, class), so a field can still be filled by name
instead of falling back to the mouse. Measured on a GitHub form, where a ref
read one call earlier was already stale.

**`launch_app` is guarded too.** Starting a program puts a window in front — a
console flashing up for two seconds is enough to take the caret out of what you
were typing, so those keystrokes go nowhere and your text ends up with a hole in
it. It joins the handover block now: you get the pulse and the notification
before the window appears, your input is held instead of lost, and your place
comes back. Same fault `focus_window` had, same fix.

**The guard survives a machine with no desktop.** `_leerlauf_ms` called `windll`
and raised where there is none, which — now that the guard fronts more tools —
took down calls that have nothing to do with the screen. It answers "nobody is
there" instead, the safe reading: work proceeds without a warning nobody would
see. Four tests that used to skip for want of a desktop now run.

**Says why a sequence belongs in one call.** `batch` and the manifest now name
the real cost: not round trips, but *your* time. Between two calls the assistant
is thinking, and while it thinks the screen is still held — five predictable
steps taken one at a time can occupy you for a minute over ten seconds of work.
Decide the sequence first, run it in one go, and hand the screen back *before*
working out anything unexpected, not after.

## 1.2.0

The input guard, rebuilt around one idea: **a burst of actions is one takeover,
not ten flickers** — and it never takes the screen without telling you on it.

**One session, not per-action.** The first action that needs the screen opens a
held block; everything after joins it; the screen comes back once, when the
assistant ends the block or after a short idle. `focus_window` now goes through
this too — the old bug where it stole the foreground in silence, with no warning
and no restore, is gone.

**Warned on screen, never in chat.** When you are active, the edge breathes
**red and deeper**, then fades red → blue as it settles — plus a **Windows
notification** that reaches you even in another window. A long block announces
its length (`~3 min`) instead of a silent freeze.

**Controls in the tray.** Right-click the tray icon for **Pause** and **Stop**;
they reach the server through a local `mode.json`, so they work even while your
input is held. **Escape no longer aborts** — a stray Esc can't cancel a task.

**Hands the screen back for logins.** `set_guard await_user:"…"` gives you the
screen, asks on screen for what only you can do (log in, type a password), and
waits — doing other background work meanwhile.

**It no longer mistakes its own input for yours.** `GetLastInputInfo` counts
injected input too — this server's own clicks, its keystrokes, and the Alt tap
every focus restore performs. Read back naively, that says "the user is typing"
while nobody is at the desk, and answers with a red pulse and a notification for
its own activity. Injections are timestamped now; only input **more recent than
ours** counts as yours.

**`priority:"me"` refuses instead of grabbing.** It waits for your go, and if
none comes within 45s it fails with a reason — the old path waited two minutes
and then took the screen anyway, which is the one thing that setting exists to
prevent.

**Watch mode.** The tray's *Watch the work* leaves the work window in front
instead of restoring yours after every block; *Work hidden* goes back to normal.

`tests/test_session.py` proves the state machine headless — twelve sections: one
warn per burst, restore once, focus_window guarded, notification fired, own
input not misread, announced blocks not cut short, priority 'me' refusing,
pause/stop/watch honoured through `mode.json`.

## 1.1.0

A security pass. Nothing here adds a feature; it removes the ways the thing
that drives your mouse could reach past the screen it is meant to stay on. Each
claim below has a test next to it, because a security claim you cannot check is
just a hope.

### The core is offline — now literally, not almost

1.0.0 said "no telemetry" and meant it, but two threads still reached the
network: the update check, and a first-run `pip install` for the two libraries.
Both are gone from the running server.

- **The update check left the server.** `check_for_update` is no longer a tool.
  Checking for a new version is a separate program, `scripts/check-for-updates.py`,
  that a person runs by hand — it asks GitHub, and downloads a build only after
  you say yes and only after its SHA-256 matches the release notes. The server
  neither offers nor triggers it. Tool count drops 35 → **34**.
- **The libraries travel inside the package.** `uiautomation`, `comtypes` and
  `pillow` are now bundled in a `lib/` folder built into the extension, so the
  first start installs nothing and waits on no download. A source checkout still
  installs them once via `INSTALL.bat`; the packaged extension never does.
- **`tests/test_offline.py` proves all of it** on every push: no networking
  imports, no install at run time, and a socket tripwire that stays at zero
  while the server starts and runs.

### Two doors closed by default

- **`launch_app` is no longer a general shell.** A command carrying shell
  operators (`&`, `|`, `>`), invoking a scripting host (`cmd`, `powershell`,
  `wscript`), or opening a URL is refused unless you pass `confirm: true`. This
  is the main way an AI redirected by something it read on screen could do real
  harm, and it is shut by default.
- **Password fields are read back as a placeholder.** Windows marks password
  boxes; their contents are now replaced with `••• (password field - contents
  hidden)` everywhere a value is returned — `describe_screen`, `read_ui_tree`,
  `find_elements`, `get_text`, `read_text`. The label stays; the secret never
  leaves the process.

### One thing this cannot fix, said plainly

The local server is offline, but it does not run alone: the AI client above it
is often a cloud service, and that client sends what it reads to its provider.
`SECURITY.md` now states this boundary directly instead of leaving it implied —
the part on your machine is offline and auditable; what you point it at still
leaves through the client, exactly as anything you paste into a cloud assistant
does.

### One package, every local client — GPT included

Making the server self-contained had a second effect: the `.mcpb` is now just a
ZIP that any local MCP client can use. Unzip it and point the client at the
`server.py` inside — the libraries are in `lib/` beside it, so it runs offline
with nothing to install. New `docs/OTHER_CLIENTS.md` spells this out for Cursor,
VS Code, Cline, Zed and **GPT via the OpenAI Agents SDK**, and `scripts/print-config.py`
prints the config block with your real path filled in. The ChatGPT consumer app
is deliberately out of scope: it only connects to a remote URL, and this server
never goes on the network. There is no separate download per client — it is the
same server for all of them.

## 1.0.0

First public release. The version numbers before this one were private
iterations and are not published; 1.0.0 is where the 35 tool names become a
promise — if one of them changes meaning, the major number changes with it.

### What it does

Windows already publishes what is on screen as structured data — every button,
field and list with its name and its state, the same thing screen readers read.
This hands that to Claude instead of a screenshot, so a control is pressed by
name rather than by guessed coordinate, and every action reports the element's
state before and after rather than assuming it worked.

**35 tools**, arranged as a cost ladder: read the tree, operate controls, read
tables as rows and columns, set sliders to an exact number, move and resize
windows, read and write the clipboard, open menus. Coordinate input and screen
capture remain for surfaces that genuinely paint themselves — editing canvases,
video timelines, games. Every tool states its price and `describe_screen` names
the order to work through, stopping at the first rung that works.

**The input guard.** When Claude needs the mouse or keyboard while you are
actually using the computer, the screen edge breathes slowly inward for ~0.9s —
time to finish the word — then snaps back in ~0.18s. The snap is the instant
your input is held: your keystrokes and clicks pause, Claude's own pass through,
and afterwards your window, focus and text caret are restored. Escape is never
swallowed. `set_guard priority:"me"` inverts it — Claude waits for a click on a
card instead of ever taking over.

**check_for_update.** The only tool that reaches the network, and only when it
is called. The monthly reminder is gated by a local timestamp, so it stays
offline unless a month has passed. No background check, no telemetry.

### What measurement changed

Every number below came from a test that ships in `tests/`, so it can be
contradicted on your own machine.

- **`describe_screen` 11.4s → 3.4s.** Two causes. Chromium's wake-up ran on
  every call although Chromium keeps its tree once built, so the result is now
  remembered per window and marked `cached` when served from memory. And the
  probe built a *full description* of every node it counted — twelve COM calls
  per node — for a number that only has to land in one of three buckets.
  Counting is now just the walk. The second fix was the larger half, and the
  twelve-pattern lookup it removed had itself been a fix from earlier, which
  made the most-used tool three times slower without anyone noticing until
  something measured it.
- **Capability detection was silently blind.** `GetInvokePattern()` and its
  siblings live on the *subclasses* of the uiautomation package, so calling
  them on a generic element raised an error that the safety wrapper swallowed —
  every element looked as though it supported nothing. `GetPattern(PatternId.X)`
  lives on the base class and answers for any element.
- **Chromium looked unreadable and was not.** A Claude window measures 13 nodes
  on a first shallow look and 207 once asked properly. The probe was wrong, not
  the browser. That covers VS Code, Slack, Discord, Teams, Notion and every web
  app.
- **Empty table cells printed their column heading.** A folder had the size
  "Größe". Once a cell has a value pattern its answer is final, empty included.
- **`element_from_point` reported success for coordinates on no screen at all.**
  Windows answers `ControlFromPoint(-99999, -99999)` with the desktop root. It
  now checks against the virtual desktop and says where that actually is.
- **`set_value` claimed success on an immovable scroll bar.** It now compares
  against the value it read first and says plainly that the control did not
  move.
- **`capture` clamped negative coordinates**, which is the wrong region on a
  monitor placed left of or above the primary one.
- **Every umlaut sent to a tool was destroyed.** MCP speaks UTF-8; a Windows
  pipe defaults to the machine's ANSI code page, measured here as `cp1252`.
  Output was pinned to UTF-8 and input was not, so results looked correct while
  arguments were already mojibake. All three streams are pinned now — this is
  easy to miss precisely because the visible half works.
- **A broken helper was pushing everything onto the mouse.** `_ref_for` turns an
  element into a ref you can act on. Its stop condition required the parent to
  have no window handle, which is true exactly one level below the desktop root
  — and the root carries a handle, so the branch never ran and it returned
  nothing for practically every element. The damage was entirely indirect:
  `element_from_point` and `get_focus` could describe a control and hand back no
  way to operate it, so the only route left was the pointer, and the input guard
  could not save the focus it promises to restore. Three tools, one line.
- **`invoke` reached for the real mouse when no pattern answered**, outside the
  edge glow and outside the input guard — in a tool documented as never touching
  your cursor. It now refuses, names what the element does offer, and prints the
  exact `click(x, y)` call if you decide the pointer is worth it.
- **`close_window` always sent Alt+F4**, which needs to steal your foreground
  first. `WindowPattern.Close()` asks the window to close itself and costs
  nothing; the keyboard is now the fallback and says when it was used.
- **`menu` went straight to the right button.** It now tries the expand pattern,
  then the context-menu key, then the pointer.

- **Blind keystrokes went wherever focus had drifted to.** This one was caught
  by watching it happen: an assistant read a form, the person clicked into a
  chat window, and the next `Enter` landed in the chat. The tool had always
  returned a note saying "confirm this landed where you intended" — read after
  the damage, so not a safeguard at all. Telling "the user moved" from "we
  moved" appears to need the source of an event, which Windows will not give:
  `GetLastInputInfo` counts injected input too. The question turns out not to
  need it. The foreground window is recorded after **every** tool call, so
  anything this server did is already in the baseline; a change appearing
  between calls came from outside. `send_keys` without a target, and `click`,
  `drag` and `hold_key` on coordinates, now refuse in that case and name both
  windows. `force: true` overrides.
- **Watching the window alone missed it, twice.** The second time, the window
  never changed — the click landed on a different control *inside* the window
  that was already in front, and a keystroke follows the keyboard focus, not the
  window. The fingerprint is now the focused control as well: its type, its
  automation id and its name. Deliberately not its rectangle, since controls
  move when a window is resized or a list scrolls, and refusing over that would
  be noise rather than safety.
- **And the check ran before the lock, which is a race.** Verifying the target
  and *then* freezing input leaves a gap, and a click lands in a millisecond. A
  check that only works sometimes is worse than no check, because it gets
  trusted. Input is now held first, the screen is given 40 ms for the last
  keystroke to finish travelling through the message queue, and only then is the
  target read — so what the check sees is what the action will hit. If it moved,
  the lock is released again and nothing is typed. The rubber-band pulse is
  deliberately a window in which you may still type, which makes this ordering
  necessary rather than merely tidy: whatever you did with that second is
  exactly what has to be seen, and it can only be seen once the lock has closed.

Every tool that steps down a rung now reports `"how"` and `"took_input"` in its
reply, so a fallback is never silent.

### Trust, sharpened after review

An outside review (GitHub Copilot) prompted four changes. It was right on each.

- **The update download is now verified against its published hash.**
  `check_for_update` reads the SHA-256 from the release notes, hashes what it
  downloaded, and only writes the file if they match. On a mismatch it refuses,
  reports both hashes, and saves nothing — a corrupted or tampered download can
  no longer reach your Downloads folder wearing the right name. A published hash
  that nothing checks against is not protection; this closes that gap.
- **Swallowed errors are no longer invisible.** `_safe()` still swallows — one
  control that refuses to answer must not abort a walk over two hundred of them
  — but it now records the type, message and line of every exception it catches,
  bounded to the last hundred, and `self_test` hands the recent ones back. Three
  real bugs survived for weeks here precisely because a swallowed error was also
  a silent one.
- **`ruff` runs in CI** on every push, and the whole codebase passes it clean.
- **An antivirus FAQ**, `docs/ANTIVIRUS.md`: why a scanner flags this, exactly
  what the input hooks do and do not do, how to verify that yourself, and how to
  make the warning stop — including turning the guard off entirely — without
  ever being told to disable your protection.

### Sharper edges for the person installing it

- **`self_test`** — ten checks in plain language, each failure carrying its fix,
  now also reporting which Python it runs under (so a Store-stub install shows at
  a glance) and any errors swallowed since startup.
- **Irreversible actions ask twice.** `close_window` refuses on the first call
  and describes what would be lost; a second call with `confirm:true` proceeds.
  The description reaches the person before the loss, not after.
- **The first run explains its own delay** in the first reply, instead of half a
  minute of apparent silence while it installs what it needs.
- **`describe_screen` reports what it spent** when a call runs long, and points a
  caller who already knows their window straight at the cheaper `read_ui_tree`.
- **Claimed windows are marked** wherever windows are listed.

### Approaches rejected, and why

- **`BlockInput` for the guard.** Needs administrator rights. A tool strangers
  install should not demand them.
- **Windows toast notifications for the "waiting" prompt.** Could not carry an
  actionable button without a registered application identity.
- **One full-screen window for the edge glow.** ~36 MB per frame; animation
  impossible. Four thin edge bars measure 0.6 ms per frame, which is what makes
  the pulse possible.
- **Window messages (`PostMessage`) to click a parked window without the
  pointer.** This would have let `claim_window` operate its window while it sits
  out of reach of the mouse — a "rung 3.5" between patterns and real clicks.
  Measured against every framework family open on a real desktop: Win32, Qt
  (DaVinci Resolve) and Chromium (Edge, the Claude window). None of them gives
  its buttons and fields their own window handle — modern toolkits paint
  everything into one window, so there is nothing for `PostMessage` to address.
  It would have failed on exactly the applications it was wanted for. Rejected
  on the measurement, not built on the hope.

### Known limits

Windows only — `docs/PORTING.md` maps every pattern used here onto the macOS
Accessibility API, but a map is not an implementation. Administrator processes
are invisible by Windows design. Control names follow the window's language;
`find_elements` also searches `automation_id`, which does not translate, and
says which one matched.
