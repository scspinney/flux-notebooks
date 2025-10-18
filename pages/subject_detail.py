import dash
from dash import html
import dash_bootstrap_components as dbc
from flux_notebooks.redcap.get_subject_info import get_subject_info
from flux_notebooks.lib.mriqc_summary import get_qc_summary
from flux_notebooks.lib.bids_inventory import summarize_subject_inventory

dash.register_page(
    __name__,
    path_template="/subject/<subject_id>",
    name="Subject Detail",
)

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

def make_qc_card(sub_id):
    qc = get_qc_summary(sub_id)
    if not qc:
        return dbc.Alert("No MRIQC data found.", color="secondary")

    def fmt(val):
        return f"{val:.2f}" if isinstance(val, (int, float)) else val or "—"

    cards = []
    for mod, stats in qc.items():
        if not stats:
            continue
        rows = [html.Tr([html.Th(k), html.Td(fmt(v))]) for k, v in stats.items()]
        cards.append(
            dbc.Card(
                [
                    dbc.CardHeader(html.H5(mod)),
                    dbc.CardBody(html.Table(rows, className="table table-sm mb-0")),
                ],
                className="shadow-sm mb-3",
            )
        )
    return dbc.Row([dbc.Col(c, md=4) for c in cards])

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

def layout(subject_id=None, **kwargs):
    return dbc.Container(
        [
            html.H2(f"Subject Overview: {subject_id}", className="text-center my-4"),
            dbc.Row([
                dbc.Col(make_info_card(subject_id), md=4),
                dbc.Col(make_inventory_card(subject_id), md=8),
            ]),
            html.Hr(),
            dbc.Row([
                dbc.Col(make_qc_card(subject_id)),
            ]),
            html.Hr(),
            html.A("← Back to MRIQC Reports", href="/mriqc", className="btn btn-secondary mt-3"),
        ],
        fluid=True,
    )
