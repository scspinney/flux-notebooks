import dash
from dash import html, dcc
from pathlib import Path
import os
import pandas as pd
from datetime import datetime
import dash_bootstrap_components as dbc
import urllib.parse

from flux_notebooks.redcap.summarize_targets import summarize_modalities
from flux_notebooks.bids.summarize_bids import summarize_bids
from flux_notebooks.freesurfer.summarize_freesurfer import summarize_freesurfer
from flux_notebooks.theme import SITE_COLORS
from flux_notebooks.redcap.summarize_redcap import summarize_redcap
from flux_notebooks.pages.home_helpers import (
    summarize_sessions,
    modality_icon_src,
    redcap_fig_or_msg,
    redcap_card,
    make_pie,
    make_modality_summary,
    make_info_panel,
)

dash.register_page(__name__, path="/", name="Home")

# ---------------------------------------------------------------------
# Site mapping and dataset paths
# ---------------------------------------------------------------------
SITE_MAP = {"montreal": "Montreal", "calgary": "Calgary", "toronto": "Toronto"}

dataset_root = Path(os.environ.get("FLUX_DATASET_ROOT", "superdemo_real")).resolve()
bids_root = (
    dataset_root
    if (dataset_root / "dataset_description.json").exists()
    else (dataset_root / "bids")
).resolve()
fs_root = dataset_root / "derivatives" / "freesurfer"

# ---------------------------------------------------------------------
# Inline CSS
# ---------------------------------------------------------------------
GLOBAL_STYLE = dcc.Markdown(
    """
    <style>
    body {
      font-family: 'Inter', sans-serif;
      background-color: #f8f9fa;
    }
    .page-transition { animation: fadeSlideIn 0.6s ease-out forwards; }
    @keyframes fadeSlideIn { from {opacity:0; transform:translateY(15px);} to {opacity:1; transform:translateY(0);} }
    .card-fade { opacity:0; transform:translateY(10px); animation: fadeInUp 0.7s ease forwards; }
    @keyframes fadeInUp { from {opacity:0; transform:translateY(15px);} to {opacity:1; transform:translateY(0);} }
    .glass-card {
      background: linear-gradient(145deg, #ffffff, #f3f3f3);
      border: 1px solid rgba(255,255,255,0.25);
      backdrop-filter: blur(8px);
      border-radius: 12px;
      box-shadow: 0 3px 6px rgba(0,0,0,0.08);
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .glass-card:hover { transform: translateY(-4px); box-shadow: 0 8px 18px rgba(0,0,0,0.15); }
    .site-line { height: 4px; width: 40%; margin: 0 auto 15px; border-radius: 2px; }
    </style>
    """,
    dangerously_allow_html=True,
)

# ---------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------
def layout():
    participants_tsv = bids_root / "participants.tsv"
    session_summary = summarize_sessions(bids_root, participants_tsv)
    last_updated = datetime.fromtimestamp(dataset_root.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    # REDCap data (reuse from redcap page)
    redcap_root = Path(os.environ.get("FLUX_REDCAP_ROOT", "data/redcap")).resolve()
    try:
        redcap_summary = summarize_redcap(redcap_root)
        redcap_figs = redcap_summary.get("figures", {}) or {}
        redcap_error = None
    except Exception as e:
        redcap_figs = {}
        redcap_error = f"Failed to summarize REDCap data at {redcap_root}: {e}"

    # Timepoint tabs (recruitment)
    def make_timepoint_tab(label, key):
        ses_data = session_summary.get(key, {})
        total_obs = ses_data.get("total", 0)
        total_tgt = 263 * len(SITE_MAP)
        overall_pie = make_pie(f"{label} Overall", total_obs, total_tgt, SITE_COLORS, emphasize=True)
        site_pies = [make_pie(site, ses_data.get("sites", {}).get(site, 0), 263, SITE_COLORS) for site in SITE_MAP.values()]
        return dbc.Tab(label=label, tab_id=key,
                       children=html.Div(style={"display": "flex", "justifyContent": "center", "alignItems": "flex-start", 
                                                "gap": "45px", "flexWrap": "wrap", "marginTop": "25px"},
                                         children=[overall_pie] + site_pies))

    # Modality tabs (restored!)
    def make_modality_tab(label, session_suffix):
        participants_tsv = bids_root / "participants.tsv"
        site_map = {}
        if participants_tsv.exists():
            try:
                df = pd.read_csv(participants_tsv, sep="\t")
                if "participant_id" in df.columns and "site_name" in df.columns:
                    site_map = dict(zip(df["participant_id"], df["site_name"]))
            except Exception as e:
                print(f"[WARN] Failed to read participants.tsv: {e}")

        site_data = []
        for site_label in SITE_MAP.values():
            modalities = {}
            site_subjects = [s for s, site in site_map.items() if site.lower() == site_label.lower()]
            total = len(site_subjects)
            for mod in ["T1W", "T2W", "task-partlycloudy", "task-laluna", "DWI"]:
                count = sum(1 for sub in site_subjects
                            if (bids_root / sub / f"ses-{session_suffix}").exists()
                            and any(mod.lower() in f.name.lower() for f in (bids_root / sub / f"ses-{session_suffix}").rglob("*.nii*")))
                modalities[mod] = count
            site_data.append({"site": site_label, "counts": modalities, "total": total})

        # Build a clean aligned grid: one icon+label column, counts columns per site.
        modality_order = ["T1W", "T2W", "task-partlycloudy", "task-laluna", "DWI"]

        left_column = html.Div(
            style={
                "display": "flex",
                "flexDirection": "column",
                "gap": "12px",
                "padding": "6px 0",
                "minWidth": "230px",
            },
            children=[html.Div(style={"height": "32px"})]  # spacer aligns with site headers
            + [
                html.Div(
                    style={
                        "display": "flex",
                        "alignItems": "center",
                        "gap": "14px",
                        "padding": "10px 12px",
                        "background": "#f8fafc",
                        "borderRadius": "14px",
                        "boxShadow": "inset 0 1px 2px rgba(0,0,0,0.06)",
                        "height": "110px",
                    },
                    children=[
                        html.Img(
                            src=modality_icon_src(mod),
                            style={"width": "120px", "height": "82px", "borderRadius": "12px", "flexShrink": 0},
                        ),
                        html.Span(
                            {"task-partlycloudy": "task-partlycloudy", "task-laluna": "task-laluna"}.get(mod, mod),
                            style={"fontWeight": "700", "color": "#111827", "fontSize": "16px"},
                        ),
                    ],
                )
                for mod in modality_order
            ],
        )

        site_columns = []
        for site_info in site_data:
            site_label = site_info["site"]
            counts_lookup = site_info["counts"]
            total = site_info["total"]
            site_columns.append(
                html.Div(
                    style={
                        "display": "flex",
                        "flexDirection": "column",
                        "gap": "12px",
                        "padding": "6px 0",
                        "minWidth": "180px",
                        "alignItems": "stretch",
                    },
                    children=[
                        html.Div(
                            site_label,
                            style={
                                "textAlign": "center",
                                "fontWeight": "800",
                                "color": SITE_COLORS.get(site_label, "#111"),
                                "paddingBottom": "4px",
                            },
                        ),
                        *[
                            html.Div(
                                f"{counts_lookup.get(mod,0)} / {total}",
                                style={
                                    "textAlign": "center",
                                    "padding": "0 8px",
                                    "background": "linear-gradient(135deg, #ffffff 0%, #f5f5f5 100%)",
                                    "borderRadius": "14px",
                                    "boxShadow": "inset 0 1px 2px rgba(0,0,0,0.05)",
                                    "fontWeight": "700",
                                    "color": SITE_COLORS.get(site_label, "#111") if counts_lookup.get(mod,0) else "#9ca3af",
                                    "display": "flex",
                                    "alignItems": "center",
                                    "justifyContent": "center",
                                    "height": "110px",
                                },
                            )
                            for mod in modality_order
                        ],
                    ],
                )
            )

        return dbc.Tab(
            label=label,
            tab_id=f"mod-{session_suffix}",
            children=html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "center",
                    "alignItems": "flex-start",
                    "gap": "18px",
                    "marginTop": "25px",
                    "flexWrap": "nowrap",
                    "overflowX": "auto",
                    "paddingBottom": "10px",
                },
                children=[left_column] + site_columns,
            ),
        )

    timepoint_tabs = dbc.Tabs(
        [make_timepoint_tab("Baseline", "baseline"),
         make_timepoint_tab("Follow-up 1", "followup1"),
         make_timepoint_tab("Follow-up 2", "followup2")],
        id="timepoint-tabs", active_tab="baseline", style={"marginTop": "10px"},
    )

    modality_tabs = dbc.Tabs(
        [make_modality_tab("Baseline", "1a"),
         make_modality_tab("Follow-up 1", "2a"),
         make_modality_tab("Follow-up 2", "3a")],
        id="modality-tabs", active_tab="mod-1a", style={"marginTop": "10px"},
    )

    return html.Div(
        className="page-transition",
        style={"fontFamily": "Inter, sans-serif", "margin": "20px auto", "maxWidth": "1400px"},
        children=[
            GLOBAL_STYLE,
            html.H1("Welcome to BIDS-Flux Dashboards", style={"marginBottom": "5px"}),
            html.P("C-PIP study overview", style={"marginBottom": "25px"}),

            html.Div(style={"textAlign": "center", "marginTop": "30px"},
                     children=[html.H4("Study Recruitment by Timepoint", style={"marginBottom": "15px"}),
                               timepoint_tabs]),

            html.Div(style={"marginTop": "50px", "textAlign": "center"},
                     children=[html.H3("Imaging Modality Coverage by Site", style={"marginBottom": "5px"}),
                               html.P("Each card shows how many subjects at each site have each modality for the selected timepoint.",
                                      style={"color": "#6b7280", "fontSize": "16px",
                                             "marginBottom": "25px", "maxWidth": "800px", "margin": "0 auto"}),
                               modality_tabs]),

            # -----------------------------------------------------------------
            # REDCap summary (embedded)
            # -----------------------------------------------------------------
            html.Div(
                style={"marginTop": "60px", "textAlign": "center"},
                children=[
                    html.H3("REDCap Summary", style={"marginBottom": "6px"}),
                    html.P(
                        "Recruitment, equity, timelines, and mental-health insights from REDCap.",
                        style={"color": "#6b7280", "fontSize": "15px", "marginBottom": "18px"},
                    ),
                    *( [redcap_card(html.Div(redcap_error, style={"color": "#b91c1c"}))] if redcap_error else [] ),
                    dcc.Tabs(
                        colors={"border": "#e5e7eb", "primary": "#2563eb", "background": "#ffffff"},
                        children=[
                            dcc.Tab(
                                label="Recruitment & Targets",
                                children=[
                                    redcap_card(
                                        [
                                            html.H4("Observed vs Target — Age × Sex (per site)", style={"marginTop": 0}),
                                            redcap_fig_or_msg(redcap_figs, "overlay_age_sex", "Targets not found or observed Sex×Age empty", height=650),
                                        ]
                                    ),
                                    redcap_card(
                                        [
                                            html.H4("Observed vs Target — Ethnicity totals (per site)", style={"marginTop": 0}),
                                            redcap_fig_or_msg(redcap_figs, "overlay_ethnicity_totals", "No totals comparison available", height=650),
                                        ],
                                        style_extra={"marginTop": "1rem"},
                                    ),
                                    redcap_card(
                                        [
                                            html.H4("Deep-dive: Observed vs Target — Age × Ethnicity", style={"marginTop": 0}),
                                            redcap_fig_or_msg(
                                                redcap_figs,
                                                "overlay_age_ethnicity",
                                                "Targets not found or observed Ethnicity×Age empty",
                                                height=900,
                                                style_extra={"overflowX": "auto"},
                                            ),
                                        ],
                                        style_extra={"marginTop": "1rem"},
                                    ),
                                ],
                            ),
                            dcc.Tab(
                                label="Equity & Representation",
                                children=[
                                    html.Div(
                                        style={
                                            "display": "grid",
                                            "gridTemplateColumns": "1fr",
                                            "gap": "24px",
                                        },
                                        children=[
                                            redcap_card([html.H4("Age groups by site (baseline)", style={"marginTop": 0}), redcap_fig_or_msg(redcap_figs, "age", "No age data available", height=480)]),
                                            redcap_card([html.H4("Sex distribution by site", style={"marginTop": 0}), redcap_fig_or_msg(redcap_figs, "sex", "No sex data available", height=480)]),
                                            redcap_card([html.H4("Gender identity by site", style={"marginTop": 0}), redcap_fig_or_msg(redcap_figs, "gender", "No gender data available", height=480)]),
                                            redcap_card([html.H4("Ethnicity (all labels)", style={"marginTop": 0}), redcap_fig_or_msg(redcap_figs, "ethnicity_full", "No ethnicity data available", height=520)]),
                                            redcap_card([html.H4("Ethnicity (White / Non-white) by site", style={"marginTop": 0}), redcap_fig_or_msg(redcap_figs, "ethnicity_white_nonwhite", "No white/non-white data available", height=480)]),
                                            redcap_card([html.H4("Household income (baseline)", style={"marginTop": 0}), redcap_fig_or_msg(redcap_figs, "income", "No income data available", height=480)]),
                                        ],
                                    )
                                ],
                            ),
                            dcc.Tab(
                                label="Timeline & Data Quality",
                                children=[
                                    redcap_card([html.H4("Baseline MRI visits by site", style={"marginTop": 0}), redcap_fig_or_msg(redcap_figs, "mri_timeline", "No MRI timeline available", height=440)]),
                                    redcap_card([html.H4("Missing counts per panel", style={"marginTop": 0}), redcap_fig_or_msg(redcap_figs, "missing_counts", "No NA summary available", height=440)], style_extra={"marginTop": "1rem"}),
                                ],
                            ),
                            dcc.Tab(
                                label="Mental Health Insights",
                                children=[
                                    redcap_card(
                                        [
                                            html.H4("Diagnoses (counts)", style={"marginTop": 0}),
                                            redcap_fig_or_msg(redcap_figs, "mh_bar", "No CFQ diagnosis variables present", height=360),
                                            html.Div(style={"height": "8px"}),
                                            redcap_fig_or_msg(redcap_figs, "mh_heatmap_with_nodx", "Heatmap unavailable", height=400),
                                        ]
                                    ),
                                    redcap_card(
                                        [
                                            html.H4("Correlations & Co-occurrence", style={"marginTop": 0}),
                                            redcap_fig_or_msg(redcap_figs, "mh_corr", "Correlation matrix unavailable", height=400),
                                            html.Div(style={"height": "8px"}),
                                            redcap_fig_or_msg(redcap_figs, "mh_cooccurrence", "Co-occurrence matrix unavailable", height=400),
                                        ],
                                        style_extra={"marginTop": "1rem"},
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),

            make_info_panel(dataset_root, last_updated),

            # html.Div(style={"marginTop": "80px", "textAlign": "center",
            #                 "color": "#777", "fontSize": "13px", "paddingBottom": "40px"},
            #          children=f"Source: BIDS + REDCap | Dataset: {dataset_root.name}"),
        ],
    )


from dash import Input, Output, State, ctx

def register_callbacks(app):
    @app.callback(
        Output("info-panel-content", "className"),
        Input("toggle-panel-btn", "n_clicks"),
        State("info-panel-content", "className"),
        prevent_initial_call=True,
    )
    def toggle_info_panel(n_clicks, current_class):
        if not n_clicks:
            raise dash.exceptions.PreventUpdate
        if "collapsed" in current_class:
            return "floating-info-panel"  # expand
        else:
            return "floating-info-panel collapsed"  # collapse
