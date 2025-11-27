import dash
from dash import html, dcc
from pathlib import Path
import os
from datetime import datetime

from flux_notebooks.pages.bids_helpers import (
    render_dir_tree,
    make_bids_info_panel,
)

dash.register_page(__name__, path="/bids", name="BIDS Summary")

dataset_root = Path(os.environ.get("FLUX_DATASET_ROOT", "superdemo_real")).resolve()
# def render_dir_tree(path: Path, level=0):
def layout():
    last_updated = datetime.fromtimestamp(dataset_root.stat().st_mtime).strftime("%Y-%m-%d %H:%M")

    return html.Div(
        className="page-transition",
        style={
            "fontFamily": "Inter, sans-serif",
            "margin": "30px auto",
            "maxWidth": "1200px",
        },
        children=[
            html.H2("🧠 BIDS Dataset Summary", style={"marginBottom": "6px"}),

             html.P(
                 "This page shows the hierarchical structure of your BIDS dataset:  "
                "from participants to sessions, modalities, and metadata files. "
                "Use this view to verify dataset completeness and structure. To visit the data repository, use the Go to Data button.",
                style={
                "textAlign": "center",
                "color": "#6b7280",
                "maxWidth": "900px",
                "margin": "0 auto 25px auto",
                "fontSize": "15px",
                "lineHeight": "1.5",
            },
            ),
            
            # ──────────────────────────────────────────────
            # Button above, aligned with accordion
            # ──────────────────────────────────────────────
            html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "flex-end",
                    "marginBottom": "10px",
                },
                children=[
                    html.A(
                        "Go to Data →",
                        href="/data",
                        style={
                            "backgroundColor": "#2563eb",
                            "color": "white",
                            "padding": "10px 18px",
                            "borderRadius": "8px",
                            "fontWeight": "600",
                            "textDecoration": "none",
                            "whiteSpace": "nowrap",
                            "boxShadow": "0 3px 10px rgba(37,99,235,0.3)",
                            "transition": "background 0.2s ease-in-out",
                        },
                    ),
                ],
            ),

            # ──────────────────────────────────────────────
            # Accordion
            # ──────────────────────────────────────────────
            html.Div(
                style={
                    "backgroundColor": "#f9fafb",
                    "padding": "20px 30px",
                    "borderRadius": "10px",
                    "boxShadow": "0 4px 12px rgba(0,0,0,0.08)",
                    "overflowY": "auto",
                    "maxHeight": "75vh",
                },
                children=render_dir_tree(dataset_root),
            ),

            # ──────────────────────────────────────────────
            # Info Sidebar
            # ──────────────────────────────────────────────
            make_bids_info_panel(dataset_root, last_updated),
        ],
    )


from dash import Input, Output, State

def register_callbacks(app):
    @app.callback(
        Output("info-panel-content-bids", "className"),
        Input("toggle-panel-btn-bids", "n_clicks"),
        State("info-panel-content-bids", "className"),
        prevent_initial_call=True,
    )
    def toggle_info_panel(n_clicks, current_class):
        if not n_clicks:
            raise dash.exceptions.PreventUpdate
        if current_class and "collapsed" in current_class:
            return "floating-info-panel"
        else:
            return "floating-info-panel collapsed"

