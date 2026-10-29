# Checklist of convention pitfalls

For every item, answer two questions:
1. What convention does the text claim?
2. What do the code, tools, or data actually use?

Base the answers on the source code of the pinned version, the repository data, or the original records, not on documentation or memory.

Sections 1–7 apply to all fields; Section 8 lists common field-specific additions.

## 1. Units and dimensions

- Unit conversions: mg vs. µg, mmol/L vs. mg/dL, eV vs. J, days vs. weeks, currencies and exchange rates; multiplier prefixes (k, M, G; KB vs. KiB).
- Per unit, per person, per case, per year: what is the denominator, and is it consistent?
- Nominal vs. real values (inflation adjustment, base year); purchasing power parity.
- Time basis of concentrations, doses, and rates (daily dose or single dose).

## 2. Percentages, proportions, and changes

- Percent vs. percentage points: "rising from 10% to 15%" is an increase of 5 percentage points, a relative increase of 50%.
- Relative vs. absolute change; multiples (fold change) vs. percent change; log fold change (log2 FC).
- Denominator of a proportion: the full sample, valid responses, or the sample after excluding missing data.
- Whether k/n matches the percentage (`number_audit.py stats` checks "k of n (x%)" automatically).
- Whether group percentages sum to 100% (allowing for rounding); whether the subgroup n values sum to the total n.

## 3. Statistics

- Standard deviation (SD) vs. standard error (SE / SEM); the level of confidence intervals (95% or 90%); credible intervals vs. confidence intervals.
- One-tailed vs. two-tailed tests; whether the test statistic, degrees of freedom, and p value are mutually consistent (`stats` recomputes them).
- Whether multiple comparisons are corrected, and by which method; whether corrected and uncorrected p values are mixed.
- Ratio measures (OR, RR, HR): the confidence interval should be roughly symmetric on the log scale; the point estimate must lie inside the interval.
- Units of regression coefficients (per 1 unit or per 1 SD); whether they are standardized; what the reference group is.
- What "significant" means: statistically significant or practically important.
- Whether sample sizes are consistent throughout: abstract, methods, Table 1, flow diagram.
- Whether repeated-measures or clustered data were treated as independent samples.

## 4. Logarithms, counts, and definitions

- log₂, ln, log₁₀; bits vs. nats; the definition of dB (10 log or 20 log).
- What is counted: events or people; visits or patients; logical or physical quantities; whether one-time costs are included.
- What is averaged over: instances, samples, random seeds, time; mean or median.
- One symbol or abbreviation with two meanings (e.g., K as both alphabet size and a number field; t as both time and T-count).

## 5. Indexing, ranges, and rounding

- 0-based or 1-based; closed or open intervals ("≤ 22" vs. "< 22"); age-group boundaries.
- Integer division and the remainder group: ⌈m/g⌉ groups or m/g groups.
- Rounding: round then compute, or compute then round; whether the number of digits is consistent across locations (2.41 and 2.4 can coexist; 2.41 and 2.50 cannot).
- Dates and time zones; fiscal vs. calendar years; start and end dates of the study period.

## 6. Parameter validity

- Whether a counterexample or lower bound given in the text (e.g., "the constant is at least c₀") conflicts with a parameter used in figures or tables (a smaller c).
- Whether claims such as "other parameters give at most X" or "the optimal choice is …" have been checked with a sweep.
- For values that depend on an assumption, whether the caption states this premise.
- Whether parameters from the sensitivity analyses and the main analysis are mixed up.

## 7. Versions, data, and pipelines

- Whether software, library, and model versions are pinned and match the versions actually used at run time (lock files, manifests, `pip show`, R's `sessionInfo()`).
- Dataset version, download date, inclusion and exclusion criteria; the order of preprocessing steps.
- Machine learning: whether there is leakage between the training, validation, and test sets; whether metrics are micro- or macro-averaged; whether the best single run or the mean over several runs is reported; the number of random seeds.
- Whether the recorded version of the frozen data matches what the text states.

## 8. Field-specific additions

### Physics / quantum information

- Distances and errors: operator norm, up-to-phase (projective) distance, diamond distance, trace distance, fidelity or infidelity. They often differ by a constant factor (e.g., 2) or by a square.
- Whether the error budget is per gate or total; whether the two parts each get ε/2 or each get ε.
- **Example (source-code facts about a public tool):** in pygridsynth 2.0.0, `EpsilonRegion` accepts u satisfying Re(z̄u) ≥ sqrt(1 − ε²/4), and `error()` returns 2·sqrt(1 − Re(z̄u)²). This is the diamond distance, so the up-to-phase operator distance d_proj ≲ ε/2. Treating ε as d_proj shifts all "achieved precisions" and the corresponding gate counts as a whole. Dividing the measured d_proj by the nominal ε reveals it: the ratio is about 0.5.

### Biomedical / clinical

- Dose units and dosing frequency; normalization by body weight or body surface area.
- Intention-to-treat (ITT) or per-protocol; how loss to follow-up is handled.
- Mixing up risk ratios, odds ratios, and risk differences; the basis for computing the NNT.
- Reference ranges and unit systems of laboratory measures (SI or conventional units).

### Chemistry / materials

- Molar vs. mass concentration; the basis for computing yield (limiting reagent).
- Energy units (kcal/mol, kJ/mol, eV); reference states and temperature.

### Economics / social sciences

- Nominal vs. real; base period; seasonal adjustment.
- Coding direction of Likert scales (whether reverse-worded items are reversed); scale sum scores vs. mean scores.
- Weighted vs. unweighted estimates; survey design effects.

### Computer science / machine learning

- Metric definitions (how F1 is averaged; versions and tokenization of BLEU and ROUGE).
- Compute budget: GPU hours; whether parameter counts include the embedding layers.
- Measurement conditions for throughput and latency (batch size, hardware, warm-up).

## 9. Template for the verification steps

```
# 1. Determine the version
pip show <pkg>            # or read the lock file or manifest; R: packageVersion("<pkg>")
python3 -c "import <pkg>, inspect; print(inspect.getsourcefile(<pkg>))"
# 2. Find the acceptance criterion, error function, or metric definition in the source code
grep -n "def error\|epsilon\|def f1\|average=" <path>
# 3. Cross-check with repository data (e.g., the distribution of measured error / nominal parameter, or recompute a summary value from the raw data)
python3 - <<'EOF'
import json; d = json.load(open("data/....json")); ...
EOF
```

Write the conclusion as one sentence: "The text says X; <tool> <version> actually uses Y (source `<file>:<line>`); the data show …; the affected numbers are …".
