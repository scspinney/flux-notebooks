from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Any, Optional
import json

import pandas as pd
from bids import BIDSLayout


def _safe_read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text()) if path.exists() else {}
    except Exception:
        return {}


def _participants_df(root: Path) -> pd.DataFrame:
    p = root / "participants.tsv"
    if not p.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(p, sep="\t", dtype=str)
        # normalize typical columns
        for col in ("age", "Age", "participant_age"):
            if col in df.columns:
                with pd.option_context("mode.use_inf_as_na", True):
                    df["age_num"] = pd.to_numeric(df[col], errors="coerce")
                break
        for col in ("sex", "gender", "Sex"):
            if col in df.columns:
                df["sex_norm"] = df[col].str.strip().str.lower()
                break
        return df
    except Exception:
        return pd.DataFrame()


def summarize_with_pybids(root: Path, validate: bool = False) -> Dict:
    """
    Summarize a BIDS dataset using PyBIDS.

    Returns a dict with:
      - n_files, subjects, sessions, tasks, datatypes
      - avail: DataFrame sub × datatype (file counts)
      - func_counts: DataFrame subject × task (functional run counts)
      - dataset_description: dict (Name, BIDSVersion, DatasetType, etc.)
      - participants: DataFrame (if participants.tsv exists)
      - size_by_datatype: DataFrame with total bytes per datatype
      - counts_by_suffix: DataFrame with file counts per suffix
      - tr_by_task: DataFrame with TR summary per task (min/median/max, distinct values)
    """
    root = Path(root)
    layout = BIDSLayout(root, validate=validate)

    subjects: List[str] = layout.get_subjects()
    sessions: List[str] = layout.get_sessions()
    tasks: List[str] = layout.get_tasks()
    datatypes: List[str] = sorted(layout.get(return_type="id", target="datatype"))

    # --- Subject × datatype availability (file counts) ---
    rows = []
    for s in subjects:
        for dt in datatypes:
            n_files = len(layout.get(subject=s, datatype=dt, return_type="file"))
            rows.append({"sub": s, "datatype": dt, "count": n_files})
    avail = (
        pd.DataFrame(rows)
        .pivot(index="sub", columns="datatype", values="count")
        .fillna(0)
        if rows
        else pd.DataFrame()
    )

    # --- Functional runs per (subject × task) ---
    func_counts = pd.DataFrame()
    if "func" in datatypes and tasks:
        rows_ft = []
        for s in subjects:
            for t in tasks:
                n_runs = len(layout.get(subject=s, task=t, datatype="func", return_type="file"))
                if n_runs > 0:
                    rows_ft.append({"subject": s, "task": t, "count": n_runs})
        if rows_ft:
            func_counts = (
                pd.DataFrame(rows_ft)
                .pivot(index="subject", columns="task", values="count")
                .fillna(0)
            )

    # --- File size totals by datatype ---
    size_rows = []
    for dt in datatypes:
        files = layout.get(datatype=dt, return_type="file")
        total = 0
        for f in files:
            try:
                total += Path(f).stat().st_size
            except Exception:
                pass
        size_rows.append({"datatype": dt, "bytes": total})
    size_by_datatype = pd.DataFrame(size_rows)
    if not size_by_datatype.empty:
        size_by_datatype["GB"] = size_by_datatype["bytes"] / (1024 ** 3)

    # --- Counts by suffix (anat: T1w/T2w; dwi: dwi; func: bold, etc.) ---
    suffixes = sorted(layout.get(return_type="id", target="suffix"))
    suf_rows = []
    for suf in suffixes:
        n = len(layout.get(suffix=suf, return_type="file"))
        if n > 0:
            suf_rows.append({"suffix": suf, "count": n})
    counts_by_suffix = pd.DataFrame(suf_rows).sort_values("count", ascending=False)

    # --- Functional metadata summaries (TR by task) ---
    tr_rows = []
    if "func" in datatypes:
        func_files = layout.get(datatype="func", suffix="bold", return_type="file")
        for f in func_files:
            md = layout.get_metadata(f)
            tr = md.get("RepetitionTime", None)
            # infer task from path/entities
            ents = layout.parse_file_entities(f)
            task = ents.get("task", None)
            if tr is not None and task is not None:
                tr_rows.append({"task": task, "TR": float(tr)})
    tr_by_task = pd.DataFrame(tr_rows)
    if not tr_by_task.empty:
        tr_by_task = tr_by_task.groupby("task")["TR"].agg(["count", "min", "median", "max"]).reset_index()
        # also add distinct TRs per task for quick diagnostics
        distinct = (
            pd.DataFrame(tr_rows)
            .groupby("task")["TR"]
            .apply(lambda s: sorted(set(round(x, 6) for x in s)))
            .reset_index(name="distinct_TRs")
        )
        tr_by_task = tr_by_task.merge(distinct, on="task", how="left")

    # --- Dataset description + participants ---
    dataset_description = _safe_read_json(root / "dataset_description.json")
    participants = _participants_df(root)

    return {
        "n_files": len(layout.get(return_type="file")),
        "subjects": subjects,
        "sessions": sessions,
        "tasks": tasks,
        "datatypes": datatypes,
        "avail": avail,
        "func_counts": func_counts,
        "size_by_datatype": size_by_datatype,
        "counts_by_suffix": counts_by_suffix,
        "tr_by_task": tr_by_task,
        "dataset_description": dataset_description,
        "participants": participants,
    }
