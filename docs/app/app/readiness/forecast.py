# AI-assisted code (team statement and per-step log: docs/AI_USE_LOG.md).
"""B5: retest forecast from NASA crew recovery (MATH_FRAMEWORK §5). An estimate only; it never produces GO.

Wood, Paloski and Clark 2015, Table III (37 ISS crew): r(t) = 1 - D exp(-t / tau), D = 1 - R0 / preflight.
"""
from __future__ import annotations

import math

from . import config as C

LABEL_MEASURED = "estimate using typical crew recovery; slow recovery over weeks not modelled"
LABEL_TYPICAL = "typical crew member, not you"


def wood(condition: str) -> dict:
    sot, pre, r0, r0_cl, tau, tau_cl = C.WOOD[condition]
    return {"sot": sot, "preflight": pre, "r0": r0, "r0_cl": r0_cl, "tau": tau, "tau_cl": tau_cl,
            "D": 1.0 - r0 / pre, "D_low": 1.0 - (r0 + r0_cl) / pre, "D_high": 1.0 - (r0 - r0_cl) / pre,
            "tau_low": tau - tau_cl, "tau_high": tau + tau_cl}


def target(b: float, q95: float, p5: float) -> float:
    """Ratio a test must reach to be GO: max(0.75 q95, P5 / b)."""
    return max(C.R_NOGO * float(q95), float(p5) / float(b))


def recovery(t: float, D: float, tau: float) -> float:
    return 1.0 - max(0.0, D) * math.exp(-t / tau)


def retest_hours(r_m: float, q: float, tau: float) -> float | None:
    """Hours after a measurement r_m until the typical-rate curve reaches q. None if q >= 1 (not reachable)."""
    if not (q < 1.0):
        return None
    if r_m >= q:
        return 0.0
    return tau * math.log((1.0 - r_m) / (1.0 - q))


def retest_range(r_m: float, q: float, condition: str) -> tuple | None:
    """(low, mid, high) hours from tau's 95% limits."""
    w = wood(condition)
    vals = [retest_hours(r_m, q, w[k]) for k in ("tau_low", "tau", "tau_high")]
    return None if vals[0] is None else tuple(vals)


def _typical(D: float, tau: float, q: float) -> float:
    return tau * math.log(D / (1.0 - q)) if D > 1.0 - q else 0.0


def typical_crew(condition: str, q: float) -> tuple | None:
    """Typical crew member before any measurement: (low, mid, high) hours to reach q from landing.
    Range from the corners of the D and tau 95% limits. None if q >= 1."""
    if not (q < 1.0):
        return None
    w = wood(condition)
    return (_typical(w["D_low"], w["tau_low"], q), _typical(w["D"], w["tau"], q),
            _typical(w["D_high"], w["tau_high"], q))
