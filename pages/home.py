# pages/home.py
import dash
from dash import html
from flux_notebooks.bids.summarize_bids import summarize_bids
from flux_notebooks.freesurfer.summarize_freesurfer import summarize_freesurfer
from flux_notebooks.redcap.summarize_redcap import summarize_redcap

from pathlib import Path
import os

dash.register_page(__name__, path="/", name="Home")

# --- Load data roots ---
dataset_root = Path(os.environ.get("FLUX_DATASET_ROOT", "superdemo")).resolve()
bids_root = (
    dataset_root
    if (dataset_root / "dataset_description.json").exists()
    else (dataset_root / "bids")
).resolve()
fs_root = dataset_root / "derivatives" / "freesurfer"

# --- Summaries ---
bids_summary = summarize_bids(bids_root)
fs_summary = summarize_freesurfer(fs_root)

# Extract high-level stats
subjects = len(bids_summary.get("subjects", []))
sessions = len(bids_summary.get("sessions", []))
tasks = len(bids_summary.get("tasks", []))
fs_subjects = len(fs_summary.get("subjects", []))

def stat_card(title, value):
    return html.Div(
        style={
            "border": "1px solid #ddd",
            "borderRadius": "8px",
            "padding": "20px",
            "margin": "10px",
            "textAlign": "center",
            "boxShadow": "0 2px 6px rgba(0,0,0,0.1)",
            "backgroundColor": "#fafafa",
            "color": "#000000",  # 👈 force text to black
            "flex": "1",
        },
        children=[
            html.H4(title, style={"marginBottom": "10px", "color": "#000000"}),
            html.H2(str(value), style={"marginTop": "0", "color": "#000000"}),
        ],
    )

layout = html.Div(
    style={"fontFamily": "sans-serif", "margin": "20px"},
    children=[
        html.H1("Welcome to Flux Dashboards"),
        html.P("Here’s a snapshot of your dataset and processing pipelines."),
        html.Div(
            style={"display": "flex", "gap": "20px"},
            children=[
                stat_card("Subjects", subjects),
                stat_card("Sessions", sessions),
                stat_card("Tasks", tasks),
                stat_card("FreeSurfer Subjects", fs_subjects),
            ],
        ),
        html.P("Use the navigation above to explore detailed dashboards."),
    ],
)
