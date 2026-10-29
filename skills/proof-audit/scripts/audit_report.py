#!/usr/bin/env python3
"""audit_report.py - the proof-audit report, computed from the verdict ledger.

Usage
  python3 audit_report.py LEDGER.md --out report.md [--lang en|zh] [--manuscript FILE ...] [--version TEXT]

The ledger is a Markdown table with at least the columns `verdict` and `verified` (see the skill's
SKILL.md). Allowed verdicts: VERIFIED, VERIFIED WITH FIXES, CONDITIONAL(<what>), GAP, INVALID, NOT CHECKED.
Severe verdicts (GAP, INVALID) count only when `verified` is "yes" (checked by the main session); otherwise the report
is marked NOT FINAL.

Exit codes: 0 no confirmed severe finding; 1 confirmed severe findings; 2 not final.
"""
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "..", "lib")))
import findings  # noqa: E402

if __name__ == "__main__":
    sys.exit(findings.main_cli("proof", prog="audit_report.py"))
