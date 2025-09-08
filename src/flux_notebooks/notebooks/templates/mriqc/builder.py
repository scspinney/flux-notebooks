# src/flux_notebooks/notebooks/templates/mriqc/builder.py
from __future__ import annotations
from typing import Dict, Any, List
from ...builder import build_from_sections
from ...sections import get_sections

output_name = "mriqc_summary.ipynb"

PIPELINE_NAMES: List[str] = [
    "mriqc:header",
    "mriqc:group_reports",
    "mriqc:t1w_metrics",
    "common:explorer",
]

def summarize(settings, generated: str) -> Dict[str, Any]:
    return dict(dataset_root=settings.dataset_root, outdir=settings.outdir, generated=generated)

def build(context: Dict[str, Any]):
    return build_from_sections(context, get_sections(PIPELINE_NAMES))
