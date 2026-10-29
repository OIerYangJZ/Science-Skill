---
name: experiment-integrity
description: Check that the code, data pipeline and measurement procedure behind a paper or report actually do what the text says, and that the experiment design itself is not producing the result. Covers claimed-vs-implemented design (pairing, seeds, sample sizes, splits, exclusions, search budgets), random-stream desynchronization, sentinel and fallback values leaking into results, discretization artifacts, small samples hiding failures, instrumentation and order effects, leakage and multiple testing, misleading figures, and gaps in the project's own automated checks. Any discipline with code or measurements (simulation, modeling, ML, lab and field data, software measurement studies, backtests). Use before submission, after all automated checks pass, when a result looks surprisingly large or clean, or when asked to red-team a finished analysis. Not for checking prose numbers against data (number-audit) or for literature novelty (novelty-audit).
argument-hint: "[manuscript or report] [code/data directory] [--rounds 1|2]"
---

# experiment-integrity: the code does what the paper says, and the design does not manufacture the result

## The problem this skill addresses

Automated checks that compare the text with result files catch drifting numbers. They do not catch a result file that is wrong because the code or the experiment design is wrong. AI assistants write and modify analysis code quickly, and they rarely re-derive whether the code still implements the design the text describes (item 9 of `FAILURE_MODES.md`).

The observed cases behind this skill:
- **A modeling paper whose automated checks were all green.** Two rounds of adversarial review still found 29 problems, three of them in the evidence files themselves:
  - **Pairing claimed but not implemented.** The text claimed a paired comparison on "the same 16 cases"; the two arms used seeds 1–16 and 101–116.
  - **Random-stream desynchronization.** A random draw placed inside a condition (`if cond and rng.random() < p`) shifted the random stream whenever a parameter changed. A sensitivity curve was non-monotone; after the draw was made unconditional it became monotone, and the conclusion got stronger.
  - **Sentinel values reported as results.** An edge-case branch returned a sentinel (`if k < 3: return 360`), and a denominator was floored at `1e-12`. Two table rows showed "0 m, probability 0" that were never computed. The first fix patched only one of the call sites.
  - **Discretization artifacts.** Grid values were reported where closed forms existed (88° vs 89°; an area overestimated by 1.8%).
  - **A small sample hid a failure.** Eight runs looked perfect; sixteen exposed a livelock in which the controller re-measured one point 1201 times. "100% success" was an artifact of sample size.
  - **Figures.** A figure title hard-coded a number that no longer matched the text, and an automatic y-axis made a 15% change look like a cliff.
  - **The check script had holes.** Substring matching let "0.47" pass because it appears inside "10.47", and binary float formatting rounded 1210.05 and 342.55 in opposite directions.
- **A software measurement study.** Three design artifacts each produced a convincing but false "major finding":
  - Verbose tracing changed the measured behavior (an observer effect).
  - Earlier rounds left server-side state that reduced the traffic of later rounds, so cross-round comparisons were contaminated.
  - Matching a file path without an end delimiter counted `id_ed25519.pub` as `id_ed25519`, and a private-key read was reported that never happened.
- **A strategy backtest.** The configuration chosen on the training half scored t = 1.68 on the test half after a 32-configuration search, with correlated assets. A naive reading would have called it an edge.

## Hard rules

1. **Do not change the user's code or data in place.** Work in a scratch copy, a new branch, or a git worktree. Propose fixes as patches. Write outputs to `integrity/<YYYY-MM-DD>/`; inside a git repository, add `integrity/` to `.git/info/exclude` and tell the user.
2. **Leads are not findings.** A scan hit, a suspicious line or an odd number becomes a finding only after it is confirmed by reading the code path, by a targeted rerun, or by an instrumented check. Report confirmed findings, refuted leads and unchecked leads separately.
3. **Quantify the impact.** For each confirmed finding, rerun the affected analysis in the scratch copy and report how the published numbers and conclusions change. "No change" is a result too.
4. **Expensive reruns need the user's go-ahead.** Estimate the runtime and cost from a small sample (including the slow tail) and ask before running anything long or paid. Hand long jobs over with an ETA instead of polling.
5. **Every confirmed problem gets a guard.** Add an assertion, test or check so that a rerun cannot silently reintroduce it (Phase 6). Fix every call site, not only the one that was noticed.
6. Talk to the user and write reports in the user's language. Code, comments and manuscript text keep their original language.

## Phase 0: Intake

- The manuscript or report (any format), and the code, data and run artifacts behind it: scripts, notebooks, configs, run manifests, logs, result files, figure scripts.
- The claimed design: what the text says about samples, seeds, arms, pairing, randomization, splits, exclusions, preprocessing, search budget, statistical tests, solvers and tolerances, instrumentation.
- Existing automated checks (test suites, number checks, CI), and the order in which the pipeline must run.
- Rounds: `1` (default), or `2`, a second round after the first round's fixes, aimed at the design and the guards themselves. In the observed case, the second round was the more valuable one.

## Phase 1: Claimed-design ledger

Extract every methodological claim from the text into `integrity/<date>/design_ledger.md`:

| ID | Claim (text, location) | Where it should be implemented | Verified how | Status |
|---|---|---|---|---|
| D1 | "paired comparison on the same 16 instances" (Sec. 4.2) | `compare.py: run_arm()` | printed seeds per arm | MISMATCH: arms use seeds 1–16 and 101–116 |

Typical claims to extract: n per arm and per condition; seeds and instances; pairing or blocking; randomization and allocation; train / validation / test split and its unit (time, group, subject); exclusion rules; preprocessing order; hyperparameter or configuration search space; number of analyses tried; stopping rules; solver tolerances and convergence; closed-form vs numerical quantities; instrumentation and logging levels; the order of measurement rounds.

## Phase 2: Static scan

```
python3 <skill-dir>/scripts/integrity_scan.py <code-dir> --out integrity/<date>
```

The scan lists leads by code; each lead must be read in context.

| Code | Pattern |
|---|---|
| S1 | Sentinel guard in a denominator (`max(d, 1e-12)`, `d + eps`) |
| S2 | Constant returned on an edge-case branch of a function that otherwise computes |
| S3 | Swallowed exception (`except: pass`, `return 0`) |
| S4 | Missing values replaced by a constant (`fillna(0)`, `nan_to_num`) |
| R1 | Random draw inside a condition or on the right of `and` / `or` |
| R2 | Random draw in only one branch of an `if` |
| R3 | Seed list per file, to compare across arms |
| P1 | Number hard-coded in figure text |
| L1 | Preprocessing fitted before the train/test split |
| G1 | Check script testing numbers by substring |
| G2 | Shell matching pitfalls (`grep -c … \|\| echo 0`, paths without end delimiters) |

Python gets an AST-based scan; R, Julia, MATLAB and shell get a lighter regex scan. Languages and patterns not covered are checked by reading, following `references/checklist.md`.

## Phase 3: Claim-to-code verification

For each row of the design ledger:
1. Find the implementing code and read the whole path, including fallbacks and error handling.
2. Verify by instrumentation in the scratch copy: print or log seeds, instance IDs, split membership, the number of fallback triggers, the number of configurations evaluated, and the solver status.
3. Mark the row MATCH, MISMATCH (with evidence) or UNVERIFIABLE (with the reason).

Search the code for every call site of any function involved in a mismatch. In the observed case, the first fix covered one call site, and another loop kept producing sentinel rows.

## Phase 4: Design checks

Work through `references/checklist.md`. The checks that most often change conclusions:
- **Randomness.** Draw random numbers unconditionally, then decide whether to use them. Compared arms use the same instances. Per-arm seeds are derived from a common instance ID.
- **Fallbacks and sentinels.** Count how often each fallback fires in the reported runs. A reported value that is a sentinel must be removed or labeled.
- **Sample size and tails.** Double the number of runs, or add stress cases, and look at the worst runs, failures and stop reasons, not only the means.
- **Numerics.** Report closed forms where they exist. Check grid or step-size convergence. Check solver termination status.
- **Measurement validity.** Compare runs with and without instrumentation. Use a fresh state per round, or randomize the order. Match identifiers with exact delimiters. For any surprisingly large or counterintuitive effect, design a control round that changes only the suspected confound before concluding.
- **Statistics.** Count every analysis or configuration tried (the garden of forking paths); hold out data or correct for multiplicity; cluster standard errors for correlated units; split by time or group where needed; no information from test data may reach training or selection.
- **Figures.** Use axis ranges that match the claim (include zero, or show the baseline when the claim is "flat" or "small"). Read numbers in titles and annotations from result files.

## Phase 5: Impact

For every confirmed finding, rerun the affected analysis in the scratch copy (rule 4 applies) and record before/after values for every number, table and figure it touches, and whether any conclusion changes. Put this in `integrity/<date>/impact.md`.

## Phase 6: Guards

Turn every confirmed problem into a permanent check that runs with the project's pipeline:
- assertions in the code (e.g. `assert seeds_arm_a == seeds_arm_b`; fail instead of returning a sentinel);
- tests over the failure case (the edge-case input, the doubled sample);
- number guards for the reported values (`number-audit`, Phase 7);
- reverse checks: strings that were corrected must not reappear.

Also check the guards themselves: boundary-delimited matching, decimal rounding (`Decimal(...).quantize(..., ROUND_HALF_UP)`), context windows for short numbers, the pipeline run order, and no assertions on wall-clock times, which change on every run.

## Phase 7: Report

Write `integrity/<date>/report.md` in the user's language, conclusions first:
1. **Confirmed findings**, ordered by impact on conclusions: the claim, what the code does, the evidence, before/after numbers, the fix (patch path), and the guard added.
2. **Design-ledger summary**: how many claims matched, mismatched, or could not be verified.
3. **Refuted leads**: briefly, so that they are not re-investigated.
4. **Not checked**, with reasons (e.g. needs a long or paid rerun the user has not approved).
5. **Commands** to reproduce the scan, the reruns and the guards.

With `--rounds 2`, run Phases 1–6 again after the fixes, this time attacking the design and the new guards.

## Final report to the user (concise, in the user's language)

- The number of confirmed findings and the ones that change a conclusion, one sentence each.
- The guards added, and how to run them.
- What still needs the user's decision: reruns to approve, or text to change.
- The paths of the report, the design ledger and the patches.
