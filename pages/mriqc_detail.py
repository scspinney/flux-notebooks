import os
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from flux_notebooks.lib.mriqc_summary import get_qc_summary
from flux_notebooks.config import Settings
from flux_notebooks.pages.mriqc_helpers import find_mriqc_htmls

# Load dataset root from environment
S = Settings.from_env()
BIDS_ROOT = os.path.join(S.dataset_root, "bids")

dash.register_page(__name__, path_template="/mriqc-detail/<subject_id>", name="MRIQC Detail", order=None, include_in_nav=False)



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

    html_links = find_mriqc_htmls(subject_id, S.dataset_root)

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
                "© 2025 BIDS-Flux Dashboards",
                className="text-center text-muted mt-5"
            ),
        ],
        fluid=True,
    )
