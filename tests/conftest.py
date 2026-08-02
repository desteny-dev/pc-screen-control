# -*- coding: utf-8 -*-
"""
Let `pytest` work here, without the tests becoming pytest's.

Every test in this folder is a standalone program: you run it with `python
tests/test_x.py`, it prints what it measured line by line, and it exits 0 or 1.
That is deliberate. Most of them drive a real Windows desktop, and when one
fails the useful output is the measurement it printed, not an assertion
traceback. CI runs them exactly that way.

But a contributor's first instinct is `pytest`, and that used to end like this:

    INTERNALERROR> SystemExit: 0
    no tests ran in 2.22s

The scripts call `sys.exit` while pytest is still importing them, which aborts
collection. Note the exit code: **zero**. It looked like success, and the
summary said no tests exist rather than that the runner broke - which is the
exact shape of failure this project keeps finding in itself.

So: pytest skips the scripts during collection, and `test_suite.py` runs each
one as a subprocess and reports it as a normal test. `pytest -q` now does what
somebody typing it expects, and the scripts stay scripts.
"""
import os

_AGGREGATOR = "test_suite.py"

collect_ignore = sorted(
    f for f in os.listdir(os.path.dirname(os.path.abspath(__file__)))
    if f.startswith("test_") and f.endswith(".py") and f != _AGGREGATOR
)
