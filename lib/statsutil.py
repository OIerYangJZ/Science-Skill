"""statsutil.py - p-values for t, F, chi-square, r and z with the standard library.

Regularized incomplete beta and gamma functions follow the usual continued
fraction / series algorithms (Numerical Recipes, ch. 6). Accuracy is far
better than the rounding of reported statistics, which is all we need.
"""
from __future__ import annotations

import math


def _betacf(a: float, b: float, x: float) -> float:
    tiny, eps = 1e-300, 3e-16
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 400):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    if x < (a + 1) / (a + b + 2):
        return math.exp(lbt) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbt) * _betacf(b, a, 1 - x) / b


def gammaincc(a: float, x: float) -> float:
    """Regularized upper incomplete gamma Q(a, x)."""
    if x <= 0:
        return 1.0
    if x < a + 1:
        s, term, n = 1.0 / a, 1.0 / a, a
        for _ in range(1000):
            n += 1
            term *= x / n
            s += term
            if abs(term) < abs(s) * 3e-16:
                break
        return 1.0 - s * math.exp(-x + a * math.log(x) - math.lgamma(a))
    tiny = 1e-300
    b = x + 1 - a
    c, d = 1 / tiny, 1 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = tiny if abs(d) < tiny else d
        c = b + an / c
        c = tiny if abs(c) < tiny else c
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 3e-16:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def p_t(t: float, df: float, two_tailed: bool = True) -> float:
    p2 = betainc(df / 2.0, 0.5, df / (df + t * t))
    return p2 if two_tailed else p2 / 2


def p_f(f: float, df1: float, df2: float) -> float:
    if f <= 0:
        return 1.0
    return betainc(df2 / 2.0, df1 / 2.0, df2 / (df2 + df1 * f))


def p_chi2(x: float, df: float) -> float:
    return gammaincc(df / 2.0, x / 2.0)


def p_z(z: float, two_tailed: bool = True) -> float:
    p2 = math.erfc(abs(z) / math.sqrt(2))
    return p2 if two_tailed else p2 / 2


def p_r(r: float, df: float, two_tailed: bool = True) -> float:
    if abs(r) >= 1:
        return 0.0
    t = r * math.sqrt(df / (1 - r * r))
    return p_t(t, df, two_tailed)
