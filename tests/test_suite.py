# -*- coding: utf-8 -*-
"""
Runs every test script and reports each as one pytest result.

This exists so `pytest` at the repository root does the obvious thing. The
scripts themselves are unchanged and still run on their own - see
`conftest.py` for why they are not written as pytest functions.

Not included: `stress.py` and `measure_desktop.py`. Both need a real desktop
and take minutes; CI runs them as their own steps.
"""
import os
import subprocess
import sys

import pytest

HIER = os.path.dirname(os.path.abspath(__file__))
SKRIPTE = sorted(
    f for f in os.listdir(HIER)
    if f.startswith("test_") and f.endswith(".py") and f != "test_suite.py"
)


@pytest.mark.parametrize("skript", SKRIPTE)
def test_skript_laeuft_durch(skript):
    lauf = subprocess.run([sys.executable, os.path.join(HIER, skript)],
                          capture_output=True, text=True, timeout=300)
    if lauf.returncode != 0:
        # The script already printed exactly what it measured and where it
        # disagreed. Repeating that is far more use than an assertion about a
        # return code, so it goes in the failure message verbatim.
        ausgabe = (lauf.stdout or "") + (lauf.stderr or "")
        pytest.fail("%s exited %d\n\n%s"
                    % (skript, lauf.returncode, ausgabe[-4000:]),
                    pytrace=False)
