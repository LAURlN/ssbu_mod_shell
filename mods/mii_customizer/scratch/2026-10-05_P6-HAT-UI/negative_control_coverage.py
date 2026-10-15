#!/usr/bin/env python3
"""Negative control for the report-coverage check in check_p6_hat_ui.py.

The coverage pass re-parses research/P6-HAT-UI.md and asserts every pc the report
cites exists in the chunk it names. That pass was added last, so it needs its own
proof that it fails when the report and the bytes disagree.

This script imports the check module, points it at a doctored copy of the report
in which one cited pc is nudged out of range, and asserts the check exits
nonzero. It writes only inside scratch/2026-10-05_P6-HAT-UI/ and touches nothing
else. Scratch tool; not a deliverable.
"""
import importlib.util
import io
import os
import re
import sys
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.normpath(os.path.join(HERE, "..", ".."))
CHECK = os.path.join(MOD, "evidence", "P6-HAT-UI", "check_p6_hat_ui.py")
DOCTORED = os.path.join(HERE, "_negative_control_report.md")

# p11 has 142 instructions (pc 0-141). Cite pc 141 -> 9999: out of range.
TARGET = re.compile(r"^\| p11 43-47 \|", re.M)


def load_check():
    spec = importlib.util.spec_from_file_location("p6check", CHECK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    with open(os.path.join(MOD, "research", "P6-HAT-UI.md"), encoding="utf-8") as fh:
        report = fh.read()
    doctored, n = TARGET.subn("| p11 43-9999 |", report, count=1)
    if n != 1:
        print("SETUP FAILED: could not find the row to doctor")
        return 2
    with open(DOCTORED, "w", encoding="utf-8") as fh:
        fh.write(doctored)

    mod = load_check()
    mod.REPORT = DOCTORED
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = mod.main()
    tail = [ln for ln in buf.getvalue().splitlines() if "FAIL" in ln]

    os.remove(DOCTORED)

    print("doctored-report exit status: %d" % rc)
    for ln in tail[:5]:
        print("  " + ln.strip())
    if rc == 0:
        print("NEGATIVE CONTROL FAILED: coverage check passed a bad report")
        return 1
    if not any("outside" in ln for ln in tail):
        print("NEGATIVE CONTROL FAILED: failed for the wrong reason")
        return 1
    print("NEGATIVE CONTROL OK: coverage check rejects an out-of-range cited pc")
    return 0


if __name__ == "__main__":
    sys.exit(main())