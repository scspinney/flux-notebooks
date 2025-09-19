from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json
import numpy as np
import pandas as pd

# Make PyBIDS import failure explicit & helpful at runtime
try:
    from bids import BIDSLayout  # type: ignore
except Exception as _IMPORT_ERR:  # pragma: no cover
    BIDSLayout = None  # type: ignore[assignment]


def _safe_read_json(path: Path) -> Dict[str, Any]:
    """Read JSON if present; return {} on any error."""
    try:
        return json.loads(path.read_text()) if path.exists() else {}
    except Exception:
        return {}


def _participants_df(root: Path) -> pd.DataFrame:
    """Return participants.tsv as a DataFrame with a couple of normalized helpers."""
    p = root / "participants.tsv"
    if not p.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(p, sep="\t", dtype=str)

        # Normalize typical age column to numeric "age_num" (best-effort)
        for col in ("age", "Age", "participant_age"):
            if col in df.columns:
                ages = pd.to_numeric(df[col], errors="coerce")
                df["age_num"] = ages.where(np.isfinite(ages), pd.NA)
                break

        # Normalize sex/gender to lowercase "sex_norm" (best-effort)
        for col in ("sex", "gender", "Sex"):
            if col in df.columns:
                df["sex_norm"] = df[col].str.strip().str.lower()
                break

        return df
    except Exception:
        return pd.DataFrame()


def summarize_bids(root: Path, validate: bool = False) -> Dict[str, Any]:
    """
    Summarize a BIDS dataset using PyBIDS.

    Returns a dict with:
      - n_files: int
      - subjects/sessions/tasks/datatypes: lists of strings
      - avail: DataFrame (rows=sub, cols=datatype; counts of files)
      - func_counts: DataFrame (rows=subject, cols=task; counts of functional runs)
      - size_by_datatype: DataFrame with total bytes (and GB) per datatype
      - counts_by_suffix: DataFrame with file counts per suffix
      - tr_by_task: DataFrame (per task: count/min/median/max + distinct_TRs)
      - dataset_description: dict
      - participants: DataFrame (may be empty)
    """
    root = Path(root)

    if BIDSLayout is None:  # pragma: no cover
        raise RuntimeError(
            "PyBIDS is required for summarize_bids but is not installed. "
            "Install it with `pip install pybids`."
        ) from _IMPORT_ERR

    layout = BIDSLayout(root, validate=validate)

    subjects: List[str] = layout.get_subjects()
    sessions: List[str] = layout.get_sessions()
    tasks: List[str] = layout.get_tasks()
    datatypes: List[str] = sorted(layout.get(return_type="id", target="datatype"))

    # --- Subject × datatype availability (file counts)
    rows_avail: List[Dict[str, Any]] = []
    for s in subjects:
        for dt in datatypes:
            n_files = len(layout.get(subject=s, datatype=dt, return_type="file"))
            rows_avail.append({"sub": s, "datatype": dt, "count": n_files})
    avail = (
        pd.DataFrame(rows_avail)
        .pivot(index="sub", columns="datatype", values="count")
        .fillna(0)
        if rows_avail
        else pd.DataFrame()
    )

    # --- Functional runs per (subject × task)
    func_counts = pd.DataFrame()
    if "func" in datatypes and tasks:
        rows_ft: List[Dict[str, Any]] = []
        for s in subjects:
            for t in tasks:
                n_runs = len(
                    layout.get(subject=s, task=t, datatype="func", return_type="file")
                )
                if n_runs > 0:
                    rows_ft.append({"subject": s, "task": t, "count": n_runs})
        if rows_ft:
            func_counts = (
                pd.DataFrame(rows_ft)
                .pivot(index="subject", columns="task", values="count")
                .fillna(0)
            )

    # --- File size totals by datatype
    size_rows: List[Dict[str, Any]] = []
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
        size_by_datatype["GB"] = size_by_datatype["bytes"] / (1024**3)

    # --- Counts by suffix (anat: T1w/T2w; dwi: dwi; func: bold; etc.)
    suffixes = sorted(layout.get(return_type="id", target="suffix"))
    suf_rows: List[Dict[str, Any]] = []
    for suf in suffixes:
        n = len(layout.get(suffix=suf, return_type="file"))
        if n > 0:
            suf_rows.append({"suffix": suf, "count": n})
    counts_by_suffix = (
        pd.DataFrame(suf_rows).sort_values("count", ascending=False).reset_index(drop=True)
        if suf_rows
        else pd.DataFrame(columns=["suffix", "count"])
    )

    # --- Functional metadata summaries (TR by task)
    tr_rows: List[Dict[str, Any]] = []
    if "func" in datatypes:
        func_files = layout.get(datatype="func", suffix="bold", return_type="file")
        for f in func_files:
            md = layout.get_metadata(f)
            tr = md.get("RepetitionTime", None)
            ents = layout.parse_file_entities(f)
            task = ents.get("task", None)
            if tr is not None and task is not None:
                # cast to float to avoid dtype issues later
                try:
                    tr_rows.append({"task": task, "TR": float(tr)})
                except Exception:
                    pass

    tr_by_task = pd.DataFrame(tr_rows)
    if not tr_by_task.empty:
        agg = (
            tr_by_task.groupby("task")["TR"]
            .agg(["count", "min", "median", "max"])
            .reset_index()
        )
        distinct = (
            tr_by_task.groupby("task")["TR"]
            .apply(lambda s: sorted(set(round(float(x), 6) for x in s)))
            .reset_index(name="distinct_TRs")
        )
        tr_by_task = agg.merge(distinct, on="task", how="left")

    # --- Dataset description + participants
    dataset_description = _safe_read_json(root / "dataset_description.json")
    participants = _participants_df(root)

    summary: Dict[str, Any] = {
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
    return summary


__all__ = ["summarize_bids"]
