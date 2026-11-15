# AI-assisted code (team statement and per-step log: docs/AI_USE_LOG.md).
"""B4: decision rules (MATH_FRAMEWORK §4). Status comes only from a measured balance test.

Per condition, in this order: invalid input -> CANNOT ASSESS; any fall -> NO-GO; r < 0.75 -> NO-GO;
score below the population floor P5 -> CAUTION; r / q95 >= 0.75 -> GO, otherwise CAUTION.
Overall = worst condition; a missing condition caps the result at CAUTION.
Two-test rule: overall GO only when the two most recent tests are both measured GO, in different sessions,
at least 2 h apart; otherwise CAUTION. Never better than the latest test.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from . import config as C

GO, CAUTION, NOGO, CA = "GO", "CAUTION", "NO-GO", "CANNOT ASSESS"


@dataclass(frozen=True)
class ConditionInput:
    trial_eqs: Sequence[float]
    fell: Sequence[bool]
    baseline: float
    q95: float
    p5: float
    valid: Sequence[bool]
    baseline_valid: bool


@dataclass(frozen=True)
class ConditionResult:
    status: str
    reason: str
    score: float = float("nan")
    ratio: float = float("nan")
    lower_bound: float = float("nan")


@dataclass(frozen=True)
class Decision:
    status: str
    reason: str
    per_condition: dict = field(default_factory=dict)
    measured: bool = False
    session_id: str | None = None
    t_hours: float | None = None
    inputs: dict | None = field(default=None, compare=False, repr=False)  # measured inputs (set by decide())


def _is_bool(x) -> bool:
    return isinstance(x, (bool, np.bool_))


def _is_real(x) -> bool:
    """A real number (not bool, not complex, not a string, not a masked value)."""
    return isinstance(x, (int, float, np.integer, np.floating)) and not _is_bool(x) and x is not np.ma.masked


_SCALARS = (int, float, np.float64, np.float32, np.int64, np.int32)  # exact types: no behaviour-changing subclasses


def _scalar(x) -> float | None:
    """A finite real scalar converted exactly once, or None."""
    if type(x) not in _SCALARS:
        return None
    v = float(x)
    return v if math.isfinite(v) else None


def _finite(x) -> bool:
    return _scalar(x) is not None


_CONTAINERS = (list, tuple, np.ndarray)  # whitelist by EXACT type: no iterators, generators, strings, and no
                                         # subclasses (e.g. masked arrays, whose masked values would be ignored)


def _container_ok(x) -> bool:
    return type(x) in _CONTAINERS


def _as_scores(eqs) -> np.ndarray | None:
    """Trial scores as a 1-D float array, or None if malformed. Only lists, tuples or 1-D arrays of real
    numbers are accepted (complex, bool, string and object values are rejected before any conversion)."""
    if not _container_ok(eqs):
        return None
    if isinstance(eqs, np.ndarray):
        if eqs.ndim != 1 or eqs.dtype.kind not in "iuf":
            return None
        return eqs.astype(float)
    if not all(_is_real(v) for v in eqs):
        return None
    return np.array([float(v) for v in eqs], dtype=float)


def _as_flags(x) -> tuple | None:
    """Yes/no flags as a tuple of Python bools, or None if malformed (same container whitelist)."""
    if not _container_ok(x):
        return None
    if isinstance(x, np.ndarray):
        if x.ndim != 1 or x.dtype.kind != "b":
            return None
        return tuple(bool(v) for v in x)
    if not all(_is_bool(v) for v in x):
        return None
    return tuple(bool(v) for v in x)


@dataclass(frozen=True)
class _Normalised:
    eqs: np.ndarray | None
    fell: tuple | None
    valid: tuple | None
    b: float | None
    q95: float | None
    p5: float | None


def _normalise(ci: ConditionInput) -> _Normalised:
    """Every container is read exactly once here; validation and scoring use only these values."""
    return _Normalised(_as_scores(ci.trial_eqs), _as_flags(ci.fell), _as_flags(ci.valid),
                       _scalar(ci.baseline), _scalar(ci.q95), _scalar(ci.p5))


def _validity_problem(ci: ConditionInput, nz: _Normalised) -> str | None:
    if nz.eqs is None:
        return "trial scores missing or malformed"
    n = nz.eqs.size
    if n < C.MIN_TRIALS:
        return f"fewer than {C.MIN_TRIALS} trials"
    if nz.valid is None or nz.fell is None or len(nz.valid) != n or len(nz.fell) != n:
        return "validity or fall information missing, incomplete or not yes/no"
    if not _is_bool(ci.baseline_valid):
        return "baseline validity missing"
    if not all(nz.valid):
        return "a trial is invalid"
    if not ci.baseline_valid:
        return "baseline is invalid"
    if nz.b is None or not (0.0 < nz.b <= 100.0):
        return "baseline out of range"
    if nz.q95 is None or nz.q95 < 1.0:
        return "noise margin undefined"
    if nz.p5 is None:
        return "population floor undefined"
    if not np.all(np.isfinite(nz.eqs)) or np.any(nz.eqs < 0.0) or np.any(nz.eqs > 100.0):
        return "a score is outside 0-100"
    return None


def decide_condition(ci: ConditionInput) -> ConditionResult:
    nz = _normalise(ci)
    problem = _validity_problem(ci, nz)
    if problem:
        return ConditionResult(CA, f"Cannot assess: {problem}.")
    score = float(np.median(nz.eqs))
    b, q95, p5 = nz.b, nz.q95, nz.p5  # the same values that passed validation
    r = score / b
    lb = r / q95
    if any(nz.fell):
        return ConditionResult(NOGO, "A trial ended in a fall or was stopped.", score, r, lb)
    if r < C.R_NOGO:
        shown = math.floor(r * 1e4) / 1e4  # truncated, never rounded up to 0.75
        return ConditionResult(NOGO, f"Below 75% of baseline (ratio {shown:.4f}, below 0.75).",
                               score, r, lb)
    if score < p5:
        return ConditionResult(CAUTION, "Below the healthy population floor (5th percentile). Refer to the crew surgeon.",
                               score, r, lb)
    if lb >= C.R_NOGO:
        return ConditionResult(GO, "At or above 75% of baseline after allowance for test–retest variability.", score, r, lb)
    return ConditionResult(CAUTION, "At or above 75% of baseline, but test–retest variability could mask a true decrement.",
                           score, r, lb)


def _worst(statuses) -> str:
    return max(statuses, key=lambda s: C.STATUS_RANK[s])


def decide(inputs: dict, session_id: str | None = None, t_hours: float | None = None) -> Decision:
    """Overall status of one measured test session (all four conditions)."""
    per = {}
    missing = []
    for cond in C.CONDITIONS:
        ci = inputs.get(cond) if inputs else None
        if ci is None:
            missing.append(cond)
            continue
        per[cond] = decide_condition(ci)
    if not per:
        return Decision(CA, "Cannot assess: no conditions measured.", per, True, session_id, t_hours, dict(inputs or {}))
    status = _worst(r.status for r in per.values())
    worst_cond = max(per, key=lambda c: C.STATUS_RANK[per[c].status])
    reason = f"{C.CONDITION_LABELS[worst_cond]}: {per[worst_cond].reason}"
    if missing and status == GO:
        status = CAUTION
        reason = "Not all four conditions were measured. GO requires the complete test."
    elif status == GO:
        reason = "All four conditions exceed 75% of baseline after allowance for test–retest variability."
    return Decision(status, reason, per, True, session_id, t_hours, dict(inputs))


def _is_full_go(d: Decision) -> bool:
    """A GO is trusted only if re-deciding its own measured inputs gives GO in all four conditions.
    Labels and numbers supplied by a caller are never trusted (provenance by recomputation)."""
    if d.measured is not True or not isinstance(d.inputs, dict) or set(d.inputs) != set(C.CONDITIONS):
        return False
    if not all(type(ci) is ConditionInput for ci in d.inputs.values()):
        return False
    return all(decide_condition(ci).status == GO for ci in d.inputs.values())


def _session_ok(sid) -> bool:
    return type(sid) is str and sid.strip() != ""


def decide_confirmed(history: Sequence[Decision]) -> Decision:
    """Overall status from the test history. GO needs two qualifying GO tests.

    Ordering contract: every entry needs a finite time and times must strictly increase along the list
    (oldest first). Anything else (missing time, out of order, tied times) -> CANNOT ASSESS, because the
    latest result cannot be identified safely."""
    if not history:
        return Decision(CA, "Cannot assess: no test recorded.")
    times = [h.t_hours for h in history]
    if not all(_finite(t) for t in times) or any(float(b) <= float(a) for a, b in zip(times[:-1], times[1:])):
        last = history[-1]
        return Decision(CA, "Cannot assess: test times are missing, tied or out of order.",
                        last.per_condition, last.measured, last.session_id, last.t_hours)
    latest = history[-1]
    if latest.measured is not True:
        return Decision(CA, "Cannot assess: the latest result is not a measured test.", latest.per_condition,
                        False, latest.session_id, latest.t_hours)
    if latest.status == GO and not _is_full_go(latest):
        return Decision(CA, "Cannot assess: the latest GO lacks a complete set of per-condition GO results.",
                        latest.per_condition, latest.measured, latest.session_id, latest.t_hours)
    if latest.status != GO:
        return latest
    caution = Decision(CAUTION, "GO in this session. A confirmatory test in a separate session at least "
                       f"{C.MIN_TEST_GAP_H:g} h later is required.", latest.per_condition, True,
                       latest.session_id, latest.t_hours)
    if len(history) < 2:
        return caution
    prev = history[-2]
    ok = (prev.measured is True and prev.status == GO and _is_full_go(prev)
          and _session_ok(latest.session_id) and _session_ok(prev.session_id)
          and latest.session_id.strip() != prev.session_id.strip()
          and float(latest.t_hours) - float(prev.t_hours) >= C.MIN_TEST_GAP_H)
    if not ok:
        return caution
    return Decision(GO, "Two measured GO tests in separate sessions at least 2 h apart.",
                    latest.per_condition, True, latest.session_id, latest.t_hours)
