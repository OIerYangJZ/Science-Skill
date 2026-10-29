# Answer key: planted problems in the synthetic study

The study in `study/` is invented: no patients, no hospitals, no data. It was written to contain the problems below, and this file was added to the repository only after the review in `review/` had finished, so the reviewing subagents could not see it.

Line numbers refer to `study/paper.md` and the files in `study/analysis/`.

| # | Problem | Where | Type |
|---|---|---|---|
| P1 | Preprocessing (standardization, feature selection) is fitted on all data, while the text says "fit on the training set only" | `train.py:27-30`, called at `:67`; `paper.md:21` | Leakage; text contradicts code |
| P2 | The best of 48 configurations is chosen by its AUC on the test split, and that AUC is reported | `train.py:40-48` | Selection on test data |
| P3 | The comparison is claimed to be paired on "the same five … splits", but the models use seeds 0–4 and 10–14 | `train.py:18-19`; `paper.md:25` | Claimed design not implemented |
| P4 | "Significantly outperforms" with no test, and the intervals overlap (0.81 ± 0.02 vs 0.79 ± 0.02) | `paper.md:5`, `:31` | Unsupported comparison |
| P5 | The abstract reports AUC 0.83; the results and `metrics.json` give 0.81 (0.812) | `paper.md:5` | Number drift |
| P6 | The abstract reports 12,480 discharges; the methods and `metrics.json` give 12,840 | `paper.md:5` | Number drift |
| P7 | The calibration values (Brier score, slope) come from a random-number placeholder marked TODO | `evaluate.py:5-9`; `paper.md:5`, `:31`, `:37` | Placeholder data on a result path |
| P8 | The F1 score is promised in the methods; the F1 function is never called and no F1 is reported | `train.py:57`; `paper.md:25` | Metric described but never computed |
| P9 | t(118) = 1.20 gives p ≈ 0.23, not p = .003 | `paper.md:29` | Statistic and p-value disagree |
| P10 | A mean of 4.37 days with n = 23 is impossible for whole-day stays (GRIM) | `paper.md:29` | Impossible mean, if the unit is whole days |
| P11 | "From 20% to 16%, a 25% relative reduction": it is a 20% reduction | `paper.md:31` | Change arithmetic |
| P12 | OR 0.62 lies outside its own 95% CI (0.70–0.96) | `paper.md:33` | Ratio and CI disagree |
| P13 | Causal language and a policy recommendation from an observational association | `paper.md:33`, `:37` | Overclaiming |
| P14 | "The first machine-learning model for 30-day readmission" is false | `paper.md:5` | Novelty overclaim |
| P15 | Reference [1] has the wrong year (2013 instead of 2011); reference [3] is fabricated and never cited | `refs.bib`; `paper.md:43`, `:47` | Bibliography |
| P16 | Defensive abstract ("we attempt to shed light", "may not generalize, and in some cases its accuracy is limited") and a work-report narrative ("We first trained… Then we ran…") | `paper.md:5`, `:11` | Defensive writing |
| C1 | *Control, correct:* 1,610 of 12,840 is 12.5% | `paper.md:29` | Must not be flagged |
