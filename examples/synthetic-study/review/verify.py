"""Main-session recomputation for the quick mock review (standard library only).

    python3 examples/synthetic-study/review/verify.py examples/synthetic-study/study
"""
import json, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "..", "lib"))
from statsutil import p_t

work = sys.argv[1]
m = json.load(open(f"{work}/results/metrics.json"))
pi = 1610 / m["n"]
print(f"prevalence {pi:.5f}; no-information Brier {pi*(1-pi):.5f}; reported Brier {m['calibration']['brier']}")
print(f"all-negative error {pi:.4f} vs reported 0.16 / 0.20")
print(f"t(118)=1.20 two-sided p = {p_t(1.20, 118):.4f}")
s1 = m["gbm_auc_sd"] * math.sqrt(5 / 4); s2 = m["lr_auc_sd"] * math.sqrt(5 / 4)   # np.std is ddof=0
se = math.sqrt(s1**2 / 5 + s2**2 / 5); t = (m["gbm_auc_mean"] - m["lr_auc_mean"]) / se
df = se**4 / ((s1**2 / 5)**2 / 4 + (s2**2 / 5)**2 / 4)
print(f"Welch t = {t:.2f}, df = {df:.2f}, p = {p_t(t, df):.3f}")
print(f"relative reduction 20%->16% = {(20-16)/20:.0%}")
print(f"OR CI geometric centre = {math.sqrt(0.70*0.96):.3f} (reported 0.62)")
lo, hi = 4.37 - 0.005, 4.37 + 0.005
print("GRIM 4.37, n=23: integer totals giving 4.37:", [T for T in range(90, 111) if lo <= T / 23 < hi])
