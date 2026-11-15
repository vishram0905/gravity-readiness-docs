# AI-assisted code (team statement and per-step log: docs/AI_USE_LOG.md).
"""All constants of the readiness model, each with its source.

Mathematical framework: MATH_FRAMEWORK v3.3.1 (frozen 14 Nov 2026). Section numbers below
refer to that document; the public summary is in ASSUMPTIONS.md and README.md.
"""
from __future__ import annotations

import os
from pathlib import Path

SEED = 20261114  # fixed seed for every random draw (determinism)

# ---------------------------------------------------------------- data
REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = REPO_ROOT / "data" / "demo"
PARAMS_DIR = REPO_ROOT / "params"
OUT_DIR = REPO_ROOT / "out"


def data_dir() -> Path:
    """Full HBEDB when HBEDB_DIR is set, otherwise the demo subset (B0 data modes)."""
    env = os.environ.get("HBEDB_DIR")
    return Path(env).expanduser() if env else DEMO_DIR


def full_data() -> bool:
    return bool(os.environ.get("HBEDB_DIR"))


FS_HZ = 100            # HBEDB sampling rate (Santos and Duarte 2016)
N_SAMPLES = 6000       # 60-s trials
N_CHANNELS = 8         # Fx Fy Fz Mx My Mz COPx COPy
CHANNELS = ("Fx", "Fy", "Fz", "Mx", "My", "Mz", "COPx", "COPy")
G = 9.81               # m/s^2
CONDITIONS = ("firm_eo", "firm_ec", "foam_eo", "foam_ec")
CONDITION_LABELS = {
    "firm_eo": "firm floor, eyes open",
    "firm_ec": "firm floor, eyes closed",
    "foam_eo": "foam, eyes open",
    "foam_ec": "foam, eyes closed",
}
AGE_GROUPS = ("Young", "Old")  # BDSinfo AgeGroup

# ---------------------------------------------------------------- COM and EQ (§2)
SEG_S = 20.0                 # NASA scores 20-s trials (Wood 2015 Methods)
SEG_N = int(SEG_S * FS_HZ)   # 2000 samples
MIN_COVERAGE = 0.99          # >= 99% valid samples in the window
MIN_SWAY_SD_CM = 0.01        # 2 x 0.005 cm instrument noise floor (Santos and Duarte 2016)
COM_HEIGHT_FRAC = 0.55       # COM height = 0.55 x body height (NASA cEQ; Wood 2015, Clement 2024)
LOS_DEG = 12.5               # limit of stability for EQ (NASA cEQ)
GYR_FRAC = 0.288             # radius of gyration k = 0.288 H (LPF sensitivity only)
HEIGHT_CM = (100.0, 250.0)   # anthropometric validity
MASS_KG = (30.0, 200.0)

# ---------------------------------------------------------------- decision (§4)
DELTA = 0.25                 # acceptable loss; Jain et al. 2010 p. 630 (< 25% decrement = recovered)
R_NOGO = 1.0 - DELTA         # 0.75
MIN_TRIALS = 3
MIN_TEST_GAP_H = 2.0         # two-test rule: sessions >= 2 h apart (team decision)
STATUS_RANK = {"GO": 0, "CAUTION": 1, "NO-GO": 2, "CANNOT ASSESS": 3}

# ---------------------------------------------------------------- literature noise (§3)
# Pang et al. 2011 MDCs (EQ points, 5-trial average): firm = SOT 1/2 analogue, foam = SOT 4/5 analogue
PANG_MDC = {
    ("firm", "Young"): 2.7, ("firm", "Old"): 3.6,
    ("foam", "Young"): 16.2, ("foam", "Old"): 22.7,
}
Q95_LIT_DRAWS = 100_000
Q95_LIT_GRID = (30, 100)     # b grid, step 1
Q95_DATA_DRAWS = 200_000

# ---------------------------------------------------------------- Wood 2015 Table III (§5)
WOOD_SOURCE = ("Wood, Paloski and Clark 2015, Aerosp Med Hum Perform 86(12 Suppl):A45-A53, "
               "Table III p. A49")
# condition: (NASA SOT, preflight EQ, R+0 EQ, R+0 95% CL, tau h, tau 95% CL)
WOOD = {
    "firm_eo": ("SOT 1", 94.3, 90.0, 2.2, 116.1, 86.6),
    "firm_ec": ("SOT 2", 89.9, 82.6, 3.9, 99.4, 74.6),
    "foam_eo": ("SOT 4", 87.9, 68.2, 8.3, 44.6, 25.6),
    "foam_ec": ("SOT 5", 74.9, 13.2, 21.1, 19.4, 10.7),
}
FORECAST_HORIZON_H = 240.0
GRID_STEP_H = 0.5

# ---------------------------------------------------------------- promethazine (§6)
# Gandia et al. 2006 Table II, 50 mg, ambulatory: (t_half h, tmax h, Cmax ug/L)
GANDIA_DOSE_MG = 50.0
GANDIA = {"oral": (15.6, 2.9, 22.5), "im": (17.8, 2.0, 52.4)}
C_REF = 11.25                # ug/L: extrapolated oral 25 mg peak (C_rel = 1)
AGE_EQUIV = 31.0 / 32.0      # Diaz-Artiles 2017 (+31%) / Bermudez Rey 2016 (+32% per decade)
AGE_SLOPE_KNEE = 42.7        # years; Bermudez Rey 2016
DOSES_MG = (0.0, 12.5, 25.0, 50.0)
ROUTES = ("oral", "im")
