import dash
from dash import html
from pathlib import Path
import os
from flux_notebooks.freesurfer.summarize_freesurfer import summarize_freesurfer

dash.register_page(__name__, path="/freesurfer", name="FreeSurfer Summary")

dataset_root = Path(os.environ.get("FLUX_DATASET_ROOT", "superdemo")).resolve()
fs_root = dataset_root / "derivatives" / "freesurfer"
summary = summarize_freesurfer(fs_root)

layout = html.Div([
    html.H2("FreeSurfer Summary"),
    html.Pre(str(summary.keys())),
])
