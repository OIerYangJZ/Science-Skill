# Claim ledger and calibration of claim strength

Defensive writing and overclaiming are two sides of the same problem: the strength of the wording does not match the strength of the evidence. The ledger pins each claim to its evidence, and the evidence then determines which verb to use and which qualifiers to add. The rules below apply across disciplines; Section 2 gives evidence levels by research genre.

## 1. Ledger format

Save as `polish/<date>/claim_ledger.md`. The scope is every claim in the abstract, introduction, conclusion, and cover letter: any sentence stating what this paper found, proved, measured, or claims counts as one claim.

| ID | Claim (verbatim, location) | Evidence type | Premises or conditions | Source in main text | Current strength | Target wording | Notes |
|---|---|---|---|---|---|---|---|
| C1 | "Any compiler that … obeys …" (abstract, sentence 5) | T1 | Grid inputs; correct on every valid stream | Thm 1, `main.tex:962` | Calibrated | "we prove that any such compiler must …" | |
| C2 | "orders of magnitude more $T$ states" (abstract, sentence 16) | C2 | A single, disclosed QRE model; only one benchmark | Sec. 8, `qre_results.csv` | Overstated (baseline not named) | "385–1,753× vs Qiskit opt3 … TKET avoids the gap" | This number does not follow from the theorem |
| C3 | "Social contact causes microbiome convergence" (abstract, concluding sentence) | O1 | Observational study, one population | Table 2, Fig. 3 | Overstated (causal wording) | "Social contact was associated with microbiome similarity, independent of diet" | Illustrative |

"Current strength" takes one of three values: **understated** (defensive), **calibrated**, **overstated** (overclaiming).

## 2. Evidence levels and corresponding wording (by research genre)

One principle applies to all genres: **make the wording as strong as the evidence, no more and no less; state conditions next to the conclusion, and only once.**

### Theory / mathematics

| Level | Evidence | Wording | Qualifiers |
|---|---|---|---|
| T1 | Theorem with a complete proof in the paper | "we prove", "X requires Y", "any … must …" (simple present tense) | No modal verbs; build conditions into the subject or a clause |
| T2 | Proof that relies on an external unproven assumption or conjecture | "we prove … assuming H", "Under H, …" | Place the assumption right next to the conclusion; it must not be omitted from the abstract |
| T3 | Construction or upper bound | "we construct", "… attains … within a constant factor" | State the model and the parameter range |
| T4 | Heuristic argument or conjecture | "we conjecture", "heuristically" | Give the evidence that supports it |

### Experiments (laboratory experiments, randomized controlled trials)

| Level | Evidence | Wording | Qualifiers |
|---|---|---|---|
| X1 | Preregistered randomized controlled trial or controlled experiment, replicated | "X reduced / increased Y by …" (causal wording permitted) | Effect size + confidence interval; sample and population |
| X2 | Single controlled experiment | "in our experiments, X reduced Y …" | Conditions, sample size; state that it has not yet been replicated |
| X3 | Pilot experiment, exploratory analysis, post hoc subgroup analysis | "in an exploratory analysis …", "pilot data indicate …" | Label explicitly as exploratory; keep out of the abstract headline |

### Observational studies (cohort, case-control, cross-sectional, survey, ecological studies)

| Level | Evidence | Wording | Qualifiers |
|---|---|---|---|
| O1 | Association analysis, adjusted for confounding | "X was associated with Y (OR …, 95% CI …)" | **Do not use** causes, leads to, effect of, drives, results in |
| O2 | With a causal identification strategy (instrumental variables, regression discontinuity, difference-in-differences, Mendelian randomization, etc.) | "consistent with a causal effect of X on Y under [assumption]" | State the identifying assumptions next to the conclusion |
| O3 | Descriptive analysis | "X was more common among …" | Do not interpret as a mechanism |

### Computation / simulation / machine learning

| Level | Evidence | Wording | Qualifiers |
|---|---|---|---|
| C1 | Exhaustive or certified computation over a limited range | "exhaustive enumeration up to N shows" | The range must be stated |
| C2 | Benchmarks or simulations | "on [benchmarks / settings], X outperforms Y by …" | Datasets, number of seeds, variance; comparators must be tuned to their best |
| C3 | Single dataset or single run | "on [dataset], we observe …" | Do not extrapolate to "in general" |

### Qualitative studies

| Level | Evidence | Wording | Qualifiers |
|---|---|---|---|
| Q1 | Thematic analysis, saturation reached, multiple coders | "participants described …", "we identified three themes …" | State the context, sample, and transferability; do not claim universality |

### Reviews and meta-analyses

| Level | Evidence | Wording | Qualifiers |
|---|---|---|---|
| R1 | Systematic review or meta-analysis conducted according to PRISMA | "pooled estimate …", "the evidence indicates …" | State the quality of evidence (e.g., GRADE) and the heterogeneity |

### Interpretation and implications (all genres)

Write "this means / implies" only when it follows from the results; when it does not, write "a possible consequence would be", or leave it out.

## 3. Rules

1. **Do not upgrade.**
   - Numerical, single-experiment, or observational evidence must not use prove, establish, or demonstrate that … causes.
   - Do not present a non-effective asymptotic result as if it were a number at practical parameters.
2. **Do not downgrade.** Proven conclusions and the primary endpoints of preregistered trials must not be written as "suggests", "may", or "we attempt to show".
3. **State conditions only once, right next to the conclusion**; do not repeat them later as disclaimers.
4. **The following words require matching evidence:**
   - law, universal, fundamental, optimal, tight: require a theorem that says exactly this;
   - first, for the first time, novel: require support from a Pool B or novelty-audit search, and may appear at most once in the whole paper;
   - orders of magnitude, dramatically, substantially: require a named comparator that is not a straw man;
   - significant(ly): use only in the statistical sense, and report the test; for the non-statistical sense, use substantial, marked, etc. instead;
   - causes, leads to, effect of, drives: require support from an experimental design or a causal identification strategy.
5. **Match the subject to the object of the evidence.**
   - If the theorem is about "processes in model M", the abstract must not say "compilers".
   - If the study population is "adults in a given region", the abstract must not say "people".
6. **Use only one headline number**, with the comparator in the same sentence. For empirical studies, include a confidence interval or another measure of uncertainty.
7. **When a result does not hold or is not meaningful under practical conditions** (e.g., a non-effective bound, or a statistically significant result with a very small effect size), the abstract and introduction must state clearly what does hold under practical conditions. If that cannot be done, do not make it the headline.
8. **Origin of the technique or method**: when you use a standard argument or an existing method, acknowledge it directly in the introduction and state what is new.
9. **Keep qualifiers required by field norms.** Associational wording in observational studies, labels on pilot experiments, confidence intervals, and limitations paragraphs required by reporting guidelines are not defensive. What should be removed are disclaimers and dilution surrounding "this paper's contribution" itself (see `defensive-patterns.md`).

## 4. Writing the scope sentence

- **Defensive:** "[Result]. This does not hold for Z, and we make no claim about W. Note that our model assumes V."
- **Calibrated:**
  - Theory: "For [class defined by V], we prove [result]." Then write one scope paragraph at the end of the introduction, ending on a design principle or an open question.
  - Empirical: "In [population / setting], X was associated with Y (…). [Design] does not establish causality; [the specific next study] would." State the limitations only once, and end on the next study.

## 5. Checklist after each rewrite round

- [ ] Every sentence in the abstract maps to a ledger ID or is a background sentence.
- [ ] For every claim that depends on an assumption (T2, O2), the assumption is stated next to it.
- [ ] No numerical, observational, or exploratory claim uses prove, establish, or a causal verb.
- [ ] Every O, OC, or OS word (flagged by `hedge_scan.py`) has matching evidence.
- [ ] Every number is in the source table of `polish_notes.md` and has been rechecked; statistics have been checked with `number-audit stats`.
- [ ] The new draft adds no conclusion that is absent from the original.
