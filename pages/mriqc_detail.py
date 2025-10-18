import dash
from dash import html
import os
from flux_notebooks.config import Settings

dash.register_page(__name__, path_template="/mriqc/<sub>", name="MRIQC Detail")

S = Settings.from_env()
MRIQC_DIR = os.path.join(S.dataset_root, "qc", "mriqc")

def layout(sub=None):
    if not sub:
        return html.Div("Invalid subject.", style={"color": "red"})

    subject_path = os.path.join(MRIQC_DIR, sub)
    if not os.path.exists(subject_path):
        return html.Div(f"No MRIQC reports found for {sub}")

    # Find all HTML reports for this subject
    html_files = []
    for root, _, files in os.walk(subject_path):
        for f in files:
            if f.endswith(".html"):
                rel = os.path.relpath(os.path.join(root, f), MRIQC_DIR)
                html_files.append(rel)

    # Sort for readability
    html_files.sort()

    # Build embedded iframes
    panels = [
        html.Div([
            html.H4(os.path.basename(f)),
            html.Iframe(
                src=f"/static/qc/mriqc/{f}",
                style={"width": "100%", "height": "900px", "border": "1px solid #ccc"},
            ),
            html.Hr(),
        ])
        for f in html_files
    ]

    return html.Div(
        [
            html.H2(f"MRIQC Reports — {sub}", style={"marginBottom": "20px"}),
            html.A("← Back to summary", href="/mriqc", style={"color": "#007bff"}),
            html.Div(panels),
        ],
        style={"maxWidth": "1200px", "margin": "auto", "padding": "20px"},
    )
