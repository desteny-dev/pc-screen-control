# Contributing

## The most useful contribution

An application where the tree comes back empty or wrong, with its
`describe_screen` output. The window `class` and `framework` are what determine
whether it can be read at all, and no amount of reasoning substitutes for
someone running it against software I do not own.

## Running it

```
pip install -r src/requirements.txt
python tests/test_installer.py     # setup logic, runs anywhere
python tests/test_update_verify.py # the update download is hash-checked
python tests/test_offline.py       # no network, no runtime install, 0 sockets
python tests/test_session.py       # one takeover per burst, warned, restored
python tests/test_any_client.py    # serves any MCP client, fails politely
python tests/test_guard_coverage.py # nothing that changes the screen is unguarded
python tests/test_wrong_window.py  # keystrokes never land in the wrong window
python tests/test_user_window.py   # the user's own window cannot be made to vanish
python -m pytest -q                # tests/test_suite.py runs them all at once
python tests/test_codex_install.py # the Codex entry keeps foreign settings
python tests/test_refs_stale.py    # a ref survives the page moving under it
python tests/test_encoding.py      # non-ASCII survives the protocol
python tests/test_refs.py          # refs resolve, and invoke refuses the mouse
python tests/test_takeover.py      # blind input stops if the user took over
python tests/test_restore.py       # focus is really given back, measured
python tests/test_handover.py      # freeze, look, act, restore, release
python tests/test_claim.py         # parking a window, and the crash rescue
python tests/test_monitors.py      # the glow follows the screens that exist now
python tests/measure_desktop.py    # measures the desktop you are sitting at
python tests/stress.py             # cost, nonsense, broken protocol, ~1 min
python src/server.py --install     # register it with your MCP client
```

CI runs all nineteen on Windows against Python 3.9, 3.11 and 3.13.

`pytest -q` works too and runs the same scripts as subprocesses — see
`tests/conftest.py` for why they are scripts and not pytest functions.
When one fails, pytest prints the measurement the script printed, which
is the part worth reading.

## Versioning

Corrected after 1.3.0 → 1.6.0 happened in two days, all of it defect work.

The rule that caused it was *"any new refusal is a minor"*. That is wrong for
this project. **A guard that becomes stricter to close a hole it should always
have covered is a fix, not a feature** — the tool's whole purpose is refusing
things that would cost somebody their work, so tightening one is repairing it.

| | |
|---|---|
| **PATCH** `1.6.x` | fixes, including a guard that now covers a case it always should have |
| **MINOR** `1.x.0` | a new tool, a new argument, a new reply field a caller must act on |
| **MAJOR** `x.0.0` | a tool removed or renamed, or a reply field that changes meaning |

**1.0 was reached on capability. 2.0 will be reached on capability too — not by
accumulating repairs.**

And still: at most one release a day unless something is actively costing
somebody work. Ten releases in a week reads as instability no matter how good
each one is, and GitHub's own abuse protection starts refusing you.

## The one rule

**Measure before you claim.** Every number in the README came from
`tests/measure_desktop.py`, and several of them contradicted what I had written
the week before — Chromium was labelled a limitation for two releases before a
measurement showed the probe was at fault, not the browser.

If you add a capability, add the check that would fail if it stopped working.
Prefer a test that reads the result back over one that asserts no exception was
raised: three tools shipped reporting success for things they had not done, and
each was caught by a test that looked at the value afterwards.

## Style

- One file per concern; the server is deliberately one readable file.
- Comments explain **why**, not what. If a line looks wrong until you know a
  Windows quirk, write the quirk down.
- Every action returns state before and after. A tool that cannot prove its
  effect says so instead of returning `ok`.

## Licence

MIT. By contributing you agree your work is published under it.
