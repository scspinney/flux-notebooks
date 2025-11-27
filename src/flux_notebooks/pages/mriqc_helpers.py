"""
Helper functions for MRIQC pages.

This module contains utility functions extracted from pages/mriqc.py
and pages/mriqc_detail.py to support the MRIQC reporting interface.
"""

import os
from pathlib import Path
from dash import html


def list_htmls(data_root: Path):
    """
    List all MRIQC HTML report files within the given data root.

    Args:
        data_root: Path to the MRIQC output directory

    Returns:
        List of dicts with keys: sub, ses, modality, path
        Each record represents one MRIQC HTML report file.
    """
    htmls = sorted(data_root.rglob("*.html"))
    records = []
    for f in htmls:
        parts = f.relative_to(data_root).parts
        if len(parts) >= 3:
            sub, ses = parts[0], parts[1]
            modality = f.name.split("_")[-1].replace(".html", "")
            records.append(dict(sub=sub, ses=ses, modality=modality, path=f))
    return records


def color_for_modality(name: str):
    """
    Return a hex color code for a given imaging modality.

    Args:
        name: Modality name (e.g., "T1w", "bold", "dwi")

    Returns:
        Hex color string suitable for CSS styling
    """
    if "T1w" in name:
        return "#0dcaf0"
    if "dwi" in name:
        return "#ffb347"
    if "bold" in name:
        return "#5cb85c"
    return "#ccc"


def make_link(r, data_root: Path):
    """
    Generate a styled HTML link to an MRIQC report.

    Args:
        r: Dict with keys: path, modality (from list_htmls)
        data_root: Path to MRIQC output directory for computing relative path

    Returns:
        dash.html.A component with colored link to MRIQC report
    """
    rel = r["path"].relative_to(data_root)
    color = color_for_modality(r["modality"])
    return html.A(
        r["path"].name.replace(".html", ""),
        href=f"/mriqc_files/{rel}",
        target="_blank",
        style={
            "display": "block",
            "margin": "2px 0",
            "color": color,
            "textDecoration": "none",
            "fontWeight": "500",
        },
    )


def find_mriqc_htmls(subject_id: str, dataset_root: str):
    """
    Locate MRIQC HTML reports for a given subject.

    Args:
        subject_id: BIDS subject identifier (e.g., "sub-001")
        dataset_root: Root path to the dataset

    Returns:
        Dict mapping modality names to lists of relative URLs
        for accessing reports via /mriqc_files/ Flask route
    """
    qc_root = os.path.join(dataset_root, "qc", "mriqc")
    html_links = {}

    if not os.path.exists(qc_root):
        print(f"[WARN] MRIQC root not found: {qc_root}")
        return html_links

    for root, _, files in os.walk(qc_root):
        for f in files:
            if f.endswith(".html") and f.startswith(subject_id):
                modality = "unknown"
                if "_T1w" in f:
                    modality = "T1w"
                elif "_bold" in f:
                    modality = "BOLD"
                elif "_dwi" in f:
                    modality = "DWI"

                abs_path = os.path.join(root, f)
                rel = os.path.relpath(abs_path, qc_root)
                html_links.setdefault(modality, []).append(rel)

    print(f"[DEBUG] Found MRIQC reports for {subject_id}: {html_links}")
    return html_links
