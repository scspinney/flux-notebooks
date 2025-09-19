import dash
from dash import html, dcc, dash_table
import plotly.express as px
import os
from pathlib import Path
from flux_notebooks.bids.summarize_bids import summarize_bids
import pandas as pd

dash.register_page(__name__, path="/bids", name="BIDS Summary")

dataset_root = Path(os.environ.get("FLUX_DATASET_ROOT", "superdemo")).resolve()
bids_root = (
    dataset_root
    if (dataset_root / "dataset_description.json").exists()
    else (dataset_root / "bids")
).resolve()

summary = summarize_bids(bids_root)

# --- Fix distinct_TRs column ---
tr_df = summary.get("tr_by_task")
if tr_df is not None and "distinct_TRs" in tr_df.columns:
    tr_df = tr_df.copy()
    tr_df["distinct_TRs"] = tr_df["distinct_TRs"].astype(str)
    summary["tr_by_task"] = tr_df

def make_table(title, df: pd.DataFrame):
    if df is None or df.empty:
        return html.Div(f"No data for {title}")
    return dash_table.DataTable(
        data=df.to_dict("records"),
        columns=[{"name": i, "id": i} for i in df.columns],
        page_size=10,
        style_table={"overflowX": "auto"},
    )

# --- Example Plot ---
fig_avail = None
if summary.get("avail") is not None and not summary["avail"].empty:
    df = summary["avail"].reset_index()
    fig_avail = px.bar(
        df.melt(id_vars=["sub"], var_name="datatype", value_name="count"),
        x="sub",
        y="count",
        color="datatype",
        barmode="stack",
        title="Availability by datatype",
    )

layout = html.Div([
    html.H2("BIDS Summary"),

    html.Div([
        html.H3("Availability by datatype"),
        make_table("Availability by datatype", summary.get("avail")),
        dcc.Graph(figure=fig_avail) if fig_avail else html.Div("No plot available"),
    ]),

    html.Div([
        html.H3("Functional runs per task"),
        make_table("Functional runs per task", summary.get("func_counts")),
    ]),

    html.Div([
        html.H3("TR summary by task"),
        make_table("TR summary by task", summary.get("tr_by_task")),
    ]),
])
