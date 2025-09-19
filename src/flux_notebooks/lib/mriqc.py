# src/flux_notebooks/lib/mriqc.py
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import re

import pandas as pd


def _read_json_safely(p: Path) -> dict:
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def _collect_qa_dir(dataset_root: Path) -> Optional[Path]:
    """
    Prefer <root>/qa/mriqc; fall back to <root>/derivatives/mriqc if present.
    """
    candidates = [
        Path(dataset_root) / "qa" / "mriqc",
        Path(dataset_root) / "derivatives" / "mriqc",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def summarize_mriqc(dataset_root: Path, outdir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Summarize MRIQC outputs found under <dataset_root>/qa/mriqc (preferred)
    or <dataset_root>/derivatives/mriqc.

    Returns a dict with:
      - qa_dir: Path
      - group_reports: List[Path] (e.g., group_T1w.html, group_bold.html)
      - subject_jsons: List[Path]
      - metrics: DataFrame (one row per subject JSON)
      - counts_by_modality: DataFrame (counts of *_T1w.json, *_bold.json, etc.)
    """
    dataset_root = Path(dataset_root)
    qa_dir = _collect_qa_dir(dataset_root)
    if qa_dir is None:
        return {
            "qa_dir": None,
            "group_reports": [],
            "subject_jsons": [],
            "metrics": pd.DataFrame(),
            "counts_by_modality": pd.DataFrame(),
        }

    # group HTMLs (keep as paths for linking in the notebook)
    group_reports = sorted(qa_dir.glob("group_*.html"))

    # subject-level JSONs (handle any modality suffix)
    subject_jsons = sorted(qa_dir.glob("sub-*.json"))

    rows: List[dict] = []
    modality_counts: dict[str, int] = {}

    for jp in subject_jsons:
        d = _read_json_safely(jp)

        # subject id: try filename first, then bids_meta
        m = re.match(r"sub-([a-zA-Z0-9]+)", jp.name)
        sub = m.group(1) if m else d.get("bids_meta", {}).get("subject_id")

        # modality: infer from filename like sub-01_T1w.json or sub-01_bold.json
        mod = None
        m2 = re.search(r"_(\w+)\.json$", jp.name)
        if m2:
            mod = m2.group(1)

        # flatten the common metrics (keys vary by MRIQC version; keep it defensive)
        flat: dict[str, Any] = {
            "subject": sub,
            "modality": mod,
        }
        # Try some typical metric blocks if present
        for block in ("iqms", "provenance", "bids_meta"):
            val = d.get(block)
            if isinstance(val, dict):
                for k, v in val.items():
                    # avoid deeply nested structures
                    if not isinstance(v, (dict, list)):
                        flat[f"{block}.{k}"] = v

        rows.append(flat)
        if mod:
            modality_counts[mod] = modality_counts.get(mod, 0) + 1

    metrics = pd.DataFrame(rows)
    counts_by_modality = (
        pd.DataFrame(sorted(modality_counts.items()), columns=["modality", "count"])
        if modality_counts
        else pd.DataFrame(columns=["modality", "count"])
    )

    # Optional exports (CSV) for the book artifacts
    if outdir:
        outdir = Path(outdir)
        outdir.mkdir(parents=True, exist_ok=True)
        if not metrics.empty:
            metrics.to_csv(outdir / "mriqc_metrics.csv", index=False)
        if not counts_by_modality.empty:
            counts_by_modality.to_csv(outdir / "mriqc_counts_by_modality.csv", index=False)

    return {
        "qa_dir": qa_dir,
        "group_reports": group_reports,
        "subject_jsons": subject_jsons,
        "metrics": metrics,
        "counts_by_modality": counts_by_modality,
    }


__all__ = ["summarize_mriqc"]
