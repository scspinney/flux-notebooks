import os
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from flux_notebooks.lib.mriqc_summary import get_qc_summary
from flux_notebooks.config import Settings

# Load dataset root from environment
S = Settings.from_env()
BIDS_ROOT = os.path.join(S.dataset_root, "bids")

dash.register_page(
    __name__,
    path_template="/mriqc-detail/<subject_id>",
    name="MRIQC Detail",
)


def _find_mriqc_htmls(subject_id):
    """
    Locate MRIQC HTML reports for a given subject.
    Returns: dict of {modality: [relative URLs for /mriqc_files/...]}
    """
    qc_root = os.path.join(S.dataset_root, "qc", "mriqc")
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



def layout(subject_id=None, **kwargs):
    if subject_id is None:
        return dbc.Container(
            [
                html.H2("MRIQC Detail"),
                html.P("No subject selected."),
                dcc.Link("← Back to Subject Search", href="/subject/none"),
            ],
            fluid=True,
        )

    qc = get_qc_summary(subject_id)
    if not qc:
        return dbc.Container(
            [
                html.H2(f"MRIQC Detail: {subject_id}", className="text-center my-4"),
                dbc.Alert("No MRIQC data found for this subject.", color="warning"),
                dcc.Link("← Back to Subject Detail", href=f"/subject/{subject_id}"),
            ],
            fluid=True,
        )

    html_links = _find_mriqc_htmls(subject_id)

    cards = []
    for mod, stats in qc.items():
        rows = [html.Tr([html.Th(k), html.Td(v)]) for k, v in stats.items()]

        # Append MRIQC HTML links for this modality
        link_rows = []
        for link in html_links.get(mod, []):
            label = os.path.basename(link).replace("_", " ").replace(".html", "")
            link_rows.append(
                html.Tr([
                    html.Th("Report"),
                    html.Td(
                        html.A(
                            label,
                            href=f"/mriqc_files/{link}",  # ✅ points to correct Flask route
                            target="_blank",
                            className="text-primary fw-semibold"
                        )
                    )
                ])
            )


        cards.append(
            dbc.Card(
                [
                    dbc.CardHeader(html.H5(mod)),
                    dbc.CardBody(
                        html.Table(rows + link_rows, className="table table-sm mb-0")
                    ),
                ],
                className="shadow-sm mb-3",
            )
        )

    return dbc.Container(
        [
            html.H2(f"MRIQC Detail: {subject_id}", className="text-center my-4"),
            html.Div(dbc.Row([dbc.Col(c, md=4) for c in cards])),
            html.Div(
                [
                    dbc.Button("← Back to Subject", href=f"/subject/{subject_id}", color="secondary", className="mt-4 me-2"),
                    dbc.Button("🏠 Back to MRIQC Reports", href="/mriqc", color="info", className="mt-4"),
                ],
                className="text-center"
            ),
            html.Footer(
                "© 2025 Flux Dashboards | REDCap + BIDS-Flux integration",
                className="text-center text-muted mt-5"
            ),
        ],
        fluid=True,
    )
