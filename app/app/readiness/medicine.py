# AI-assisted code (team statement and per-step log: docs/AI_USE_LOG.md).
"""B5: promethazine concentration and its forecast scenario (MATH_FRAMEWORK §6). Forecast only.

PK: one compartment, first-order absorption, C(t) = A (exp(-ke t) - exp(-ka t)); Gandia et al. 2006 Table II
(50 mg, ambulatory); dose proportional. C_rel = C / 11.25 ug/L (extrapolated oral 25 mg peak).
Scenario (unvalidated): oral 25 mg peak ~ 0.97 decade of inner-ear ageing; delta_c(t) = 0.97 C_rel(t) b_c / b,
applied only where the HBEDB age slope is established (foam-EO). The drug never raises r.
"""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
from scipy.optimize import brentq

from . import config as C

WARN_ORTHOSTATIC = ("Orthostatic risk. In a NASA study of 8 healthy participants given intravenous promethazine, "
                    "all 8 became presyncopal on tilt testing, compared with 3 of 8 without the drug (Shi et al. "
                    "2011). The risk after oral or intramuscular doses is not quantified here. Stand only with "
                    "assistance.")
WARN_FLIGHT = ("Promethazine absorption differs in flight, with a lower and later peak concentration reported "
               "(Boyd et al. 2009). Only the direction of this difference is known, and it is not modelled.")
LABEL = "unvalidated scenario that adjusts only the retest estimate"


@lru_cache(maxsize=None)
def pk(route: str) -> tuple[float, float, float]:
    """(ke, ka, A50) for the route; A50 scales the 50 mg curve so its peak equals Gandia's Cmax."""
    t_half, tmax, cmax = C.GANDIA[route]
    ke = math.log(2.0) / t_half
    f = lambda ka: math.log(ka / ke) / (ka - ke) - tmax  # noqa: E731  decreasing in ka for ka > ke
    ka = brentq(f, ke * (1 + 1e-9), 1e3)
    shape = math.exp(-ke * tmax) - math.exp(-ka * tmax)
    return ke, ka, cmax / shape


def conc(t, dose_mg: float, route: str):
    """Plasma concentration (ug/L) at t hours after the dose; 0 before the dose."""
    t = np.asarray(t, dtype=float)
    if dose_mg <= 0:
        return np.zeros_like(t)
    ke, ka, a50 = pk(route)
    tt = np.maximum(t, 0.0)
    c = a50 * dose_mg / C.GANDIA_DOSE_MG * (np.exp(-ke * tt) - np.exp(-ka * tt))
    return np.where(t > 0, c, 0.0)


def c_rel(t, dose_mg: float, route: str):
    return conc(t, dose_mg, route) / C.C_REF


def _dconc(t, dose_mg, route):
    t = np.asarray(t, dtype=float)
    if dose_mg <= 0:
        return np.zeros_like(t)
    ke, ka, a50 = pk(route)
    tt = np.maximum(t, 0.0)
    d = a50 * dose_mg / C.GANDIA_DOSE_MG * (-ke * np.exp(-ke * tt) + ka * np.exp(-ka * tt))
    return np.where(t > 0, d, 0.0)


def _gain(b_c, baseline) -> float:
    if b_c is None or not (b_c > 0) or not (baseline and baseline > 0):
        return 0.0
    return C.AGE_EQUIV * float(b_c) / float(baseline) / C.C_REF


def delta(t, dose_mg: float, route: str, b_c, baseline: float, t_dose: float = 0.0):
    """Ratio decrement from the drug at time t (hours since landing); zero where b_c is None or <= 0."""
    g = _gain(b_c, baseline)
    t = np.asarray(t, dtype=float)
    if g == 0.0 or dose_mg <= 0:
        return np.zeros_like(t)
    return g * conc(t - t_dose, dose_mg, route)


def initial_deficit(r_m: float, t_m: float, tau: float, dose_mg=0.0, route="oral", b_c=None, baseline=1.0,
                    t_dose=0.0) -> float:
    """D_i = max(0, (1 - r_m - delta(t_m)) exp(t_m / tau))."""
    d_m = float(delta(t_m, dose_mg, route, b_c, baseline, t_dose))
    return max(0.0, (1.0 - r_m - d_m) * math.exp(t_m / tau))


def curve(t, D: float, tau: float, dose_mg=0.0, route="oral", b_c=None, baseline=1.0, t_dose=0.0):
    """r(t) = 1 - max(0, D) exp(-t / tau) - delta(t)."""
    t = np.asarray(t, dtype=float)
    return 1.0 - max(0.0, D) * np.exp(-t / tau) - delta(t, dose_mg, route, b_c, baseline, t_dose)


def split_time(route: str, t_dose: float, t_start: float = 0.0) -> float:
    """T* = max(t_start, dose time + tmax): after it the forecast curve is strictly increasing."""
    _, tmax, _ = C.GANDIA[route]  # (t_half, tmax, Cmax)
    return max(float(t_start), float(t_dose) + tmax)


def t_go(D: float, tau: float, q: float, dose_mg=0.0, route="oral", b_c=None, baseline=1.0, t_dose=0.0,
         t_start=0.0) -> float | None:
    """Last time >= t_start at which r(t) < q (after it, r stays >= q). None if q >= 1 (not reachable).
    Returns t_start if r >= q throughout."""
    if not (q < 1.0):
        return None
    D = max(0.0, float(D))
    g = _gain(b_c, baseline)
    has_drug = g > 0 and dose_mg > 0
    fv = lambda t: curve(t, D, tau, dose_mg, route, b_c, baseline, t_dose) - q  # noqa: E731  (vectorised)
    f = lambda t: float(fv(t))  # noqa: E731
    if not has_drug:
        if D <= 1.0 - q:
            return float(t_start)
        return max(float(t_start), tau * math.log(D / (1.0 - q)))
    t_star = split_time(route, t_dose, t_start)
    # tail: after T* = dose + tmax both terms increase, so r is strictly increasing; bracket outward
    if f(t_star) < 0:
        hi = t_star + 1.0
        while f(hi) < 0:
            hi = t_star + 2.0 * (hi - t_star)
        return _confirm(f, fv, brentq(f, t_star, hi, xtol=1e-9), t_star)
    if t_star <= t_start:
        return float(t_start)
    # before T*: split [t_start, T*] into monotone pieces at the dose time (derivative jump) and at every
    # zero of the analytic derivative, including zeros that fall exactly on a grid point
    dr = lambda t: (D / tau) * math.exp(-t / tau) - g * float(_dconc(t - t_dose, dose_mg, route))  # noqa: E731
    knots = {float(t_start), float(t_star)}
    a0 = max(float(t_start), float(t_dose))
    knots.add(a0)
    grid = np.linspace(a0, t_star, 4001)
    vals = (D / tau) * np.exp(-grid / tau) - g * _dconc(grid - t_dose, dose_mg, route)
    sg = np.sign(vals)
    knots.update(grid[sg == 0].tolist())
    for i in np.flatnonzero(sg[:-1] * sg[1:] < 0):
        knots.add(brentq(dr, grid[i], grid[i + 1], xtol=1e-12))
    knots = sorted(knots)
    ans = float(t_start)
    for a, b in reversed(list(zip(knots[:-1], knots[1:]))):
        fa, fb = f(a), f(b)
        if fb < 0:
            ans = b
            break
        if fa < 0:
            ans = brentq(f, a, b, xtol=1e-9)
            break
    return _confirm(f, fv, ans, t_star)


def _confirm(f, fv, ans: float, t_star: float, n: int = 20001) -> float:
    """Safety net: r must stay >= q after the returned time. Scan [ans, T* + 48 h] densely; if any point is
    still below target, move the answer to the last crossing after it."""
    hi = max(t_star, ans) + 48.0
    ts = np.linspace(ans, hi, n)
    vals = fv(ts)
    below = np.flatnonzero(vals[1:] < 0) + 1
    if below.size == 0:
        return ans
    j = int(below[-1])
    if j == n - 1:
        raise RuntimeError("go-time solver: target not reached within the safety scan")
    return brentq(f, ts[j], ts[j + 1], xtol=1e-9)
