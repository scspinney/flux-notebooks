import os
import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
from flux_notebooks.redcap.get_subject_info import get_subject_list
from flux_notebooks.config import Settings
from flux_notebooks.pages.subject_detail_helpers import (
    make_info_card,
    make_inventory_card,
    make_qc_strip,
    make_pipeline_status,
)

S = Settings.from_env()
BIDS_ROOT = os.path.join(S.dataset_root, "bids")

dash.register_page(
    __name__,
    path_template="/subject/<subject_id>",
    name="Subject Detail",
)

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
            html.Div(id="qc-container", children=make_qc_strip(subject_id, None, S.dataset_root)),
            make_pipeline_status(subject_id, S.dataset_root, BIDS_ROOT),
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
    return make_qc_strip(subject_id, selected_session, S.dataset_root)
