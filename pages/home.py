import dash
from dash import html, dcc
from pathlib import Path
import os
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime
import dash_bootstrap_components as dbc

from flux_notebooks.redcap.summarize_targets import summarize_modalities
from flux_notebooks.bids.summarize_bids import summarize_bids
from flux_notebooks.freesurfer.summarize_freesurfer import summarize_freesurfer
from flux_notebooks.theme import SITE_COLORS

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
# Helpers
# ---------------------------------------------------------------------
def summarize_sessions(bids_root: Path, participants_file: Path):
    """Count subjects by session and site."""
    summary = {"baseline": {"sites": {}, "total": 0},
               "followup1": {"sites": {}, "total": 0},
               "followup2": {"sites": {}, "total": 0}}
    if not bids_root.exists():
        return summary
    try:
        df = pd.read_csv(participants_file, sep="\t")
        site_lookup = dict(zip(df["participant_id"], df["site_name"]))
    except Exception as e:
        print(f"[WARN] Failed to load participants.tsv: {e}")
        site_lookup = {}
    for subdir in bids_root.glob("sub-*"):
        if not subdir.is_dir(): continue
        sub = subdir.name
        site = site_lookup.get(sub, "Unknown")
        sessions = [p.name for p in subdir.glob("ses-*") if p.is_dir()]
        for ses in sessions:
            key = {"ses-1a": "baseline", "ses-2a": "followup1", "ses-3a": "followup2"}.get(ses)
            if not key: continue
            summary[key]["total"] += 1
            summary[key]["sites"][site] = summary[key]["sites"].get(site, 0) + 1
    return summary



def make_pie(label, enrolled, target, emphasize=False):
    enrolled_pct = round((enrolled / target * 100), 1) if target else 0
    site_color = SITE_COLORS.get(label, "#0F0B01")

    # --- sizes that fit inside your card ---
    size = 300 if emphasize else 160   # <- big donut fits; tweak 300–320 if you want
    size_factor= 2.2 if emphasize else 1.5
    fig = go.Figure()
    fig.add_trace(go.Pie(
        values=[enrolled, max(target - enrolled, 0)],
        labels=["Enrolled", "Remaining"],
        marker_colors=[site_color, "#E0E0E0"],
        hole=0.55, sort=False, textinfo="none", showlegend=False,
    ))
    fig.update_traces(marker_line=dict(color="white", width=2))
    fig.update_layout(
        height=size, width=size,                     # <- exact square
        margin=dict(t=10, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        annotations=[dict(
            text=f"<b>{enrolled_pct:.1f}%</b>",
            x=0.5, y=0.5, showarrow=False, align="center",
            font=dict(size=int(18 * size_factor), color="#111", family="Inter, sans-serif"))])
    
    #gradient_color = f"radial-gradient(circle at 30% 30%, {site_color}, {site_color}15, #f8f8f8)"
    # Use Montreal tone for all sites
    base_gradient = "linear-gradient(145deg, #e8f3ff 0%, #c7e7f0 100%)"

    if emphasize:
        # Darker, richer version to make the big donut pop slightly
        gradient_color = "linear-gradient(145deg, #cddcf9 0%, #b2caef 100%)"
    else:
        gradient_color = base_gradient



    return html.Div(
        className=("card-fade glass-card " + ("big-donut" if emphasize else "")).strip(),
        style={
            "textAlign": "center", "margin": "10px", "padding": "12px",
            "borderRadius": "12px", "background": gradient_color,
            "boxShadow": "0 5px 14px rgba(0,0,0,0.15)" if emphasize else "0 3px 8px rgba(0,0,0,0.1)",
        },
        children=[
            html.H5(label, style={"marginBottom": "4px", "color": site_color, "fontWeight": "600"}),
            html.Div(  # square container that the SVG fills
                dcc.Graph(figure=fig, config={"displayModeBar": False}, style={"height": "100%", "width": "100%"}),
                style={"width": f"{size}px", "height": f"{size}px", "margin": "0 auto"},
            ),
            html.Div(f"{enrolled}/{target} enrolled", style={
                        "fontSize": "16px" if emphasize else "15px",
                        "color": "#333",
                        "fontWeight": "600",
                        "marginTop": "4px"
                    },
                ),
        ],
    )



# def make_pie(label, enrolled, target, emphasize=False):
#     """Single donut chart."""
#     enrolled_pct = round((enrolled / target * 100), 1) if target else 0
#     site_color = SITE_COLORS.get(label, "#FFB300")
#     fig = go.Figure()
#     fig.add_trace(go.Pie(
#         values=[enrolled, max(target - enrolled, 0)],
#         labels=["Enrolled", "Remaining"],
#         marker_colors=[site_color, "#E0E0E0"],
#         hole=0.55, sort=False, textinfo="none", showlegend=False))
#     size_factor = 2.2 if emphasize else 1.0
#     base_size = 160
#     fig.update_traces(marker_line=dict(color="white", width=2))
#     fig.update_layout(
#         height=int(base_size * size_factor),
#         width=int(base_size * size_factor),
#         margin=dict(t=10, b=10, l=10, r=10),
#         paper_bgcolor="rgba(0,0,0,0)",
#         plot_bgcolor="rgba(0,0,0,0)",
#         annotations=[dict(
#             text=f"<b>{enrolled_pct:.1f}%</b><br><span style='font-size:11px;color:#666;'>enrolled</span>",
#             x=0.5, y=0.5, showarrow=False, align="center",
#             font=dict(size=int(18 * size_factor), color="#111", family="Inter, sans-serif"))])
#     gradient_color = f"radial-gradient(circle at 30% 30%, {site_color}, {site_color}15, #f8f8f8)"
#     return html.Div(
#         className="card-fade glass-card",
#         style={"textAlign": "center", "margin": "10px", "padding": "12px",
#                "borderRadius": "12px", "background": gradient_color,
#                "boxShadow": "0 5px 14px rgba(0,0,0,0.15)" if emphasize else "0 3px 8px rgba(0,0,0,0.1)"},
#         children=[
#             html.H5(label, style={"marginBottom": "4px", "color": site_color, "fontWeight": "600"}),
#             dcc.Graph(figure=fig, config={"displayModeBar": False}),
#             html.Div(f"{enrolled}/{target} enrolled", style={"fontSize": "12px", "color": "#555"}),
#         ],
#     )


def make_modality_summary(mod_data, site_name=None):
    site_color = SITE_COLORS.get(site_name, "#444")
    modality_labels = ["T1W", "T2W", "task-partlycloudy", "task-laluna", "DWI"]
    percents = {m["name"]: m.get("percent", 0) for m in mod_data.get("modalities", [])}
    rows = [
        html.Div(
            [html.Span(label, style={"fontWeight": "600"}),
             html.Span(f"{percents.get(label,0):.1f}%", style={"float": "right", "color": site_color if percents.get(label,0)>=80 else "#888"})],
            style={"marginBottom": "6px", "fontSize": "15px", "color": "#333" if percents.get(label,0)>0 else "#999"})
        for label in modality_labels
    ]
    return html.Div(
        className="glass-card card-fade",
        style={"padding": "35px 45px", "borderRadius": "16px", "minWidth": "360px",
               "maxWidth": "420px", "minHeight": "260px", "textAlign": "left",
               "boxShadow": "0 4px 16px rgba(0,0,0,0.12)",
               "background": "linear-gradient(135deg, #ffffff 0%, #f7f7f7 100%)"},
        children=[
            html.H4(site_name, style={"textAlign": "center", "marginBottom": "12px",
                                      "color": site_color, "fontWeight": "600"}),
            html.Div(className="site-line", style={"backgroundColor": site_color}),
            html.Div(rows),
        ],
    )

# ---------------------------------------------------------------------
# Floating Info Panel (Collapsible with Toggle Tab)
# ---------------------------------------------------------------------
def make_info_panel(dataset_root, last_updated):
    """Collapsible right-side info panel with usage notes."""
    return html.Div(
        [
            # --- Toggle button (small side tab)
            html.Div(
                "ℹ️",
                id="toggle-panel-btn",
                className="info-toggle-tab",
                n_clicks=0,
                title="Show / Hide usage notes",
            ),

            # --- Main panel content ---
            html.Div(
                id="info-panel-content",
                className="floating-info-panel collapsed",
                children=[
                    html.H5("💡 Usage & Interpretation Guide", style={"marginBottom": "0.6rem"}),
                    html.P(
                        "This dashboard summarizes recruitment progress and imaging coverage across all C-PIP sites. "
                        "Use this guide to interpret the charts and navigate the tools effectively.",
                        style={"fontSize": "0.95rem", "color": "#374151"},
                    ),
                    html.Hr(),
                    html.H6("📊 Recruitment Donuts"),
                    html.Ul(
                        [
                            html.Li("Each ring shows participant recruitment progress per site and overall."),
                            html.Li("Hover to see exact percentages and counts."),
                            html.Li("Tabs switch between Baseline and Follow-up sessions."),
                        ],
                        style={"fontSize": "0.9rem", "color": "#4b5563", "paddingLeft": "1.1rem"},
                    ),
                    html.H6("🧠 Modality Coverage Cards", style={"marginTop": "0.8rem"}),
                    html.Ul(
                        [
                            html.Li("Each card shows how complete each imaging modality is per site."),
                            html.Li("Higher percentages mean more subjects have that modality."),
                            html.Li("Helps identify gaps or missing scans."),
                        ],
                        style={"fontSize": "0.9rem", "color": "#4b5563", "paddingLeft": "1.1rem"},
                    ),
                    html.H6("🔎 Navigation Tips", style={"marginTop": "0.8rem"}),
                    html.Ul(
                        [
                            html.Li("Use the top navbar to move between summaries and detailed reports."),
                            html.Li("MRIQC and fMRIPrep pages show participant-level HTML reports."),
                            html.Li("BIDS Summary lists available subjects and sessions."),
                        ],
                        style={"fontSize": "0.9rem", "color": "#4b5563", "paddingLeft": "1.1rem"},
                    ),
                    html.Hr(),
                    html.P(
                        f"📅 Last updated: {last_updated}",
                        style={"fontSize": "0.85rem", "color": "#6b7280", "marginTop": "0.8rem"},
                    ),
                    html.P(
                        f"🗂 Dataset root: {dataset_root.name}",
                        style={"fontSize": "0.85rem", "color": "#6b7280"},
                    ),
                ],
            ),
        ],
        id="collapsible-info-wrapper",
    )


# ---------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------
def layout():
    participants_tsv = bids_root / "participants.tsv"
    session_summary = summarize_sessions(bids_root, participants_tsv)
    last_updated = datetime.fromtimestamp(dataset_root.stat().st_mtime).strftime("%Y-%m-%d %H:%M")

    # Timepoint tabs (recruitment)
    def make_timepoint_tab(label, key):
        ses_data = session_summary.get(key, {})
        total_obs = ses_data.get("total", 0)
        total_tgt = 263 * len(SITE_MAP)
        overall_pie = make_pie(f"{label} Overall", total_obs, total_tgt, emphasize=True)
        site_pies = [make_pie(site, ses_data.get("sites", {}).get(site, 0), 263) for site in SITE_MAP.values()]
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

        site_cards = []
        for site_label in SITE_MAP.values():
            modalities = []
            site_subjects = [s for s, site in site_map.items() if site.lower() == site_label.lower()]
            total = len(site_subjects)
            for mod in ["T1W", "T2W", "task-partlycloudy", "task-laluna", "DWI"]:
                count = sum(1 for sub in site_subjects
                            if (bids_root / sub / f"ses-{session_suffix}").exists()
                            and any(mod.lower() in f.name.lower() for f in (bids_root / sub / f"ses-{session_suffix}").rglob("*.nii*")))
                percent = round(100 * count / total, 1) if total else 0
                modalities.append({"name": mod, "percent": percent})
            site_cards.append(make_modality_summary({"modalities": modalities}, site_label))

        return dbc.Tab(label=label, tab_id=f"mod-{session_suffix}",
                       children=html.Div(style={"display": "flex", "justifyContent": "center",
                                                "gap": "35px", "flexWrap": "wrap", "marginTop": "25px"},
                                         children=site_cards))

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

            html.Div(style={"textAlign": "center", "marginTop": "25px"},
                     children=[
                         dbc.Button("📊 Detailed Recruitment Info", href="/redcap", color="primary",
                                    style={"fontWeight": "600", "fontSize": "16px",
                                           "padding": "10px 24px", "borderRadius": "10px",
                                           "backgroundColor": "#2563eb", "border": "none"}),
                         html.Div("View full demographic breakdowns, equity metrics, and data quality trends from REDCap.",
                                  style={"marginTop": "10px", "color": "#6b7280", "fontSize": "16px"})]),

            html.Div(style={"marginTop": "50px", "textAlign": "center"},
                     children=[html.H3("Imaging Modality Coverage by Site", style={"marginBottom": "5px"}),
                               html.P("Each card shows the percentage of subjects at each site with available imaging modalities per timepoint.",
                                      style={"color": "#6b7280", "fontSize": "16px",
                                             "marginBottom": "25px", "maxWidth": "800px", "margin": "0 auto"}),
                               modality_tabs]),

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
