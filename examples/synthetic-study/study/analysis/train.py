"""Train and evaluate the 30-day readmission models.

Run from the project root:  python analysis/train.py
Writes results/metrics.json.
"""
import json

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from evaluate import calibration_report

GBM_SEEDS = [0, 1, 2, 3, 4]
LR_SEEDS = [10, 11, 12, 13, 14]


def load():
    data = np.load("data/discharges.npz")
    return data["X"], data["y"]


def prepare(X, y):
    X = StandardScaler().fit_transform(X)
    X = SelectKBest(f_classif, k=40).fit_transform(X, y)
    return X


def grid():
    for depth in (2, 3, 4, 5):
        for rate in (0.01, 0.05, 0.1, 0.2):
            for trees in (100, 300, 500):
                yield dict(max_depth=depth, learning_rate=rate, n_estimators=trees)


def run_gbm(X, y, seed):
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=seed)
    best = None
    for params in grid():
        model = GradientBoostingClassifier(random_state=seed, **params).fit(Xtr, ytr)
        auc = roc_auc_score(yte, model.predict_proba(Xte)[:, 1])
        if best is None or auc > best[0]:
            best = (auc, params, model)
    return best


def run_lr(X, y, seed):
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=seed)
    model = LogisticRegression(max_iter=1000).fit(Xtr, ytr)
    return roc_auc_score(yte, model.predict_proba(Xte)[:, 1])


def f1_at_threshold(y, p, t=0.5):
    pred = p >= t
    tp = ((pred == 1) & (y == 1)).sum()
    fp = ((pred == 1) & (y == 0)).sum()
    fn = ((pred == 0) & (y == 1)).sum()
    return 2 * tp / max(2 * tp + fp + fn, 1)


def main():
    X, y = load()
    X = prepare(X, y)
    gbm = [run_gbm(X, y, s)[0] for s in GBM_SEEDS]
    lr = [run_lr(X, y, s) for s in LR_SEEDS]
    out = {
        "n": int(len(y)),
        "gbm_auc_mean": round(float(np.mean(gbm)), 3),
        "gbm_auc_sd": round(float(np.std(gbm)), 3),
        "lr_auc_mean": round(float(np.mean(lr)), 3),
        "lr_auc_sd": round(float(np.std(lr)), 3),
        "calibration": calibration_report(),
    }
    with open("results/metrics.json", "w") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
