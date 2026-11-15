# AI-assisted code (team statement and per-step log: docs/AI_USE_LOG.md).
"""Reader for the Human Balance Evaluation Database (HBEDB; Santos and Duarte 2016, PhysioNet).

WFDB format 32: little-endian int32, 8 channels interleaved, physical = (digital - baseline) / gain,
with gain and baseline per channel from the .hea header (``gain(baseline)/unit``).
Forces are those the subject applies on the plate; x is anterior-posterior, positive anterior.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C

_SIG_RE = re.compile(r"^(?P<file>\S+)\s+(?P<fmt>\d+)\s+(?P<gain>[-+0-9.eE]+)(?:\((?P<base>[-+0-9]+)\))?/(?P<unit>\S+)"
                     r"\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(?P<name>\S+)\s*$")


@dataclass
class Header:
    record: str
    n_signals: int
    fs: float
    n_samples: int
    names: list[str]
    units: list[str]
    gains: np.ndarray
    baselines: np.ndarray
    comments: dict[str, str] = field(default_factory=dict)


def parse_header(path: Path) -> Header:
    lines = [ln.rstrip("\n") for ln in Path(path).read_text().splitlines() if ln.strip()]
    rec, nsig, fs, nsamp = lines[0].split()[:4]
    names, units, gains, bases, comments = [], [], [], [], {}
    for ln in lines[1:]:
        if ln.startswith("#"):
            key, _, val = ln[1:].partition(":")
            comments[key.strip()] = val.strip()
            continue
        m = _SIG_RE.match(ln)
        if not m:
            raise ValueError(f"cannot parse signal line in {path}: {ln!r}")
        if m["fmt"] != "32":
            raise ValueError(f"unsupported WFDB format {m['fmt']} in {path}")
        names.append(m["name"])
        units.append(m["unit"])
        gains.append(float(m["gain"]))
        bases.append(int(m["base"]) if m["base"] is not None else 0)
    if len(names) != int(nsig):
        raise ValueError(f"{path}: header lists {len(names)} signals, expected {nsig}")
    return Header(rec, int(nsig), float(fs), int(nsamp), names, units,
                  np.array(gains, dtype=np.float64), np.array(bases, dtype=np.int64), comments)


def read_signals(dat_path: Path, hdr: Header) -> np.ndarray:
    raw = np.fromfile(dat_path, dtype="<i4")
    expected = hdr.n_samples * hdr.n_signals
    if raw.size != expected:
        raise ValueError(f"{dat_path}: {raw.size} values, expected {expected}")
    digital = raw.reshape(hdr.n_samples, hdr.n_signals).astype(np.int64)
    return (digital - hdr.baselines) / hdr.gains  # int64 avoids overflow: baselines exceed int32


def _condition(vision: str, surface: str) -> str:
    surf = {"Firm": "firm", "Foam": "foam"}[surface]
    vis = {"Open": "eo", "Closed": "ec"}[vision]
    return f"{surf}_{vis}"


@lru_cache(maxsize=4)
def load_info(root: str | None = None) -> pd.DataFrame:
    """BDSinfo.txt with derived columns: condition, healthy, vestibular."""
    root_p = Path(root) if root else C.data_dir()
    info = pd.read_csv(root_p / "BDSinfo.txt", sep="\t")
    info["condition"] = [_condition(v, s) for v, s in zip(info["Vision"], info["Surface"])]
    lab = info["Illness2"].astype(str).str.contains("labyrinthitis", case=False, na=False)
    info["vestibular"] = lab
    info["healthy"] = (info["Disability"].astype(str).str.strip() == "No") & ~lab
    info = info.sort_values("Trial").reset_index(drop=True)
    return info


@dataclass
class Trial:
    trial_id: str
    subject: int
    condition: str
    age: float
    age_group: str
    height_cm: float
    mass_kg: float
    healthy: bool
    vestibular: bool
    data: np.ndarray  # (N_SAMPLES, 8) physical units
    fs: float

    def channel(self, name: str) -> np.ndarray:
        return self.data[:, C.CHANNELS.index(name)]


def load_trial(trial_id: str, root: str | Path | None = None) -> Trial:
    root_p = Path(root) if root else C.data_dir()
    info = load_info(str(root_p))
    row = info.loc[info["Trial"] == trial_id]
    if row.empty:
        raise KeyError(f"{trial_id} not in BDSinfo.txt under {root_p}")
    r = row.iloc[0]
    hdr = parse_header(root_p / f"{trial_id}.hea")
    if tuple(hdr.names) != C.CHANNELS:
        raise ValueError(f"{trial_id}: unexpected channel order {hdr.names}")
    data = read_signals(root_p / f"{trial_id}.dat", hdr)
    return Trial(trial_id, int(r["Subject"]), r["condition"], float(r["Age"]), str(r["AgeGroup"]),
                 float(r["Height"]), float(r["Weight"]), bool(r["healthy"]), bool(r["vestibular"]),
                 data, hdr.fs)


def missing_trials(root: str | Path | None = None) -> pd.DataFrame:
    """Per subject and condition, how many of the 3 protocol trials are absent (reported, not dropped)."""
    info = load_info(str(Path(root) if root else C.data_dir()))
    counts = info.groupby(["Subject", "condition"]).size()
    rows = []
    for subj in sorted(info["Subject"].unique()):
        for cond in C.CONDITIONS:
            n = int(counts.get((subj, cond), 0))
            if n < C.MIN_TRIALS:
                rows.append({"Subject": int(subj), "condition": cond, "present": n,
                             "missing": C.MIN_TRIALS - n})
    return pd.DataFrame(rows, columns=["Subject", "condition", "present", "missing"])


def trial_ids(root: str | Path | None = None) -> list[str]:
    return load_info(str(Path(root) if root else C.data_dir()))["Trial"].tolist()
