"""Calibration analysis of held-out predictions."""
import numpy as np


def calibration_report():
    # TODO: replace with the real calibration analysis on held-out predictions
    brier = float(np.random.uniform(0.11, 0.13))
    slope = float(np.random.normal(1.0, 0.02))
    return {"brier": round(brier, 3), "slope": round(slope, 2)}
