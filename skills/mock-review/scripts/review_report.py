#!/usr/bin/env python3
"""review_report.py - the mock-review report, computed from verification.md.

Usage
  python3 review_report.py LEDGER.md --out report.md [--lang en|zh] [--manuscript FILE ...] [--version TEXT] [--pin PIN.json]

The ledger is a Markdown table with at least the columns `verdict` and `verified` (see the skill's
SKILL.md). Allowed verdicts: CONFIRMED, PARTIALLY CONFIRMED, REFUTED, NOT CHECKED.
Severe verdicts (CONFIRMED, PARTIALLY CONFIRMED) count only when `verified` is "yes" (checked by the main session); otherwise the report
is marked NOT FINAL.

Exit codes: 0 no confirmed severe finding; 1 confirmed severe findings; 2 not final.
"""
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "..", "lib")))
import findings  # noqa: E402
import json  # noqa: E402


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--pin" in argv:
        i = argv.index("--pin")
        pin = json.load(open(argv[i + 1], encoding="utf-8"))
        del argv[i:i + 2]
        hashes = "; ".join(f"{k} {v[:16]}…" for k, v in (pin.get("manuscript_sha256") or {}).items())
        version = f"git {str(pin.get('head') or '-')[:7]}; {hashes}; line numbers apply only to this version"
        if "--version" not in argv:
            argv += ["--version", version]
    return findings.main_cli("review", argv, prog="review_report.py")


if __name__ == "__main__":
    sys.exit(main())
