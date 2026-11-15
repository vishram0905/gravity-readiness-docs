# AI-assisted code (team statement and per-step log: docs/AI_USE_LOG.md).
"""B2: centre of mass (COM) and NASA-style equilibrium score (EQ).

COM (primary): zero-point-to-zero-point double integration (GLP; Zatsiorsky and King 1998).
When the horizontal force is zero, the COM lies above the centre of pressure (COP), so between
consecutive zero crossings of Fx the body acceleration a = -Fx/m is integrated twice with the
initial velocity chosen so that COM equals COP at both crossings (MATH_FRAMEWORK §2).

EQ (NASA cEQ; Wood 2015, Clement 2024): theta = atan(AP peak-to-peak COM / (0.55 H)) in degrees,
EQ = 100 (1 - theta / 12.5) x fraction completed, floor 0.
"""
from __future__ import annotations

import math

import numpy as np

from . import config as C


# ---------------------------------------------------------------- anthropometry
def valid_anthro(height_cm: float, mass_kg: float) -> bool:
    try:
        h, m = float(height_cm), float(mass_kg)
    except (TypeError, ValueError):
        return False
    return (math.isfinite(h) and math.isfinite(m)
            and C.HEIGHT_CM[0] <= h <= C.HEIGHT_CM[1] and C.MASS_KG[0] <= m <= C.MASS_KG[1])


def valid_height(height_cm: float) -> bool:
    try:
        h = float(height_cm)
    except (TypeError, ValueError):
        return False
    return math.isfinite(h) and C.HEIGHT_CM[0] <= h <= C.HEIGHT_CM[1]


# ---------------------------------------------------------------- COM
def body_acceleration(fx: np.ndarray, mass_kg: float, detrend: str | None = None) -> np.ndarray:
    """a = -Fx/m in cm/s^2 (N/kg = m/s^2; x 100 because COP is in cm). Fx offset removed first."""
    f = np.asarray(fx, dtype=float)
    f = _remove_offset(f, detrend)
    return -f / float(mass_kg) * 100.0


def _remove_offset(f: np.ndarray, detrend: str | None) -> np.ndarray:
    if detrend is None:
        return f - f.mean()  # primary: constant offset only (MATH_FRAMEWORK §2)
    if detrend == "linear":  # sensitivity only
        t = np.arange(f.size, dtype=float)
        coef = np.polyfit(t, f, 1)
        return f - np.polyval(coef, t)
    raise ValueError(f"unknown detrend option {detrend!r}")


def zero_crossings(f: np.ndarray) -> np.ndarray:
    """Crossing index = first sample after the sign of f changes (zero counts as positive).
    This is the convention under which every expected value of the framework was verified
    (docs/BUILD_LOG.md, B2)."""
    neg = np.signbit(np.asarray(f, dtype=float))
    return np.flatnonzero(neg[1:] != neg[:-1]) + 1


def com_glp(cop_ap: np.ndarray, fx: np.ndarray, mass_kg: float, fs: float = C.FS_HZ,
            detrend: str | None = None) -> np.ndarray:
    """COM (cm) from the GLP method. NaN before the first and after the last zero crossing."""
    cop = np.asarray(cop_ap, dtype=float)
    fx = np.asarray(fx, dtype=float)
    if cop.shape != fx.shape:
        raise ValueError("cop and fx must have the same length")
    f = _remove_offset(fx, detrend)
    a = -f / float(mass_kg) * 100.0
    dt = 1.0 / fs
    com = np.full(cop.size, np.nan)
    zc = zero_crossings(f)
    for k0, k1 in zip(zc[:-1], zc[1:]):
        if k1 <= k0:
            continue
        seg = a[k0:k1 + 1]
        v_rel = np.concatenate([[0.0], np.cumsum((seg[1:] + seg[:-1]) * 0.5 * dt)])
        p_rel = np.concatenate([[0.0], np.cumsum((v_rel[1:] + v_rel[:-1]) * 0.5 * dt)])
        T = (k1 - k0) * dt
        t = np.arange(k1 - k0 + 1) * dt
        v0 = (cop[k1] - cop[k0] - p_rel[-1]) / T
        com[k0:k1 + 1] = cop[k0] + v0 * t + p_rel
    return com


def com_lpf(cop_ap: np.ndarray, *, fs: float, height_cm: float) -> np.ndarray:
    """Sensitivity only: COP low-pass filter, gain 1/(1 + w^2/w0^2), w0^2 = g h/(k^2 + h^2)."""
    cop = np.asarray(cop_ap, dtype=float)
    H = float(height_cm) / 100.0
    h, k = C.COM_HEIGHT_FRAC * H, C.GYR_FRAC * H
    w0sq = C.G * h / (k * k + h * h)
    mean = cop.mean()
    spec = np.fft.rfft(cop - mean)
    w = 2 * np.pi * np.fft.rfftfreq(cop.size, d=1.0 / fs)
    return np.fft.irfft(spec / (1.0 + w * w / w0sq), n=cop.size) + mean


# ---------------------------------------------------------------- EQ
def eq_window(com: np.ndarray, height_cm: float, fs: float = C.FS_HZ, completed: float = 1.0) -> float:
    """EQ for one 20-s window; NaN unless every validity condition holds (MATH_FRAMEWORK §2)."""
    x = np.asarray(com, dtype=float)
    if x.size != int(round(C.SEG_S * fs)):
        return float("nan")
    try:
        comp = float(completed)
    except (TypeError, ValueError):
        return float("nan")
    if not (math.isfinite(comp) and 0.0 <= comp <= 1.0):
        return float("nan")
    if not valid_height(height_cm):
        return float("nan")
    ok = np.isfinite(x)
    if ok.mean() < C.MIN_COVERAGE:
        return float("nan")
    xv = x[ok]
    if xv.size < 2 or np.std(xv) < C.MIN_SWAY_SD_CM:
        return float("nan")
    ptp = float(xv.max() - xv.min())
    theta = math.degrees(math.atan(ptp / (C.COM_HEIGHT_FRAC * float(height_cm))))
    return max(0.0, 100.0 * (1.0 - theta / C.LOS_DEG) * comp)


def trial_scores(trial, detrend: str | None = None) -> dict:
    """First full 20-s window from the first valid COM sample (eq_w1) and the next one (eq_w2;
    used only to simulate a retest in the demo). Invalid anthropometry -> no scores, valid False."""
    out = {"trial_id": trial.trial_id, "subject": trial.subject, "condition": trial.condition,
           "age": trial.age, "age_group": trial.age_group, "height_cm": trial.height_cm,
           "mass_kg": trial.mass_kg, "healthy": trial.healthy, "vestibular": trial.vestibular,
           "eq_w1": float("nan"), "eq_w2": float("nan"), "valid": False}
    if not valid_anthro(trial.height_cm, trial.mass_kg):
        return out
    com = com_glp(trial.channel("COPx"), trial.channel("Fx"), trial.mass_kg, trial.fs, detrend)
    finite = np.flatnonzero(np.isfinite(com))
    if finite.size == 0:
        return out
    i0 = int(finite[0])
    n = int(round(C.SEG_S * trial.fs))
    if i0 + n <= com.size:
        out["eq_w1"] = eq_window(com[i0:i0 + n], trial.height_cm, trial.fs)
    if i0 + 2 * n <= com.size:
        out["eq_w2"] = eq_window(com[i0 + n:i0 + 2 * n], trial.height_cm, trial.fs)
    out["valid"] = bool(math.isfinite(out["eq_w1"]))
    return out


def build_trial_table(force: bool = False, detrend: str | None = None):
    """Scores for every trial in the active data mode; cached to out/trial_table.csv (full data)."""
    import pandas as pd

    from . import hbedb
    name = "trial_table.csv" if detrend is None else f"trial_table_{detrend}.csv"
    cache = C.OUT_DIR / name
    if C.full_data() and cache.exists() and not force:
        return pd.read_csv(cache)
    rows = [trial_scores(hbedb.load_trial(t), detrend) for t in hbedb.trial_ids()]
    df = pd.DataFrame(rows)
    if C.full_data():
        C.OUT_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache, index=False)
    return df
