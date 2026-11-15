# AI-assisted code (team statement and per-step log: docs/AI_USE_LOG.md).
"""Context panel: NASA OSDR Inspiration4 crew blood tests, each value as a share of the crew member's own preflight mean.

Context only. These values never enter the balance decision. Source: NASA Open Science Data Repository, OSD-569
(complete blood count) and OSD-575 (comprehensive metabolic panel), SpaceX Inspiration4 (3-day flight, 4 crew).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "osdr" / "inspiration4_labs.csv"
ANALYTES = ("HEMOGLOBIN", "HEMATOCRIT", "SODIUM", "POTASSIUM", "UREA NITROGEN (BUN)", "CREATININE", "GLUCOSE")
TIMEPOINTS = ("L-92", "L-44", "L-3", "R+1", "R+45", "R+82", "R+194")
PREFLIGHT = ("L-92", "L-44", "L-3")
DAYS = {"L-92": -92, "L-44": -44, "L-3": -3, "R+1": 1, "R+45": 45, "R+82": 82, "R+194": 194}
STUDY_URL = {"OSD-569": "https://osdr.nasa.gov/bio/repo/data/studies/OSD-569",
             "OSD-575": "https://osdr.nasa.gov/bio/repo/data/studies/OSD-575"}


def load(path: Path = DATA_FILE) -> pd.DataFrame:
    df = pd.read_csv(path)
    for c in ("value", "range_min", "range_max"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["day"] = df["timepoint"].map(DAYS)
    return df


def relative_to_preflight(df: pd.DataFrame) -> pd.DataFrame:
    """Adds 'share' = value / mean of the same crew member's preflight values (L-92, L-44, L-3) for that analyte."""
    pre = (df[df.timepoint.isin(PREFLIGHT)].groupby(["analyte", "subject"])["value"].mean()
           .rename("preflight_mean").reset_index())
    out = df.merge(pre, on=["analyte", "subject"], how="left")
    out["share"] = out["value"] / out["preflight_mean"]
    out["outside_range"] = (out["value"] < out["range_min"]) | (out["value"] > out["range_max"])
    return out


def day_after_landing(df: pd.DataFrame) -> pd.DataFrame:
    """One row per analyte and crew member at R+1: value, own preflight mean, change, lab range flag."""
    r = relative_to_preflight(df)
    return r[r.timepoint == "R+1"][["analyte", "subject", "units", "value", "preflight_mean", "share",
                                    "range_min", "range_max", "outside_range"]].reset_index(drop=True)
