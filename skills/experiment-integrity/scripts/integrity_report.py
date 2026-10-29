#!/usr/bin/env python3
"""integrity_report.py - the experiment-integrity report, computed from the findings ledger.

Usage
  python3 integrity_report.py LEDGER.md --out report.md [--lang en|zh] [--manuscript FILE ...] [--version TEXT]

The ledger is a Markdown table with at least the columns `verdict` and `verified` (see the skill's
SKILL.md). Allowed verdicts: CONFIRMED, POSSIBLE, REFUTED, NOT CHECKED (add a column tier with T / S / R).
Severe verdicts (CONFIRMED) count only when `verified` is "yes" (checked by the main session); otherwise the report
is marked NOT FINAL.

Exit codes: 0 no confirmed severe finding; 1 confirmed severe findings; 2 not final.
"""
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "..", "lib")))
import findings  # noqa: E402

if __name__ == "__main__":
    sys.exit(findings.main_cli("integrity", prog="integrity_report.py"))
