# AI-assisted code (team statement and per-step log: docs/AI_USE_LOG.md).
"""Gravity-Transition Readiness: can this astronaut safely leave the vehicle now, and if not, when?

Interactive: the user sets the balance-test inputs and the decision engine returns the result live.
Run:  streamlit run app.py
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from readiness import config as C
from readiness import crew_labs as L
from readiness import hbedb as H
from readiness import signals as S
from readiness import forecast as F
from readiness import medicine as M
from readiness import params as P
from readiness import scenarios as SC
from readiness.decision import ConditionInput, Decision, decide, decide_confirmed

st.set_page_config(page_title="Gravity-Transition Readiness", page_icon="🧭", layout="wide")

STATUS_STYLE = {  # colour is never the only cue: each status has a symbol and a word
    "GO": ("#1b5e20", "#e8f5e9", "✔"),
    "CAUTION": ("#8a5a00", "#fff8e1", "!"),
    "NO-GO": ("#b71c1c", "#ffebee", "✖"),
    "CANNOT ASSESS": ("#37474f", "#eceff1", "?"),
}
LINKS = {
    "Wood, Paloski and Clark 2015 (NASA crew posturography after ISS)": "https://doi.org/10.3357/AMHP.EC07.2015",
    "Human Balance Evaluation Database (PhysioNet)": "https://physionet.org/content/hbedb/1.0.0/",
    "Santos and Duarte 2016 (HBEDB paper)": "https://doi.org/10.7717/peerj.2648",
    "NASA Human Research Program: risks of human spaceflight": "https://humanresearchroadmap.nasa.gov/risks/",
}
OUTCOMES = ("normal", "fall", "invalid")
OUTCOME_LABELS = {"normal": "completed", "fall": "fall", "invalid": "invalid recording"}
GAP = C.MIN_TEST_GAP_H
T_MAX = 240.0  # supported time range after landing (h)

# The decision rules, numbered once and cited by number wherever a result is explained.
RULES = [
    "An invalid recording yields CANNOT ASSESS.",
    "A fall or a stopped trial yields NO-GO, whatever the score.",
    "A score below 75% of baseline yields NO-GO.",
    "A score below the healthy population floor (5th percentile) yields CAUTION and referral to the crew surgeon.",
    "A score at or above the GO threshold yields GO. The threshold keeps the score at or above 75% of baseline "
    "after allowance for test–retest variability.",
    "Any other score yields CAUTION.",
    "The overall result is the least favourable condition. Overall GO requires two consecutive GO tests in "
    f"separate sessions at least {GAP:g} h apart.",
]


def rule_of(reason: str) -> int:
    """Number (1–7) of the rule that produced an engine reason."""
    for key, n in (("test times", 7), ("Cannot assess", 1), ("fall", 2), ("Below 75%", 3), ("population floor", 4),
                   ("but test–retest", 6), ("Two measured GO", 7), ("confirmatory", 7), ("Not all four", 7),
                   ("after allowance", 5)):
        if key in reason:
            return n
    return 7


# ---------------------------------------------------------------- data (cached)
@st.cache_data(show_spinner=False)
def demo_people() -> dict:
    return json.loads((C.DEMO_DIR / "demo_people.json").read_text())


@st.cache_resource(show_spinner="Loading balance recordings ...")
def person(subject: int) -> SC.Person:
    return SC.load_person(subject)


VOLUNTEER_LABELS = {"Young healthy": "A · younger adult", "Older healthy": "B · older adult",
                    "Below the population floor": "C · low baseline balance"}
people = demo_people()
PARTICIPANTS = [f"Participant {VOLUNTEER_LABELS.get(k, k)}" for k in people]


@st.cache_data(show_spinner="Preparing examples ...")
def examples() -> dict:
    """Example inputs derived from the HBEDB recordings (post-landing ones simulated). Each fills the controls."""
    out = {}
    for pi, (key, subj) in enumerate(people.items()):
        p = SC.load_person(int(subj))
        who = PARTICIPANTS[pi].replace("Participant ", "")
        for name in ("Just landed (6 h)", "First GO test", "Confirmation test 2 h later", "Fall during test",
                     "Healthy check"):  # the landing story first, then the baseline-day checks
            r = SC.run_scenario(p, name)
            if name == "Confirmation test 2 h later" and not r.go_reached:
                continue
            if name == "First GO test":
                stage = (f"{r.t_hours:g} h after landing, first GO" if r.go_reached
                         else f"{r.t_hours:g} h after landing, GO not reached")
            elif name == "Confirmation test 2 h later":
                stage = f"{r.t_hours:g} h after landing, confirmatory session"
            elif name == "Just landed (6 h)":
                stage = "6 h after landing"
            elif name == "Healthy check":
                stage = "baseline day, no landing"
            else:
                stage = "baseline day, simulated fall"
            inp = r.test.inputs
            history = []
            if len(r.history_times) > 1:  # the first GO session, with its own simulated trials and time
                t1 = float(r.history_times[0])
                _, tr1 = SC.run_test(p, t1, "S1")
                history = [{"t": t1, "trials": {c: [float(v) for v in tr1[c]] for c in C.CONDITIONS},
                            "out": {c: "normal" for c in C.CONDITIONS}, "source": "SIMULATED EXAMPLE"}]
            awaiting = False
            if history:  # the confirmatory session is recorded too; the next draft would start 2 h later
                history.append({"t": float(r.t_hours), "trials": {c: [float(v) for v in inp[c].trial_eqs]
                                                                  for c in C.CONDITIONS},
                                "out": {c: "normal" for c in C.CONDITIONS}, "source": "SIMULATED EXAMPLE"})
                awaiting = True
            out[f"{who} · {stage}"] = {
                "who": pi, "landed": r.t_hours is not None, "awaiting": awaiting,
                "t": float(r.t_hours or 6.0) + (GAP if awaiting else 0.0), "history": history,
                "trials": {c: [float(v) for v in inp[c].trial_eqs] for c in C.CONDITIONS},
                "eq": {c: float(np.median(inp[c].trial_eqs)) for c in C.CONDITIONS},
                "out": {c: "fall" if any(inp[c].fell) else "normal" for c in C.CONDITIONS},
                "simulated": r.t_hours is not None or name == "Fall during test"}
    return out


EX = examples()
EX_NAMES = list(EX)
ss = st.session_state


def load_example():
    e = EX[ss.example]
    ss.who, ss.landed, ss.t = PARTICIPANTS[e["who"]], e["landed"], e["t"]
    ss.history = [dict(h) for h in e["history"]]
    ss.generated = None
    ss.awaiting = e["awaiting"]
    ss.dose, ss.route, ss.dose_after = 0.0, "oral", 0.0  # an example never inherits an earlier medicine scenario
    for c in C.CONDITIONS:
        ss[f"eq_{c}"], ss[f"out_{c}"] = e["eq"][c], e["out"][c]
        for k in range(3):
            ss[f"tr_{c}_{k}"] = e["trials"][c][k]


def trials_of(c) -> list:
    """The three trial scores of the current session in a condition (equal values in single-score mode)."""
    if ss.get("trials_mode"):
        return [float(ss[f"tr_{c}_{k}"]) for k in range(3)]
    return [float(ss[f"eq_{c}"])] * 3


def mark_entered():  # any score or outcome entered for the next session makes it a session of its own
    ss.awaiting = False


def mode_change():  # keep the two input modes consistent when switching
    for c in C.CONDITIONS:
        tr = [float(ss[f"tr_{c}_{k}"]) for k in range(3)]
        if ss.trials_mode and float(np.median(tr)) != float(ss[f"eq_{c}"]):
            for k in range(3):
                ss[f"tr_{c}_{k}"] = float(ss[f"eq_{c}"])
        elif not ss.trials_mode:
            ss[f"eq_{c}"] = float(np.median(tr))


if "init" not in ss:
    ss.init = True
    ss.example = next(n for n in EX_NAMES if n.startswith("A ·") and "6 h after landing" in n)
    load_example()
    ss.dose, ss.route, ss.dose_after = 0.0, "oral", 0.0
    ss.trials_mode = False

# ---------------------------------------------------------------- header
st.title("Gravity-Transition Readiness Model")
st.markdown("#### Can this crew member leave the vehicle safely after landing, and if not, when should balance be retested?")
h1, h2, h3 = st.columns(3)
with h1:
    st.markdown("**The problem.** Balance is most impaired immediately after a gravity transition. After ISS missions, "
                "the NASA crew recovery model estimates an equilibrium score of 13.2 at landing against 74.9 before "
                "flight (eyes closed, sway-referenced support, n = 37). On the Moon or Mars, no ground team will be "
                "present to assist a crew member who falls during egress.")
with h2:
    st.markdown("**The measurement.** A standing-balance test on a force plate: three 20-s trials in each of "
                "four sensory conditions, scored with the NASA equilibrium-score formula and compared with the crew member's "
                "own preflight baseline.")
with h3:
    st.markdown("**The decision.** Seven explicit safety rules return GO, CAUTION or NO-GO, name the rule applied, and "
                "estimate the retest time from NASA crew recovery data. Adjust any input on the left to see the "
                "decision respond.")
st.caption("Decision support for the crew surgeon. It does not constitute clearance. Thresholds are provisional and "
           "not validated for egress.")

left, right = st.columns([2, 3], gap="large")

# ---------------------------------------------------------------- inputs
with left:
    st.subheader("Test inputs")
    st.selectbox("Load an example", EX_NAMES, key="example", on_change=load_example,
                 help="Fills every control, and resets the pharmacological scenario to no dose. Post-landing examples are simulated from the participant's own "
                      "HBEDB recordings and the NASA crew recovery model.")
    st.radio("Crew member baseline", PARTICIPANTS, key="who", on_change=lambda: ss.update(history=[], awaiting=False),
                 help="Preflight baseline and age group. HBEDB reference scores serve as the preflight proxy. "
                      "Changing the crew member clears the session history.")
    pi = PARTICIPANTS.index(ss.who)
    subject = int(list(people.values())[pi])
    p = person(subject)
    st.toggle("After landing", key="landed")
    st.slider("Hours after landing", 0.5, T_MAX, step=0.5, key="t", format="%.1f h", disabled=not ss.landed)
    T = float(ss.t) if ss.landed else None

    def fill_typical():  # replaces the scores only; falls and invalid recordings are kept (rules 1 and 2)
        ss.generated = {}
        ss.awaiting = False
        for c in C.CONDITIONS:  # the participant's own trial spread on the typical NASA crew curve
            tr = [float(v) for v in SC.simulated_trials(p, c, float(ss.t))]
            ss[f"eq_{c}"] = float(np.median(tr))
            for k in range(3):
                ss[f"tr_{c}_{k}"] = tr[k]
            ss.generated[c] = tr

    st.button("Set scores to typical NASA crew recovery at this time", on_click=fill_typical,
              disabled=not ss.landed, use_container_width=True)

    st.markdown("**Equilibrium score per condition** (EQ; 100 = no sway)")
    st.toggle("Enter the three trials separately", key="trials_mode", on_change=mode_change,
              help="Single-score mode applies one score to all three trials. Trial mode takes the three recorded "
                   "trial scores, and the decision uses their median.")
    for c in C.CONDITIONS:
        b = p.baseline(c)
        lab = f"{C.CONDITION_LABELS[c].capitalize()} · baseline {b:.1f}"
        if ss.trials_mode:
            st.markdown(f"<span style='font-size:0.9rem'>{lab} · median "
                        f"{float(np.median(trials_of(c))):.1f}</span>", unsafe_allow_html=True)
            cols = st.columns(3)
            for k in range(3):
                cols[k].number_input(f"Trial {k + 1}", 0.0, 100.0, step=0.1, format="%.1f", key=f"tr_{c}_{k}",
                                     on_change=mark_entered)
        else:
            st.slider(lab, 0.0, 100.0, step=0.1, key=f"eq_{c}", format="%.1f", on_change=mark_entered)
        st.radio("Trial outcome", OUTCOMES, key=f"out_{c}", horizontal=True, format_func=OUTCOME_LABELS.get, on_change=mark_entered,
                 label_visibility="collapsed")

    st.markdown("**Session history**")
    hist = ss.get("history", [])
    last_t = hist[-1]["t"] if hist else None

    def record():
        ss.history = hist + [{"t": float(ss.t), "trials": {c: trials_of(c) for c in C.CONDITIONS},
                              "out": {c: ss[f"out_{c}"] for c in C.CONDITIONS},
                              "source": ss.get("last_source", "USER-ENTERED VALUES")}]
        ss.t = min(T_MAX, float(ss.t) + GAP)  # the next session starts at the earliest permitted time
        ss.awaiting = True  # the next session counts only once its own scores are entered

    b1, b2 = st.columns(2)
    b1.button("Record this session", on_click=record, use_container_width=True,
              disabled=(not ss.landed or ss.get("awaiting", False) or (last_t is not None and float(ss.t) <= last_t)
))
    b2.button("Clear sessions", on_click=lambda: ss.update(history=[], awaiting=False), use_container_width=True, disabled=not hist)
    st.caption("Each recorded session keeps its own trial scores and time after landing. The current inputs form the "
               f"next session. Overall GO requires two consecutive GO sessions at least {GAP:g} h apart (rule 7). "
               "Recording advances the time by 2 h, and the next session counts only once its own scores are entered. "
               f"Sessions can be recorded up to {T_MAX:g} h after landing, the supported range of the model.")

# ---------------------------------------------------------------- run the decision engine on the inputs
def build_inputs(trials: dict, outs: dict) -> dict:
    out = {}
    for c in C.CONDITIONS:
        b = p.baseline(c)
        oc = outs[c]
        out[c] = ConditionInput(list(trials[c]), [oc == "fall", False, False], b, P.noise_q95(b, c, p.age_group),
                                P.p5(c, p.age_group), [oc != "invalid"] * 3, p.baseline_valid(c))
    return out


inputs = build_inputs({c: trials_of(c) for c in C.CONDITIONS}, {c: ss[f"out_{c}"] for c in C.CONDITIONS})
t_now = T if T is not None else 0.0
history = ss.get("history", []) if T is not None else []  # sessions are timed from landing
hist_decisions = [decide(build_inputs(h["trials"], h["out"]), f"S{i + 1}", h["t"]) for i, h in enumerate(history)]
awaiting = bool(ss.get("awaiting")) and bool(history)
if awaiting:  # no new session yet: the assessment rests on the recorded sessions only
    test = hist_decisions[-1]
    overall = decide_confirmed(hist_decisions)
    T = t_now = float(history[-1]["t"])
else:
    test = decide(inputs, f"S{len(history) + 1}", t_now)
    overall = decide_confirmed(hist_decisions + [test])
# Overall GO rests only on recorded sessions: an entered but unrecorded confirmatory session must be recorded first.
pending_record = (not awaiting) and bool(history) and overall.status == "GO"
if pending_record:
    overall = Decision("CAUTION", "GO in this session, which would confirm the recorded GO session. Record this "
                       "session to complete the confirmatory test.", test.per_condition, True, test.session_id, t_now)
per = test.per_condition
q_by_cond = {c: F.target(p.baseline(c), P.noise_q95(p.baseline(c), c, p.age_group), P.p5(c, p.age_group))
             for c in C.CONDITIONS}
governing = max(per, key=lambda c: C.STATUS_RANK[per[c].status])
any_fall = any(ss[f"out_{c}"] == "fall" for c in C.CONDITIONS)
landed = T is not None
e = EX[ss.example]
def _same_scores(ref: dict) -> bool:
    if ss.get("trials_mode"):
        return all(trials_of(c) == list(ref[c]) for c in C.CONDITIONS)
    return all(float(ss[f"eq_{c}"]) == float(np.median(ref[c])) for c in C.CONDITIONS)


unchanged = (PARTICIPANTS[e["who"]] == ss.who and e["landed"] == ss.landed and (not ss.landed or e["t"] == ss.t)
             and [h["t"] for h in ss.get("history", [])] == [h["t"] for h in e["history"]]
             and _same_scores(e["trials"]) and all(e["out"][c] == ss[f"out_{c}"] for c in C.CONDITIONS))
generated = bool(ss.get("generated")) and _same_scores(ss.generated)
source = (("SIMULATED EXAMPLE" if e["simulated"] else "HBEDB RECORDING") if unchanged
          else "SIMULATED: TYPICAL NASA RECOVERY" if generated else "USER-ENTERED VALUES")
if awaiting:
    source = history[-1].get("source", source)
else:
    ss.last_source = source  # stored with the session if it is recorded
hist_sources = [h.get("source", "USER-ENTERED VALUES") for h in history]
tag_text = (source + " · SIMULATED SESSION IN HISTORY"
            if any("SIMULATED" in x for x in hist_sources) and "SIMULATED" not in source else source)

# The planned dose stays in force when the session is GO: it can lower a passing score before a confirmatory test.
med_allowed = landed and test.status != "CANNOT ASSESS" and overall.status != "CANNOT ASSESS" and not any_fall
med = (SC.Medicine(float(ss.get("dose", 0.0)), ss.get("route", "oral"), T + float(ss.get("dose_after", 0.0)))
       if med_allowed else SC.Medicine())
fc, fc_none, reach, unreach, passed = [], {}, [], [], set()


def q_of(c):
    return F.target(p.baseline(c), P.noise_q95(p.baseline(c), c, p.age_group), P.p5(c, p.age_group))


if med_allowed:
    fc = SC.forecast_after_test(p, test, T, med)
    fc_none = {f.condition: f for f in SC.forecast_after_test(p, test, T, SC.Medicine())}
    # A condition already at or above its GO threshold needs no recovery. The recovery model cannot represent a
    # score above baseline, so such a condition is neither 'reachable' nor 'unreachable': it has passed.
    # Only a condition whose crossing cannot be computed (GO threshold at or above baseline) and that no planned dose
    # can lower is set aside. Every computed crossing, including a dose-induced later one, enters the estimate.
    passed = {f.condition for f in fc if f.hours is None and f.r_m >= q_of(f.condition)
              and not (med.active and P.drug_slope(f.condition) is not None)}
    reach = [f for f in fc if f.hours is not None]
    unreach = [f for f in fc if f.hours is None and f.condition not in passed]
worst = max((f.hours[1] for f in reach), default=0.0)


def dose_note() -> str:
    """Effect of an active planned dose on a session whose scores are at or above every GO threshold."""
    if not med.active:
        return ""
    if unreach:
        return (" With the planned dose, no time at which every condition regains its GO threshold can be estimated. "
                "Refer to the crew surgeon.")
    if worst > 0:
        return (f" With the planned dose, the typical-recovery model predicts a score below the GO threshold until "
                f"approximately {T + worst:.0f} h after landing."
                + (f" This time lies beyond the supported range of {T_MAX:g} h after landing and is an extrapolation "
                   "of the recovery model." if T + worst > T_MAX else ""))
    return ""


def next_action() -> str:
    ov, ts = overall.status, test.status
    if ov == "GO":
        note = dose_note()
        return ("No further testing is required under the decision rules. The egress decision rests with the crew "
                "surgeon." + (note + (" Reassessment after the dose is advised." if "Refer" not in note else "")
                              if note else ""))
    if ov == "CANNOT ASSESS":
        if "test times" in overall.reason:
            if history[-1]["t"] + GAP > T_MAX:
                return (f"No further session can be recorded within the supported range of {T_MAX:g} h after "
                        "landing. Clear the session history to start a new assessment.")
            return (f"Set the time of this session at least {GAP:g} h after the last recorded session "
                    f"({history[-1]['t']:g} h), or clear the session history.")
        return "Repeat the test with valid recordings in all four sensory conditions."
    if pending_record:
        return "Record this session. Overall GO is given only for recorded sessions." + dose_note()
    if ts == "GO":
        note = dose_note()
        if note and not unreach and worst > GAP:  # the planned dose, not the 2-h gap, sets the earliest time
            return (f"A confirmatory test is required in a separate session at least {GAP:g} h later." + note
                    + " The confirmatory test should not precede that time.")
        if landed and T + GAP > T_MAX:
            return (f"A confirmatory test is required in a separate session at least {GAP:g} h later, which lies "
                    f"beyond the supported range of {T_MAX:g} h after landing. Refer to the crew surgeon." + note)
        return (f"A confirmatory test is required in a separate session at least {GAP:g} h later"
                + (f" (from {T + GAP:g} h after landing)." if landed else ".") + note)
    lead = "Do not leave the vehicle unassisted. " if ts == "NO-GO" else ""
    if not landed or any_fall:
        return lead + "Refer to the crew surgeon and repeat the test in a separate session."
    if unreach:
        return lead + ("No retest time can be estimated because the GO threshold is not reached under the typical "
                       "recovery model. Refer to the crew surgeon.")
    if worst <= 0:
        return lead + "Retest is indicated now: under the typical recovery rate, every condition has reached its GO threshold."
    beyond = (f" This time lies beyond the supported range of {T_MAX:g} h after landing and is an extrapolation of "
              "the recovery model." if T + worst > T_MAX else "")
    return (lead + f"Retest in approximately {worst:.0f} h (≈{T + worst:.0f} h after landing"
            + (", with the planned dose" if med.active else "") + ")." + beyond
            + " A retest, not this estimate, decides GO.")


# ---------------------------------------------------------------- output
with right:
    st.subheader("Model output")
    fg, bg, sym = STATUS_STYLE[overall.status]
    sub = ("confirmatory session entered · record it to complete" if pending_record
           else "single GO session · confirmatory test required" if overall.status == "CAUTION" and test.status == "GO"
           else "two GO sessions · egress decision by the crew surgeon" if overall.status == "GO" else "")
    sub_html = (f'<span style="font-size:1.05rem;font-weight:600;color:{fg};margin-left:12px;vertical-align:middle">'
                f'{sub}</span>' if sub else "")
    tag = ('<span style="font-size:0.75rem;font-weight:700;letter-spacing:0.06em;color:#424242;border:1px solid #757575;'
           f'border-radius:4px;padding:1px 6px;margin-left:10px;vertical-align:middle">{tag_text}</span>')
    rn = rule_of(overall.reason)
    shown_reason = (overall.reason if source == "HBEDB RECORDING"
                    else overall.reason.replace("Two measured GO tests", "Two GO tests"))
    st.markdown(
        f"""<div style="border:3px solid {fg};background:{bg};border-radius:12px;padding:18px 22px;margin:4px 0 8px 0">
        <div style="font-size:2.4rem;font-weight:800;color:{fg};line-height:1.1">{sym} {overall.status}{sub_html}{tag}</div>
        <div style="font-size:1.08rem;color:#212121;margin-top:8px"><b>Rule {rn}:</b> {shown_reason}</div>
        <div style="font-size:1.08rem;color:#212121;margin-top:6px"><b>Recommended action:</b> {next_action()}</div>
        </div>""", unsafe_allow_html=True)
    def _src(x):
        return "simulated" if "SIMULATED" in x else "recording" if x == "HBEDB RECORDING" else "entered"
    if len(hist_decisions):
        sess = [f"{h['t']:g} h {d.status} ({_src(h.get('source', ''))})" for h, d in zip(history, hist_decisions)]
        if not awaiting:
            sess.append(f"{t_now:g} h {test.status} (current, {_src(source)})")
        st.markdown("**Sessions in this assessment:** " + " · ".join(sess))
    if awaiting:
        st.info(f"The {t_now:g} h session is recorded. " + (
            f"Enter the scores of the next session (from {t_now + GAP:g} h after landing) to continue the assessment. "
            "Advancing the time alone does not create a session." if t_now + GAP <= T_MAX else
            f"No further session can be recorded within the supported range of {T_MAX:g} h after landing."))
    nasa_used = ["**NO-GO criterion** of a 25% decrement from the crew member's own baseline (Jain et al. 2010, NASA crew "
                 "posturography)",
                 "**Equilibrium-score formula** of the NASA Sensory Organization Test (Wood et al. 2015)"
                 + ("" if source == "USER-ENTERED VALUES" else ", applied here to a centre-of-mass estimate from "
                    "force-plate signals")]
    if landed:
        nasa_used.append(f"**Typical ISS crew at {T:g} h** on the chart, from the NASA crew recovery model (Wood et al. "
                         "2015, Table III, n = 37)")
    if med_allowed and fc and test.status != "GO" and not unreach and worst > 0:
        nasa_used.append("**Retest time** from the same recovery model")
    st.markdown("**NASA data in this result:** " + " · ".join(nasa_used) + ".")
    if med.active:
        st.info(f"**Pharmacological scenario active:** promethazine {med.dose_mg:g} mg "
                f"{'oral' if med.route == 'oral' else 'intramuscular'}, planned at {med.t_dose:g} h after landing "
                "(unvalidated scenario). Only the retest estimate is adjusted.")
        st.warning(M.WARN_ORTHOSTATIC)

    # Gauge per condition: where the score sits against the NO-GO line and the GO threshold.
    ratios = {c: float(np.median(trials_of(c))) / p.baseline(c) for c in C.CONDITIONS}
    x_max = max(1.15, max(ratios.values()) + 0.05, max(q_by_cond.values()) + 0.05)
    fig = go.Figure()
    names = [C.CONDITION_LABELS[c] for c in C.CONDITIONS][::-1]
    for i, c in enumerate(C.CONDITIONS[::-1]):
        q = q_by_cond[c]
        for x0, x1, col in ((0, C.R_NOGO, "#ffcdd2"), (C.R_NOGO, max(C.R_NOGO, q), "#ffe0b2"), (q, x_max, "#c8e6c9")):
            fig.add_shape(type="rect", x0=x0, x1=x1, y0=i - 0.32, y1=i + 0.32, fillcolor=col, line_width=0, layer="below")
        fig.add_shape(type="line", x0=q, x1=q, y0=i - 0.4, y1=i + 0.4, line=dict(color="#1b5e20", width=2))
        fl = P.p5(c, p.age_group) / p.baseline(c)  # healthy population floor, as a share of this baseline
        if 0 < fl < x_max:
            fig.add_shape(type="line", x0=fl, x1=fl, y0=i - 0.32, y1=i + 0.32,
                          line=dict(color="#5d4037", width=2, dash="dot"))
        r = per[c]
        mark = {"GO": "#1b5e20", "CAUTION": "#8a5a00", "NO-GO": "#b71c1c", "CANNOT ASSESS": "#37474f"}[r.status]
        fig.add_scatter(x=[ratios[c]], y=[i], mode="markers+text", showlegend=False,
                        marker=dict(size=16, color=mark, symbol="x" if ss[f"out_{c}"] == "fall" else "diamond"),
                        text=[f"{ratios[c]:.0%} · {r.status}"], textposition="bottom center",
                        hovertemplate=f"{C.CONDITION_LABELS[c]}: {ratios[c]:.1%} of baseline, GO threshold {q:.1%}"
                                      "<extra></extra>")
        if landed:
            w = F.wood(c)
            r_nasa = F.recovery(T, w["D"], w["tau"])
            fig.add_scatter(x=[r_nasa], y=[i], mode="markers", showlegend=False,
                            marker=dict(size=24, color="rgba(0,0,0,0)", line=dict(color="#0d47a1", width=2.5)),
                            hovertemplate=f"typical ISS crew at {T:g} h: {r_nasa:.0%} (Wood et al. 2015)<extra></extra>")
    fig.add_vline(x=C.R_NOGO, line_color="#b71c1c", line_dash="dot",
                  annotation_text="75%", annotation_position="top")
    fig.update_layout(height=320, margin=dict(t=24, b=40, l=10, r=10),
                      xaxis=dict(range=[0, x_max], tickformat=".0%", title="score as % of own baseline"),
                      yaxis=dict(tickvals=list(range(4)), ticktext=names, range=[-0.6, 3.6]))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Red: below 75% of baseline (NO-GO, rule 3). Amber: CAUTION band. Green: at or above the GO threshold "
               "(solid green line, rule 5). Dotted brown line: healthy population floor (rule 4). When rules 1–3 do not "
               "already apply, a score left of it gives CAUTION, even close to 100% of baseline. A cross marks a fall, "
               "which gives NO-GO wherever the score lies (rule 2)."
               + (f" Open blue circle: typical ISS crew member at {T:g} h after landing, from the NASA recovery fits for "
                  "the corresponding Sensory Organization Test conditions (Wood et al. 2015, Table III), transferred to "
                  "the conditions used here, with foam standing in for NASA's sway-referenced support. In simulated "
                  "examples the score coincides with the circle by construction, which is not independent agreement."
                  if landed else ""))

    # Rule check per condition, in the order the engine applies the rules.
    def tick(ok):
        return "✔" if ok else "✖"
    rows = []
    for c in C.CONDITIONS:
        r, oc, q = per[c], ss[f"out_{c}"], q_by_cond[c]
        eq = float(np.median(trials_of(c)))
        rows.append({"Condition": C.CONDITION_LABELS[c], "% of baseline": f"{ratios[c]:.0%}",
                     "1 valid": tick(oc != "invalid"), "2 no fall": tick(oc != "fall"),
                     "3 ≥ 75%": tick(ratios[c] >= C.R_NOGO),
                     "4 ≥ floor": f"{tick(eq >= P.p5(c, p.age_group))} ({P.p5(c, p.age_group) / p.baseline(c):.0%})",
                     "5 ≥ GO threshold": f"{tick(ratios[c] >= q)} ({q:.0%})",
                     "Result": f"{STATUS_STYLE[r.status][2]} {r.status} (rule {rule_of(r.reason)})"})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.caption("Rules are applied in numerical order, and the first that applies sets the result for the condition. "
               "Rule 5 compares the score with the GO threshold, which accounts for test–retest variability, so a "
               "score close to the threshold may still give CAUTION.")
    rules_md = "\n".join(f"{i}. **{t}** *(applied)*" if i == rn else f"{i}. {t}" for i, t in enumerate(RULES, 1))
    with st.expander("Decision rules", expanded=True):
        st.markdown(rules_md)

# ---------------------------------------------------------------- estimated retest time
def forecast_axis() -> np.ndarray:
    """Hours from the current session forward, far enough to include the estimated crossing and its range."""
    t0 = T if T is not None else 0.0
    end = max(C.FORECAST_HORIZON_H, t0 + 24.0)
    if med.active:
        end = max(end, med.t_dose + 72.0)
    if reach:
        end = max(end, t0 + max(f.hours[2] for f in reach) + 12.0)
    return np.linspace(t0, end, int((end - t0) * 4) + 1)


t_axis = forecast_axis()  # the model is not extrapolated backwards in time before the measurement
if med_allowed and fc and (test.status != "GO" or (med.active and (unreach or worst > 0))):
    st.subheader("Estimated retest time")
    if unreach:
        lim = unreach[0]
    elif worst > 0:
        lim = max(reach, key=lambda f: f.hours[1])
    else:
        lim = min(fc, key=lambda f: f.r_m - q_by_cond[f.condition])
    if passed:
        names_p = [C.CONDITION_LABELS[c] for c in C.CONDITIONS if c in passed]
        explain_passed = (f" {names_p[0].capitalize()} is already at or above its GO threshold and requires no "
                          "recovery." if len(names_p) == 1 else
                          f" {len(names_p)} conditions ({' · '.join(names_p)}) are already at or above their GO "
                          "thresholds and require no recovery.")
    else:
        explain_passed = ""
    cond = lim.condition
    q_lim = q_by_cond[cond]
    label = C.CONDITION_LABELS[cond]
    gl = C.CONDITION_LABELS[governing]
    if test.status == "GO":
        explain = ("The session is GO. With the planned dose, " + label + (
            " is not predicted to regain its GO threshold under the typical recovery model." if unreach else
            f" is predicted to fall below its GO threshold and to regain it at approximately {T + worst:.0f} h after "
            "landing."))
    elif unreach:
        explain = (f"{label.capitalize()} is not predicted to reach its GO threshold under the typical recovery model, "
                   "so no retest time can be estimated.")
    elif worst <= 0:
        explain = "Under the typical recovery rate, every condition has already reached its GO threshold."
    elif cond == governing:
        explain = (f"{gl.capitalize()} determines the present {test.status} result and is also predicted to reach its "
                   "GO threshold last, so it determines the retest estimate.")
    else:
        explain = (f"{gl.capitalize()} determines the present {test.status} result. {label.capitalize()} is predicted "
                   "to reach its GO threshold last and therefore determines the retest estimate.")
    st.markdown(explain + explain_passed + " Recovery rates are taken from NASA crew data (Wood et al. 2015, Table III, n = 37 ISS crew).")
    fig2 = go.Figure()
    base_curve = M.curve(t_axis, lim.D_i, lim.tau)
    fig2.add_scatter(x=t_axis, y=base_curve, name="typical recovery (Wood et al. 2015)", line=dict(color="#1565c0"))
    curve_min = float(np.min(base_curve))
    if med.active and P.drug_slope(cond) is not None:
        dosed = M.curve(t_axis, lim.D_i, lim.tau, med.dose_mg, med.route, P.drug_slope(cond), p.baseline(cond),
                        med.t_dose)
        curve_min = min(curve_min, float(np.min(dosed)))
        fig2.add_scatter(x=t_axis, y=dosed, name=f"with {med.dose_mg:g} mg {med.route}",
                         line=dict(color="#6a1b9a", dash="dot"))
    fig2.add_scatter(x=[T], y=[lim.r_m], mode="markers", marker=dict(size=11, color="#212121"), name="current session")
    fig2.add_hline(y=q_lim, line_dash="dash", line_color="#1b5e20",
                   annotation_text=f"GO threshold {q_lim:.2f}" + ("" if lim.hours else " (not reached)"),
                   annotation_position="bottom right")
    if test.status == "GO":
        title = f"Effect of the planned dose<br><sup>{label}</sup>"
    if unreach:
        title = title if test.status == "GO" else f"No retest estimate<br><sup>{label} does not reach its GO threshold</sup>"
    elif worst <= 0:
        fig2.add_vline(x=T, line_color="#0d47a1", annotation_text="retest indicated", annotation_position="top")
        title = f"Retest indicated<br><sup>{label} at its GO threshold under the typical rate</sup>"
    else:
        mid = T + lim.hours[1]
        lo = T + max(f.hours[0] for f in reach)  # shading = overall range across conditions, as in the caption
        hi = T + max(f.hours[2] for f in reach)
        fig2.add_vrect(x0=lo, x1=hi, fillcolor="#90caf9", opacity=0.25, line_width=0)
        fig2.add_vline(x=mid, line_color="#0d47a1", annotation_text=(f"retest ≈ {mid:.0f} h" if test.status != "GO" else f"threshold regained ≈ {mid:.0f} h"),
                       annotation_position="top")
        if test.status != "GO":
            title = f"Retest estimate<br><sup>{label} (rate-limiting condition)</sup>"
    y_lo = max(0.0, min(lim.r_m, curve_min, q_lim) - 0.08)
    st.plotly_chart(fig2.update_layout(title=title, height=340, yaxis=dict(range=[y_lo, max(1.04, q_lim + 0.04, lim.r_m + 0.04)],
                                                                           title="ratio to baseline"),
                                       xaxis_title="hours after landing", margin=dict(t=70, b=10),
                                       legend=dict(orientation="h", y=-0.25)), use_container_width=True)
    if not unreach and worst > 0:
        lo = max(f.hours[0] for f in reach)
        hi = max(f.hours[2] for f in reach)
        st.caption(f"Range {lo:.0f}–{hi:.0f} h after this session, derived from the published 95% confidence limits "
                   "of the crew model parameters (not a 95% interval for this crew member). The single-exponential "
                   "model does not represent the slower recovery phase over subsequent weeks.")

# ---------------------------------------------------------------- recovery compared with typical NASA crew
if landed:
    from plotly.subplots import make_subplots

    st.subheader("Recovery compared with typical NASA crew")
    pts = [(h["t"], h["trials"], h["out"], f"recorded {h['t']:g} h") for h in history]
    out_of_order = (not awaiting) and bool(history) and t_now <= history[-1]["t"]
    if not awaiting and not out_of_order:  # a draft timed before the last recorded session is not a recovery point
        pts.append((t_now, {c: trials_of(c) for c in C.CONDITIONS}, {c: ss[f"out_{c}"] for c in C.CONDITIONS},
                    f"current {t_now:g} h"))
    t_hi = max(48.0, max(x[0] for x in pts) * 1.25)
    tt_n = np.linspace(0, t_hi, 400)
    fig3 = make_subplots(rows=2, cols=2, shared_xaxes=True, shared_yaxes=False, vertical_spacing=0.16,
                         horizontal_spacing=0.06, subplot_titles=[C.CONDITION_LABELS[c].capitalize()
                                                                  for c in C.CONDITIONS])
    diffs = {}
    for k, c in enumerate(C.CONDITIONS):
        rr, cc = k // 2 + 1, k % 2 + 1
        w = F.wood(c)
        fig3.add_scatter(x=tt_n, y=[F.recovery(x, w["D"], w["tau"]) for x in tt_n], row=rr, col=cc,
                         line=dict(color="#0d47a1", width=2), name="typical ISS crew (Wood et al. 2015)",
                         showlegend=k == 0, hovertemplate="typical ISS crew at %{x:.0f} h: %{y:.0%}<extra></extra>")
        fig3.add_hline(y=q_by_cond[c], line_dash="dash", line_color="#1b5e20", row=rr, col=cc)
        xs, ys, sym, lab = [], [], [], []
        for t_i, tr_i, out_i, name_i in pts:
            if out_i[c] == "invalid":  # an invalid recording is not a measurement
                continue
            r_i = float(np.median(tr_i[c])) / p.baseline(c)
            xs.append(t_i); ys.append(r_i); lab.append(name_i)
            sym.append("x" if out_i[c] == "fall" else "circle-open" if name_i.startswith("current") else "circle")
        fig3.add_scatter(x=xs, y=ys, mode="markers+lines", row=rr, col=cc, showlegend=k == 0, name="this crew member",
                         line=dict(color="#424242", width=1, dash="dot"),
                         marker=dict(size=10, color="#212121", symbol=sym), text=lab,
                         hovertemplate="%{text}: %{y:.0%} of own baseline<extra></extra>")
        if xs:
            diffs[c] = (ys[-1] - F.recovery(xs[-1], w["D"], w["tau"])) * 100, lab[-1]
    for k, c in enumerate(C.CONDITIONS):  # each panel spans its own curve, threshold and points
        w = F.wood(c)
        vals = [F.recovery(0, w["D"], w["tau"]), q_by_cond[c], 1.0]
        vals += [float(np.median(x[1][c])) / p.baseline(c) for x in pts if x[2][c] != "invalid"]
        fig3.update_yaxes(range=[max(0.0, min(vals) - 0.04), max(vals) + 0.04], tickformat=".0%",
                          row=k // 2 + 1, col=k % 2 + 1)
    fig3.update_xaxes(range=[0, t_hi])
    fig3.update_xaxes(title_text="hours after landing", row=2)
    fig3.update_layout(height=460, margin=dict(t=40, b=10, l=10, r=10), legend=dict(orientation="h", y=-0.18))
    st.plotly_chart(fig3, use_container_width=True)
    labs = {d[1] for d in diffs.values()}
    latest = next(iter(labs)) if len(labs) == 1 else "latest valid session per condition"
    parts = [f"{C.CONDITION_LABELS[c]} {int(round(diffs[c][0])):+d}" if c in diffs  # no "-0"
             else f"{C.CONDITION_LABELS[c]}: no valid recording" for c in C.CONDITIONS]
    st.markdown(f"**Difference from typical ISS crew ({latest}), percentage points of baseline:** "
                + " · ".join(parts) + ". Positive values indicate a score above the typical recovery curve at the "
                "same time after landing.")
    if out_of_order:
        st.caption(f"The current session ({t_now:g} h) precedes the last recorded session and is not plotted.")
    st.caption("Descriptive comparison only; it does not enter the decision. Blue line: NASA crew recovery model "
               "(Wood et al. 2015, Table III, n = 37), transferred to the conditions used here as in the chart above. "
               "Dashed green line: this crew member's GO threshold. Filled points: recorded sessions; open point: the "
               "current session; a cross marks a fall. Invalid recordings are not plotted. With two or more sessions, the trajectory shows whether this "
               "crew member is recovering faster or slower than the typical crew member. Simulated sessions follow the "
               "typical curve with this participant's own trial spread, so their agreement with it is by construction.")

tab_meas, tab_med, tab_nasa, tab_other = st.tabs(["From force plate to score", "Pharmacological scenario",
                                                  "NASA data and limitations", "Additional crew data (context)"])


@st.cache_data(show_spinner=False)
def baseline_trace(subject: int, cond: str):
    """Centre-of-mass sway of the participant's first baseline trial in a condition, first valid 20-s window."""
    info = H.load_info()
    tid = info[(info.Subject == subject) & (info.condition == cond)].sort_values("Trial").Trial.iloc[0]
    tr = H.load_trial(tid)
    com = S.com_glp(tr.channel("COPx"), tr.channel("Fx"), tr.mass_kg, tr.fs)
    i0 = int(np.flatnonzero(np.isfinite(com))[0])
    n = int(round(C.SEG_S * tr.fs))
    win = com[i0:i0 + n]
    return tid, tr.height_cm, np.arange(n) / tr.fs, win - np.nanmean(win), S.eq_window(win, tr.height_cm, tr.fs)


with tab_meas:
    st.markdown("**How a balance recording becomes a score.** The force plate records the centre of pressure and the "
                "horizontal force at 100 Hz. The centre of mass is estimated from these signals by double integration "
                "of the horizontal force between its zero crossings. This estimator is an adaptation: Wood et al. "
                "(2015) estimated the centre of mass by low-pass filtering the centre of pressure (second-order "
                "Butterworth, 0.85 Hz). The equilibrium "
                "score follows the NASA formula: the peak-to-peak anterior–posterior sway over 20 s is converted into a "
                "sway angle θ relative to the centre-of-mass height (0.55 × body height), and EQ = 100 × (1 − θ / 12.5°), "
                "where 12.5° is the limit of stability. A score of 100 indicates no sway.")
    mc = st.radio("Condition", C.CONDITIONS, format_func=lambda c: C.CONDITION_LABELS[c], index=3, key="meas_cond",
                  horizontal=True)
    tid, hgt, tt, xx, eq_tr = baseline_trace(subject, mc)
    ptp = float(np.nanmax(xx) - np.nanmin(xx))
    theta = float(np.degrees(np.arctan(ptp / (C.COM_HEIGHT_FRAC * hgt))))
    fig6 = go.Figure()
    fig6.add_scatter(x=tt, y=xx, line=dict(color="#1565c0", width=1.5), name="centre of mass")
    fig6.add_hline(y=float(np.nanmax(xx)), line_dash="dot", line_color="#757575")
    fig6.add_hline(y=float(np.nanmin(xx)), line_dash="dot", line_color="#757575",
                   annotation_text=f"peak-to-peak {ptp:.2f} cm", annotation_position="bottom right")
    fig6.update_layout(title=f"Recorded baseline trial {tid}<br><sup>{C.CONDITION_LABELS[mc]}, anterior–posterior "
                             "centre-of-mass sway</sup>", height=320, xaxis_title="time (s)",
                       yaxis_title="sway (cm)", margin=dict(t=70, b=10), showlegend=False)
    st.plotly_chart(fig6, use_container_width=True)
    st.markdown(f"θ = atan({ptp:.2f} cm / (0.55 × {hgt:.0f} cm)) = {theta:.2f}°, so EQ = 100 × (1 − {theta:.2f} / 12.5) "
                f"= **{eq_tr:.1f}**.")
    st.caption(f"HBEDB participant {subject} (Santos and Duarte 2016), first valid 20-s window of the first trial in "
               "this condition. The median of the three trials is the preflight baseline used in the decision. The "
               "same computation applies to any force plate that records the centre of pressure and the horizontal "
               "force.")
# ---------------------------------------------------------------- tab: medicine what-if
with tab_med:
    st.markdown("**Promethazine (antiemetic) planned at or after the current session.** A planned dose adjusts only "
                f"the retest estimate and never the test result ({M.LABEL}).")
    if not med_allowed:
        st.caption("Not applicable to the present inputs. The scenario applies only after landing, when every "
                   "condition has a valid recording and no fall has occurred.")
    else:
        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            st.select_slider("Planned dose (mg)", options=list(C.DOSES_MG), key="dose")
        with mc2:
            st.radio("Route", ["oral", "im"], format_func=lambda r: "oral" if r == "oral" else "intramuscular",
                     horizontal=True, key="route", disabled=ss.get("dose", 0.0) == 0)
        with mc3:
            st.slider("Dose time (h after the current session)", 0.0, 48.0, step=0.5, key="dose_after",
                      disabled=ss.get("dose", 0.0) == 0)
        if ss.get("dose", 0.0) in (12.5, 50.0):
            st.caption("The 12.5 and 50 mg effects are extrapolated from the 25 mg study.")
    if med.active and fc:
        def _cross(f, with_dose: bool):
            c = f.condition
            if with_dose:
                return M.t_go(f.D_i, f.tau, q_by_cond[c], med.dose_mg, med.route, P.drug_slope(c),
                              p.baseline(c), med.t_dose, 0.0)
            return M.t_go(f.D_i, f.tau, q_by_cond[c])

        med_conds = [f for f in fc if f.hours is not None and f.condition in fc_none and
                     fc_none[f.condition].hours is not None and P.drug_slope(f.condition) is not None]
        if not med_conds:
            st.caption("The dose does not shift any condition with an attainable GO threshold for these inputs.")
        for f in med_conds:
            h0, h1 = _cross(fc_none[f.condition], False), _cross(f, True)
            st.caption(f"{C.CONDITION_LABELS[f.condition].capitalize()} reaches its GO threshold at approximately "
                       f"{h0:.1f} h after landing without the dose and {h1:.1f} h with it, on the typical-recovery "
                       "curves.")
        if not unreach and all(c in fc_none and fc_none[c].hours is not None for c in (f.condition for f in fc)):
            all0 = [_cross(fc_none[f.condition], False) for f in fc]
            all1 = [_cross(f, True) for f in fc]
            if None not in all0 and None not in all1:
                o0, o1 = max(all0), max(all1)
                st.caption(f"All four conditions reach their GO thresholds at approximately {o0:.1f} h after landing "
                           f"without the dose and {o1:.1f} h with it" + (" (no change)." if abs(o1 - o0) < 0.05 else "."))
        st.info(M.WARN_FLIGHT)


# ---------------------------------------------------------------- tab: other crew data (NASA OSDR)
@st.cache_data(show_spinner=False)
def crew_labs():
    return L.relative_to_preflight(L.load())


with tab_other:
    labs = crew_labs()
    st.markdown("**Clinical blood panels of the Inspiration4 crew (NASA OSDR).** A comprehensive crew health monitor "
                "would include indicators beyond balance. The NASA Open Science Data Repository (OSDR) holds blood "
                "panels for the four Inspiration4 crew members (3-day flight, 2021) before and after flight. The same "
                "within-subject principle is applied: each value is expressed relative to the individual's own "
                "preflight mean. **These data do not enter the balance decision.**")
    analyte = st.radio("Analyte", L.ANALYTES, index=0, horizontal=True,
                           format_func=lambda a: a.capitalize().replace("(bun)", "(BUN)"))
    lab = labs[labs.analyte == analyte]
    fig4 = go.Figure()
    for subj, g in lab.groupby("subject"):
        g = g.sort_values("day")
        fig4.add_scatter(x=g["day"], y=g["share"], mode="lines+markers", name=f"crew member {subj}")
    fig4.add_vline(x=0, line_dash="dot", line_color="#616161", annotation_text="flight", annotation_position="top")
    fig4.add_hline(y=1.0, line_color="#9e9e9e", line_width=1)
    fig4.update_layout(title=f"{analyte.capitalize().replace('(bun)', '(BUN)')}<br><sup>ratio to each crew member's "
                             "preflight mean</sup>", height=340,
                       xaxis_title="days before launch (negative) and after return (positive), with the 3-day flight at 0",
                       yaxis_title="ratio to preflight mean", margin=dict(t=70, b=10),
                       legend=dict(orientation="h", y=-0.3))
    st.plotly_chart(fig4, use_container_width=True)
    r1 = lab[lab.timepoint == "R+1"].sort_values("subject")
    st.dataframe(pd.DataFrame({"Crew member": r1["subject"], "Day after return (R+1)": r1["value"].round(2),
                               "Preflight mean": r1["preflight_mean"].round(2),
                               "Ratio to preflight": (r1["share"] * 100).round(0).astype(int).astype(str) + "%",
                               "Laboratory reference range": r1["range_min"].astype(str) + "–" + r1["range_max"].astype(str)
                               + " " + r1["units"],
                               "Outside range": r1["outside_range"].map({True: "yes", False: "no"})}),
                 hide_index=True, use_container_width=True)
    st.caption("Source: NASA OSDR [OSD-569](https://osdr.nasa.gov/bio/repo/data/studies/OSD-569) (complete blood "
               "count) and [OSD-575](https://osdr.nasa.gov/bio/repo/data/studies/OSD-575) (comprehensive metabolic "
               "panel). Reference ranges are those of the testing laboratory, as released. The data describe four "
               "civilian crew members after a 3-day flight and illustrate the within-subject approach. They are not "
               "norms for egress.")

# ---------------------------------------------------------------- tab: NASA data and limits
with tab_nasa:
    st.markdown(
        "The retest estimate is based on post-flight recovery of 37 International Space Station (ISS) crew members "
        "measured by computerised dynamic posturography (Wood et al. 2015, Table III). In condition 5 of the Sensory "
        "Organization Test (SOT), with eyes closed on a sway-referenced support, the mean equilibrium score was 74.9 "
        "before flight, and the fitted recovery model estimates 13.2 at landing (95% limits ±21.1).\n\n"
        "The NO-GO criterion of a 25% decrement follows Jain et al. (2010), who regarded a decrement of less than "
        "25% from a crew member's own preflight score as recovery.\n\n"
        "Clinical blood panels of the Inspiration4 crew (NASA OSDR, OSD-569 and OSD-575) are presented as context "
        "under 'Additional crew data', each value relative to the individual's preflight mean.\n\n"
        "NASA lists sensorimotor impairment after gravity transitions among the risks of human spaceflight. On the "
        "Moon or Mars, no ground team will be present to assist a crew member during egress.")
    st.dataframe(pd.read_csv(C.PARAMS_DIR / "wood2015_table3.csv").drop(columns="source"), hide_index=True)
    for k, v in LINKS.items():
        st.markdown(f"- [{k}]({v})")
    st.markdown("**Validation and safeguards**\n\n"
        "*Calibration.* Scored with the NASA equilibrium score, healthy adults aged 25–55 years reach 94.1 on a firm "
        "floor with eyes open, compared with a NASA crew preflight mean of 94.3, and 92.9 with eyes closed, compared "
        "with 89.9. Cohorts and protocols differ, and on foam with eyes closed the scores are 10.9 points higher "
        "(85.8 vs 74.9). Details are given in out/VALIDATION.md.\n\n"
        "*Safeguards.* Any fall yields NO-GO. Invalid recordings yield CANNOT ASSESS, never GO, and a test with a "
        "missing condition is limited to CAUTION. GO requires two consecutive GO tests in separate sessions, and the "
        "recovery estimate never confers GO.\n\n"
        "*Verification.* The automated test suite checks every rule against an independent statement of the "
        "arithmetic, the exact thresholds and malformed inputs, and checks the recovery solver against a brute-force "
        "search.\n\n"
        "*Acknowledged limitation.* Healthy individuals are frequently held at CAUTION after a single test "
        "(single-test GO rate 42.9% in cross-validation). The rules favour a retest over a false clearance.\n\n"
        "*Examples.* Example inputs come from three HBEDB participants. Post-landing examples scale the participant's "
        "recorded trials onto the typical NASA crew recovery curve, score = baseline × r(t) × (trial / median trial), "
        "with r(t) = 1 − D·e^(−t/τ). The fall example marks one recorded trial as a fall for demonstration. These are "
        "demonstrations, not measurements of astronauts.")
    st.markdown("**Protocol and transfer assumptions**\n\n"
        "*Test administration.* The test deliberately challenges balance in crew members who may fall, so it should be "
        "administered with a spotter or a safety harness, and a fall is recorded as a trial outcome.\n\n"
        "*Centre-of-mass estimator.* The centre of mass is estimated by double integration of the horizontal force "
        "between zero crossings, whereas Wood et al. (2015) low-pass filtered the centre of pressure. The "
        "equilibrium-score formula is the same, but the complete NASA measurement pipeline is not reproduced.\n\n"
        "*Test conditions.* Foam surfaces stand in for the sway-referenced support of the NASA Sensory Organization "
        "Test. They are similar in sensory content but not in protocol.\n\n"
        "*Gravity.* The NASA recovery data describe return to Earth gravity after ISS missions. Recovery after landing "
        "on the Moon (0.17 g) or Mars (0.38 g) has not been characterised, so the retest estimate is a transfer "
        "assumption for those missions.\n\n"
        "*Sessions.* Each recorded session keeps its own trial scores and time. The two-session rule is applied to "
        "these recorded sessions, never to a reconstruction.")
    with st.expander("Assumptions and limitations"):
        st.markdown((C.REPO_ROOT / "ASSUMPTIONS.md").read_text().split("\n", 2)[2])

st.caption("Prototype for NASA Space Apps 2026. Not a medical device. No NASA endorsement is implied.")
