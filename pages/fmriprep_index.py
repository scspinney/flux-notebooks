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
        dbc.Row(
            [
                dbc.Col(
                    dcc.Dropdown(
                        id="sub-filter",
                        options=[{"label": s, "value": s} for s in SUBJECTS],
                        placeholder="Filter by subject...",
                        multi=True,
                    ),
                    md=5,
                ),
                dbc.Col(
                    dcc.Input(
                        id="search",
                        type="text",
                        placeholder="Search reports...",
                        debounce=True,
                        className="form-control",
                    ),
                    md=5,
                ),
            ],
            className="justify-content-center mb-4 g-2",
        ),
        dbc.Row(
            dbc.Col(
                html.Div(id="fmriprep-view"),
                md=8,
                className="mx-auto",  # centers content
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
    Input("sub-filter", "value"),
    Input("search", "value"),
)
def update_view(sub_filter, search_text):
    reports = REPORTS
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

    #return dbc.Accordion(items, start_collapsed=True, always_open=False)
    return dbc.Card(
        dbc.CardBody(
            dbc.Accordion(items, start_collapsed=True, always_open=False),
            className="bg-light rounded-3 shadow-sm p-3"
        ),
        className="border-0"
    )
