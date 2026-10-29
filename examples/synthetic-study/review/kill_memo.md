# Kill memo

**K1. Calibration was never measured; the reported values are random numbers.** evaluate.py:5-9 (no predictions passed, train.py:76); paper.md:5, 31, 37. `np.random.uniform(0.11, 0.13)` and `np.random.normal(1.0, 0.02)`, marked TODO, feed metrics.json. Brier 0.12 is worse than the no-information Brier of 0.110, impossible for a calibrated model.

**K2. "Significantly outperforms logistic regression" does not follow.** train.py:18-19, 27-30, 43-47, 67; paper.md:21, 25, 31. The GBM is the best of 48 configurations scored on the reported test split; LR is untuned. Scaling and feature selection use all data, test labels included, contradicting "training set only". Split seeds differ (0-4 vs 10-14), so the comparison is unpaired. No test exists; Welch on metrics.json gives p = 0.17.

**K3. No code produces the remaining results, and several are impossible.** paper.md:5, 29, 31, 33, 37. Misclassification of 16% and 20% exceeds the 12.5% error of predicting no readmission. t(118) = 1.20 gives p = 0.23, not .003. OR 0.62 lies outside its CI (0.70-0.96) yet drives a causal discharge policy. n = 12,480 vs 12,840. Data are not shared.

Not a kill at PLOS ONE: "first ML model" is false (Futoma 2015; Christodoulou 2019), but novelty is not a criterion.

---

## Files read and numbers recomputed

### Files read (all read-only)
- <review-dir>/criteria.txt
- <review-dir>/PIN.json
- <review-dir>/pack/paper.md
- <review-dir>/pack/refs.bib
- <review-dir>/pack/analysis/train.py
- <review-dir>/pack/analysis/evaluate.py
- <review-dir>/pack/data/README.md
- <review-dir>/pack/results/metrics.json
- Directory listings only (no file contents read): the study root, pack/, work-attacker/ and reports/. MANIFEST.md and work-defender/ were not opened.

### Scratch script written and run (pure Python with only the standard library; scipy was not installed)
- <review-dir>/work-attacker/scratch/recompute.py. It computes t-distribution p-values with a regularized incomplete beta function.

### Numbers recomputed
1. **Prevalence** = 1610 / 12840 = 0.12539. This matches the 12.5% in paper.md:29.
2. **No-information Brier score**: π(1 − π) = 0.12539 × 0.87461 = 0.1097. A calibrated model has Brier = π(1 − π) − Var(p) ≤ 0.1097, so the reported 0.121 (metrics.json) or 0.12 (paper) is worse than predicting the prevalence for everyone. The code draws this value from U(0.11, 0.13) (evaluate.py:7), and most of that range lies above 0.1097.
3. **Trivial-classifier error**: predicting "no readmission" for every patient gives an error of π = 12.5%. The reported misclassification rates are 20% (LR) and 16% (GBM), both higher (paper.md:31). For a calibrated model, the error of the 0.5-threshold rule is E[min(p, 1 − p)] ≤ E[p] = π = 12.5%, so 16% also contradicts "calibration was excellent".
4. **Relative reduction**: (20 − 16) / 20 = 20%, not the 25% stated at paper.md:31.
5. **t(118) = 1.20**: two-sided p = 0.2325, not .003 (paper.md:29). Reaching p = .003 at df = 118 would need t ≈ 3.03. Also, df = 118 implies about 120 patients, not 12,840.
6. **GBM vs LR, Welch test** using metrics.json (np.std uses ddof = 0, so I converted to sample SDs):
   - GBM sample SD = 0.018 × √(5/4) = 0.02012; LR sample SD = 0.021 × √(5/4) = 0.02348.
   - SE = √(0.02012²/5 + 0.02348²/5) = 0.01383.
   - t = 0.021 / 0.01383 = 1.52, Welch df = 7.82, two-sided p = 0.168.
   - A paired test is not possible because the splits differ (seeds 0-4 vs 10-14, train.py:18-19).
7. **AUC sampling error on one split**:
   - Test set n = 0.3 × 12840 = 3852, with about 483 readmissions and 3369 non-readmissions.
   - Hanley-McNeil SE at AUC 0.81 is about 0.0122.
   - The 0.021 GBM-LR gap is therefore under 2 single-split SEs, before any correction for picking the GBM as the best of 48 configurations scored on the test split (train.py:43-47).
8. **OR and CI**: the geometric centre of the CI 0.70-0.96 is √(0.70 × 0.96) = 0.82. The reported OR of 0.62 lies outside the interval (paper.md:33).
9. **GRIM check on mean length of stay** (4.37 days, n = 23): 4.37 × 23 = 100.51. The nearest attainable means for integer days are 100/23 = 4.348 and 101/23 = 4.391, so 4.37 is not attainable (paper.md:29).
10. **Sample-size and AUC inconsistencies**:
    - The Abstract gives n = 12,480, while Methods, Results and metrics.json give 12,840 (a difference of 360).
    - The Abstract gives AUC 0.83, while Results give 0.81 and metrics.json gives 0.812.

### Code facts used (static reading)
- prepare() (train.py:27-30) fits StandardScaler and SelectKBest(f_classif, k = 40) on the full X and y before any split (train.py:67). This contradicts paper.md:21.
- run_gbm() (train.py:40-48) chooses hyperparameters by test-set AUC and returns that same AUC.
- run_lr() (train.py:51-54) uses different seeds and has no tuning.
- f1_at_threshold() (train.py:57-62) is defined but never called, so the F1 score promised in Methods (paper.md:25) is never computed. No code computes misclassification rates, the age t-test, the OR for discharge before noon, or the length of stay.
- calibration_report() (evaluate.py:5-9) takes no arguments, sets no seed and returns random values.

### Literature checked (PubMed)
- Futoma J, et al. A comparison of models for predicting early hospital readmissions. J Biomed Inform 2015 (PMID 26044081).
- Christodoulou E, et al. A systematic review shows no performance benefit of machine learning over logistic regression for clinical prediction models. J Clin Epidemiol 2019 (PMID 30763612).
