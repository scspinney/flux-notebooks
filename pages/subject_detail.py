import os
import glob
import json
import pandas as pd
import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
from flux_notebooks.redcap.get_subject_info import get_subject_info, get_subject_list
from flux_notebooks.lib.mriqc_summary import get_qc_summary
from flux_notebooks.lib.bids_inventory import summarize_subject_inventory
from flux_notebooks.config import Settings

S = Settings.from_env()
BIDS_ROOT = os.path.join(S.dataset_root, "bids")

dash.register_page(
    __name__,
    path_template="/subject/<subject_id>",
    name="Subject Detail",
)

# ------------------------------------------------------------
# --- Helper Cards
# ------------------------------------------------------------

def make_info_card(sub_id):
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

# ------------------------------------------------------------
# --- Quality Control (with human ratings + notes)
# ------------------------------------------------------------

def make_qc_strip(subject_id, session_filter=None):
    qc_root = os.path.join(S.dataset_root, "qc", "mriqc", subject_id)
    human_qc_path = os.path.join(S.dataset_root, "qc", "human_qc.csv")

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

# ------------------------------------------------------------
# --- Derived Data Status
# ------------------------------------------------------------

def make_pipeline_status(subject_id):
    root = S.dataset_root
    subject_root = os.path.join(BIDS_ROOT, subject_id)
    if not os.path.exists(subject_root):
        return html.Div()

    sessions = [s for s in os.listdir(subject_root) if s.startswith("ses-")] or ["—"]
    rows = []
    for ses in sorted(sessions):
        paths = {
            "DICOM → BIDS": os.path.exists(os.path.join(root, "bids", subject_id, ses)),
            "MRIQC": os.path.exists(os.path.join(root, "qc", "mriqc", subject_id)),
            "fMRIPrep": os.path.exists(
                os.path.join(root, "derivatives", "fmriprep", subject_id, ses)
            ),
            "Connectome": os.path.exists(
                os.path.join(root, "derivatives", "connectome", subject_id, ses)
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

# ------------------------------------------------------------
# --- Layout
# ------------------------------------------------------------

def layout(subject_id=None, **kwargs):
    if subject_id in [None, "none", "None", ""]:
        return dbc.Container(
            [
                html.H2("Subject Search", className="text-center my-4"),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Label("Select Site:"),
                                dcc.Dropdown(
                                    id="site-filter",
                                    options=[
                                        {"label": "Calgary", "value": "Calgary"},
                                        {"label": "Montreal", "value": "Montreal"},
                                        {"label": "Toronto", "value": "Toronto"},
                                    ],
                                    placeholder="Select site...",
                                ),
                            ],
                            md=4,
                        ),
                        dbc.Col(
                            [
                                html.Label("Search Subject ID:"),
                                dcc.Dropdown(
                                    id="subject-search",
                                    placeholder="Start typing a subject ID...",
                                    options=[],
                                ),
                            ],
                            md=6,
                        ),
                        dbc.Col(
                            dbc.Button(
                                "View Subject",
                                id="view-subject-btn",
                                color="primary",
                                className="mt-4",
                            ),
                            md=2,
                        ),
                    ],
                    className="mb-4",
                ),
                html.Div(id="search-feedback", className="text-center text-muted mt-3"),
            ],
            fluid=True,
        )

    return dbc.Container(
        [
            html.H2(f"Subject Overview: {subject_id}", className="text-center my-4"),
            dbc.Row(
                dbc.ButtonGroup(
                    [
                        dbc.Button("← Back to Search", href="/subject/none", color="secondary"),
                        dbc.Button("🧠 MRIQC Reports", href=f"/mriqc-detail/{subject_id}", color="info"),
                        dbc.Button("🧩 fMRIPrep Summary", href=f"/fmriprep-detail/{subject_id}", color="primary"),
                    ],
                    size="lg",
                    className="d-flex justify-content-center mb-4 gap-2",
                ),
                className="text-center mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(make_info_card(subject_id), md=4),
                    dbc.Col(make_inventory_card(subject_id), md=8),
                ]
            ),
            html.Div(id="qc-container", children=make_qc_strip(subject_id)),
            make_pipeline_status(subject_id),
            html.Footer(
                "© 2025 BIDS-Flux Dashboards",
                className="text-center text-muted mt-5",
            ),
        ],
        fluid=True,
    )

# ------------------------------------------------------------
# --- Callbacks
# ------------------------------------------------------------

@callback(Output("subject-search", "options"), Input("site-filter", "value"))
def update_subject_dropdown(selected_site):
    subjects = get_subject_list(site=selected_site)
    return [{"label": s, "value": s} for s in subjects]


@callback(
    Output("search-feedback", "children"),
    Input("view-subject-btn", "n_clicks"),
    State("subject-search", "value"),
    prevent_initial_call=True,
)
def go_to_subject(n_clicks, selected_subject):
    if not selected_subject:
        return dbc.Alert("Please select a subject first.", color="warning")
    return dcc.Location(href=f"/subject/{selected_subject}", id="redirect-subject")


@callback(
    Output("qc-container", "children"),
    Input("session-filter", "value"),
    State("url", "pathname"),
)
def update_qc_table(selected_session, path):
    if not path or "/subject/" not in path:
        return html.Div()
    subject_id = path.split("/subject/")[-1]
    return make_qc_strip(subject_id, session_filter=selected_session)
