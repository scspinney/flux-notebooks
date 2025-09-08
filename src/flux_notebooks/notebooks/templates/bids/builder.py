# src/flux_notebooks/notebooks/templates/bids/builder.py
from __future__ import annotations
from typing import Dict, Any, List
from ...builder import build_from_sections, save_tables
from ...sections import get_sections
from ....bids.summarize_bids import summarize_with_pybids

output_name = "bids_summary.ipynb"

# Choose the sections you want; omit KPI here to remove it by default.
PIPELINE_NAMES: List[str] = [
    "bids:intro",
    "bids:init",
    "bids:metadata",
    # "bids:kpi",
    "bids:availability",
    "bids:func_runs",
    "bids:tr",
    "common:explorer",
]

def summarize(settings, generated: str) -> Dict[str, Any]:
    summary = summarize_with_pybids(settings.dataset_root, validate=settings.validate_bids)
    save_tables(summary, settings.outdir)
    return dict(
        dataset_root=settings.dataset_root,
        outdir=settings.outdir,
        generated=generated,
        n_subjects=len(summary["subjects"]),
        n_sessions=len(summary["sessions"]),
        n_tasks=len(summary["tasks"]),
        datatypes=summary["datatypes"],
    )

def build(context: Dict[str, Any]):
    return build_from_sections(context, get_sections(PIPELINE_NAMES))
