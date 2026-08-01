# PC Screen Control — where this is going

*Written by the maintainer. Read this before proposing changes.*

---

## Start here

**Current state:** v1.4.1 is released. 34 tools, 18 test files in CI on Python
3.9 / 3.11 / 3.13, all green. Two packages ship: `.mcpb` for Claude Desktop and
`.zip` with a setup script for ChatGPT desktop, Codex, Cursor, VS Code, Cline
and Zed — same server inside both.

Three releases in a row came from the same place: what the guard protects and
what a person actually loses were not the same list.

1.3.0 — the guard knew whether the screen had *moved*, but not whether the
foreground was still the window the assistant had *declared*. After a block
ended mid-task those were the same answer, and a command meant for a terminal
was typed into somebody's chat. The declared window is tracked separately now,
taken from the call itself so no tool can forget it
(`tests/test_wrong_window.py`).

1.3.1 — the check and the send cannot be one instruction. Seen once live: the
check passed honestly and the keys landed elsewhere a fraction of a second
later. Cannot be prevented; the silence after it can. `send_keys` reports
`off_target` naming both windows.

1.3.2 — the person's own window could be closed, parked out of reach or
minimised, because no tool knew which window they were sitting in; a
`window_title` matching theirs instead of ours was the whole distance. It is
now refused, an ambiguous title is refused rather than guessed for anything
destructive, `Alt+F4`/`Ctrl+W` without a ref is refused, and a foreground that
did not come back is reported on the next call whatever tool that is
(`tests/test_user_window.py`).

1.3.3 — and then a live test of 1.3.2 showed the sharpest version of the same
mistake: the release *measured* whether it had given the screen back, wrote the
result into `_RUECKGABE`, and **nothing ever read it**. A comment said tools
copy it into their reply; none did. `set_guard block:'end'` now returns
`handed_back`, including `in_front_now` — what is actually in front, measured
after the restore, as opposed to whether the call returned true.

1.3.4 — the reader of every reply is a model with no memory of the machine
between turns. Only `set_guard` said whether a block was open, and swallowed
exceptions were recorded but only visible in `self_test`, which nobody runs
mid-task. Both now ride along with every acting call.

1.4.0 — and then the visual half was measured for the first time instead of
assumed. The pulse and the notification work. What did not: the overlay was
never restarted after it died, so one crash silently ended the guard for the
rest of the server's life; a leftover overlay sat glowing with nothing held;
and the frame followed the virtual desktop rather than each monitor, so on a
second, shorter screen a person got two edges out of four. `wait` inside
`batch` is refused past 2 seconds rather than merely discouraged.

**The pattern worth carrying forward:** every one of these was a case where the
code was internally consistent and still wrong, because the question it asked
was not the question the person cared about. When adding a guard, write down
what the person loses, not what the code does.

**And a second one, for reviewers:** the ring buffer for swallowed exceptions
shipped before 1.0.0 and is in `_FEHLER_LOG`; `_safe` has never been
`except: pass`. The server opens no socket, so there is no update to verify a
hash of — the release assets' SHA-256 values are published in the release notes
instead. Both are recommended regularly by reviewers who quote the code they
expect rather than the code that is there. **Quote the actual lines you are
objecting to, with their line numbers, or the recommendation will be closed.**

Since 1.0.0, in order: the update check left the server and became a program a
person runs by hand; the libraries are bundled so nothing installs and nothing
reaches the network at run time (`tests/test_offline.py` proves it);
`launch_app` refuses shells and URLs unless confirmed; password fields read back
as a placeholder; and the guard was rebuilt around a session — one takeover per
burst, warned on screen with a red pulse and a Windows notification, restored
once, with **every** tool that can change the screen going through it by default
(`tests/test_guard_coverage.py` holds that line).

The published release matches this commit. The consistency checker that compares
every number and claim across README, manifest, CHANGELOG, SECURITY and the
built package passes, and a second checker verifies the published release
against the code at its tag.

**The Version 1 checklist further down is DONE — every item of it.** It is kept
as a record of what was decided and why, not as work. If you propose SHA-256
verification of the update, a ring buffer for swallowed exceptions, Store-Python
detection, ruff in CI, an antivirus FAQ, or honest cost reporting in
`describe_screen`, you are describing this project as it was before 1.0.0. All
six shipped. **Read the code before recommending anything; this file is history,
the code is the state.**

**Your job:** write the code for what is actually open — the list is in
`## What is actually open` below. One item per PR, with the *reason* in the
commit message.

**Not your job:** building the `.mcpb`, running the Windows GUI tests,
publishing releases, or checking that the docs still match the code. That is
done separately on a real Windows desktop, because most of these tests need one.
Assume every claim you make will be measured before it ships.

**Before you propose anything**, read `CHANGELOG.md`. Several obvious ideas were
tried and rejected with reasons recorded there.

---

## What is actually open

Everything below is unclaimed and worth doing. Nothing here is on the Version 1
checklist — that one is finished.

**1. Confirm by hand that the tray menu now opens during a held block.**
It could not before 1.4.1: the mouse hook swallowed the click before the icon
ever saw it, so Pause and Stop were unreachable during the only moments they
exist for. The taskbar is now carved out of the swallowing and the code path is
covered in `tests/test_user_window.py` section 14 - but "a human clicked it
mid-takeover and the menu opened" is still unmeasured, and it is the one claim
that matters most. **Needs a hand on a real mouse.**

**2. macOS.** `docs/PORTING.md` maps every pattern used here onto the
Accessibility API. That map has never been compiled. The guard is the harder
half: macOS has no `WH_KEYBOARD_LL`, and holding input needs an Accessibility
permission the user grants explicitly.

**3. `_spur_suchen` — decide it from the numbers now.**
The 4000-node rescue walk measures itself since 1.4.0 and `self_test` reports
`stale_ref_rescue`: runs, nodes, seconds, worst run, and how often the limit
was hit. If the worst run is milliseconds, leave it alone. If it is not, an
automation-id index built during the tree read makes it O(1). **Do not touch
this without pasting the numbers.**

*Closed in 1.4.0, all by measurement on a real desktop, not by reasoning:* the
pulse and the notification (pixels read on every edge of both monitors); the
overlay restarting after it dies; a leftover overlay left glowing; the frame
following the virtual desktop instead of each monitor; and `wait` inside
`batch`, which is now refused past 2 seconds instead of merely discouraged.

**Not open, deliberately:** anything that puts the server on a network,
anything that makes a tool reach the internet, and any "convenience" that
weakens the rule that every screen-changing tool goes through the guard.

---

## What this project is, in one paragraph

Most tools that let an AI use a Windows PC take a screenshot and guess a
coordinate. This one hands the AI the accessibility tree instead — the same
structured data a screen reader uses — so a control is pressed by name and every
action reports the element's state before and after. That part is no longer
novel; at least five projects now do it, including one from Scott Hanselman.

**What is not solved anywhere else is the human sitting at the same desk.**
Every other Windows MCP server behaves as though the computer were empty. This
one assumes someone is using it, and treats their attention, their focus and
their keystrokes as things that cost something to take. That is the thesis, and
everything in Version 1 exists to make it true rather than merely claimed.

---

## The rule this project is built on

> **Measure before you claim. If a function does not report whether it worked,
> it will eventually stop working and nobody will notice.**

This is not a slogan. It is the reason for most of the code. Three separate
defects survived for weeks because the code that was supposed to do the work
looked complete and silently did nothing:

- `SetForegroundWindow` is refused for a background process, silently. The
  restore had never once run.
- `_ref_for` returned nothing for almost every element, which quietly forced
  three tools down onto the mouse.
- `stdin` was never pinned to UTF-8, so every non-English character sent to any
  tool was destroyed on the way in while the replies looked perfect.

Each was found by a test that checked the **outcome**, not the call. Several
tests had to be fixed first because they passed against broken code. When you
add a test, delete the fix in a scratch copy and confirm the test fails. A test
that cannot fail is a feeling, not a test.

---

## Response to the Copilot review

The review was accurate and I am acting on most of it. Where I am not, here is
why — do not re-propose these without new evidence.

| Point | Verdict |
|---|---|
| **Update download is unverified** | **Correct, and the sharpest finding.** The release notes publish a SHA-256 and `check_for_update` never checks it. In scope for v1. |
| **Broad `except` blocks swallow errors** | **Correct, and this project has been bitten by it three times.** In scope for v1, but narrowly: `_safe()` stays, and gains a diagnostic channel. |
| **Low-level input hooks look like a keylogger** | **Correct that AV will complain.** Already disclosed in SECURITY.md. Needs a FAQ, not a redesign — the hooks are the feature. |
| **No type hints, no linter** | Correct. Cheap. In scope for v1. |
| **Modularise the single file** | **Rejected for v1.** One readable file is a deliberate trust decision: a stranger installing something that controls their PC can audit it in one sitting. Splitting it into eight modules makes the code nicer for me and the audit harder for them. Revisit if it passes ~4000 lines. |
| **Windows-only, single maintainer** | Correct and unfixable. Already stated plainly in the README. `docs/PORTING.md` maps every pattern onto the macOS API and is honest that a map is not an implementation. |
| **External security audit before wide distribution** | Agreed in principle, not affordable. The substitute is that the whole server is one readable file with its tests shipped next to it. Say so; do not pretend otherwise. |

**Yes, open PRs** for: signature verification, exception narrowing, type hints,
linting, the AV FAQ. **No PRs** for: splitting the file, removing the hooks,
adding a framework, adding a dependency that is not strictly needed.

---

# Version 1.0 — the goal

**Theme: it works on a computer someone is still using, and it can prove it.**

Version 1 is finished when a stranger can install it, work alongside it for an
afternoon, and never once be surprised by it. Nothing in this list is a feature
idea; each one closes a gap between what the README promises and what the code
does.

### A. Trust — the part I cannot hand-wave

- [ ] **Verify the downloaded `.mcpb` against the published SHA-256.**
      `check_for_update` already reads the release JSON, and the release body
      already contains the hash. Parse it, hash the download, refuse and delete
      on mismatch, and report which hash was expected. Never install; only
      download and verify.
- [ ] **A diagnostic channel for swallowed errors.** `_safe()` currently
      discards the exception. It should record type, message and call site in a
      ring buffer that `self_test` can return. Keep `_safe()` — the swallowing
      is deliberate, because one dead control must not kill a tree walk — but
      stop making the swallowed thing invisible.
- [ ] **Type hints on every public function, `ruff` in CI.** No behaviour
      changes in the same commit.
- [ ] **An antivirus FAQ in the docs.** Why it triggers, what the hooks
      actually do, how to verify that claim yourself, how to switch the guard
      off entirely with `set_guard enabled:false`.

### B. Coexistence — the thesis, made true

Most of this is done. What remains is the last case.

- [x] Focus, window and text caret restored after every action, measured
- [x] Restore happens **under the lock**, before input is handed back
- [x] Takeover refused when the window *or* the focused control moved
- [x] `claim_window` parks a window where the mouse physically cannot reach
- [x] Crash rescue: a parked window is written to disk and recovered on restart
- [x] Rubber-band pulse, Escape never swallowed, ten-second watchdog
- [x] **Window-targeted input (`PostMessage`) as rung 3.5.** ~~Decision gate:
      measure against Win32, Qt, Chromium.~~ **MEASURED AND REJECTED.** On a real
      desktop, none of the three framework families gives its controls their own
      window handle — Qt (DaVinci) and Chromium (browsers) paint everything into
      one window, and even Win32 apps increasingly do. There is nothing for
      `PostMessage` to address, so it would fail on exactly the applications it
      was wanted for. Recorded in CHANGELOG under rejected approaches. **Do not
      re-propose this** without new evidence that the framework situation has
      changed.

### C. Idiot-proofing — the part that decides whether anyone gets this far

- [x] `self_test`: ten checks, plain language, every failure carries its fix
- [x] Irreversible actions refuse on the first call and describe the loss
- [x] The first run explains its own delay in the first reply
- [x] Claimed windows are marked wherever windows are listed
- [ ] **Make the Python requirement survivable.** It is the single biggest
      reason someone never gets this working. In order: detect the Microsoft
      Store placeholder and say so by name; make the failure message name the
      exact checkbox that was missed; offer an optional second release asset
      with Python embedded. Optional, never instead of the small file — a 30 MB
      download from an unknown developer reads as *more* suspicious, not less.
- [ ] **A `describe_screen` that is honest about cost.** It is 3.4s and every
      task is told to start with it. Either make it faster or make the reply say
      what it spent.

### D. Housekeeping

- [ ] **The published release must equal the code.** It is currently several
      commits behind. From the first real download onward: any change to the
      contents gets a new version number. No exceptions, no "it is only a
      docs change".
- [x] An automated consistency checker that compares every number and claim
      across README, manifest, CHANGELOG, SECURITY and the built package —
      and that is itself tested by reintroducing known defects.

### Version 1 is done when

1. `self_test` returns `Everything works` on a clean Windows install with only
   the documented prerequisites.
2. Every claim in the README maps to a test in `tests/` that fails if the claim
   stops being true.
3. The downloaded update is verified against a published hash.
4. CI is green on Python 3.9, 3.11 and 3.13.
5. A person who has never seen this can install it and get a window list
   without asking me anything.

---

# Version 2.0 — deliberately after 1.0

**Theme: it also sees and hears.**

Do not start this before 1.0 ships. It is a different problem with a different
risk profile, and mixing the two would mean neither is finished. Version 1 is
about *not disturbing the human*. Version 2 is about *perceiving what has no
accessibility tree at all*.

### The gap it closes

The cost ladder ends at rung 4 for a reason: editing canvases, video timelines
and games publish no controls, so there is nothing to read and nothing to press
by name. Today the honest answer is "take a picture and click a coordinate".
That is the same guessing this project exists to replace — it is simply where
the structured data runs out.

### What it should become

- **Images, precisely.** Not "there is a button somewhere" but position, state,
  colour, text and relationship, at a quality good enough to act on rather than
  to describe.
- **Video as time, not as frames.** Analyse on a fixed cadence — roughly every
  0.5 s — and emit a timestamped text record rather than a pile of pictures.
  Movement, cuts, what changed and when.
- **Audio as text with timestamps.** Speech, music, silence, level. On the same
  clock as the video record.
- **Fusion.** The three streams share one timeline, so a question like "what
  happened at 0:42" has one answer assembled from all of them, not three
  answers that have to be reconciled by the reader.

### Why timestamps are the design and not a detail

Text is what a model reasons over well. A timestamp is what makes separate
observations comparable. Get the clock right and the three streams merge almost
for free; get it wrong and no amount of model quality repairs it.

### Constraints carried over from Version 1

- Everything local. As of 1.1.0 **no tool reaches the network at all** — the
  update check is a separate hand-run program and the dependencies are bundled.
  Keep it that way: any perception feature (v2) processes frames locally, and
  anything that would open a socket ships as a separate opt-in program a person
  runs, never as a server tool. `tests/test_offline.py` is the guard.
- Every observation reports its own confidence and its own cost, the same way
  every action reports before and after.
- No new dependency without a measurement showing what it buys.
- If an approach cannot be measured, it does not ship. This applies to
  perception more than anywhere else, because a description is *always*
  plausible — which is exactly why it must be checked against something.

---

## How to work on this

1. Read `CHANGELOG.md` before proposing anything. Several obvious ideas were
   already tried and rejected with reasons — `BlockInput` needs administrator
   rights, Windows toasts cannot carry an actionable button, a full-screen
   overlay cannot be animated at 36 MB per frame.
2. Measure first, then write. Numbers in this repository come from scripts in
   `tests/` that ship with it, so anyone can contradict them.
3. Small commits with the *reason* in the message, not the diff. The diff is
   already visible.
4. If you find a claim in the docs that the code does not support, that is a
   bug in the code or a bug in the docs — never a thing to leave alone.
