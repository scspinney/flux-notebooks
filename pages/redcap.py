# pages/redcap.py
import os
from pathlib import Path

import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc

from flux_notebooks.redcap.summarize_redcap import summarize_redcap
from flux_notebooks.pages.redcap_helpers import (
    fig_or_msg,
    card,
    kpi,
    fmt_pct,
    GRID_STYLES,
    TAB_STYLES,
)

dash.register_page(__name__, path="/redcap", name="REDCap Summary")

# ── Load datasets (safe fallback if env var isn't set) ────────────────────────
DATASET_ROOT = Path(os.environ.get("FLUX_REDCAP_ROOT", "data/redcap")).resolve()
try:
    _summary = summarize_redcap(DATASET_ROOT)
    FIGS = _summary.get("figures", {}) or {}
    COUNTS = _summary.get("counts", None)
    COUNTS_NA = _summary.get("counts_na", None)
except Exception as e:
    FIGS, COUNTS, COUNTS_NA = {}, None, None
    _load_error = f"Failed to summarize REDCap data at {DATASET_ROOT}: {e}"
else:
    _load_error = None

# Unpack styles for convenience
grid1 = GRID_STYLES["grid1"]
grid2 = GRID_STYLES["grid2"]
grid3 = GRID_STYLES["grid3"]
grid_wrap = GRID_STYLES["grid_wrap"]
tab_style = TAB_STYLES["default"]
tab_selected_style = TAB_STYLES["selected"]


# Compute a few top-line KPIs from COUNTS / COUNTS_NA if available
# kpi_cards = []
# if COUNTS is not None:
#     try:
#         total_enrolled = int(COUNTS["Total available counts"].sum())
#         sites = ", ".join(list(COUNTS.index.astype(str)))

#         def _get(col):
#             return int(COUNTS_NA[col].sum()) if (COUNTS_NA is not None and col in COUNTS_NA) else 0

#         age_na = _get("Age NA")
#         sex_na = _get("Sex NA")
#         eth_na = _get("Ethnicity NA")
#         kpi_cards = [
#             _kpi(f"{total_enrolled}", "Total baseline participants", f"Sites: {sites}"),
#             _kpi(f"{age_na}", "Age missing (N)", sub=_fmt_pct(age_na, total_enrolled)),
#             _kpi(f"{sex_na}", "Sex missing (N)", sub=_fmt_pct(sex_na, total_enrolled)),
#             _kpi(f"{eth_na}", "Ethnicity missing (N)", sub=_fmt_pct(eth_na, total_enrolled)),
#         ]
#     except Exception:
#         kpi_cards = []

# ── Layout ────────────────────────────────────────────────────────────────────
layout = html.Div(
    style={
        "fontFamily": "system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial",
        "padding": "20px",
    },
    children=[
        # Header
        html.H2("REDCap Summary", style={"textAlign": "center", "margin": "6px 0 2px 0"}),
        html.Div(
            "A narrative view of cohort recruitment, equity targets, timelines, and early mental-health insights.",
            style={"textAlign": "center", "color": "#6b7280", "marginBottom": "14px"},
        ),
        # html.Div(
        #     f"Data root: {DATASET_ROOT}",
        #     style={"textAlign": "center", "color": "#9ca3af", "fontSize": "12px", "marginBottom": "10px"},
        # ),

        # Error banner (if any)
        *([card(html.Div(_load_error, style={"color": "#b91c1c"}))] if _load_error else []),

        # KPIs (responsive)
        #html.Div(style=grid_wrap, children=kpi_cards) if kpi_cards else html.Div(),

        html.Div(style={"height": "12px"}),

        # Quick filters row (kept for future callbacks; non-blocking UI)
        # card(
        #     [
        #         html.Div(
        #             style=grid3,
        #             children=[
        #                 html.Div(
        #                     [
        #                         html.Label("Site", style={"fontWeight": 600}),
        #                         dcc.Dropdown(
        #                             id="redcap-filter-site",
        #                             options=[
        #                                 {"label": s, "value": s}
        #                                 for s in (COUNTS.index.tolist() if COUNTS is not None else ["Calgary", "Montreal", "Toronto"])
        #                             ],
        #                             placeholder="All sites",
        #                             multi=True,
        #                             className="flux-input",
        #                         ),
        #                     ]
        #                 ),
        #                 html.Div(
        #                     [
        #                         html.Label("Age group", style={"fontWeight": 600}),
        #                         dcc.Dropdown(
        #                             id="redcap-filter-age",
        #                             options=[{"label": a, "value": a} for a in ["0-2", "2-5", "6-9", "10-12", "13-15", "16-18"]],
        #                             placeholder="All age groups",
        #                             multi=True,
        #                             className="flux-input",
        #                         ),
        #                     ]
        #                 ),
        #                 html.Div(
        #                     [
        #                         html.Label("Show", style={"fontWeight": 600}),
        #                         dcc.Checklist(
        #                             id="redcap-filter-show",
        #                             options=[
        #                                 {"label": " Targets", "value": "Target"},
        #                                 {"label": " Observed", "value": "Observed"},
        #                             ],
        #                             value=["Target", "Observed"],
        #                             inline=True,
        #                         ),
        #                     ]
        #                 ),
        #             ],
        #         ),
        #         html.Div(
        #             "Filters are present for future callbacks; current figures reflect the full cohort.",
        #             style={"color": "#9ca3af", "fontSize": "12px", "marginTop": "6px"},
        #         ),
        #     ]
        # ),

        html.Div(style={"height": "16px"}),

        # ── Tabs organized by research questions ───────────────────────────────
        dcc.Tabs(
            colors={"border": "#e5e7eb", "primary": "#2563eb", "background": "#ffffff"},
            children=[
                # 1) Recruitment & Targets
                dcc.Tab(
                    label="Recruitment & Targets",
                    style=tab_style,
                    selected_style=tab_selected_style,
                    children=[
                        # Overview (stacked vertically)
                        html.Div(
                            style={"display": "grid", "gridTemplateColumns": "1fr", "gap": "16px"},
                            children=[
                                card(
                                    [
                                        html.H4("Observed vs Target — Age × Sex (per site)", style={"marginTop": 0}),
                                        fig_or_msg("overlay_age_sex", "Targets not found or observed Sex×Age empty", FIGS, FIGS,
                                            height=650,
                                        ),
                                    ]
                                ),
                                card(
                                    [
                                        html.H4("Observed vs Target — Ethnicity totals (per site)", style={"marginTop": 0}),
                                        fig_or_msg("overlay_ethnicity_totals", "No totals comparison available", FIGS, FIGS,
                                            height=650,
                                        ),
                                    ],
                                    style_extra={"marginTop": "1rem"},
                                ),
                            ],
                        ),
                        html.Div(style={"height": "12px"}),

                        # Deep-dive (collapsible)
                        card(
                            [
                                html.Div(
                                    [
                                        html.H4("Deep-dive: Observed vs Target — Age × Ethnicity", style={"margin": "0"}),
                                        html.Div(
                                            [
                                                html.Button(
                                                    "Show / Hide deep-dive",
                                                    id="redcap-toggle-ageeth",
                                                    n_clicks=0,
                                                    style={
                                                        "border": "1px solid #e5e7eb",
                                                        "background": "#f9fafb",
                                                        "padding": "6px 10px",
                                                        "borderRadius": "8px",
                                                        "cursor": "pointer",
                                                        "fontWeight": 600,
                                                        "marginTop": "8px",
                                                    },
                                                )
                                            ],
                                            style={"textAlign": "right"},
                                        ),
                                    ],
                                    style={"display": "flex", "alignItems": "baseline", "justifyContent": "space-between"},
                                ),
                                dbc.Collapse(
                                    id="redcap-ageeth-collapse",
                                    is_open=False,
                                    children=[
                                        html.Div(style={"height": "10px"}),
                                        fig_or_msg("overlay_age_ethnicity", "Targets not found or observed Ethnicity×Age empty", FIGS, FIGS,
                                            height=900,
                                            style_extra={"overflowX": "auto"},
                                        ),
                                    ],
                                ),
                            ]
                        ),
                    ],
                ),

                # 2) Equity & Representation
                dcc.Tab(
                    label="Equity & Representation",
                    style=tab_style,
                    selected_style=tab_selected_style,
                    children=[
                        html.Div(
                            style=grid1,
                            children=[
                                card(
                                    [html.H4("Age groups by site (baseline)", style={"marginTop": 0}), fig_or_msg("age", "No age data available", FIGS, FIGS, height=420)]
                                ),
                                card(
                                    [html.H4("Sex distribution by site", style={"marginTop": 0}), fig_or_msg("sex", "No sex data available", FIGS, FIGS, height=420)]
                                ),
                                card(
                                    [html.H4("Gender identity by site", style={"marginTop": 0}), fig_or_msg("gender", "No gender data available", FIGS, FIGS, height=420)]
                                ),
                                card(
                                    [html.H4("Ethnicity (all labels)", style={"marginTop": 0}), fig_or_msg("ethnicity_full", "No ethnicity data available", FIGS, FIGS, height=420)]
                                ),
                                card(
                                    [
                                        html.H4("Ethnicity (White / Non-white) by site", style={"marginTop": 0}),
                                        fig_or_msg("ethnicity_white_nonwhite", "No white/non-white data available", FIGS, FIGS, height=420),
                                    ]
                                ),
                                card(
                                    [html.H4("Household income (baseline)", style={"marginTop": 0}), fig_or_msg("income", "No income data available", FIGS, FIGS, height=420)]
                                ),
                            ],
                        ),
                    ],
                ),

                # 3) Timeline & Data Quality
                dcc.Tab(
                    label="Timeline & Data Quality",
                    style=tab_style,
                    selected_style=tab_selected_style,
                    children=[
                        html.Div(
                            style=grid1,
                            children=[
                                card(
                                    [html.H4("Baseline MRI visits by site", style={"marginTop": 0}), fig_or_msg("mri_timeline", "No MRI timeline available", FIGS, FIGS, height=440)]
                                ),
                                card(
                                    [html.H4("Missing counts per panel", style={"marginTop": 0}), fig_or_msg("missing_counts", "No NA summary available", FIGS, FIGS, height=440)]
                                ),
                            ],
                        ),
                    ],
                ),

                # 4) Mental Health Insights
                dcc.Tab(
                    label="Mental Health Insights",
                    style=tab_style,
                    selected_style=tab_selected_style,
                    children=[
                        html.Div(
                            style=grid1,
                            children=[
                                html.Div(
                                    children=[
                                        html.H4("Diagnoses (counts)", style={"marginTop": 0}),
                                        fig_or_msg("mh_bar", "No CFQ diagnosis variables present", FIGS, FIGS, height=360),
                                        html.Div(style={"height": "8px"}),
                                        fig_or_msg("mh_heatmap_with_nodx", "Heatmap unavailable", FIGS, FIGS, height=400),
                                    ],
                                    style={"display": "grid", "gridTemplateRows": "auto auto auto"},
                                ),
                                html.Div(
                                    children=[
                                        html.H4("Correlations & Co-occurrence", style={"marginTop": 0}),
                                        fig_or_msg("mh_corr", "Correlation matrix unavailable", FIGS, FIGS, height=400),
                                        html.Div(style={"height": "8px"}),
                                        fig_or_msg("mh_cooccurrence", "Co-occurrence matrix unavailable", FIGS, FIGS, height=400),
                                    ],
                                    style={"display": "grid", "gridTemplateRows": "auto auto auto"},
                                ),
                            ],
                        )
                    ],
                ),
            ],
        ),
    ],
)

# ── Callbacks (UI-only; no data filtering yet) ────────────────────────────────
@callback(
    Output("redcap-ageeth-collapse", "is_open"),
    Input("redcap-toggle-ageeth", "n_clicks"),
    State("redcap-ageeth-collapse", "is_open"),
)
def _toggle_age_eth(n, is_open):
    if not n:
        return False
    return not is_open
