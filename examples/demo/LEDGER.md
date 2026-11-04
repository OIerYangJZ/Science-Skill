# Research ledger: a better loss for low-light denoising (synthetic demo)

**Status (2026-11-04): the new loss improves in-distribution accuracy over 5 seeds; out-of-distribution gain not shown.**

## 1. Results

| ID | Result (exact statement or pointer) | Status | Depends on | Evidence | Reviewed / verified (by, date) |
|---|---|---|---|---|---|
| R1 | New loss: 0.893 vs 0.812 baseline accuracy, 5 seeds | VERIFIED | | `results.csv` | labmate re-run, 2026-11-02 |
| R2 | Gain persists out of distribution | PRELIMINARY | R1 | `results.csv` (0.774 vs 0.769) | |

## 4. Routes tried

| ID | Date | Route (one line) | Outcome | Stops at (barrier or step) | Evidence | Reopen only if |
|---|---|---|---|---|---|---|
| X1 | 2026-10-28 | Perceptual loss on VGG features | NEGATIVE | no gain over baseline (5 seeds) | `runs/x1` | a domain-specific feature extractor exists |
| X2 | 2026-10-30 | Train at 4x resolution | BLOCKED | GPU quota exhausted | cluster ticket | quota restored |
