# AI-assisted code (team statement and per-step log: docs/AI_USE_LOG.md).
"""B7: demo cases. Post-landing tests are SIMULATED and labelled as such.

A demo person's baseline is their own three HBEDB trials per condition (first 20-s windows). A simulated test at
t hours after landing scales the person's real second-window scores (real trial-to-trial spread) onto NASA's
typical crew recovery curve (Wood 2015 Table III):

    EQ_k(t) = b x r_sim(t) x (w2_k / median(w2)),   r_sim(t) = 1 - D exp(-t / tau) - delta(t)

The forecast uses the same curve, so the generator and the forecast agree by construction. Statuses shown are
whatever the decision engine returns for the generated test; nothing is forced.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import config as C
from . import forecast as F
from . import hbedb
from . import medicine as M
from . import params as P
from . import signals as S
from .decision import GO, ConditionInput, Decision, decide, decide_confirmed

SIM_LABEL = "simulated post-landing test"
SCENARIOS = ("Healthy check", "Just landed (6 h)", "First GO test", "Confirmation test 2 h later",
             "Fall during test")

# Demo people (HBEDB subject numbers), chosen by scripts/make_demo.py; see data/demo/DEMO_PEOPLE.md
DEMO_PEOPLE: dict[str, int] = {}


@dataclass
class Medicine:
    dose_mg: float = 0.0
    route: str = "oral"
    t_dose: float = 0.0  # hours since landing

    @property
    def active(self) -> bool:
        return self.dose_mg > 0


@dataclass
class Person:
    subject: int
    age: float
    age_group: str
    height_cm: float
    mass_kg: float
    w1: dict = field(default_factory=dict)       # condition -> 3 first-window scores
    w2: dict = field(default_factory=dict)       # condition -> 3 second-window scores
    valid: dict = field(default_factory=dict)    # condition -> 3 validity flags

    def baseline(self, cond: str) -> float:
        return float(np.median(self.w1[cond]))

    def baseline_valid(self, cond: str) -> bool:
        return len(self.w1.get(cond, [])) == 3 and all(self.valid[cond]) and bool(np.all(np.isfinite(self.w1[cond])))


def load_person(subject: int, root=None) -> Person:
    info = hbedb.load_info(None if root is None else str(root))
    rows = info[info.Subject == subject].sort_values("Trial")
    if rows.empty:
        raise KeyError(f"subject {subject} not available")
    first = rows.iloc[0]
    person = Person(int(subject), float(first.Age), str(first.AgeGroup), float(first.Height), float(first.Weight))
    for cond in C.CONDITIONS:
        ids = rows[rows.condition == cond].Trial.tolist()
        sc = [S.trial_scores(hbedb.load_trial(t, root)) for t in ids]
        person.w1[cond] = [s["eq_w1"] for s in sc]
        person.w2[cond] = [s["eq_w2"] for s in sc]
        person.valid[cond] = [bool(s["valid"]) and np.isfinite(s["eq_w2"]) for s in sc]
    return person


def r_sim(t: float, cond: str, person: Person, med: Medicine | None = None) -> float:
    w = F.wood(cond)
    med = med or Medicine()
    d = M.delta(t, med.dose_mg, med.route, P.drug_slope(cond), person.baseline(cond), med.t_dose) if med.active else 0.0
    return float(F.recovery(t, w["D"], w["tau"]) - float(d))


def simulated_trials(person: Person, cond: str, t: float | None, med: Medicine | None = None) -> list[float]:
    """t = None -> healthy check (the person's real second-window scores, no landing)."""
    w2 = np.asarray(person.w2[cond], dtype=float)
    if t is None:
        return list(np.clip(w2, 0, 100))
    b = person.baseline(cond)
    eq = b * r_sim(t, cond, person, med) * (w2 / np.median(w2))
    return list(np.clip(eq, 0, 100))


def condition_input(person: Person, cond: str, trial_eqs, fell=None) -> ConditionInput:
    b = person.baseline(cond)
    return ConditionInput(list(trial_eqs), list(fell or [False] * len(trial_eqs)), b,
                          P.noise_q95(b, cond, person.age_group), P.p5(cond, person.age_group),
                          list(person.valid[cond]), person.baseline_valid(cond))


def run_test(person: Person, t: float | None, session_id: str, med: Medicine | None = None,
             fall_condition: str | None = None) -> tuple[Decision, dict]:
    inputs, trials = {}, {}
    for cond in C.CONDITIONS:
        eqs = simulated_trials(person, cond, t, med)
        fell = [False] * len(eqs)
        if cond == fall_condition:
            fell[0] = True
        trials[cond] = eqs
        inputs[cond] = condition_input(person, cond, eqs, fell)
    return decide(inputs, session_id, 0.0 if t is None else float(t)), trials


def first_go_time(person: Person, med: Medicine | None = None, horizon: float = C.FORECAST_HORIZON_H,
                  step: float = C.GRID_STEP_H) -> float | None:
    """Earliest time on a 0.5-h grid at which the generated test is GO for the test itself; None if not reached."""
    for t in np.arange(step, horizon + step / 2, step):
        dec, _ = run_test(person, float(t), "probe", med)
        if dec.status == GO:
            return float(t)
    return None


@dataclass
class ScenarioResult:
    name: str
    t_hours: float | None
    test: Decision | None          # the latest measured test
    overall: Decision              # after the two-test rule
    trials: dict
    note: str = ""
    history_times: list = field(default_factory=list)
    go_reached: bool = True        # False: the person never reaches GO within the forecast horizon


def run_scenario(person: Person, name: str, med: Medicine | None = None) -> ScenarioResult:
    med = med or Medicine()
    if name == "Healthy check":
        test, trials = run_test(person, None, "S1")
        return ScenarioResult(name, None, test, decide_confirmed([test]), trials,
                              "Second 20-s windows of the same HBEDB trials (no landing).", [0.0])
    if name == "Fall during test":
        test, trials = run_test(person, None, "S1", fall_condition="foam_ec")
        return ScenarioResult(name, None, test, decide_confirmed([test]), trials,
                              "Baseline session with one foam, eyes-closed trial marked as a fall for demonstration (not a recorded event).", [0.0])
    if name == "Just landed (6 h)":
        test, trials = run_test(person, 6.0, "S1", med)
        return ScenarioResult(name, 6.0, test, decide_confirmed([test]), trials, SIM_LABEL, [6.0])
    t1 = first_go_time(person, med)
    if t1 is None:  # keep the simulated test's time and provenance; it is NOT a baseline-day recording
        T = float(C.FORECAST_HORIZON_H)
        test, trials = run_test(person, T, "S1", med)
        return ScenarioResult(name, T, test, decide_confirmed([test]), trials,
                              f"{SIM_LABEL} at {T:g} h. GO is not reached within 10 days for this participant, so "
                              "neither a first GO nor a confirmatory session exists", [T], go_reached=False)
    first, trials1 = run_test(person, t1, "S1", med)
    if name == "First GO test":
        return ScenarioResult(name, t1, first, decide_confirmed([first]), trials1,
                              f"{SIM_LABEL}, earliest GO on a 0.5-h grid", [t1])
    t2 = t1 + C.MIN_TEST_GAP_H
    second, trials2 = run_test(person, t2, "S2", med)
    return ScenarioResult(name, t2, second, decide_confirmed([first, second]), trials2,
                          f"{SIM_LABEL}, second session {C.MIN_TEST_GAP_H:g} h after the first GO", [t1, t2])


# ---------------------------------------------------------------- forecast for the screen
@dataclass
class ConditionForecast:
    condition: str
    r_m: float
    q: float | None
    hours: tuple | None      # (low, mid, high) hours after the test; None if q >= 1
    D_i: float
    tau: float


def forecast_after_test(person: Person, test: Decision, t_m: float, med: Medicine | None = None) -> list:
    med = med or Medicine()
    out = []
    for cond in C.CONDITIONS:
        res = test.per_condition.get(cond)
        if res is None or not np.isfinite(res.ratio):
            continue
        b = person.baseline(cond)
        q = F.target(b, P.noise_q95(b, cond, person.age_group), P.p5(cond, person.age_group))
        w = F.wood(cond)
        b_c = P.drug_slope(cond)
        hours = []
        for tau in (w["tau_low"], w["tau"], w["tau_high"]):
            D_i = M.initial_deficit(res.ratio, t_m, tau, med.dose_mg, med.route, b_c, b, med.t_dose)
            tg = M.t_go(D_i, tau, q, med.dose_mg, med.route, b_c, b, med.t_dose, t_m)
            hours.append(None if tg is None else tg - t_m)
        D_mid = M.initial_deficit(res.ratio, t_m, w["tau"], med.dose_mg, med.route, b_c, b, med.t_dose)
        out.append(ConditionForecast(cond, res.ratio, q if q < 1 else None,
                                     None if hours[1] is None else tuple(hours), D_mid, w["tau"]))
    return out
