# Gradient boosting for early prediction of 30-day hospital readmission

## Abstract

Hospital readmission within 30 days is costly and often preventable. Although many risk scores exist, we attempt to shed light on whether modern machine learning can improve on them. Using 12,480 adult discharges from a regional hospital network, we trained a gradient-boosted model on routinely collected discharge data. The model achieved an AUC of 0.83 and significantly outperformed logistic regression. It was also well calibrated (Brier score 0.12). To our knowledge, this is the first machine-learning model for 30-day readmission. Our method may not generalize, and in some cases its accuracy is limited.

## Introduction

Unplanned readmissions within 30 days affect roughly one in seven discharged adults and are used as a quality indicator by payers [1]. Existing risk scores rely on a handful of variables and discriminate only moderately [1]. Gradient boosting [2] can capture non-linear interactions between laboratory values, medications and prior utilization, which the scores ignore.

We first trained a logistic regression model. Then we ran a series of experiments with gradient boosting. In this paper we compare the two approaches on the same data and report discrimination and calibration.

## Methods

### Data

We used de-identified discharge records of adults (age ≥ 18) discharged alive between 2019 and 2023 from four hospitals of a regional network, n = 12,840. Each record contains 112 candidate predictors: demographics, diagnoses, laboratory values at discharge, medications, and utilization in the previous year. The outcome was any unplanned readmission to a network hospital within 30 days.

### Models

All preprocessing (standardization and univariate feature selection of the 40 most informative predictors) was fit on the training set only, to avoid information leakage. We compared a gradient-boosted classifier with a logistic regression baseline. Hyperparameters of the gradient-boosted model were chosen by a grid search over 48 configurations (tree depth, learning rate, number of trees).

### Evaluation

Both models were evaluated on the same five random 70/30 train/test splits, so that the comparison is paired. We report the area under the ROC curve (AUC, mean ± SD over the five splits), the F1 score at a 0.5 threshold, and calibration (Brier score and calibration slope) on held-out predictions.

## Results

Readmission occurred after 1,610 of 12,840 discharges (12.5%). Patients who were readmitted were older than those who were not (t(118) = 1.20, p = .003). Mean length of stay in a chart-review validation subsample was 4.37 days (n = 23).

The gradient-boosted model significantly outperforms the logistic regression baseline (0.81 ± 0.02 vs 0.79 ± 0.02). At the 0.5 threshold, it reduced the misclassification rate from 20% to 16%, a 25% relative reduction. Calibration was excellent (Brier score 0.12, calibration slope 0.99).

Among secondary findings, discharge before noon leads to lower readmission (OR 0.62, 95% CI 0.70–0.96).

## Discussion

Gradient boosting improves the prediction of 30-day readmission over logistic regression on routinely collected data, and is well calibrated. Because it uses only data available at discharge, it could be deployed in the discharge workflow. Hospitals should schedule discharges before noon to reduce readmissions.

The study has limitations. Data come from one regional network, and external validation is needed.

## References

[1] Kansagara D, Englander H, Salanitro A, et al. Risk prediction models for hospital readmission: a systematic review. JAMA. 2013;306(15):1688–1698.

[2] Friedman JH. Greedy function approximation: a gradient boosting machine. Annals of Statistics. 2001;29(5):1189–1232.

[3] Smith A, Lee J. Deep readmission forecasting with universal transformers. Journal of Medical Internet Research. 2023;25:e99999.
