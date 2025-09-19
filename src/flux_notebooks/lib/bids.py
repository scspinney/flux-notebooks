from __future__ import annotations
from pathlib import Path
import os, json
import pandas as pd
import matplotlib.pyplot as plt

def load_metadata(dataset_root: Path):
    """Return (dataset_description_dict | {}, participants_df | None)."""
    ds = {}
    p = dataset_root / "dataset_description.json"
    if p.exists():
        try:
            ds = json.loads(p.read_text())
        except Exception:
            ds = {}
    participants = None
    pt = dataset_root / "participants.tsv"
    if pt.exists():
        participants = pd.read_csv(pt, sep="\t", dtype=str)
    return ds, participants

def summarize_participants(participants: pd.DataFrame):
    """Small summaries used in the notebook; each may be None."""
    if not isinstance(participants, pd.DataFrame):
        return None, None
    age_tbl = None
    sex_tbl = None
    if any(c.lower().startswith("age") for c in participants.columns):
        age_col = [c for c in participants.columns if c.lower().startswith("age")][0]
        with pd.option_context("mode.use_inf_as_na", True):
            ages = pd.to_numeric(participants[age_col], errors="coerce")
        age_tbl = pd.DataFrame({"n":[ages.notna().sum()], "min":[ages.min()], "median":[ages.median()], "max":[ages.max()]})
    if any(c.lower() in ("sex","gender") for c in participants.columns):
        sex_col = [c for c in participants.columns if c.lower() in ("sex","gender")][0]
        sex_tbl = participants[sex_col].str.lower().value_counts().rename_axis("sex").to_frame("count")
    return age_tbl, sex_tbl

def compute_size_by_datatype(dataset_root: Path, avail: pd.DataFrame | None) -> pd.DataFrame:
    """Best-effort GB by top-level datatype folders present in `avail`."""
    if not isinstance(avail, pd.DataFrame):
        return pd.DataFrame()
    sizes = {}
    for dt in avail.columns:
        dt_dir = dataset_root / dt
        if not dt_dir.exists():
            continue
        tot = 0
        for p, _, files in os.walk(dt_dir):
            for f in files:
                try:
                    tot += (Path(p)/f).stat().st_size
                except Exception:
                    pass
        sizes[dt] = tot / (1024**3)
    return pd.DataFrame({"datatype": list(sizes.keys()), "GB": list(sizes.values())}).sort_values("GB", ascending=False)

def plot_availability_tables(avail: pd.DataFrame):
    """Bar charts used in the notebook; returns None (draws to matplotlib)."""
    if not isinstance(avail, pd.DataFrame) or avail.empty: 
        return
    A = avail.copy()
    if "sub" in A.columns:
        A = A.set_index("sub")

    totals = A.sum(axis=0).sort_values(ascending=False)
    plt.figure(figsize=(max(8, 0.6*len(totals)), 4))
    totals.plot(kind="bar")
    plt.ylabel("files"); plt.title("Total files per datatype")
    plt.tight_layout(); plt.show()

    per_sub = A.sum(axis=1).sort_values(ascending=False)
    plt.figure(figsize=(max(8, 0.35*len(per_sub)), 4))
    per_sub.plot(kind="bar")
    plt.ylabel("files"); plt.title("Total files per subject")
    plt.tight_layout(); plt.show()
