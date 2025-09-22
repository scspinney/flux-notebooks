# pages/redcap.py
import os
from pathlib import Path
import dash
from dash import html, dcc

from flux_notebooks.redcap.summarize_redcap import summarize_redcap

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


# ── Small helpers ─────────────────────────────────────────────────────────────
def _height_to_css(height):
    if height is None:
        return "calc(100vh - 260px)"
    if isinstance(height, int):
        return f"{height}px"
    return str(height)


def fig_or_msg(key: str, msg: str, height: int | str | None = 430, style_extra=None):
    fig = FIGS.get(key)
    style = {"height": _height_to_css(height)}
    if style_extra:
        style.update(style_extra)
    if fig is not None and getattr(fig, "data", None):  # non-empty figure
        return dcc.Graph(figure=fig, style=style, config={"displaylogo": False})
    return html.Div(
        msg,
        style={
            **style,
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center",
            "color": "#6b7280",           # slate-500
            "background": "#f8fafc",      # slate-50
            "border": "1px dashed #e5e7eb",
            "borderRadius": "10px",
        },
    )


def card(children, style_extra=None):
    base = {
        "background": "white",
        "padding": "16px",
        "borderRadius": "12px",
        "border": "1px solid #e5e7eb",
    }
    if style_extra:
        base.update(style_extra)
    return html.Div(children, className="shadow-sm", style=base)


# 2-col responsive grid (falls back to 1-col on narrow screens)
grid2 = {"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px"}
grid3 = {"display": "grid", "gridTemplateColumns": "1fr 1fr 1fr", "gap": "16px"}
grid1 = {"display": "grid", "gridTemplateColumns": "1fr", "gap": "16px"}

# Tabs styles
tab_style = {
    "padding": "10px 14px",
    "fontWeight": 600,
    "color": "#111827",
    "background": "#f3f4f6",
    "border": "1px solid #e5e7eb",
    "borderBottom": "none",
    "borderRadius": "10px 10px 0 0",
}
tab_selected_style = {**tab_style, "background": "#ffffff", "borderTop": "3px solid #2563eb"}

# ── KPI helpers ───────────────────────────────────────────────────────────────
def _kpi(value, label, sub=None):
    return card(
        [
            html.Div(f"{value}", style={"fontSize": "28px", "fontWeight": 800}),
            html.Div(label, style={"color": "#6b7280", "fontSize": "13px"}),
            html.Div(sub or "", style={"color": "#9ca3af", "fontSize": "12px", "marginTop": "4px"}),
        ],
        style_extra={"padding": "14px 16px"},
    )

def _fmt_pct(num, den):
    try:
        if den <= 0:
            return "—"
        return f"{(100.0 * num / den):.0f}%"
    except Exception:
        return "—"

# Compute a few top-line KPIs from COUNTS / COUNTS_NA if available
kpi_cards = []
if COUNTS is not None:
    try:
        total_enrolled = int(COUNTS["Total available counts"].sum())
        sites = ", ".join(list(COUNTS.index.astype(str)))
        # NA rates (overall across sites)
        def _get(col):
            return int(COUNTS_NA[col].sum()) if (COUNTS_NA is not None and col in COUNTS_NA) else None
        age_na = _get("Age NA") or 0
        sex_na = _get("Sex NA") or 0
        eth_na = _get("Ethnicity NA") or 0
        kpi_cards = [
            _kpi(f"{total_enrolled}", "Total baseline participants", f"Sites: {sites}"),
            _kpi(f"{age_na}", "Age missing (N)", sub=_fmt_pct(age_na, total_enrolled)),
            _kpi(f"{sex_na}", "Sex missing (N)", sub=_fmt_pct(sex_na, total_enrolled)),
            _kpi(f"{eth_na}", "Ethnicity missing (N)", sub=_fmt_pct(eth_na, total_enrolled)),
        ]
    except Exception:
        kpi_cards = []

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
            "A narrative view of cohort status, equity targets, timelines, and early mental-health insights.",
            style={"textAlign": "center", "color": "#6b7280", "marginBottom": "18px"},
        ),
        html.Div(
            f"Data root: {DATASET_ROOT}",
            style={"textAlign": "center", "color": "#9ca3af", "fontSize": "12px", "marginBottom": "10px"},
        ),

        # Error banner (if any)
        *([card(html.Div(_load_error, style={"color": "#b91c1c"}))] if _load_error else []),

        # KPIs
        html.Div(style=grid3, children=kpi_cards) if kpi_cards else html.Div(),

        html.Div(style={"height": "12px"}),

        # Quick filters row (non-blocking placeholders; future wiring)
        card(
            [
                html.Div(
                    style=grid3,
                    children=[
                        html.Div(
                            [
                                html.Label("Site", style={"fontWeight": 600}),
                                dcc.Dropdown(
                                    id="redcap-filter-site",
                                    options=[{"label": s, "value": s} for s in (COUNTS.index.tolist() if COUNTS is not None else ["Calgary","Montreal","Toronto"])],
                                    placeholder="All sites",
                                    multi=True,
                                ),
                            ]
                        ),
                        html.Div(
                            [
                                html.Label("Age group", style={"fontWeight": 600}),
                                dcc.Dropdown(
                                    id="redcap-filter-age",
                                    options=[{"label": a, "value": a} for a in ["0-2","2-5","6-9","10-12","13-15","16-18"]],
                                    placeholder="All age groups",
                                    multi=True,
                                ),
                            ]
                        ),
                        html.Div(
                            [
                                html.Label("Show", style={"fontWeight": 600}),
                                dcc.Checklist(
                                    id="redcap-filter-show",
                                    options=[
                                        {"label": " Targets", "value": "Target"},
                                        {"label": " Observed", "value": "Observed"},
                                    ],
                                    value=["Target","Observed"],
                                    inline=True,
                                ),
                            ]
                        ),
                    ],
                ),
                html.Div(
                    "Filters are present for future callbacks; current figures reflect the full cohort.",
                    style={"color": "#9ca3af", "fontSize": "12px", "marginTop": "6px"},
                ),
            ]
        ),

        html.Div(style={"height": "16px"}),

        # ── Tabs organized by research questions ───────────────────────────────
        dcc.Tabs(
            colors={"border": "#e5e7eb", "primary": "#2563eb", "background": "#ffffff"},
            children=[
                # 1) Recruitment & Targets
                dcc.Tab(
                    label="Recruitment & Targets",
                    style=tab_style, selected_style=tab_selected_style,
                    children=[
                        html.Div(
                            style=grid2,
                            children=[
                                card([html.H4("Observed vs Target — Age × Sex", style={"marginTop": 0}),
                                      fig_or_msg("overlay_age_sex", "Targets not found or observed Sex×Age empty", height=720)]),
                                card([html.H4("Observed vs Target — Ethnicity totals", style={"marginTop": 0}),
                                      fig_or_msg("overlay_ethnicity_totals", "No totals comparison available", height=520)]),
                            ],
                        ),
                        html.Div(style={"height": "12px"}),
                        card([html.H4("Observed vs Target — Age × Ethnicity", style={"marginTop": 0}),
                              fig_or_msg("overlay_age_ethnicity", "Targets not found or observed Ethnicity×Age empty", height=1500, style_extra={"overflowX": "auto"})]),
                    ],
                ),

                # 2) Equity & Representation
                dcc.Tab(
                    label="Equity & Representation",
                    style=tab_style, selected_style=tab_selected_style,
                    children=[
                        html.Div(
                            style=grid2,
                            children=[
                                card([html.H4("Age groups by site (baseline)", style={"marginTop": 0}),
                                      fig_or_msg("age", "No age data available", height=430)]),
                                card([html.H4("Sex distribution by site", style={"marginTop": 0}),
                                      fig_or_msg("sex", "No sex data available", height=430)]),
                                card([html.H4("Gender identity by site", style={"marginTop": 0}),
                                      fig_or_msg("gender", "No gender data available", height=430)]),
                                card([html.H4("Ethnicity (all labels)", style={"marginTop": 0}),
                                      fig_or_msg("ethnicity_full", "No ethnicity data available", height=430)]),
                                card([html.H4("Ethnicity (White / Non-white) by site", style={"marginTop": 0}),
                                      fig_or_msg("ethnicity_white_nonwhite", "No white/non-white data available", height=430)]),
                                card([html.H4("Household income (baseline)", style={"marginTop": 0}),
                                      fig_or_msg("income", "No income data available", height=430)]),
                            ],
                        ),
                    ],
                ),

                # 3) Timeline & Data Quality
                dcc.Tab(
                    label="Timeline & Data Quality",
                    style=tab_style, selected_style=tab_selected_style,
                    children=[
                        html.Div(
                            style=grid2,
                            children=[
                                card([html.H4("Baseline MRI visits by site", style={"marginTop": 0}),
                                      fig_or_msg("mri_timeline", "No MRI timeline available", height=460)]),
                                card([html.H4("Missing counts per panel", style={"marginTop": 0}),
                                      fig_or_msg("missing_counts", "No NA summary available", height=460)]),
                            ],
                        ),
                    ],
                ),

                # 4) Mental Health Insights
                dcc.Tab(
                    label="Mental Health Insights",
                    style=tab_style, selected_style=tab_selected_style,
                    children=[
                        html.Div(
                            style=grid2,
                            children=[
                                html.Div(
                                    children=[
                                        html.H4("Diagnoses (counts)", style={"marginTop": 0}),
                                        fig_or_msg("mh_bar", "No CFQ diagnosis variables present", height=380),
                                        html.Div(style={"height": "8px"}),
                                        fig_or_msg("mh_heatmap_with_nodx", "Heatmap unavailable", height=420),
                                    ],
                                    style={"display": "grid", "gridTemplateRows": "auto auto auto"},
                                ),
                                html.Div(
                                    children=[
                                        html.H4("Correlations & Co-occurrence", style={"marginTop": 0}),
                                        fig_or_msg("mh_corr", "Correlation matrix unavailable", height=420),
                                        html.Div(style={"height": "8px"}),
                                        fig_or_msg("mh_cooccurrence", "Co-occurrence matrix unavailable", height=420),
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
