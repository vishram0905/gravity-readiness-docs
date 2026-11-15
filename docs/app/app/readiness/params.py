# AI-assisted code (team statement and per-step log: docs/AI_USE_LOG.md).
"""B3: baselines, noise margins (q95) and population floors (P5).

MATH_FRAMEWORK §3:
- q95_data: within condition x age group x baseline tertile (healthy people), relative residuals around each
  person's mean (divided by the person's median, inflated by sqrt(3/2) for the 2 degrees of freedom lost) are
  bootstrapped: R = median(1 + 3 retest residuals) / median(1 + 3 baseline residuals); q95_data = 95th pct.
- q95_lit(b): Pang et al. 2011 MDCs -> per-trial SD = MDC / (1.96 sqrt 2) x sqrt 5; 95th percentile of
  median(3 noisy retest trials) / median(3 noisy baseline trials) at true level b, trials clipped to [0, 100].
- q95 = max(q95_data, q95_lit(b)) (team decision).
- P5: 5th percentile of healthy baselines in the age group.
- b_c: minus the slope of baseline EQ on age (per decade) above 42.7 y, only where the 95% CI excludes 0.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache

import numpy as np
import pandas as pd

from . import config as C

PARAMS_FILE = C.PARAMS_DIR / "hbedb_params.json"
LIT_FILE = C.PARAMS_DIR / "q95_lit.json"
LIT_GRID = np.arange(C.Q95_LIT_GRID[0], C.Q95_LIT_GRID[1] + 0.5, 1.0)


def surface(condition: str) -> str:
    return condition.split("_")[0]


def lit_trial_sd(surf: str, age_group: str) -> float:
    return C.PANG_MDC[(surf, age_group)] / (1.96 * math.sqrt(2.0)) * math.sqrt(5.0)


# ---------------------------------------------------------------- derivation (build machine only)
def healthy_persons(trials: pd.DataFrame) -> pd.DataFrame:
    """One row per healthy person x condition with 3 valid trials (both windows): baseline and trial scores."""
    h = trials[trials["healthy"] & ~trials["vestibular"]]
    rows = []
    for (subj, cond), g in h.groupby(["subject", "condition"]):
        if len(g) == 3 and g["eq_w1"].notna().all() and g["eq_w2"].notna().all() and g["valid"].all():
            g = g.sort_values("trial_id")
            w1 = g["eq_w1"].to_numpy(float)
            rows.append({"subject": subj, "condition": cond, "age_group": g["age_group"].iloc[0],
                         "age": float(g["age"].iloc[0]), "w1": w1, "w2": g["eq_w2"].to_numpy(float),
                         "baseline": float(np.median(w1))})
    return pd.DataFrame(rows)


def derive_data_params(trials: pd.DataFrame, draws: int = C.Q95_DATA_DRAWS, seed: int = C.SEED) -> dict:
    rng = np.random.default_rng(seed)
    P = healthy_persons(trials)
    out: dict = {}
    for ag in C.AGE_GROUPS:
        for cond in C.CONDITIONS:
            d = P[(P.condition == cond) & (P.age_group == ag)]
            base = d["baseline"].to_numpy(float)
            edges = np.quantile(base, [1 / 3, 2 / 3])
            tert = np.digitize(base, edges)
            q95 = []
            for k in range(3):
                rel = np.concatenate([(w - w.mean()) / np.median(w)
                                      for w, t in zip(d["w1"], tert) if t == k]) * math.sqrt(1.5)
                rb = 1.0 + rng.choice(rel, (draws, 3))
                rt = 1.0 + rng.choice(rel, (draws, 3))
                q95.append(float(np.quantile(np.median(rt, 1) / np.median(rb, 1), 0.95)))
            out[f"{ag}|{cond}"] = {"p5": float(np.quantile(base, 0.05)), "edges": [float(e) for e in edges],
                                   "q95": q95, "n": int(len(d))}
    h = trials[trials["healthy"] & ~trials["vestibular"]]
    for cond in C.CONDITIONS:
        d = h[(h.condition == cond) & (h.age > C.AGE_SLOPE_KNEE)]
        b = d.groupby("subject").agg(eq=("eq_w1", "median"), age=("age", "first"))
        x, y = b["age"].to_numpy(float) / 10.0, b["eq"].to_numpy(float)
        X = np.c_[np.ones_like(x), x]
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        res = y - X @ beta
        se = math.sqrt(float(res @ res) / (len(y) - 2) * float(np.linalg.inv(X.T @ X)[1, 1]))
        lo, hi = beta[1] - 1.96 * se, beta[1] + 1.96 * se
        out[f"slope|{cond}"] = {"n": int(len(y)), "slope_per_decade": float(beta[1]), "ci": [float(lo), float(hi)],
                                "b_c": float(-beta[1]) if hi < 0 else None}
    return out


def derive_q95_lit(draws: int = C.Q95_LIT_DRAWS, seed: int = C.SEED) -> dict:
    out = {"grid": LIT_GRID.tolist()}
    for ag in C.AGE_GROUPS:
        for surf in ("firm", "foam"):
            rng = np.random.default_rng(seed)
            sd = lit_trial_sd(surf, ag)
            vals = []
            for b in LIT_GRID:
                base = np.median(np.clip(b + rng.normal(0.0, sd, (draws, 3)), 0, 100), axis=1)
                test = np.median(np.clip(b + rng.normal(0.0, sd, (draws, 3)), 0, 100), axis=1)
                ok = base > 0
                vals.append(float(np.quantile(test[ok] / base[ok], 0.95)))
            out[f"{ag}|{surf}"] = vals
    return out


# ---------------------------------------------------------------- lookup (app and tests)
@lru_cache(maxsize=1)
def load_params() -> dict:
    return json.loads(PARAMS_FILE.read_text())


@lru_cache(maxsize=1)
def load_q95_lit() -> dict:
    return json.loads(LIT_FILE.read_text())


def _entry(condition: str, age_group: str) -> dict:
    return load_params()[f"{age_group}|{condition}"]


def tertile(b: float, condition: str, age_group: str) -> int:
    return int(np.digitize([b], _entry(condition, age_group)["edges"])[0])


def q95_data(b: float, condition: str, age_group: str) -> float:
    return float(_entry(condition, age_group)["q95"][tertile(b, condition, age_group)])


def q95_lit(b: float, condition: str, age_group: str) -> float:
    t = load_q95_lit()
    return float(np.interp(b, t["grid"], t[f"{age_group}|{surface(condition)}"]))


def noise_q95(b: float, condition: str, age_group: str) -> float:
    """q95 = max(q95_data[tertile(b)], q95_lit(b)); NaN if b is not a finite number."""
    if b is None or not math.isfinite(float(b)):
        return float("nan")
    return max(q95_data(b, condition, age_group), q95_lit(b, condition, age_group))


def p5(condition: str, age_group: str) -> float:
    return float(_entry(condition, age_group)["p5"])


def drug_slope(condition: str) -> float | None:
    """b_c (EQ points per decade of ageing) or None where the age effect is not established."""
    return load_params()[f"slope|{condition}"]["b_c"]
