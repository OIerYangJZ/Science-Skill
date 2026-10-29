# Defense against the kill memo

**Version defended:** the pack pinned in PIN.json (head `a74b31e57c2b46760e9b0c2741e6d40bc8892552`). The sha256 of `pack/paper.md` is `1279a53b…e8f8`, which matches PIN.json. The copies in `work-defender/` are byte-identical to the pack.

**Bottom line.** I checked every factual sub-claim in the memo against the paper and the code, or recomputed it. None can be rebutted from the paper. All three kill arguments are correct for the manuscript as submitted, and it should not be sent out in this form. Each problem can in principle be fixed, because the authors hold the data. However, almost every fix needs a rerun on that data, and the two headline claims may not survive the rerun: "significantly outperformed logistic regression" and "well calibrated".

| Kill | Verdict | New results needed? |
|---|---|---|
| K1 (calibration values are random numbers) | Conceded. FIXABLE only by running the real calibration analysis. Until then the calibration claims must be withdrawn. | Yes |
| K2 ("significantly outperforms LR" does not follow) | Conceded. FIXABLE, but every sub-claim needs a rerun with a corrected pipeline. The word "significantly" must go now. | Yes |
| K3 (unsupported or impossible secondary numbers) | Conceded. FIXABLE. Some items are text-only fixes, but most need recomputation. One sub-claim from the notes (GRIM) is not established. | Mostly yes |

---

## K1. Calibration was never measured; the reported values are random numbers

### K1a. The calibration values come from a random-number placeholder. Verdict: true, FIXABLE (needs new results)

**Evidence.**
- `analysis/evaluate.py:5-9` takes no predictions and sets no seed:
  ```
  def calibration_report():
      # TODO: replace with the real calibration analysis on held-out predictions
      brier = float(np.random.uniform(0.11, 0.13))
      slope = float(np.random.normal(1.0, 0.02))
  ```
- `analysis/train.py:76` calls it with no arguments (`"calibration": calibration_report(),`). Its output goes straight into `results/metrics.json:7-9` (`"brier": 0.121, "slope": 0.99`).
- No other file in the pack computes a Brier score or a calibration slope. A grep for `brier` and `slope` finds only these lines.
- PIN.json records `"tracked_changes_uncommitted": false`, so this code is the committed pipeline that produced metrics.json.
- The paper reports these values as findings in three places:
  - paper.md:5 (Abstract): "It was also well calibrated (Brier score 0.12)."
  - paper.md:31 (Results): "Calibration was excellent (Brier score 0.12, calibration slope 0.99)."
  - paper.md:37 (Discussion): "…and is well calibrated."
- paper.md:25 promises calibration "on held-out predictions". The code never computes it.
- The paper has no passage that answers this point.

**Minimal change.**
1. Implement `calibration_report(y_test, p_test)` for each split's held-out predictions:
   - Brier score, reported next to the no-information Brier π(1−π) of that split, or as a scaled Brier;
   - calibration intercept and calibration slope, from a logistic regression of y on logit(p);
   - a calibration plot.
2. Report the mean ± SD over the splits.
3. Replace the numbers at paper.md:5, 31 and 37 with the new ones, and keep the words "well/excellent" only if those numbers support them.
4. Until the rerun exists, delete all three calibration claims.
5. The response letter should say plainly that the submitted calibration values were placeholders. Even with the data, the submitted values cannot be reproduced, because no seed is set.

**New results:** yes. They require the data, which only the authors have.

### K1b. A Brier score of 0.12 is worse than the no-information Brier score, so it is incompatible with a calibrated model. Verdict: true, FIXABLE (same fix as K1a)

**Evidence (my own recomputation, `work-defender/scratch/recompute.py`).**
- Prevalence: 1610 / 12840 = 0.12539. This matches paper.md:29.
- No-information Brier score: π(1−π) = 0.10967.
- For a perfectly calibrated model (E[y | p] = p), Brier = π(1−π) − Var(p) ≤ 0.1097. The reported 0.121 (0.12 in the text) is above this bound.
- Test-set prevalence variation does not rescue the value:
  - the test split has n = 3852, so the hypergeometric SD of test prevalence is 0.0045;
  - even at +3 SD (test prevalence 0.139), the no-information Brier is 0.1195, still below 0.121.
- The memo understates its own point. It says "most of" U(0.11, 0.13) lies above 0.1097, but the whole range does, because 0.11 > 0.1097. Every value the placeholder can produce is worse than predicting the prevalence for everyone.
- One nuance does not help the paper. A slope near 1 does not by itself guarantee calibration-in-the-large, so a model with slope 0.99 and a large intercept error could have a Brier score of 0.12. But such a model is not "excellently" calibrated (paper.md:31). The memo's inference therefore holds against the paper's own claim.
- What the real number should look like: in a simulated, perfectly calibrated logistic-binormal model at prevalence 0.125 and AUC 0.815, Brier = 0.089.

**Minimal change:** as in K1a. The "well calibrated" claim survives the rerun only if the real Brier score is clearly below π(1−π) and the calibration intercept and slope are close to 0 and 1. The misclassification rates at paper.md:31 (see K3b) suggest it may not.

---

## K2. "Significantly outperforms logistic regression" does not follow

### K2a. The GBM is the best of 48 configurations scored on the test split it is reported on, and LR is untuned. Verdict: true, FIXABLE (needs new results)

**Evidence.**
- The grid in `train.py:33-37` has 4 × 4 × 3 = 48 configurations, which matches paper.md:21.
- `run_gbm` (`train.py:43-48`) fits each configuration on Xtr, scores it by `roc_auc_score(yte, …)` on the test split, keeps the maximum, and returns that maximum AUC (`train.py:68`, `[0]`).
- The reported GBM AUC is therefore a best-of-48 score on the test data. It is not the held-out estimate that paper.md:25 promises ("on held-out predictions").
- The paper only says "chosen by a grid search over 48 configurations" (paper.md:21). It never says that tuning used training data, so nothing in the text answers the point.
- LR is `LogisticRegression(max_iter=1000)` with defaults (`train.py:53`), with no tuning.
- The LR point is true but probably minor. The asymmetry in selection is what matters: only the GBM gets optimistic selection on the test set.

**Minimal change.**
1. Tune the GBM inside each training split (inner CV or a validation split carved out of the training data). Evaluate the single chosen model once on the test split.
2. Either tune LR's C in the same inner loop, or state that LR uses default L2 regularization.
3. Revise paper.md:21 to describe the tuning.

**New results:** yes.

### K2b. Scaling and feature selection were fit on all the data, contradicting "training set only". Verdict: true, FIXABLE (needs new results)

**Evidence.**
- `prepare(X, y)` (`train.py:27-30`) fits `StandardScaler` and `SelectKBest(f_classif, k=40)` on the full X and y.
- `main()` calls it at `train.py:67`, before any `train_test_split`, so feature selection sees the test labels.
- The paper (paper.md:21) says the opposite: "All preprocessing (standardization and univariate feature selection of the 40 most informative predictors) was fit on the training set only, to avoid information leakage."
- Both models use the same leaky X. The leak makes both absolute AUCs optimistic, but its effect on the GBM–LR difference has no known sign. Its size cannot be estimated without the data.

**Minimal change.**
- Put StandardScaler, SelectKBest and the model in one sklearn `Pipeline`, fit inside each training split (and inside the inner tuning loop from K2a), then rerun.
- Rewriting the text to match the code would describe a leaky design, so it is not an acceptable fix.

**New results:** yes.

### K2c. The split seeds differ (0–4 versus 10–14), so the comparison is unpaired. Verdict: true, FIXABLE (needs new results)

**Evidence.**
- `train.py:18-19` sets `GBM_SEEDS = [0, 1, 2, 3, 4]` and `LR_SEEDS = [10, 11, 12, 13, 14]`.
- Each seed is passed as `random_state` to `train_test_split` (`train.py:41`, `train.py:52`), so the two models never see the same split.
- paper.md:25 states the opposite: "Both models were evaluated on the same five random 70/30 train/test splits, so that the comparison is paired."

**Minimal change:** use one list of seeds for both models, keep the per-split AUCs, and rerun.

**New results:** yes.

### K2d. No significance test exists; a Welch test on metrics.json gives p = 0.17. Verdict: true, FIXABLE (the text fix is immediate; a supported claim needs new results)

**Evidence.**
- Neither the code nor the paper contains a test statistic or p-value for the comparison. paper.md:31 says only "significantly outperforms … (0.81 ± 0.02 vs 0.79 ± 0.02)".
- My recomputation of the Welch test:
  - `np.std` uses ddof = 0, so the sample SDs are 0.0201 (GBM) and 0.0235 (LR);
  - difference 0.021, SE 0.0138, t = 1.52, Welch df = 7.82, **p = 0.168**;
  - using the paper's rounded values (0.81 ± 0.02 vs 0.79 ± 0.02): t = 1.58, df = 8, p = 0.153.
- The memo's number is confirmed.
- **Fairness caveat, not a rebuttal.** A Welch test on unpaired split-level AUCs is not the right test for the design either, and p = 0.17 does not show that the models are equivalent. With properly paired splits:
  - a naive paired t-test would reach p < .05 if the SD of the per-split AUC differences were below 0.017;
  - a Nadeau–Bengio corrected test would need that SD below 0.0095.
  - It is unknown whether the corrected pipeline meets either threshold. Removing the selection optimism from K2a will also shrink the 0.021 gap.
- The memo's working notes argue from a single-split Hanley–McNeil SE (I get 0.0122 as well). That argument ignores the correlation between two models' AUCs on the same test set, so it would not settle the question once the splits are paired.

**Minimal change.**
- Now (text only): replace "significantly outperformed" (paper.md:5) and "significantly outperforms" (paper.md:31) with a descriptive statement such as "had a higher mean AUC (0.81 vs 0.79; difference not formally tested)". Soften "improves" in paper.md:37 accordingly.
- After the rerun from K2a–c: report the paired per-split differences with a corrected resampled t-test, or DeLong tests per split. Keep "significant" only if that test supports it.

**New results:** yes, if any claim of superiority is to be kept.

---

## K3. No code produces the remaining results, and several of them are impossible

### K3a. No code produces the misclassification rates, F1, the age test, length of stay, the readmission count or the OR. Verdict: true, FIXABLE (needs new results)

**Evidence.**
- `train.py` writes only `n`, the AUC means and SDs, and the calibration placeholder (`train.py:70-77`).
- `f1_at_threshold` (`train.py:57-62`) is defined but never called; grep finds only its definition. The F1 score promised at paper.md:25 ("the F1 score at a 0.5 threshold") never appears in the Results.
- Nothing in the pack computes any of the following:
  - the 20% and 16% misclassification rates (paper.md:31);
  - the 1,610 readmissions (paper.md:29);
  - the age t-test (paper.md:29);
  - the length of stay in the "chart-review validation subsample" (paper.md:29). This subsample is not described in Methods.
  - the noon-discharge OR (paper.md:33). The noon-discharge exposure is not defined in Methods.

**Minimal change:** add scripts that compute each reported number from the data, write them to results/, and quote them from there. Describe the validation subsample and the noon-discharge analysis in Methods.

**New results:** yes.

### K3b. Misclassification rates of 16% and 20% exceed the 12.5% error of predicting no readmission. Verdict: true, FIXABLE (needs new results)

**Evidence.**
- Predicting "no readmission" for everyone has an error of 1610 / 12840 = 12.54%. Both rates at paper.md:31 ("from 20% to 16%") are worse than that trivial rule.
- For a calibrated model, the expected error of the 0.5-threshold rule is E[min(p, 1−p)] ≤ E[p] = π. In my simulated calibrated model at AUC 0.815, the error is 11.6%.
- So the 16% misclassification rate and "Calibration was excellent" in the same paragraph (paper.md:31) contradict each other. At least one of them is wrong.
- The arithmetic in the same sentence is also wrong (working notes, item 4): (20 − 16) / 20 = 20%, not the "25% relative reduction" stated. The 25% is (20 − 16) / 16.

**Minimal change:**
- compute the confusion-matrix metrics (the promised F1, the misclassification rate and, ideally, sensitivity and specificity) from the held-out predictions of the corrected pipeline;
- report them next to the all-negative baseline;
- fix the relative-reduction arithmetic.

**New results:** yes.

### K3c. t(118) = 1.20 gives p = 0.23, not .003. Verdict: true, FIXABLE (needs new results, or delete the sentence)

**Evidence.**
- My recomputation: t(118) = 1.20 gives a two-sided **p = 0.2325**. Reaching p = .003 at df = 118 would need t = 3.03.
- df = 118 also cannot come from comparing readmitted with non-readmitted patients in the stated cohort: a pooled test there has df = 12,838.
- Even at df = 12,838, p = 0.230.
- The triple (statistic, df, p) at paper.md:29 is internally inconsistent, and nothing in the pack shows which part is wrong.

**Minimal change:** rerun the age comparison on the full cohort and report group means and SDs, t, df and p. As a text-only alternative, delete the sentence, which is not needed for the main claim.

**New results:** yes, unless the sentence is deleted.

### K3d. The OR of 0.62 lies outside its own CI (0.70–0.96), yet it drives a causal discharge policy. Verdict: true, FIXABLE (recomputation for the number; text-only change for the causal language)

**Evidence.**
- The geometric centre of 0.70–0.96 is √(0.70 × 0.96) = 0.820, so 0.62 lies outside its own interval (paper.md:33).
- A CI of the same width around 0.62 would be 0.53–0.73.
- The language is causal:
  - paper.md:33: "discharge before noon leads to lower readmission";
  - paper.md:37: "Hospitals should schedule discharges before noon to reduce readmissions."
- The paper describes no exposure definition, no adjustment set and no causal design for this analysis. Its only limitation is "Data come from one regional network, and external validation is needed" (paper.md:39), which does not address confounding.

**Minimal change:**
- recompute the OR and its CI with code, and state whether the estimate is adjusted and for which covariates;
- rephrase the result as an association ("was associated with lower odds of readmission");
- delete the policy sentence at paper.md:37.

**New results:** yes for the corrected OR and CI. The language change needs none.

### K3e. The abstract's n = 12,480 differs from the 12,840 elsewhere, and the abstract's AUC 0.83 differs from the 0.81 elsewhere (the AUC from the working notes). Verdict: true, FIXABLE (text only)

**Evidence.**
- Sample size: paper.md:5 says "Using 12,480 adult discharges", while paper.md:17 ("n = 12,840"), paper.md:29 ("1,610 of 12,840") and `metrics.json` (`"n": 12840`) all say 12,840.
- AUC: paper.md:5 says "an AUC of 0.83", while paper.md:31 says 0.81 and metrics.json says 0.812.

**Minimal change:** set the abstract to 12,840. Set the AUC to the value from the corrected rerun (K2); the current 0.81 is itself optimistic.

**New results:** none for n. For the AUC, only through K2.

### K3f. The GRIM check on length of stay (4.37 days, n = 23) shows the mean is impossible (working notes, item 9). Verdict: not established. FIXABLE by a statement (text only, unless the unit is integer days)

**Evidence.**
- 4.37 × 23 = 100.51, and the nearest attainable means are 100/23 = 4.348 and 101/23 = 4.391. So 4.37 is impossible **if** length of stay is recorded in whole days.
- The paper does not state the unit. paper.md:29 says only "Mean length of stay … was 4.37 days (n = 23)". If length of stay is computed from admission and discharge timestamps, GRIM does not apply.
- I cannot rebut the point, because the paper does not say the stay is fractional. I also cannot confirm it.

**Minimal change:** state how length of stay was measured. If it is integer days, correct the mean from the data. In any case, add the code (see K3a).

**New results:** only if the unit is integer days.

### K3g. The data are not shared. Verdict: true, FIXABLE as a disclosure (text only); the limit on reproduction remains

**Evidence.**
- `data/README.md:1`: "The discharge records are not shareable under the data-use agreement."
- The paper has no data availability statement.

**Minimal change:** add a Data Availability statement naming the data-use agreement, the body that grants access and the contact route, and deposit the code.

**New results:** none.

**Residual:** reviewers cannot rerun the analysis. Whether restricted access with a stated route is acceptable is a question of venue policy, which I could not check with the materials I was allowed to use.

---

## Note: novelty is not a kill argument in the memo, but I concede it

- paper.md:5 says "To our knowledge, this is the first machine-learning model for 30-day readmission."
- The paper's own reference list contradicts this: [3] "Smith A, Lee J. Deep readmission forecasting with universal transformers. Journal of Medical Internet Research. 2023" (paper.md:47).
- I did not check the external papers the memo names (Futoma 2015; Christodoulou 2019), because they are outside the allowed materials.
- **Fix (text only):** delete the sentence.

Two problems with the reference list, found in the pack itself, should be fixed at the same time:
- **Reference [3] is never cited in the text.** Its DOI `10.2196/99999` and article number `e99999` (refs.bib:26-28) look like placeholders. Verify that it exists before submission, and remove it if it does not.
- **Reference [1] has the wrong year.** It is given as 2013 (paper.md:43; refs.bib:8), but its bib key `kansagara2011` and DOI `10.1001/jama.2011.1515` (refs.bib:1, 9) both indicate 2011.

---

## Files read and commands run

**Files read (read-only):**
- <review-dir>/PIN.json
- <review-dir>/reports/kill_memo.md (the memo and the referee's working notes)
- <review-dir>/pack/paper.md
- <review-dir>/pack/refs.bib
- <review-dir>/pack/analysis/train.py
- <review-dir>/pack/analysis/evaluate.py
- <review-dir>/pack/results/metrics.json
- <review-dir>/pack/data/README.md

**Directory listings only (contents of other files not opened):** the study root, pack/, reports/ and work-defender/. I did not open criteria.txt, MANIFEST.md or anything in work-attacker/.

**Commands run:**
1. `ls -la` and `find -type f` on the study root, pack/ and reports/; `cat PIN.json`.
2. `cat -n` on every pack file and on kill_memo.md.
3. `shasum -a 256` on all files in pack/ and work-defender/. paper.md matches the PIN hash, and work-defender/ is identical to pack/.
4. Checks for Python packages: Python 3.14.7 is available; numpy, scipy, sklearn and mpmath are not installed.
5. `grep -rniE "brier|slope|f1_at_threshold|misclass|noon|age|ttest|odds|length|1610|calibration_report|prepare\(|SEEDS"` over pack/, plus `grep -n "\[3\]" paper.md`, to confirm which reported quantities have code behind them and that reference [3] is uncited.
6. Wrote and ran `<review-dir>/work-defender/scratch/recompute.py` (standard library only, run with `python3 -I`, reading work-defender/results/metrics.json). It computes:
   - prevalence, the no-information Brier score and the SD of test-split prevalence;
   - the trivial-classifier error and the relative-reduction arithmetic;
   - t-distribution p-values (regularized incomplete beta) for t(118) = 1.20 and t(12838) = 1.20, and the t needed for p = .003;
   - the Welch test on metrics.json and on the paper's rounded values, plus paired-design thresholds (naive and Nadeau–Bengio);
   - the Hanley–McNeil SE;
   - the OR and CI geometric centre, implied SE and a re-centred CI;
   - the GRIM check and the grid size;
   - a simulation (seed 20261029, N = 200,000) of a perfectly calibrated logistic-binormal model at prevalence 0.125, giving AUC, Brier score and error at 0.5. At AUC 0.815: Brier 0.089, error 11.6%.
7. A `sed` edit to that script, to correct its printout of the share of U(0.11, 0.13) above π(1−π) (it now prints 1.000), and a rerun.
