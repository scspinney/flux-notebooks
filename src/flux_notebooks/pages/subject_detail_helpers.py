"""Helper functions for subject detail page.

This module contains helper functions extracted from pages/subject_detail.py
to improve code organization and maintainability.
"""

import os
import glob
import json
import pandas as pd
from dash import html, dcc
import dash_bootstrap_components as dbc
from flux_notebooks.redcap.get_subject_info import get_subject_info
from flux_notebooks.lib.mriqc_summary import get_qc_summary
from flux_notebooks.lib.bids_inventory import summarize_subject_inventory


def make_info_card(sub_id):
    """Create demographics card for a subject.
    
    Args:
        sub_id: Subject ID string
        
    Returns:
        dbc.Card: Card component with demographics table
    """
    info = get_subject_info(sub_id)
    if not info:
        return dbc.Alert(f"No demographic info found for {sub_id}.", color="warning")
    rows = [html.Tr([html.Th(k), html.Td(v)]) for k, v in info.items()]
    return dbc.Card(
        [
            dbc.CardHeader(html.H4("Demographics")),
            dbc.CardBody(html.Table(rows, className="table table-sm mb-0")),
        ],
        className="shadow-sm mb-4",
    )


def make_inventory_card(sub_id):
    """Create BIDS data inventory card for a subject.
    
    Args:
        sub_id: Subject ID string
        
    Returns:
        dbc.Card or dbc.Alert: Card component with inventory table
    """
    inv = summarize_subject_inventory(sub_id)
    if not inv:
        return dbc.Alert("No BIDS data found.", color="secondary")
    rows = [html.Tr([html.Th(k), html.Td(v)]) for k, v in inv.items()]
    return dbc.Card(
        [
            dbc.CardHeader(html.H4("Data Inventory")),
            dbc.CardBody(html.Table(rows, className="table table-sm mb-0")),
        ],
        className="shadow-sm mb-4",
    )


def make_qc_strip(subject_id, session_filter, dataset_root):
    """Create quality control summary card with MRIQC metrics and human ratings.
    
    Args:
        subject_id: Subject ID string
        session_filter: Optional session filter string (e.g., "ses-1a")
        dataset_root: Path to dataset root directory
        
    Returns:
        html.Div or dbc.Card: QC summary component
    """
    qc_root = os.path.join(dataset_root, "qc", "mriqc", subject_id)
    human_qc_path = os.path.join(dataset_root, "qc", "human_qc.csv")

    # --- Load and normalize human QC CSV ---
    human_qc = None
    if os.path.exists(human_qc_path):
        df = pd.read_csv(human_qc_path, dtype=str)
        df.columns = df.columns.str.strip().str.lower()
        if "subjid" in df.columns:
            df["subjid"] = (
                df["subjid"]
                .astype(str)
                .str.replace("sub-", "", regex=False)
                .str.strip()
                .str.lower()
            )
        human_qc = df

    if not os.path.exists(qc_root):
        return html.Div("No MRIQC data found.", className="text-muted fst-italic")

    # --- QC metric badges ---
    def qc_badge(value, metric, thresholds):
        if value is None:
            color, label = "secondary", "—"
        elif value < thresholds[0]:
            color, label = "danger", f"{value:.2f}"
        elif value < thresholds[1]:
            color, label = "warning", f"{value:.2f}"
        else:
            color, label = "success", f"{value:.2f}"
        return dbc.Badge(f"{metric}: {label}", color=color, class_name="mx-1")

    # --- Mapping between acquisition names and CSV columns ---
    mapping = {
        "t1w": "t1",
        "acq-b1000_dwi": "dmri_run1",
        "acq-b2000_dwi": "dmri_run2",
        "acq-b3000_dwi": "dmri_run3",
        "partlycloudy": "fmri_run1",
        "laluna": "fmri_run2",
    }

    # --- Human rating badge ---
    def human_rating_badge(subjid, acq_name):
        if human_qc is None or "subjid" not in human_qc.columns:
            return "—"

        subjid_norm = subjid.replace("sub-", "").strip().lower()
        row = human_qc[human_qc["subjid"] == subjid_norm]
        if row.empty:
            return "—"

        match_key = None
        acq_name_l = acq_name.lower()
        for pattern, col in mapping.items():
            if pattern in acq_name_l:
                match_key = col
                break

        if not match_key or match_key not in human_qc.columns:
            return "—"

        val = str(row.iloc[0][match_key]).strip()
        if not val or val.lower() in ["nan", "none"]:
            return "—"

        try:
            val = int(val)
        except ValueError:
            return "—"

        color, text = {
            1: ("danger", "Fail (1)"),
            2: ("warning", "Minor (2)"),
            3: ("success", "Pass (3)"),
        }.get(val, ("secondary", str(val)))

        return dbc.Badge(text, color=color, class_name="mx-1 fw-semibold")

    # --- Notes button ---
    def notes_button(subjid):
        if human_qc is None or "notes" not in human_qc.columns:
            return "—"
        subjid_norm = subjid.replace("sub-", "").strip().lower()
        row = human_qc[human_qc["subjid"] == subjid_norm]
        if row.empty:
            return "—"
        note = str(row.iloc[0]["notes"]).strip()
        if not note or note.lower() in ["nan", "none"]:
            return "—"
        return dbc.Button(
            "📝",
            color="info",
            size="sm",
            title=note,
            style={"padding": "0.25rem 0.5rem", "fontSize": "0.85rem"},
        )

    # --- Parse MRIQC JSONs ---
    sessions = {}
    for json_file in glob.glob(os.path.join(qc_root, "**", "*.json"), recursive=True):
        fname = os.path.basename(json_file)
        if not any(k in fname for k in ["T1w", "bold", "dwi"]):
            continue
        try:
            with open(json_file, "r") as f:
                data = json.load(f)
        except Exception:
            continue

        ses = next((p for p in fname.split("_") if p.startswith("ses-")), "unknown")
        sessions.setdefault(ses, []).append((fname.replace(".json", ""), data))

    if not sessions:
        return html.Div("No sessions found.", className="text-muted")

    filtered_sessions = {
        ses: acqs
        for ses, acqs in sessions.items()
        if (session_filter is None or ses == session_filter)
    }

    # --- Build table rows ---
    rows = []
    for ses, acquisitions in sorted(filtered_sessions.items()):
        for acq_name, data in acquisitions:
            if "t1w" in acq_name.lower():
                icon = "🧠"
                metrics = [
                    qc_badge(data.get("cnr"), "CNR", [0.8, 1.5]),
                    qc_badge(data.get("snr_total"), "SNR", [4, 6]),
                ]
            elif "bold" in acq_name.lower():
                icon = "🎞️"
                metrics = [
                    qc_badge(data.get("fd_mean"), "FD mean", [0.15, 0.30]),
                    qc_badge(data.get("tsnr"), "tSNR", [30, 50]),
                ]
            elif "dwi" in acq_name.lower():
                icon = "🌊"
                metrics = [qc_badge(data.get("snr_total"), "SNR", [4, 6])]
            else:
                icon = "❔"
                metrics = [dbc.Badge("Unknown", color="secondary")]

            subjid = subject_id.replace("sub-", "").strip()
            rows.append(
                html.Tr(
                    [
                        html.Th(ses),
                        html.Td(f"{icon} {acq_name}"),
                        html.Td(metrics),
                        html.Td(human_rating_badge(subjid, acq_name)),
                        html.Td(notes_button(subjid)),
                    ]
                )
            )

    # --- Build the card ---
    return dbc.Card(
        [
            dbc.CardHeader(
                dbc.Row(
                    [
                        dbc.Col(html.H5("Quality Control at a Glance"), md="auto"),
                        dbc.Col(
                            dcc.Dropdown(
                                id="session-filter",
                                options=[
                                    {"label": s, "value": s}
                                    for s in sorted(sessions.keys())
                                ],
                                placeholder="Select session...",
                                clearable=True,
                                value=session_filter,
                                style={"width": "250px", "fontSize": "0.9rem"},
                            ),
                            width="auto",
                            className="ms-auto",
                        ),
                    ],
                    align="center",
                    justify="between",
                ),
                className="d-flex align-items-center",
            ),
            dbc.CardBody(
                html.Table(
                    [
                        html.Thead(
                            html.Tr(
                                [
                                    html.Th("Session"),
                                    html.Th("Acquisition"),
                                    html.Th("QC Metrics"),
                                    html.Th("Human Rating"),
                                    html.Th("Notes"),
                                ]
                            )
                        ),
                        html.Tbody(rows),
                    ],
                    className="table table-sm mb-0 align-middle",
                )
            ),
        ],
        className="shadow-sm my-4",
    )


def make_pipeline_status(subject_id, dataset_root, bids_root):
    """Create derived data pipeline status card for a subject.
    
    Args:
        subject_id: Subject ID string
        dataset_root: Path to dataset root directory
        bids_root: Path to BIDS directory
        
    Returns:
        html.Div or dbc.Card: Pipeline status component
    """
    subject_root = os.path.join(bids_root, subject_id)
    if not os.path.exists(subject_root):
        return html.Div()

    sessions = [s for s in os.listdir(subject_root) if s.startswith("ses-")] or ["—"]
    rows = []
    for ses in sorted(sessions):
        paths = {
            "DICOM → BIDS": os.path.exists(os.path.join(dataset_root, "bids", subject_id, ses)),
            "MRIQC": os.path.exists(os.path.join(dataset_root, "qc", "mriqc", subject_id)),
            "fMRIPrep": os.path.exists(
                os.path.join(dataset_root, "derivatives", "fmriprep", subject_id, ses)
            ),
            "Connectome": os.path.exists(
                os.path.join(dataset_root, "derivatives", "connectome", subject_id, ses)
            ),
        }
        row_cells = [html.Th(ses)] + [
            html.Td("✅" if done else "⏳") for done in paths.values()
        ]
        rows.append(html.Tr(row_cells))

    return dbc.Card(
        [
            dbc.CardHeader(html.H5("Derived Data Status")),
            dbc.CardBody(
                html.Table(
                    [
                        html.Thead(
                            html.Tr(
                                [
                                    html.Th("Session"),
                                    html.Th("DICOM → BIDS"),
                                    html.Th("MRIQC"),
                                    html.Th("fMRIPrep"),
                                    html.Th("Connectome"),
                                ]
                            )
                        ),
                        html.Tbody(rows),
                    ],
                    className="table table-sm mb-0",
                )
            ),
        ],
        className="shadow-sm my-4",
    )
