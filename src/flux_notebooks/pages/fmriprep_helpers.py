"""
Helper functions for fMRIPrep pages.

This module contains utility functions extracted from pages/fmriprep_index.py
to support the fMRIPrep reporting interface.
"""

from pathlib import Path
from dash import html
import dash_bootstrap_components as dbc


def list_htmls(data_root: Path):
    """
    List top-level fMRIPrep subject HTML reports (no duplicates).

    Args:
        data_root: Path to fMRIPrep derivatives directory

    Returns:
        List of dicts with keys: sub, ses, modality, path
        Each record represents one fMRIPrep HTML report file.
    """
    records = []

    # Only top-level HTML reports matter, e.g. fmriprep/sub-XXXX.html
    for f in sorted(data_root.glob("sub-*.html")):
        sub = f.stem  # e.g. "sub-1359"
        ses = "main"
        modality = "fMRIPrep"
        records.append(dict(sub=sub, ses=ses, modality=modality, path=f))

    return records


def color_for_modality(name: str):
    """
    Return a hex color code for a given imaging modality.

    Args:
        name: Modality name (e.g., "fMRIPrep")

    Returns:
        Hex color string suitable for CSS styling
    """
    if "fmriprep" in name.lower():
        return "#009FDF"  # same blue accent as Flux
    return "#ccc"


def make_link(r: dict, data_root: Path):
    """
    Generate a styled button link to an fMRIPrep report.

    Args:
        r: Dict with keys: path, modality (from list_htmls)
        data_root: Path to fMRIPrep derivatives directory for computing relative path

    Returns:
        html.A component with button link to fMRIPrep report
    """
    rel = r["path"].relative_to(data_root)
    return html.A(
        dbc.Button(
            "View Report",
            color="primary",
            size="sm",
            className="mt-1",
            style={"fontWeight": "500", "textTransform": "none"},
        ),
        href=f"/fmriprep_files/{rel}",
        target="_blank",
        style={"textDecoration": "none"},
    )
