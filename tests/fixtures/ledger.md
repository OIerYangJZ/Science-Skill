# Research ledger: push the bound from a to b

**Status (2026-10-29): bound a proved and reviewed; b open.**

Goal: push the bound from a to b
Current best: - (status, evidence)

Status words. Results: VERIFIED (independently checked: proof reviewed / result replicated / analysis re-run by
someone else), UNVERIFIED (complete but not independently checked), CONDITIONAL(hypothesis or assumption),
PRELIMINARY (heuristic, pilot, exploratory, trend), NEGATIVE (tested and not supported), RETRACTED.
Routes (approaches, experiments, analyses, proof strategies): FAILED (the idea does not work, with the reason),
BLOCKED (could not be carried out: compute, bug, access, time; NOT evidence against the idea), INCONCLUSIVE (carried
out, but the result does not decide), PARTIAL, SUPERSEDED, IN-PROGRESS, SUCCEEDED.
Dependencies: list the IDs a result or target relies on in "Depends on" (results, targets, conjectures). A result
can be VERIFIED only if everything it depends on is VERIFIED; otherwise mark it CONDITIONAL(<IDs>).

## 1. Results

| ID | Result (exact statement or pointer) | Status | Depends on | Evidence | Reviewed / verified (by, date) |
|---|---|---|---|---|---|
| R1 | lemma A | VERIFIED | | `ev.md` | reviewer, 2026-10-01 |
| R2 | bound under conjecture | VERIFIED | R1, T1 | `ev.md` | reviewer, 2026-10-02 |
| R3 | corollary of retracted lemma | UNVERIFIED | R4 | `ev.md` | |
| R4 | old lemma | RETRACTED | | `ev.md` | |
| R5 | loop a | UNVERIFIED | R6 | `ev.md` | |
| R6 | loop b | UNVERIFIED | R5, Z9 | `ev.md` | |
| R7 | conditional bound | CONDITIONAL(T1) | R1, T1 | `ev.md` | |

## 2. Data and numerical evidence

| ID | Test / experiment / analysis | Range or sample covered | Result | Evidence |
|---|---|---|---|---|

## 3. Open targets (ranked)

| ID | Target statement | Would give | Depends on | Why hard / barrier |
|---|---|---|---|---|
| T1 | conjecture H | b | | open problem |
| T2 | extension to r=3 | b+ | R1 | |
| T3 | sharper constant | | R7 | |

## 4. Routes tried

| ID | Date | Route (one line) | Outcome | Stops at (barrier or step) | Evidence | Reopen only if |
|---|---|---|---|---|---|---|
| X1 | 2026-10-01 | sieve route | FAILED | square-root barrier | `ev.md` | new estimate |
| X2 | 2026-10-03 | big computation | BLOCKED | | `ev.md` | |
| X3 | 2026-10-04 | numerics on small cases | INCONCLUSIVE | does not reach the critical range | `ev.md` | larger k |

## 5. Barriers

| Barrier | What it says | Routes that hit it |
|---|---|---|

## 6. Stop rules

- Budget: <time / compute / money available for this goal>
- Stop or pivot when: <e.g. N consecutive routes stop at the same barrier; budget spent; review date reached>
- Review date: <YYYY-MM-DD>

## 7. Log

- 2026-10-29: ledger created.
