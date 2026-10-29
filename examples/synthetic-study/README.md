# Worked example: a quick mock review of a synthetic clinical-prediction paper

This is a complete run of `/mock-review --quick` on an invented manuscript, followed by the library's scripts on the same material. It shows what each part of the library catches, what it misses, and how its claims were verified. Everything here is synthetic: the paper, the hospitals, the numbers and reference [3] do not exist.

| | |
|---|---|
| Manuscript | [`study/paper.md`](study/paper.md): a gradient-boosting model for 30-day readmission, with code ([`study/analysis/`](study/analysis/)), results ([`study/results/metrics.json`](study/results/metrics.json)) and a bibliography ([`study/refs.bib`](study/refs.bib)); the data are "not shareable" |
| Planted problems | 16, plus one correct control ([`ANSWER_KEY.md`](ANSWER_KEY.md), added only after the review finished) |
| Target venue | PLOS ONE; its criteria were fetched verbatim from the official page ([`review/criteria.txt`](review/criteria.txt)) |
| Run | 2026-10-29; main session and two fresh subagents, all Claude; attacker about 3.5 minutes, defender about 5 minutes |
| Review files | [`review/kill_memo.md`](review/kill_memo.md), [`review/defense.md`](review/defense.md), [`review/verification.md`](review/verification.md), [`review/quick_report.md`](review/quick_report.md), [`review/verify.py`](review/verify.py) |

## How the run went

1. **Pack and pin.** The study was committed to a scratch git repository and packed with `review_pack.py pack`. `PIN.json` recorded the SHA-256 of `paper.md`. The answer key existed only in the main session.
2. **Attack.** A fresh subagent, allowed to read only the pack, the criteria and `PIN.json`, wrote a 200-word rejection memo with three kill arguments: the calibration values are random numbers (K1); "significantly outperforms" does not follow, because of tuning on the test split, leaky preprocessing, unpaired seeds and no test (K2); and the secondary numbers have no code behind them and several are impossible (K3). Its working notes recomputed 10 numbers with the standard library, and it checked PubMed for prior work. The list of files it read shows that it stayed inside the pack.
3. **Defend.** A second fresh subagent, seeing only the pack and the memo, conceded all three arguments as FIXABLE with new results, sub-claim by sub-claim, with its own recomputations. It disputed one sub-claim: the GRIM argument assumes whole-day stays, which the paper never states. It also found two bibliography problems in the pack that the attacker had not raised.
4. **Verify.** The main session recomputed every number in its own copy ([`review/verify.py`](review/verify.py)), reread each code path, resolved the two prior-work PMIDs, and recorded the innocent explanations it ruled out. All three kill arguments were confirmed. GRIM stayed **partially confirmed**, because a fractional length of stay cannot be excluded from the paper.
5. **Report.** [`review/quick_report.md`](review/quick_report.md) concludes: fix and rerun first; a full review is not worth running on this version.

## Scorecard

"Quick review" means anywhere in the memo, the attacker's notes or the defense, after main-session verification. "Scripts" means the bundled scripts run on their own, after the fixes listed below.

| # | Planted problem | Quick review | Scripts |
|---|---|---|---|
| P1 | Preprocessing fitted on all data | ✅ K2 | ✅ `integrity_scan` L1 (cross-function rule added in this run) |
| P2 | Tuning on the test split | ✅ K2 | ✅ `integrity_scan` L2 (rule added in this run) |
| P3 | Unpaired seeds behind a "paired" claim | ✅ K2 | ◐ `integrity_scan` R3 lists both seed lists (added in this run); a reader compares them |
| P4 | "Significantly" with overlapping intervals | ✅ K2 (Welch p = 0.17) | ✅ `number_audit stats` overlap; `hedge_scan` OS |
| P5 | Abstract AUC 0.83 vs 0.81 | ✅ notes and defense | ✅ `number_audit trace`: orphan (fixed in this run) |
| P6 | Abstract n 12,480 vs 12,840 | ✅ K3 | ✅ `number_audit trace`: orphan |
| P7 | Placeholder calibration values | ✅ K1, plus a Brier score worse than predicting the prevalence | ✅ `integrity_scan` X1 (the TODO marker) |
| P8 | F1 promised, never computed | ✅ notes and defense | ✅ `integrity_scan` X2 |
| P9 | t(118) = 1.20 with p = .003 | ✅ K3 | ✅ `number_audit stats` (GROSS: significance flips) |
| P10 | Impossible mean length of stay (GRIM) | ◐ notes; disputed by the defense; partially confirmed | ✅ `number_audit stats` GRIM (phrasing support added in this run) |
| P11 | 25% that should be 20% | ✅ notes and defense | ✅ `number_audit stats` delta |
| P12 | OR outside its CI | ✅ K3 | ✅ `number_audit stats` OR CI |
| P13 | Causal language and policy advice | ✅ K3 and defense | ❌ wording outside the editor-facing sections is not scanned |
| P14 | False "first" claim | ✅ memo footnote (novelty is not a PLOS ONE criterion); PMIDs verified | ◐ `hedge_scan` O flags the claim (pattern broadened in this run); refuting it needs `novelty-audit` |
| P15 | Wrong year; fabricated, uncited reference | ✅ defense | ✅ `refcheck` YEAR_MISMATCH and NOT_FOUND |
| P16 | Defensive abstract, work-report narrative | ❌ by design: kill memos ignore wording | ✅ `hedge_scan` D2, D4, D5, D16, D15 |
| C1 | Correct control 1,610/12,840 = 12.5% | ✅ recomputed as consistent | ✅ `number_audit stats` k/n ok (recognized after this run's fix) |

**Found by the review but not planted:**
- the Brier score of 0.12 is worse than the no-information Brier score of 0.110, which contradicts "excellent calibration";
- misclassification rates of 16–20% are worse than the 12.5% error of predicting "no readmission" for everyone;
- df = 118 is implausible for a comparison within a cohort of 12,840;
- there is no data availability statement;
- the validation subsample and the noon-discharge exposure are never defined in the methods.

The two layers complement each other. The quick review found the problems that change the conclusion and the problems that need reasoning, such as the Brier and base-rate contradictions. The scripts found the mechanical problems deterministically, including the wording and the bibliography, which a kill memo ignores by design. Neither layer alone covered all 16 planted problems.

## What this run changed in the library

Running the scripts on this study exposed gaps, which were fixed in the same commit, each with a regression test:

| Skill | Gap found | Fix |
|---|---|---|
| number-audit | `trace` counted the manuscript as its own source when run from another directory, so the abstract's 0.83 looked "text-only" | The manuscript is excluded however the paths were written |
| number-audit | GRIM missed "Mean length of stay … was 4.37 days (n = 23)" | Words between "mean" and the value are allowed; continuous quantities (AUC, rates, scores) are skipped |
| number-audit | "84.23%；n=6" in a Chinese manuscript was read as a sample size | GRIM % no longer crosses full-width punctuation |
| number-audit | "1,610 of 12,840 discharges (12.5%)" was not recognized | Thousands separators and unit words are allowed in k-of-n checks |
| number-audit | The overlap check reported the previous sentence's line | It reports the sentence's own line |
| experiment-integrity | Leakage was missed when preprocessing and splitting live in different functions | L1 now checks across functions |
| experiment-integrity | Selection on the test split had no rule | New code L2 |
| experiment-integrity | Seed lists such as `GBM_SEEDS = [0, …]` were not listed | R3 lists them |
| cite-verify | Crossref keeps "A Systematic Review" in a separate subtitle field, which caused a false TITLE_MISMATCH | Subtitles are appended before comparing |
| paper-polish | "The first machine-learning model" was not flagged | The O pattern covers more nouns and hyphenated modifiers |
| novelty-audit | `lit_graph resolve` did not accept PMIDs | PMID and PMCID are accepted |
| mock-review | The attacker prompt said "read only the pack" but required `criteria.txt`; whether the defender may see the attacker's recomputations was unclear | Both prompts now name every allowed file |

## Limits of this example

- It is one run on one synthetic paper. Model output varies between runs, and real manuscripts hide problems less densely.
- The planted problems were written by the same model family that reviewed them.
- Without data, nothing could be rerun. Every confirmation is at tier S: source and results read, not rerun.
- The review used English, so that the example is readable in this repository. By default, the skill writes reports in the user's language.

## Reproduce

```bash
# scripts only (offline, seconds)
S=examples/synthetic-study/study
python3 skills/number-audit/scripts/number_audit.py stats $S/paper.md --out /tmp/demo/stats
python3 skills/number-audit/scripts/number_audit.py extract $S/paper.md --out /tmp/demo/na
python3 skills/number-audit/scripts/number_audit.py trace /tmp/demo/na/numbers.json --repo $S --regions abstract
python3 skills/experiment-integrity/scripts/integrity_scan.py $S
python3 skills/paper-polish/scripts/hedge_scan.py $S/paper.md
python3 -I skills/cite-verify/scripts/refcheck.py check $S/refs.bib --all --out /tmp/demo/refcheck   # online
python3 examples/synthetic-study/review/verify.py $S

# the review itself (in Claude Code): copy study/ into a new git repository first, without ANSWER_KEY.md
/mock-review <that repository> "PLOS ONE" --quick
```

The offline script results are pinned by `SyntheticStudy` in [`tests/run_tests.py`](../../tests/run_tests.py).
