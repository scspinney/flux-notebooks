import dash
from dash import html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc
from pathlib import Path
from flux_notebooks.config import Settings
from collections import defaultdict

dash.register_page(__name__, path="/mriqc", name="MRIQC Reports")

S = Settings.from_env()
DATA_ROOT = Path(S.dataset_root) / "qc" / "mriqc"

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

REPORTS = list_htmls()
SUBJECTS = sorted(set(r["sub"] for r in REPORTS))
MODALITIES = sorted(set(r["modality"] for r in REPORTS))

# ---------------------------------------------------------------------
def color_for_modality(name):
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
layout = dbc.Container(
    [
        html.H2("MRIQC Reports", className="mt-3 mb-2 text-center"),
        html.P(f"Dataset root: {S.dataset_root}", className="text-muted small text-center"),
        dbc.Row(
            [
                dbc.Col(
                    dcc.Dropdown(
                        id="sub-filter",
                        options=[{"label": s, "value": s} for s in SUBJECTS],
                        placeholder="Filter by subject...",
                        multi=True,
                    ),
                    md=4,
                ),
                dbc.Col(
                    dcc.Dropdown(
                        id="mod-filter",
                        options=[{"label": m, "value": m} for m in MODALITIES],
                        placeholder="Filter by modality...",
                        multi=True,
                    ),
                    md=4,
                ),
                dbc.Col(
                    dcc.Input(
                        id="search",
                        type="text",
                        placeholder="Search reports...",
                        debounce=True,
                        className="form-control",
                    ),
                    md=4,
                ),
            ],
            className="mb-4",
        ),
        html.Div(id="report-view"),
    ],
    fluid=True,
)

# ---------------------------------------------------------------------
@callback(
    Output("report-view", "children"),
    Input("sub-filter", "value"),
    Input("mod-filter", "value"),
    Input("search", "value"),
)
def update_view(sub_filter, mod_filter, search_text):
    # Filter reports
    reports = REPORTS
    if sub_filter:
        reports = [r for r in reports if r["sub"] in sub_filter]
    if mod_filter:
        reports = [r for r in reports if any(m in r["modality"] for m in mod_filter)]
    if search_text:
        text = search_text.lower()
        reports = [r for r in reports if text in r["path"].name.lower()]

    if not reports:
        return html.P("No reports match your filters.", className="text-center text-muted")

    # Group by subject → session → modality
    grouped = defaultdict(lambda: defaultdict(list))
    for r in reports:
        grouped[r["sub"]][r["ses"]].append(r)

    # Build accordion
    items = []
    for sub, sessions in grouped.items():
        # Collect all session names for headers
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


    return dbc.Accordion(items, start_collapsed=True, always_open=False)
