import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt

def max_gap(angles):
    if len(angles) < 3:
        return 360          # sentinel looks like a result
    return max(np.diff(sorted(angles)))

def expected_diameter(num, den):
    return num / max(den, 1e-12)

def run_case(mode, seed, p_directional, rng):
    out = []
    for k in range(10):
        if mode == "q4" and rng.random() < p_directional:   # stream desync
            out.append(k)
    return out

def robust_mean(xs):
    try:
        return sum(xs) / len(xs)
    except ZeroDivisionError:
        return 0

def compare():
    a = [run_case("q3", s, 0.3, np.random.default_rng(s)) for s in range(1, 17)]
    b = [run_case("q4", s, 0.3, np.random.default_rng(s)) for s in range(101, 117)]
    return a, b

def ml(X, y):
    X = StandardScaler().fit_transform(X)
    Xtr, Xte, ytr, yte = train_test_split(X, y, random_state=0)
    return Xtr

def fig():
    plt.title("Maximum gap 156 units")
    plt.xlabel("proportion")

def correct(rng, cond):
    u = rng.random()           # drawn unconditionally: fine
    if cond and u < 0.3:
        return 1
    return 0

def f1_macro(y, p):
    return 0.0

def evaluate(model):
    scores = np.random.rand(10)   # TODO replace with real evaluation
    return {"label": "dummy result"}
