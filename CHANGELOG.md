# Changelog

## 1.6.3

**The maker has a different name.** NATHAN Development is now Desteny
Development, under the same roof as the rest of the work rather than beside it.
Nothing in the program changed: same 34 tools, same behaviour, same tests.

This is a release and not a quiet edit for one reason. The name sits inside the
package, in `manifest.json` - so the moment it changed, the code and the
published 1.6.2 disagreed while both called themselves 1.6.2. Two different
files with the same version number is worse than any naming question: after
that, nobody can say which one they have.

The repository keeps its name. `pc-screen-control` is the product, not the
maker. Commits made before the rename still carry the old one; the brand was
renamed, the past was not.


## 1.6.2

**The warning was being drawn in the wrong place, and nothing could have said
so.** On a two-monitor desktop - 3840x2160 and 1080x1920 - the glow was one
frame of 1280x720 in the top-left corner of the big screen. Measured, not
guessed: the overlay's own bar windows were at that size.

1280x720 is not a scaling artefact. It is what Windows hands back to a process
that asks about the desktop before the desktop is ready. The overlay asked
exactly once, in its first line, and kept the answer for the rest of the
session - and it is started with the first block after the app launches, which
on a cold boot is precisely when the answer is not ready yet.

The same reading is now taken again whenever the glow is about to be shown, and
once a second for as long as it is up. That is a few microseconds, and it
covers every way screens can change without having to name them: waking from
sleep, a monitor switched on, resolution or scaling changed, a cable moved, a
remote session - and the case above, where nothing changed at all and the first
answer was simply wrong. Bars are created and retired to match; the work
happens on the message-loop thread, because creating a window from the reader
thread is the same mistake that hid the input hold for two releases.

**And it is no longer only the eye that can catch this.** The overlay reports
the rectangles it draws on, and `self_test` holds them against the screens
Windows describes right now. A glow in the wrong place is a line of text, not a
thing you have to happen to notice.

This is the third time the same shape of defect has come back: *something is
measured once, and nothing checks whether it is still true.* The first two were
about a call whose failure was swallowed. This one is about an answer that was
correct for nobody and was never asked again.


## 1.6.1

### Three more of the same, found by looking rather than by waiting

1.6.0 fixed a `SetFocus` whose failure was swallowed. That is a *pattern*, not
an incident, so the rest of the file was audited for it: every call whose
result is discarded and whose success the next line assumes.

**`focus_window` reported `ok: True` without ever asking whether the window
came forward.** It used a bare `el.SetActive()` — which Windows refuses
silently for a background process, exactly like `SetForegroundWindow`. The
robust version, with the thread attachment and the foreground-lock timeout,
already existed in this file as `_vordergrund_setzen` — but only the *restore*
path used it. The tool a caller actually reaches for had the naive one.

That is how an assistant ends up believing it is in a terminal when it is not:
it called `focus_window`, got `ok: True`, and typed. It now verifies, reports
`in_front`, returns `ok: False` with what to do instead, and — importantly —
**does not declare a target it could not reach**, because a declared target
that is not in front is exactly what blind typing trusts.

**`close_window`'s Alt+F4 fallback** brought the window forward with the same
unverified call and sent regardless. Alt+F4 closes whatever is in *front*. It
now verifies first and sends nothing if the wrong window is there.

**`capture`** could return a picture captioned "window: X" that shows whatever
was covering X. It now says so in the caption.

Checked and *not* changed: `menu` waits for the popup to appear, and `window`
returns before/after state. Both already verify their own effect.

### Versioning, corrected

1.3.0 → 1.6.0 in two days, all of it repairs. The rule that caused it was
"any new refusal is a minor" — wrong for this project. **A guard that becomes
stricter to close a hole it should always have covered is a fix, not a
feature.** From here, tightened guards are patches; minors are new tools,
arguments or reply fields. **2.0 will be reached on capability, not by
accumulating repairs.**

## 1.6.0

### A ref made the intent explicit. It never made the destination certain.

Reported from real use, twice, and both reports trace to the same six lines:

> *"Two lines slipped into Claude Code's window instead of PowerShell — the
> window pulled the focus away."*

> *"The Claude window has been closed several times. It happens often."*

`send_keys` with a ref did this:

```python
vorher = _state(el)
_safe(lambda: el.SetFocus())      # failure swallowed
...
wache = None if args.get("ref") else (...)   # no check when a ref is given
```

And beside it, a comment: *"with a ref the focus was just set explicitly above,
so there is nothing to drift."* **An assumption the code never checked** — the
same shape of mistake as the tray icon comment in 1.4.1, and the third of its
kind found in this project.

`SetFocus` fails silently on a window that will not take the foreground, and an
Electron app can pull the foreground back a moment later. The keystrokes then
go through the **physical keyboard**, which serves whatever is in front — not
the element that was named.

**Now:** after focusing, the foreground is compared with the ref's window
*before anything is sent*. If they differ, it refuses and names both, and
points at `set_text`, which writes into the element itself and needs no
foreground at all. Afterwards it reports `off_target` on this path too, exactly
as the ref-less path already did.

### Window-closing keys with a ref were exempt from everything

`Alt+F4` and `Ctrl+W` without a ref have been refused since 1.3.2 — but **with**
a ref they bypassed every check, on the theory that naming a window makes the
intent explicit. It does. It does not make the person's own window ours to
close. Their window now needs the same handle-plus-confirmation as
`close_window`.

*This is the likely cause of "the Claude window was closed again".*

## 1.5.0

### Work on a parked window now costs the person nothing

`claim_window` moves a window just past the edge of every monitor. It keeps
running and stays fully operable by name — but nobody can see it, and Windows
will not let the mouse pointer leave the monitors, so nobody can click it
either.

Operating such a window through the accessibility interface therefore changes
nothing anyone can see and needs nothing anyone is using. Taking their keyboard
for it was ceremony. Measured on a real desktop before this changed: writing
into a parked Notepad reported `input_held: true` — **the screen was taken to
type into a window nobody could look at.**

`invoke`, `set_text`, `toggle`, `expand`, `select` and `set_value` on a claimed
window now open **no block**: no pulse, no notification, no held input. Park a
window once and the assistant works beside the person instead of instead of
them.

Deliberately **not** exempt, and the list is the point: anything that uses the
physical mouse or keyboard — `click`, `drag`, `send_keys`, `hold_key` — because
those act wherever the hardware points, not on a window. And anything that
changes what is visible: `focus_window`, `window`, `close_window`,
`claim_window`, `release_window`, `launch_app`, `batch`.

### The README is less than half as long

339 lines to 182. What was removed was not information but repetition — the
cost ladder, the walkthrough and the design notes live in `docs/GUIDE.md`,
which is where somebody goes who has already decided. The front page is for
somebody deciding.

Added instead, because it was the most common honest question and the answer
was scattered: **does it use your screen?** Thirty of the thirty-four tools
never touch the mouse or keyboard; four do and say so; and a claimed window is
outside your view entirely. Also stated plainly: this is **not** a private
virtual display, Windows does not offer one, and parking off-monitor is the
closest thing that genuinely works.

### macOS is not coming, and now says so

`docs/PORTING.md` maps the patterns onto the macOS Accessibility API, and that
map has been read as a plan. It is not one: nobody has compiled a line of it,
and the guard half — holding input — has no macOS equivalent of
`WH_KEYBOARD_LL`. The README now says **not available** rather than implying
it is on the way.

## 1.4.2

### Finding a control again after the page moved: 98x faster where it matters

The rescue that re-finds an element after a re-render walked the window's tree
from Python, one COM round trip per node. 1.4.0 made it measure itself; these
are the numbers it produced on real windows:

| | walk only | asking UI Automation |
|---|---|---|
| Claude (Electron) | 1.278s | **0.013s** |
| ChatGPT | 0.589s | **0.023s** |
| Suno in a browser | 0.709s | **0.041s** |
| a small dialog | 0.021s | 0.021s — already fast |

UI Automation can run the search **inside the application that owns the
window**, in one call, so it is asked first whenever the element had an
automation id. Same answer in every case measured; only the time changed.

**The cost, stated honestly:** when the element really is gone, the search now
tries UIA *and then* walks, so the miss case is about 5% slower — 2.19s to
2.31s on the worst window. That is the right trade: a ref goes stale far more
often than it disappears, and the seconds being saved are seconds the person's
screen is held.

The fallback walk is **breadth-first** now. Depth-first spent its whole
4000-node budget on the first deep branch it happened to enter; a control that
moved in a re-render is almost always still near where it was. And when the
search does run out of budget, the error says so — *"cut off at N nodes before
it could look everywhere"* — instead of implying the control is gone.

*This is what "only with numbers" meant. The first implementation was silently
broken (`_AutomationClient` is not exported at package level), measured as "no
improvement", and was nearly reverted on that basis. Measuring the idea and
measuring your typo look identical from the outside.*

### A test that failed at random, fixed rather than re-run

The stress test required the **window count** to be identical across three
reads. That is not a property of the server — it is a claim that nobody opened
or closed anything for a second and a half. Notifications appear, tooltips come
and go, our own overlay shows and hides. It failed on a different Python each
time, and **a test that fails at random gets ignored — and then it is not there
on the day it matters**, which is the same argument this project makes about a
guard that refuses correct work.

It now checks the narrower thing that is actually about the server: a window
present in **all three** reads must be described identically every time. Churn
is reported, not failed on.

### The one promise, re-proved on the shipped file

`release-check.yml` reaches the network — it has to, it compares a published
download against published source. That is a fair thing to be suspicious of, so
it now ends by proving the opposite about the only code that matters: it reads
every Python file **inside the published package** and fails the release if any
of them imports `socket`, `urllib`, `http`, `ssl`, `requests` or anything else
that could open a connection.

`SECURITY.md` now draws the line exactly rather than leaving "no network" to do
work it cannot do. Two files in this repository use the network — the updater
you start by hand, and that workflow, which runs on GitHub's machines. Neither
ships. The extension contains `server.py`, `overlay.py`, `manifest.json`,
`requirements.txt` and `lib/`, and a `.mcpb` is a zip, so you can list it
yourself.

## 1.4.1

**The stop button did not work while the screen was held.**

The tray menu is the only way to pause or stop a takeover from outside. The
code said a takeover could not lock anyone out of it, and gave a reason:

> *the tray icon and its menu are a normal window, not part of the swallowed
> input.*

That reasoning is wrong. **A low-level mouse hook intercepts input before any
window sees it** — being a normal window has nothing to do with it. So while a
block was held, a real click on the tray icon was swallowed like every other
click, and Pause and Stop were unreachable during the only moments they exist
for. The emergency brake did not work while the car was moving.

The taskbar is now carved out of the swallowing, and so is the whole screen
while the menu is open — including the keyboard, so the menu can be driven with
arrow keys and Enter. The taskbar's position is re-read once a second, because
it can move or auto-hide.

*Found while checking the last open item on the list rather than by anything
going wrong — which is the point of having the list.*

## 1.4.0

### Why this is 1.4.0 and not 1.3.5

1.3.1 through 1.3.4 all shipped in a day, and at least two of them changed
what the server *refuses* — new refusals are a change in behaviour, not a
patch. Calling them patch releases was wrong, and it made a manual install
cost more than the fix was worth. From here: **patch = fixes only; minor =
any new refusal, tool, or reply field the caller must act on; and not more
than one release a day unless something is actually costing somebody
work.**

### The guard could go missing and never come back

Found on a real desktop. `_overlay_starten` returned the stored handle
whenever it was not `None` — which is true of a **dead** process too. So the
first time the overlay ended for any reason, every later command went into a
pipe nobody was reading. The overlay is not decoration: the warning, the
pulse, the notification **and the input hold** all live in it. Losing it once
meant losing the guard for the rest of the server's life, silently. It is now
restarted, restarts are counted, and if it will not stay up the guard says so
instead of pretending.

### A leftover overlay sat glowing with nothing held

Also found on a real desktop: four bars visible, nothing holding, from an
earlier server. A glow that means nothing is worse than no glow, because the
next real one means nothing either. The overlay now hides anything on screen
whenever its state is "off", whatever path led there.

### The pulse only framed the desktop, not your screen

The bars followed the virtual desktop — one box around *all* monitors.
Measured here on two screens of different height: the bottom edge of the
desktop sat 240px **below** the smaller monitor, so somebody working on that
screen got a top edge, a right edge and nothing else. Half a frame reads as a
glitch, not a warning. **Each monitor now gets its own complete frame.**

The held bar is also re-drawn a few times a second and re-asserted as topmost,
because being topmost once is not being topmost: any window that asks for it
later goes above. The pixels are cached, so the redraw costs less than one
frame of the animation before it.

### Measured, so it is no longer a matter of opinion

- **Pulse:** red `#EF4444` reaching ~200px inward at 800ms, snapping to blue
  `#22D3EE` at 46px. Verified by reading screen pixels on all four edges of
  both monitors, before, during and after.
- **Notification:** appears.
- **Input hold:** the overlay reports `hooks:1` on lock and `hooks:0` on
  release.
- **Stale-ref rescue:** `self_test` now reports `stale_ref_rescue` — runs,
  nodes walked, seconds, worst run, how often the 4000-node limit was hit.
  Whether that walk should become an index is a question for those numbers.

### `wait` inside `batch` is now refused past 2 seconds

The block is held for the whole batch, so a ten-second wait is ten seconds of
somebody locked out of their own screen while nothing happens. It was written
down as a rule, and rules that are only written down get broken. Short settles
still pass — a window needs a beat to catch up.

## 1.3.4

**The reader of these replies is a model with no memory of the machine between
turns.** Two things it could not know now travel with every acting call.

**Is the block still open.** Only `set_guard` reported that. After two turns
the assistant is guessing, and a block held open by a forgotten `start` is
exactly how somebody ends up locked out of their own desk. Every reply from a
tool that can change the screen now carries `block_open`, `seconds_held`,
`working_in`, the real `input_held`, and a reminder to end it. Readers are not
nagged — they open no block.

**What was swallowed during this call.** `_safe` hides exceptions on purpose:
one control that refuses to answer must not abort a walk over two hundred of
them. Every swallow was already recorded — but only `self_test` showed them,
and nobody runs `self_test` mid-task. So a call that quietly lost three
exceptions looked exactly like a clean one. If anything was swallowed *during
this call*, it is now attached to the result it may have shaped, with the type,
the line, and what it means. A clean call says nothing.

*Prompted by a review arguing that with an LLM as the user, the guard is no
longer politeness but an error-detection system. That framing is right, and
these were the two places the system could not see itself.*

## 1.3.3

### The input hold was never actually on

Reported in one sentence, and it undoes an assumption the whole design rested
on: *"I could still move my mouse and type while you had my window."*

A low-level hook is delivered to the **message queue of the thread that
installed it**. The commands from the server arrive on the overlay's stdin
thread — and that thread sits blocked in a read, with no message loop at all.
So `SetWindowsHookEx` succeeded, returned a valid handle, and the callbacks
were never dispatched. Windows drops such a hook after `LowLevelHooksTimeout`
and says nothing.

Nothing failed. Nothing was logged. `self_test` reported the overlay as
present, because it checked that the *file* existed. The pulse drew, the
notification appeared, the block opened and closed — and the person's keyboard
and mouse were free the entire time, while every layer above was certain they
were held.

**The fix is one line of architecture:** the protocol thread now only records a
wish, and `tick()` — which runs on the message-loop thread, the one thread that
can receive the callbacks — installs and removes the hooks. That is also the
thread the callbacks have to arrive on, so it is the only correct place.

**And it now says so.** The overlay reports `hooks:1` / `hooks:0` back to the
server, and `set_guard block:'start'` returns `input_held`. When Windows
refuses the hooks, the reply says the screen is shared and to behave
accordingly, instead of promising a hold that is not there.

*This is the third defect in this project found by the same rule: a function
that does not report whether it worked will eventually stop working, and nobody
will notice.*

### The server measured whether it gave the screen back, and then never said so
Found by testing 1.3.2 on a live desktop: after a block ended, the foreground
was a different window than expected — and there was no way to tell from the
outside whether that was correct or a failure.

The release wrote its result into `_RUECKGABE` on every block, with a comment
saying tools copy it into their reply. Nothing did. The claim *"your focus is
restored is a measurement, not a promise"* was true of the measurement and
false of the reporting, which is exactly how a foreground that never came back
could keep happening without producing a single signal.

`set_guard block:'end'` now returns `handed_back`:

| field | |
|---|---|
| `foreground_restored` | did the call succeed |
| `their_window` | the window this block owed them |
| `in_front_now` | what is **actually** in front, measured after the restore |
| `caret_restored` | did the text cursor come back with it |
| `attempts` | how many tries it took |

`in_front_now` is the one that matters. `foreground_restored` answers whether
the call worked; `in_front_now` answers where the person is looking, which is
the question that was never being asked.

## 1.3.2

**The window you were in is no longer something this can make disappear.**
Reported from real use: *"when it takes control my active window goes to the
background, and now and then it was even closed."*

Three tools can make a window vanish — `close_window` closes it, `claim_window`
moves it past every monitor, `window state:minimized` hides it — and none of
them knew which window the person was sitting in. A `window_title` that matched
theirs instead of ours was the whole distance between working and lost work.
A fourth path was not a tool at all: `Alt+F4` or `Ctrl+W` sent without a ref,
landing on whatever happened to hold the keyboard.

The takeover already saves that window, because it has to put it back at the
end. The same handle is now used for the opposite purpose:

- **Closing, parking or minimising it is refused.** The exception is narrow on
  purpose — naming that exact `window_handle` *and* `confirm:true` gets
  through, so "close my Notepad" still works. What is closed off is the
  accidental path.
- **An ambiguous `window_title` is refused, not guessed,** for anything
  destructive. Three windows containing "Chrome" now come back as three
  candidates with their handles instead of whichever was first.
- **`Alt+F4` and `Ctrl+W` are refused without a ref.** Every other stray
  keystroke can be deleted again; these cannot.
- **A foreground that did not come back is said out loud.** The restore now
  gets three attempts instead of two, and if the person's window is still not
  in front, the *next* call — whatever tool that is — carries the handle, the
  title, and what to do about it. A block often ends on a timer, with no reply
  to attach the failure to, which is how this stayed invisible.
- **Watch mode explains itself once.** It skips the restore deliberately;
  somebody who switched it on last week and forgot only sees their window
  ending up behind.

## 1.3.1

**Blind keystrokes now say when they missed.** The check that keeps typing out
of the wrong window happens a moment before the keystrokes are sent, and those
cannot be one instruction. On a shared screen that gap is real: seen once in
live testing, a restore finished late, the check passed honestly — the target
*was* in front — and the keys landed elsewhere a fraction of a second later.

Nothing can be undone after the fact. What must not happen is silence about it,
because the next thing an assistant does after an unnoticed miss is type more.
So `send_keys` without a ref now compares where the keystrokes actually landed
against the window it was working in, and when they differ it returns
`off_target: true` with a warning that names both windows and says to stop,
re-focus, and check whether anything needs undoing.

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
