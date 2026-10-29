# Experiment-integrity checklist

Work through the sections that apply. For each item, record in the design ledger or the report: checked how, result, evidence.

## 1. Text versus code

- [ ] Every methodological claim in the text (design, n, seeds, pairing, splits, exclusions, preprocessing, search space, tests) maps to code that implements it.
- [ ] The numbers of runs, seeds and instances in the text equal those in the run manifests and logs.
- [ ] Every number in the text, tables and figure captions was written to a result file by code. Numbers computed only in notebooks or ad-hoc scripts are either persisted or removed.
- [ ] Result files on disk are not newer than the manuscript. If they are, the text may describe an older run (`ls -lt` results versus manuscript).
- [ ] Labels, numbering and names agree across text, tables, figures and code. Proposition, figure and table numbers in hand-written strings are a common place for disagreement.

## 2. Randomness

- [ ] Random numbers are drawn unconditionally, then used or discarded. No draws inside conditions, short-circuit operators or one-sided branches (scan codes R1, R2).
- [ ] Compared arms, conditions and parameter values use the same instances: per-instance seeds derived from an instance ID, not consecutive draws from one global stream (R3).
- [ ] Sensitivity analyses vary only the parameter, not the scenarios. If a sensitivity curve is non-monotone where theory says monotone, suspect stream desynchronization first.
- [ ] The number of seeds is reported, and results are summarized across seeds with their spread.

## 3. Fallbacks, sentinels and errors

- [ ] Every fallback branch is listed, with how often it fired in the reported runs (S1–S4).
- [ ] No sentinel (0, 360, inf, NaN replaced by 0, an epsilon-floored ratio) reaches a reported table as if computed.
- [ ] A fix to a fallback is applied at every call site (search the whole code base).
- [ ] Errors are counted and reported, not swallowed.
- [ ] Fallback outputs are new and valid. For example, a search fallback must not return a point that was already evaluated; that is how a controller re-measured the same point 1201 times.

## 4. Sample size and tails

- [ ] Rerun with more samples (×2) or harder cases. Look at the minimum and maximum, the failures, the stop reasons and the budget exhaustion, not only the mean.
- [ ] A "100% success" or "zero failures" claim is supported by enough runs to make it meaningful (state the count).
- [ ] Rare-event claims have a power or interval statement.

## 5. Numerics

- [ ] Quantities with closed forms are reported from the closed form; grid and Monte Carlo values are labeled as approximations.
- [ ] Grid or step-size convergence is checked for reported values (halve the step and compare).
- [ ] Solver status, iteration limits, tolerances and convergence flags are checked for every reported run.
- [ ] Wall-clock times are reported as orders of magnitude (they change on every run), unless they come from a one-off official record.

## 6. Measurement validity (lab, field, software and system measurements)

- [ ] Observer effect: compare with and without instrumentation, or verbose logging, or probes.
- [ ] Order and carry-over: use a fresh state per round (new accounts, paths, samples, subjects), or randomize or counterbalance the order.
- [ ] Exact matching: identifiers and paths are matched with delimiters at both ends. A pattern for a file name must not match its siblings (`key` vs `key.pub`).
- [ ] Counting tools behave as assumed. For example, `grep -c` exits with status 1 and prints 0 when there is no match.
- [ ] Every counterintuitive or very large effect is followed by a control round that changes only the suspected confound.
- [ ] Calibration and blanks or negative controls are run and reported.

## 7. Statistics and validation

- [ ] The number of analyses, models or configurations tried is counted. Selection uses held-out data, or the multiplicity is corrected.
- [ ] Standard errors account for clustering and correlated units (time windows, subjects, sites, assets).
- [ ] Splits respect the dependence structure (time, group, subject). No information from test data reaches preprocessing, feature selection, tuning or early stopping (scan code L1).
- [ ] Baselines are tuned with the same budget as the proposed method.
- [ ] Preregistered analyses are distinguished from exploratory ones in the text.

## 8. Figures

- [ ] Numbers in titles, annotations and legends are read from result files (P1).
- [ ] Axis ranges match the claim. "Nearly constant" needs an axis that includes zero or a visible baseline. Auto-scaled axes can turn a 15% change into a cliff.
- [ ] Error bars state what they are (SD, SE, CI) and over what (seeds, subjects, folds).

## 9. The project's own checks

- [ ] Numbers are matched with boundaries (`(?<![0-9.])value(?![0-9])`) and with a context window. Short numbers ("12", "1000") are never matched without context.
- [ ] Rounding uses decimal arithmetic (`Decimal(str(v)).quantize(..., ROUND_HALF_UP)`); binary float formatting rounds inconsistently.
- [ ] Reverse checks list values that were corrected, so that they cannot reappear.
- [ ] Checks run in the required order. Freshness hashes chained across steps produce false failures, or stale passes, when they run out of order.
- [ ] Checks fail loudly. A check that cannot find its input reports an error, not a pass.

## 10. Domain notes

- **Simulation and modeling.** Seeds per instance; closed forms; convergence; edge-case inputs (fewer than k points, empty sets); fallbacks in optimizers and planners.
- **Machine learning.** Data leakage (preprocessing, duplicates across splits, temporal leakage); tuning on test data; seed variance; baselines retuned; benchmark contamination.
- **Lab and clinical data.** Blinding and allocation concealment as implemented, not as planned; exclusions applied consistently; batch effects; units and calibration.
- **Software and system measurements.** Observer effects; caching and server-side state; warm-up; exact matching; clock and timezone handling.
- **Finance and backtests.** Look-ahead bias; survivorship; transaction costs and fills; multiple strategies searched; correlated assets (clustered t); out-of-sample by time.
