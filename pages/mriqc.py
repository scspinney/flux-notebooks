import dash
from dash import html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc
import pandas as pd
from pathlib import Path
from collections import defaultdict
from flux_notebooks.config import Settings

dash.register_page(__name__, path="/mriqc", name="MRIQC Reports")

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------
S = Settings.from_env()
DATA_ROOT = Path(S.dataset_root) / "qc" / "mriqc"
BIDS_ROOT = Path(S.dataset_root) / "bids"
PARTICIPANTS_TSV = BIDS_ROOT / "participants.tsv"

# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------
def list_htmls():
    htmls = sorted(DATA_ROOT.rglob("*.html"))
    records = []
    for f in htmls:
        parts = f.relative_to(DATA_ROOT).parts
        if len(parts) >= 3:
            sub, ses = parts[0], parts[1]
            modality = f.name.split("_")[-1].replace(".html", "")
            records.append(dict(sub=sub, ses=ses, modality=modality, path=f))
    return records


def color_for_modality(name: str):
    if "T1w" in name:
        return "#0dcaf0"
    if "dwi" in name:
        return "#ffb347"
    if "bold" in name:
        return "#5cb85c"
    return "#ccc"


def make_link(r):
    rel = r["path"].relative_to(DATA_ROOT)
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


# ---------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------
REPORTS = list_htmls()
SUBJECTS = sorted(set(r["sub"] for r in REPORTS))
MODALITIES = sorted(set(r["modality"] for r in REPORTS))

# ---------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------
layout = dbc.Container(
    [
        html.H2("MRIQC Reports", className="mt-4 mb-2 text-center fw-semibold"),
        html.P(
            """
            This section provides quick access to MRIQC-generated quality control reports 
            for all available subjects and sessions in the dataset. 
            Each subject entry expands to show per-modality HTML reports (e.g., T1w, T2w, BOLD), 
            allowing you to visually inspect data quality, motion, and artifacts. 
            Use the filters below to locate specific sites, subjects, imaging modalities, or reports. 
            """,
            style={
                "textAlign": "center",
                "color": "#6b7280",
                "maxWidth": "900px",
                "margin": "0 auto 25px auto",
                "fontSize": "15px",
                "lineHeight": "1.5",
            },
        ),

        # --------------------------
        # Centered Filter + Search Layout (aligned with accordion)
        # --------------------------
        dbc.Row(
            dbc.Col(
                [
                    # First row — site, subject, modality
                    dbc.Row(
                        [
                            dbc.Col(
                                dcc.Dropdown(
                                    id="site-filter",
                                    options=[
                                        {"label": "Montreal", "value": "Montreal"},
                                        {"label": "Calgary", "value": "Calgary"},
                                        {"label": "Toronto", "value": "Toronto"},
                                    ],
                                    placeholder="Filter by site...",
                                    clearable=True,
                                    className="mb-2",
                                ),
                                md=4,
                            ),
                            dbc.Col(
                                dcc.Dropdown(
                                    id="sub-filter",
                                    options=[{"label": s, "value": s} for s in SUBJECTS],
                                    placeholder="Filter by subject...",
                                    multi=True,
                                    className="mb-2",
                                ),
                                md=4,
                            ),
                            dbc.Col(
                                dcc.Dropdown(
                                    id="mod-filter",
                                    options=[{"label": m, "value": m} for m in MODALITIES],
                                    placeholder="Filter by modality...",
                                    multi=True,
                                    className="mb-2",
                                ),
                                md=4,
                            ),
                        ],
                        className="g-2 justify-content-center",
                    ),

                    # Second row — centered search bar
                    dbc.Row(
                        dbc.Col(
                            dcc.Input(
                                id="search",
                                type="text",
                                placeholder="Search reports...",
                                debounce=True,
                                className="form-control mt-2 mb-4",
                                style={"width": "100%"},
                            ),
                            md=12,
                        ),
                        className="justify-content-center",
                    ),
                ],
                md=8,  # <-- same width as accordion block below
                className="mx-auto",
            ),
            className="justify-content-center",
        ),



        # --------------------------
        # Centered accordion of reports
        # --------------------------
        dbc.Row(
            dbc.Col(
                html.Div(id="report-view"),
                md=8,
                className="mx-auto",
            ),
            justify="center",
        ),
    ],
    fluid=True,
    className="pb-5",
)


# ---------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------

@callback(
    Output("sub-filter", "options"),
    Input("site-filter", "value"),
)
def update_subject_options(selected_site):
    """
    Dynamically update the subject dropdown based on the selected site.
    Uses participants.tsv to identify subjects associated with each site.
    """
    if not PARTICIPANTS_TSV.exists():
        print(f"[WARN] participants.tsv not found at {PARTICIPANTS_TSV}")
        return [{"label": s, "value": s} for s in SUBJECTS]

    try:
        df = pd.read_csv(PARTICIPANTS_TSV, sep="\t")
    except Exception as e:
        print(f"[WARN] Failed to read participants.tsv: {e}")
        return [{"label": s, "value": s} for s in SUBJECTS]

    if "site_name" not in df.columns or "participant_id" not in df.columns:
        print("[WARN] participants.tsv missing required columns: 'site_name' or 'participant_id'")
        return [{"label": s, "value": s} for s in SUBJECTS]

    if selected_site:
        df = df[df["site_name"].str.lower() == selected_site.lower()]

    subs = sorted(df["participant_id"].unique().tolist())
    return [{"label": s, "value": s} for s in subs]


@callback(
    Output("report-view", "children"),
    Input("site-filter", "value"),
    Input("sub-filter", "value"),
    Input("mod-filter", "value"),
    Input("search", "value"),
)
def update_view(site_filter, sub_filter, mod_filter, search_text):
    """
    Filter and display MRIQC reports based on selected filters.
    """
    reports = REPORTS

    # --- Site filter (using participants.tsv)
    if site_filter and PARTICIPANTS_TSV.exists():
        try:
            df = pd.read_csv(PARTICIPANTS_TSV, sep="\t")
            if "site_name" in df.columns and "participant_id" in df.columns:
                subs_for_site = df.loc[
                    df["site_name"].str.lower() == site_filter.lower(), "participant_id"
                ].tolist()
                reports = [r for r in reports if r["sub"] in subs_for_site]
        except Exception as e:
            print(f"[WARN] Site filter failed: {e}")

    # --- Subject filter
    if sub_filter:
        reports = [r for r in reports if r["sub"] in sub_filter]

    # --- Modality filter
    if mod_filter:
        reports = [r for r in reports if any(m in r["modality"] for m in mod_filter)]

    # --- Search filter
    if search_text:
        text = search_text.lower()
        reports = [r for r in reports if text in r["path"].name.lower()]

    if not reports:
        return html.P(
            "No reports match your filters.",
            className="text-center text-muted mt-4",
        )

    # --- Group by subject → session → modality
    grouped = defaultdict(lambda: defaultdict(list))
    for r in reports:
        grouped[r["sub"]][r["ses"]].append(r)

    # --- Build accordion
    items = []
    for sub, sessions in grouped.items():
        ses_names = sorted(sessions.keys())
        rows = []
        for modality in ["T1w", "dwi", "bold"]:
            cols = []
            for ses in ses_names:
                ses_reports = [r for r in sessions[ses] if modality in r["modality"]]
                if ses_reports:
                    links = [make_link(r) for r in ses_reports]
                else:
                    links = [html.Span("—", style={"color": "#aaa"})]
                cols.append(dbc.Col(links, md=4, style={"minWidth": "200px"}))
            rows.append(
                dbc.Row(
                    [dbc.Col(html.Strong(modality, style={"width": "80px"}), md=2)] + cols,
                    className="align-items-start mb-1",
                )
            )

        body = dbc.CardBody(rows)
        items.append(
            dbc.AccordionItem(
                [body],
                title=html.A(
                    f"{sub} ({len(sessions)} sessions)",
                    href=f"/subject/{sub}",
                    style={"textDecoration": "none", "color": "#000"},
                ),
            )
        )

    return dbc.Card(
        dbc.CardBody(
            dbc.Accordion(items, start_collapsed=True, always_open=False),
            className="bg-light rounded-3 shadow-sm p-3",
        ),
        className="border-0",
    )








# import dash
# from dash import html, dcc, Input, Output, callback
# import dash_bootstrap_components as dbc
# from pathlib import Path
# from flux_notebooks.config import Settings
# from collections import defaultdict

# dash.register_page(__name__, path="/mriqc", name="MRIQC Reports")

# S = Settings.from_env()
# DATA_ROOT = Path(S.dataset_root) / "qc" / "mriqc"

# # ---------------------------------------------------------------------
# def list_htmls():
#     htmls = sorted(DATA_ROOT.rglob("*.html"))
#     records = []
#     for f in htmls:
#         parts = f.relative_to(DATA_ROOT).parts
#         if len(parts) >= 3:
#             sub, ses = parts[0], parts[1]
#             modality = f.name.split("_")[-1].replace(".html", "")
#             records.append(dict(sub=sub, ses=ses, modality=modality, path=f))
#     return records

# REPORTS = list_htmls()
# SUBJECTS = sorted(set(r["sub"] for r in REPORTS))
# MODALITIES = sorted(set(r["modality"] for r in REPORTS))

# # ---------------------------------------------------------------------
# def color_for_modality(name):
#     if "T1w" in name:
#         return "#0dcaf0"
#     if "dwi" in name:
#         return "#ffb347"
#     if "bold" in name:
#         return "#5cb85c"
#     return "#ccc"

# def make_link(r):
#     rel = r["path"].relative_to(DATA_ROOT)
#     color = color_for_modality(r["modality"])
#     return html.A(
#         r["path"].name.replace(".html", ""),
#         href=f"/mriqc_files/{rel}",
#         target="_blank",
#         style={
#             "display": "block",
#             "margin": "2px 0",
#             "color": color,
#             "textDecoration": "none",
#             "fontWeight": "500",
#         },
#     )

# # ---------------------------------------------------------------------
# # layout = dbc.Container(
# #     [
# #         html.H2("MRIQC Reports", className="mt-3 mb-2 text-center"),
# #         html.P(f"Dataset root: {S.dataset_root}", className="text-muted small text-center"),
# #         dbc.Row(
# #             [
# #                 dbc.Col(
# #                     dcc.Dropdown(
# #                         id="sub-filter",
# #                         options=[{"label": s, "value": s} for s in SUBJECTS],
# #                         placeholder="Filter by subject...",
# #                         multi=True,
# #                     ),
# #                     md=4,
# #                 ),
# #                 dbc.Col(
# #                     dcc.Dropdown(
# #                         id="mod-filter",
# #                         options=[{"label": m, "value": m} for m in MODALITIES],
# #                         placeholder="Filter by modality...",
# #                         multi=True,
# #                     ),
# #                     md=4,
# #                 ),
# #                 dbc.Col(
# #                     dcc.Input(
# #                         id="search",
# #                         type="text",
# #                         placeholder="Search reports...",
# #                         debounce=True,
# #                         className="form-control",
# #                     ),
# #                     md=4,
# #                 ),
# #             ],
# #             className="mb-4",
# #         ),
# #         html.Div(id="report-view"),
# #     ],
# #     fluid=True,
# # )


# # layout = dbc.Container(
# #     [
# #         html.H2("MRIQC Reports", className="mt-4 mb-2 text-center fw-semibold"),
# #         # html.P(
# #         #     f"Dataset root: {S.dataset_root}",
# #         #     className="text-muted small text-center mb-4",
# #         # ),
# #         html.P(
# #             """
# #             This section provides quick access to MRIQC-generated quality control reports 
# #             for all available subjects and sessions in the dataset. 
# #             Each subject entry expands to show per-modality HTML reports (e.g., T1w, T2w, BOLD), 
# #             allowing you to visually inspect data quality, motion, and artifacts. 
# #             Use the filters above to locate specific subjects, imaging modalities, or reports. 
# #             """,
# #             style={
# #                 "textAlign": "center",
# #                 "color": "#6b7280",
# #                 "maxWidth": "900px",
# #                 "margin": "0 auto 25px auto",
# #                 "fontSize": "15px",
# #                 "lineHeight": "1.5",
# #             },
# #         ),
# #         # Filter bar
# #         dbc.Row(
# #             [
# #                 dbc.Col(
# #                     dcc.Dropdown(
# #                         id="sub-filter",
# #                         options=[{"label": s, "value": s} for s in SUBJECTS],
# #                         placeholder="Filter by subject...",
# #                         multi=True,
# #                     ),
# #                     md=4,
# #                 ),
# #                 dbc.Col(
# #                     dcc.Dropdown(
# #                         id="mod-filter",
# #                         options=[{"label": m, "value": m} for m in MODALITIES],
# #                         placeholder="Filter by modality...",
# #                         multi=True,
# #                     ),
# #                     md=4,
# #                 ),
# #                 dbc.Col(
# #                     dcc.Input(
# #                         id="search",
# #                         type="text",
# #                         placeholder="Search reports...",
# #                         debounce=True,
# #                         className="form-control",
# #                     ),
# #                     md=4,
# #                 ),
# #             ],
# #             className="justify-content-center mb-4 g-2",
# #         ),

# #         # Centered accordion
# #         dbc.Row(
# #             dbc.Col(
# #                 html.Div(id="report-view"),
# #                 md=8,
# #                 className="mx-auto",  # centers horizontally
# #             ),
# #             justify="center",
# #         ),
# #     ],
# #     fluid=True,
# #     className="pb-5",
# # )



# layout = dbc.Container(
#     [
#         html.H2("MRIQC Reports", className="mt-4 mb-2 text-center fw-semibold"),

#         html.P(
#             """
#             This section provides quick access to MRIQC-generated quality control reports 
#             for all available subjects and sessions in the dataset. 
#             Each subject entry expands to show per-modality HTML reports (e.g., T1w, T2w, BOLD), 
#             allowing you to visually inspect data quality, motion, and artifacts. 
#             Use the filters below to locate specific sites, subjects, imaging modalities, or reports. 
#             """,
#             style={
#                 "textAlign": "center",
#                 "color": "#6b7280",
#                 "maxWidth": "900px",
#                 "margin": "0 auto 25px auto",
#                 "fontSize": "15px",
#                 "lineHeight": "1.5",
#             },
#         ),

#         # --------------------------
#         # Filter bar (now with Site)
#         # --------------------------
#         dbc.Row(
#             [
#                 dbc.Col(
#                     dcc.Dropdown(
#                         id="site-filter",
#                         options=[
#                             {"label": "Montreal", "value": "Montreal"},
#                             {"label": "Calgary", "value": "Calgary"},
#                             {"label": "Toronto", "value": "Toronto"},
#                         ],
#                         placeholder="Filter by site...",
#                         clearable=True,
#                         className="mb-2",
#                     ),
#                     md=3,
#                 ),
#                 dbc.Col(
#                     dcc.Dropdown(
#                         id="sub-filter",
#                         options=[{"label": s, "value": s} for s in SUBJECTS],
#                         placeholder="Filter by subject...",
#                         multi=True,
#                         className="mb-2",
#                     ),
#                     md=3,
#                 ),
#                 dbc.Col(
#                     dcc.Dropdown(
#                         id="mod-filter",
#                         options=[{"label": m, "value": m} for m in MODALITIES],
#                         placeholder="Filter by modality...",
#                         multi=True,
#                         className="mb-2",
#                     ),
#                     md=3,
#                 ),
#                 dbc.Col(
#                     dcc.Input(
#                         id="search",
#                         type="text",
#                         placeholder="Search reports...",
#                         debounce=True,
#                         className="form-control mb-2",
#                     ),
#                     md=3,
#                 ),
#             ],
#             className="justify-content-center mb-4 g-2",
#         ),

#         # --------------------------
#         # Centered accordion of reports
#         # --------------------------
#         dbc.Row(
#             dbc.Col(
#                 html.Div(id="report-view"),
#                 md=8,
#                 className="mx-auto",  # centers horizontally
#             ),
#             justify="center",
#         ),
#     ],
#     fluid=True,
#     className="pb-5",
# )


# # ---------------------------------------------------------------------
# @callback(
#     Output("report-view", "children"),
#     Input("sub-filter", "value"),
#     Input("mod-filter", "value"),
#     Input("search", "value"),
# )
# def update_view(sub_filter, mod_filter, search_text):
#     # Filter reports
#     reports = REPORTS
#     if sub_filter:
#         reports = [r for r in reports if r["sub"] in sub_filter]
#     if mod_filter:
#         reports = [r for r in reports if any(m in r["modality"] for m in mod_filter)]
#     if search_text:
#         text = search_text.lower()
#         reports = [r for r in reports if text in r["path"].name.lower()]

#     if not reports:
#         return html.P("No reports match your filters.", className="text-center text-muted")

#     # Group by subject → session → modality
#     grouped = defaultdict(lambda: defaultdict(list))
#     for r in reports:
#         grouped[r["sub"]][r["ses"]].append(r)

#     # Build accordion
#     items = []
#     for sub, sessions in grouped.items():
#         # Collect all session names for headers
#         ses_names = sorted(sessions.keys())
#         rows = []
#         for modality in ["T1w", "dwi", "bold"]:
#             cols = []
#             for ses in ses_names:
#                 ses_reports = [r for r in sessions[ses] if modality in r["modality"]]
#                 if ses_reports:
#                     links = [make_link(r) for r in ses_reports]
#                 else:
#                     links = [html.Span("—", style={"color": "#aaa"})]
#                 cols.append(dbc.Col(links, md=4, style={"minWidth": "200px"}))
#             rows.append(
#                 dbc.Row(
#                     [dbc.Col(html.Strong(modality, style={"width": "80px"}), md=2)] + cols,
#                     className="align-items-start mb-1",
#                 )
#             )

#         body = dbc.CardBody(rows)
#         items.append(
#             dbc.AccordionItem(
#                 [body],
#                 title=html.A(
#                     f"{sub} ({len(sessions)} sessions)",
#                     href=f"/subject/{sub}",
#                     style={"textDecoration": "none", "color": "#000"},
#                 ),
#             )
#         )


#     #return dbc.Accordion(items, start_collapsed=True, always_open=False)
#     return dbc.Card(
#     dbc.CardBody(
#         dbc.Accordion(items, start_collapsed=True, always_open=False),
#         className="bg-light rounded-3 shadow-sm p-3"
#     ),
#     className="border-0"
# )

