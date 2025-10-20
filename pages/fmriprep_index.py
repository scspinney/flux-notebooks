import dash
from dash import html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc
from pathlib import Path
from flux_notebooks.config import Settings
from collections import defaultdict

# ---------------------------------------------------------------------
dash.register_page(__name__, path="/fmriprep", name="fMRIPrep Reports")

S = Settings.from_env()
DATA_ROOT = Path(S.dataset_root) / "derivatives" / "fmriprep"
BIDS_ROOT = Path(S.dataset_root) / "bids"
PARTICIPANTS_TSV = BIDS_ROOT / "participants.tsv"
import pandas as pd

# ---------------------------------------------------------------------
def list_htmls():
    """List top-level fMRIPrep subject HTML reports correctly (no duplicates)."""
    records = []

    # Only top-level HTML reports matter, e.g. fmriprep/sub-XXXX.html
    for f in sorted(DATA_ROOT.glob("sub-*.html")):
        sub = f.stem  # e.g. "sub-1359"
        ses = "main"
        modality = "fMRIPrep"
        records.append(dict(sub=sub, ses=ses, modality=modality, path=f))

    return records




REPORTS = list_htmls()
SUBJECTS = sorted(set(r["sub"] for r in REPORTS))
MODALITIES = ["fMRIPrep"]

# ---------------------------------------------------------------------
def color_for_modality(name):
    if "fmriprep" in name.lower():
        return "#009FDF"  # same blue accent as Flux
    return "#ccc"


# def make_link(r):
#     rel = r["path"].relative_to(DATA_ROOT)
#     color = color_for_modality(r["modality"])
#     return html.A(
#         r["path"].name.replace(".html", ""),
#         href=f"/fmriprep_files/{rel}",
#         target="_blank",
#         style={
#             "display": "block",
#             "margin": "2px 0",
#             "color": color,
#             "textDecoration": "none",
#             "fontWeight": "500",
#         },
#     )


# def make_link(r):
#     rel = r["path"].relative_to(DATA_ROOT)
#     return html.A(
#         "Report",
#         href=f"/fmriprep_files/{rel}",
#         target="_blank",
#         style={
#             "display": "inline-block",
#             "color": "#0d6efd",
#             "textDecoration": "none",
#             "fontWeight": "500",
#         },
#     )
def make_link(r):
    rel = r["path"].relative_to(DATA_ROOT)
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




# ---------------------------------------------------------------------
# layout = dbc.Container(
#     [
#         html.H2("fMRIPrep Reports", className="mt-3 mb-2 text-center"),
#         html.P(f"Dataset root: {S.dataset_root}", className="text-muted small text-center"),
#         dbc.Row(
#             [
#                 dbc.Col(
#                     dcc.Dropdown(
#                         id="sub-filter",
#                         options=[{"label": s, "value": s} for s in SUBJECTS],
#                         placeholder="Filter by subject...",
#                         multi=True,
#                     ),
#                     md=6,
#                 ),
#                 dbc.Col(
#                     dcc.Input(
#                         id="search",
#                         type="text",
#                         placeholder="Search reports...",
#                         debounce=True,
#                         className="form-control",
#                     ),
#                     md=6,
#                 ),
#             ],
#             className="mb-4",
#         ),
#         html.Div(id="fmriprep-view"),
#     ],
#     fluid=True,
# )



layout = dbc.Container(
    [
        html.H2("fMRIPrep Reports", className="mt-4 mb-2 text-center fw-semibold"),
        # html.P(
        #     f"Dataset root: {S.dataset_root}",
        #     className="text-muted small text-center mb-4",
        # ),
        html.P(
            """
            This section provides participant-level fMRIPrep preprocessing reports for all available sessions. 
            Each report summarizes the steps of anatomical and functional preprocessing, including skull-stripping, 
            spatial normalization, tissue segmentation, and confound estimation. 
            Researchers can use these reports to verify the quality of anatomical alignment, motion correction, 
            and registration to template space before downstream analysis. 
            Use the filters above to explore reports by subject or session. 
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
        # Filters + Search (centered and aligned with accordion)
        # --------------------------
        dbc.Row(
            dbc.Col(
                [
                    # Top row — filters
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
                                md=6,
                            ),
                            dbc.Col(
                                dcc.Dropdown(
                                    id="sub-filter",
                                    options=[{"label": s, "value": s} for s in SUBJECTS],
                                    placeholder="Filter by subject...",
                                    multi=True,
                                    className="mb-2",
                                ),
                                md=6,
                            ),
                        ],
                        className="g-2",
                    ),

                    # Second row — search bar
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
                md=10,  # <── controls the total width; same as accordion (≈1100px)
                lg=8,   # slightly narrower on larger screens
                className="mx-auto",
                style={"maxWidth": "1100px"},
            ),
            className="justify-content-center",
        ),


        # --------------------------
        # Centered Accordion
        # --------------------------
        dbc.Row(
            dbc.Col(
                html.Div(id="fmriprep-view"),
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
@callback(
    Output("fmriprep-view", "children"),
    Input("site-filter", "value"),
    Input("sub-filter", "value"),
    Input("search", "value"),
)
def update_view(site_filter, sub_filter, search_text):
    reports = REPORTS
    if site_filter and PARTICIPANTS_TSV.exists():
        try:
            df = pd.read_csv(PARTICIPANTS_TSV, sep="\t")
            if "site_name" in df.columns and "participant_id" in df.columns:
                subs_for_site = df.loc[
                    df["site_name"].str.lower() == site_filter.lower(),
                    "participant_id"
                ].tolist()
                reports = [r for r in reports if r["sub"] in subs_for_site]
        except Exception as e:
            print(f"[WARN] Site filter failed: {e}")

    if sub_filter:
        reports = [r for r in reports if r["sub"] in sub_filter]
    if search_text:
        text = search_text.lower()
        reports = [r for r in reports if text in r["path"].name.lower()]

    if not reports:
        return html.P("No fMRIPrep reports match your filters.", className="text-center text-muted")

    grouped = defaultdict(lambda: defaultdict(list))
    for r in reports:
        grouped[r["sub"]][r["ses"]].append(r)

    items = []
    for sub, sessions in grouped.items():
        ses_names = sorted(sessions.keys())
        rows = []
        for modality in MODALITIES:
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
                    cols,
                    className="align-items-start mb-2",
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
        className="rounded-4 p-4",
        style={
            "backgroundColor": "#fafafa",  # subtle off-white
            "boxShadow": "inset 0 1px 0 rgba(255,255,255,0.5), 0 8px 20px rgba(0,0,0,0.06)",
            "border": "1px solid rgba(0,0,0,0.04)",
        },
    ),
    className="border-0",
    style={
        "maxWidth": "1100px",
        "margin": "0 auto",
        "borderRadius": "18px",
        "boxShadow": "0 4px 18px rgba(0,0,0,0.04)",
        "background": "linear-gradient(180deg, #fefefe 0%, #f9f9f9 100%)",
    },
)




@callback(
    Output("sub-filter", "options", allow_duplicate=True),
    Input("site-filter", "value"),
    prevent_initial_call=True,
)
def update_subject_options(selected_site):
    """Populate subject dropdown dynamically from participants.tsv."""
    try:
        if not PARTICIPANTS_TSV.exists():
            return [{"label": s, "value": s} for s in SUBJECTS]

        df = pd.read_csv(PARTICIPANTS_TSV, sep="\t")
        if "site_name" not in df.columns or "participant_id" not in df.columns:
            return [{"label": s, "value": s} for s in SUBJECTS]

        if selected_site:
            df = df[df["site_name"].str.lower() == selected_site.lower()]

        subs = sorted(df["participant_id"].unique().tolist())
        return [{"label": s, "value": s} for s in subs]
    except Exception as e:
        print(f"[WARN] update_subject_options failed: {e}")
        return [{"label": s, "value": s} for s in SUBJECTS]

