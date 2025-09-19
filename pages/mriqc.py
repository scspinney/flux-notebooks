import dash
from dash import html
import os
from flux_notebooks.lib.mriqc import summarize_mriqc
from flux_notebooks.config import Settings

dash.register_page(__name__, path="/mriqc", name="MRIQC Summary")

# Load settings from environment (consistent with your notebooks)
S = Settings.from_env()

summary = summarize_mriqc(S.dataset_root, outdir=S.outdir)

layout = html.Div([
    html.H2("MRIQC Summary"),
    html.Pre(str(summary.keys())),
])
