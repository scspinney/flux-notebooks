# pages/bids.py
import os
from pathlib import Path

import dash
from dash import html, dcc, dash_table
import plotly.express as px
import pandas as pd

from flux_notebooks.bids.summarize_bids import summarize_bids

dash.register_page(__name__, path="/bids", name="BIDS Summary")

# ── Locate dataset root robustly ─────────────────────────────────────────────
DATASET_ROOT = Path(os.environ.get("FLUX_DATASET_ROOT", "superdemo_real")).resolve()

# Prefer nested /bids if it exists
if (DATASET_ROOT / "bids" / "dataset_description.json").exists():
    BIDS_ROOT = DATASET_ROOT / "bids"
elif (DATASET_ROOT / "dataset_description.json").exists():
    BIDS_ROOT = DATASET_ROOT
else:
    print(f"[WARN] No BIDS dataset found under {DATASET_ROOT}")
    BIDS_ROOT = None

# ── Summarize dataset safely ────────────────────────────────────────────────
if BIDS_ROOT and BIDS_ROOT.exists():
    print(f"[BIDS] Using root: {BIDS_ROOT}")
    SUMMARY = summarize_bids(BIDS_ROOT)
else:
    SUMMARY = {
        "avail": pd.DataFrame(),
        "func_counts": pd.DataFrame(),
        "tr_by_task": pd.DataFrame(),
    }

# Coerce distinct_TRs column for display
if SUMMARY.get("tr_by_task") is not None and not SUMMARY["tr_by_task"].empty:
    tr_df = SUMMARY["tr_by_task"].copy()
    if "distinct_TRs" in tr_df.columns:
        tr_df["distinct_TRs"] = tr_df["distinct_TRs"].astype(str)
    SUMMARY["tr_by_task"] = tr_df


# ── UI helpers ───────────────────────────────────────────────────────────────
def card(children, style_extra=None):
    base = {
        "background": "rgba(255,255,255,0.04)",  # looks good on dark themes
        "padding": "14px",
        "borderRadius": "12px",
        "border": "1px solid rgba(255,255,255,0.08)",
    }
    if style_extra:
        base.update(style_extra)
    return html.Div(children, style=base)


grid2 = {"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px"}
grid1 = {"display": "grid", "gridTemplateColumns": "1fr", "gap": "16px"}


def make_table(title: str, df: pd.DataFrame | None, page_size: int = 10):
    if df is None or df.empty:
        return card(html.Div(f"No data for {title}", style={"color": "#9ca3af"}))
    return card(
        dash_table.DataTable(
            data=df.to_dict("records"),
            columns=[{"name": c, "id": c} for c in df.columns],
            page_size=page_size,
            style_table={"overflowX": "auto"},
            style_header={
                "backgroundColor": "rgba(255,255,255,0.06)",
                "fontWeight": "700",
                "border": "none",
            },
            style_cell={
                "backgroundColor": "rgba(0,0,0,0)",
                "color": "#e5e7eb",
                "borderBottom": "1px solid rgba(255,255,255,0.06)",
                "padding": "8px",
                "fontSize": "14px",
            },
        )
    )


# ── Plot helpers (robust to different shapes) ────────────────────────────────
def _fig_availability(avail: pd.DataFrame | None):
    """Stacked bar of available files per datatype for each subject."""
    if avail is None or avail.empty:
        return None
    df = avail.reset_index().rename(columns={"index": "sub"})  # ensure 'sub'
    long = df.melt(id_vars=["sub"], var_name="datatype", value_name="count")
    fig = px.bar(long, x="sub", y="count", color="datatype", barmode="stack")
    fig.update_layout(
        title="Availability by datatype",
        margin=dict(l=10, r=10, t=40, b=10),
        height=420,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend_title_text="datatype",
    )
    return fig


def _as_task_counts(obj: pd.DataFrame | pd.Series | None) -> pd.DataFrame | None:
    """Normalize 'runs per task' into a two-column DataFrame: (task, count)."""
    if obj is None:
        return None

    if isinstance(obj, pd.Series):
        d = obj.reset_index()
        if d.shape[1] == 2:
            d.columns = ["task", "count"]
        else:
            d = d.rename(columns={d.columns[0]: "task"})
            d["count"] = obj.values
        return d[["task", "count"]]

    if not isinstance(obj, pd.DataFrame) or obj.empty:
        return None

    d = obj.copy()

    if "task" not in d.columns:
        d = d.reset_index()
        if "task" not in d.columns:
            d = d.rename(columns={d.columns[0]: "task"})

    if "count" not in d.columns:
        numcols = [
            c for c in d.columns if c != "task" and pd.api.types.is_numeric_dtype(d[c])
        ]
        if numcols:
            d = d.rename(columns={numcols[0]: "count"})
        else:
            # last resort: count rows per task
            d = d.groupby("task", as_index=False).size().rename(columns={"size": "count"})

    return d[["task", "count"]]


def _fig_runs_per_task(obj):
    d = _as_task_counts(obj)
    if d is None or d.empty:
        return None
    d = d.sort_values("count", ascending=False)
    fig = px.bar(d, x="task", y="count")
    fig.update_layout(
        title="Functional runs per task",
        margin=dict(l=10, r=10, t=40, b=10),
        height=420,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(tickangle=-35)
    return fig


# ── Build figures (won’t crash if sections are missing) ──────────────────────
fig_avail = _fig_availability(SUMMARY.get("avail"))
fig_runs = _fig_runs_per_task(SUMMARY.get("func_counts"))

# ── Page layout ───────────────────────────────────────────────────────────────
layout = html.Div(
    [
        html.H2("BIDS Summary", style={"margin": "6px 0 12px 0"}),
        # Availability section
        card(
            [
                html.H4("Availability overview", style={"marginTop": 0}),
                html.Div(
                    [
                        card(
                            dcc.Graph(figure=fig_avail)
                            if fig_avail
                            else html.Div("No plot available", style={"color": "#9ca3af"})
                        ),
                        make_table("Availability by datatype", SUMMARY.get("avail")),
                    ],
                    style=grid2,
                ),
            ]
        ),
        html.Div(style={"height": "14px"}),

        # Runs per task
        card(
            [
                html.H4("Functional runs per task", style={"marginTop": 0}),
                dcc.Graph(figure=fig_runs)
                if fig_runs
                else html.Div("No functional runs to show", style={"color": "#9ca3af"}),
            ]
        ),
        html.Div(style={"height": "14px"}),

        # TR summary table
        card(
            [
                html.H4("TR summary by task", style={"marginTop": 0}),
                make_table("TR summary by task", SUMMARY.get("tr_by_task"), page_size=8),
            ]
        ),
    ],
    style={"display": "grid", "gap": "16px"},
)
