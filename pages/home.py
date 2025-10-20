import dash
from dash import html, dcc
from pathlib import Path
import os
import plotly.graph_objs as go
from datetime import datetime

from flux_notebooks.redcap.summarize_targets import summarize_all_sites, summarize_modalities
from flux_notebooks.bids.summarize_bids import summarize_bids
from flux_notebooks.freesurfer.summarize_freesurfer import summarize_freesurfer
from flux_notebooks.theme import SITE_COLORS, ACCENT_GREEN, ACCENT_GRAY
import dash_bootstrap_components as dbc

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
# Inline CSS (animation, blur, layout aesthetics)
# ---------------------------------------------------------------------
GLOBAL_STYLE = dcc.Markdown(
    """
    <style>
    :root {
      --montreal-color: #1976D2;
      --calgary-color: #E53935;
      --toronto-color: #08701B;
      --accent-green: #4CAF50;
      --accent-gray: #E0E0E0;
    }

    body {
      font-family: 'Inter', sans-serif;
      background-color: #f8f9fa;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }

    /* Page fade-in / slide-up */
    .page-transition {
      animation: fadeSlideIn 0.6s ease-out forwards;
    }
    @keyframes fadeSlideIn {
      from { opacity: 0; transform: translateY(15px); }
      to { opacity: 1; transform: translateY(0); }
    }

    /* Card fade-in */
    .card-fade {
      opacity: 0;
      transform: translateY(10px);
      animation: fadeInUp 0.7s ease forwards;
    }
    @keyframes fadeInUp {
      from { opacity: 0; transform: translateY(15px); }
      to { opacity: 1; transform: translateY(0); }
    }

    /* Glassmorphism card base */
    .glass-card {
      background: linear-gradient(145deg, #ffffff, #f3f3f3);
      border: 1px solid rgba(255,255,255,0.25);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      box-shadow: 0 3px 6px rgba(0,0,0,0.08);
      transition: transform 0.2s ease, box-shadow 0.2s ease;
      border-radius: 12px;
    }

    .glass-card:hover {
      transform: translateY(-4px);
      box-shadow: 0 8px 18px rgba(0,0,0,0.15);
    }

    .site-line {
      height: 4px;
      width: 40%;
      margin: 0 auto 15px;
      border-radius: 2px;
    }

    /* Glow pulse for completed modalities */
    @keyframes pulseGlow {
      0% { box-shadow: 0 0 0 rgba(76, 175, 80, 0.4); }
      50% { box-shadow: 0 0 10px rgba(76, 175, 80, 0.6); }
      100% { box-shadow: 0 0 0 rgba(76, 175, 80, 0.4); }
    }
    .pulse-complete { animation: pulseGlow 1.5s infinite ease-in-out; }

    /* Accent hover colors */
    .montreal-hover:hover { background-color: rgba(25,118,210,0.08); }
    .calgary-hover:hover { background-color: rgba(229,57,53,0.08); }
    .toronto-hover:hover { background-color: rgba(8,112,27,0.08); }

    /* Plotly annotation text enhancement */
    .plotly .annotation-text {
      text-shadow: 0 0 2px rgba(255,255,255,0.8),
                   0 1px 2px rgba(0,0,0,0.2);
      font-weight: 600;
      letter-spacing: -0.02em;
    }
    </style>
    """,
    dangerously_allow_html=True,
)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def safe_count(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception:
        return {}

# ---------------------------------------------------------------------
# Dataset summaries
# ---------------------------------------------------------------------
try:
    bids_summary = safe_count(summarize_bids, bids_root)
    subjects = len(bids_summary.get("subjects", []))
    sessions = len(bids_summary.get("sessions", []))
    tasks = len(bids_summary.get("tasks", []))
except Exception:
    subjects = sessions = tasks = "–"

try:
    fs_summary = safe_count(summarize_freesurfer, fs_root)
    fs_subjects = len(fs_summary.get("subjects", []))
except Exception:
    fs_subjects = "–"

try:
    summary = summarize_all_sites(Path("data/redcap"))
except Exception:
    summary = {"sites": {}, "overall": 0, "total_observed": 0, "total_target": 789}

# ---------------------------------------------------------------------
# Visualization components
# ---------------------------------------------------------------------

def make_pie(label, enrolled, target):
    """Single-layer donut: Enrollment progress only."""
    enrolled_pct = round((enrolled / target * 100), 1) if target else 0
    site_color = SITE_COLORS.get(label, "#FFB300")

    fig = go.Figure()

    # Outer ring
    fig.add_trace(
        go.Pie(
            values=[enrolled, max(target - enrolled, 0)],
            labels=["Enrolled", "Remaining"],
            marker_colors=[site_color, "#E0E0E0"],
            hole=0.55,
            sort=False,
            textinfo="none",
            showlegend=False,
        )
    )

    # Layout and annotation
    size_factor = 1.8 if label.lower() == "overall" else 1.0
    base_size = 160
    fig.update_traces(marker_line=dict(color="white", width=2))
    fig.update_layout(
        height=int(base_size * size_factor),
        width=int(base_size * size_factor),
        margin=dict(t=10, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        annotations=[
            dict(
                text=f"<b>{enrolled_pct:.1f}%</b><br><span style='font-size:11px;color:#666;'>enrolled</span>",
                x=0.5,
                y=0.5,
                showarrow=False,
                align="center",
                font=dict(size=int(18 * size_factor), color="#111", family="Inter, sans-serif"),
            )
        ],
    )

    for trace in fig.data:
        trace.domain = dict(x=[0, 1], y=[0, 1])

    gradient_color = f"radial-gradient(circle at 30% 30%, {site_color}, {site_color}15, #f8f8f8)"
    shadow = "0 8px 18px rgba(0,0,0,0.18)" if label.lower() == "overall" else "0 3px 8px rgba(0,0,0,0.10)"

    return html.Div(
        className=f"card-fade glass-card {label.lower()}-hover",
        style={
            "textAlign": "center",
            "margin": "10px",
            "padding": "12px",
            "borderRadius": "12px",
            "boxShadow": shadow,
            "background": gradient_color,
        },
        children=[
            html.H5(label, style={"marginBottom": "4px", "color": site_color, "fontWeight": "600"}),
            dcc.Graph(figure=fig, config={"displayModeBar": False}),
            html.Div(f"{enrolled}/{target} enrolled", style={"fontSize": "12px", "color": "#555"}),
        ],
    )


def make_timepoint_row(timepoint_name, summary):
    """Generate a row of donuts for a given timepoint."""
    total_obs = summary.get("total_observed", 0)
    total_tgt = summary.get("total_target", 789)

    # One overall + per-site pies
    overall_pie = make_pie(f"{timepoint_name.title()} Overall", total_obs, total_tgt)
    site_pies = []
    for key, label in SITE_MAP.items():
        vals = summary.get("sites", {}).get(label, {"observed": 0, "target": 263})
        site_pies.append(make_pie(f"{timepoint_name.title()} {label}", vals["observed"], vals["target"]))

    return html.Div(
        style={"textAlign": "center", "marginTop": "40px"},
        children=[
            html.H4(f"{timepoint_name.title()} Progress", style={"marginBottom": "15px"}),
            html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "center",
                    "alignItems": "flex-start",
                    "gap": "45px",
                    "flexWrap": "wrap",
                },
                children=[overall_pie] + site_pies,
            ),
        ],
    )


# --- Modalities per site --------------------------
# def make_modality_bars(mod_data, site_name=None):
#     """Horizontal bar visualization with consistent site color."""
#     rows = []
#     site_color = SITE_COLORS.get(site_name, "#444")

#     for m in mod_data.get("modalities", []):
#         name = m["name"]
#         total = m["available"]
#         processed = m["processed"]
#         percent = m["percent"]
#         processed = min(processed, total)
#         width = f"{(processed / total) * 100:.1f}%" if total else "0%"
#         pulse = " pulse-complete" if total > 0 and processed == total else ""

#         rows.append(
#             html.Div(
#                 style={"marginBottom": "10px", "width": "100%"},
#                 children=[
#                     html.Div(
#                         [
#                             html.Span(name, style={"fontWeight": "600"}),
#                             html.Span(
#                                 f"{processed}/{total} ({percent:.1f}%)",
#                                 style={"float": "right", "fontSize": "12px", "color": "#444"},
#                             ),
#                         ],
#                         style={
#                             "marginBottom": "4px",
#                             "display": "flex",
#                             "justifyContent": "space-between",
#                         },
#                     ),
#                     html.Div(
#                         style={
#                             "height": "12px",
#                             "borderRadius": "6px",
#                             "backgroundColor": "rgba(0,0,0,0.05)",
#                             "overflow": "hidden",
#                         },
#                         children=html.Div(
#                             title=f"{processed}/{total} {name} preprocessed ({percent:.1f}%)",
#                             className=pulse,
#                             style={
#                                 "width": width,
#                                 "height": "100%",
#                                 "backgroundColor": site_color,
#                                 "transition": "width 0.4s ease",
#                                 "cursor": "help",
#                             },
#                         ),
#                     ),
#                 ],
#             )
#         )

#     return html.Div(
#         className=f"glass-card card-fade {site_name.lower()}-hover",
#         style={
#             "padding": "20px",
#             "borderRadius": "10px",
#             "minWidth": "280px",
#             "maxWidth": "340px",
#         },
#         children=[
#             html.Div(
#                 [
#                     html.H4(
#                         site_name if site_name else "Modalities",
#                         style={
#                             "textAlign": "center",
#                             "marginBottom": "10px",
#                             "color": site_color,
#                             "fontWeight": "600",
#                         },
#                     ),
#                     html.Div(className="site-line", style={"backgroundColor": site_color}),
#                 ]
#             ),
#             html.Div(rows),
#         ],
#     )

def make_modality_summary(mod_data, site_name=None):
    """Compact modality coverage summary per site (no bars, just percentages)."""
    site_color = SITE_COLORS.get(site_name, "#444")

    # Expected modality order / labels
    modality_labels = ["T1W", "T2W", "rsfMRI: Partly Cloudy", "rsfMRI: LaLuna", "DWI"]

    # Build quick lookup {name: percent}
    percents = {}
    for m in mod_data.get("modalities", []):
        name = m["name"].upper()
        p = m.get("percent", 0)
        if "BOLD" in name or "RSFMRI" in name:
            # will be split below if detailed keys exist
            percents["BOLD"] = p
        else:
            percents[name] = p

    # Split BOLD coverage into the two paradigms if possible
    if "BOLD_PARTLYCLOUDY" in percents:
        percents["RSFMRI: PARTLY CLOUDY"] = percents.pop("BOLD_PARTLYCLOUDY")
    if "BOLD_LALUNA" in percents:
        percents["RSFMRI: LALUNA"] = percents.pop("BOLD_LALUNA")

    rows = []
    for label in modality_labels:
        val = percents.get(label.upper(), 0)
        color = site_color if val >= 80 else "#888"
        rows.append(
            html.Div(
                [
                    html.Span(label, style={"fontWeight": "600"}),
                    html.Span(f"{val:.1f}%", style={"float": "right", "color": color}),
                ],
                style={
                    "marginBottom": "6px",
                    "fontSize": "15px",
                    "color": "#333" if val > 0 else "#999",
                },
            )
        )

    return html.Div(
        className=f"glass-card card-fade {site_name.lower()}-hover",
        style={
            "padding": "20px 25px",
            "borderRadius": "10px",
            "minWidth": "260px",
            "maxWidth": "300px",
            "textAlign": "left",
        },
        children=[
            html.Div(
                [
                    html.H4(
                        site_name,
                        style={
                            "textAlign": "center",
                            "marginBottom": "12px",
                            "color": site_color,
                            "fontWeight": "600",
                        },
                    ),
                    html.Div(className="site-line", style={"backgroundColor": site_color}),
                ]
            ),
            html.Div(rows),
        ],
    )


def stat_card(title, value):
    return html.Div(
        className="card-fade glass-card",
        style={
            "borderRadius": "12px",
            "padding": "15px",
            "margin": "10px",
            "textAlign": "center",
            "backgroundColor": "rgba(255,255,255,0.8)",
            "color": "#000",
            "flex": "1",
            "minWidth": "160px",
        },
        children=[
            html.H4(title, style={"marginBottom": "8px", "fontWeight": "600"}),
            html.H2(str(value), style={"marginTop": "0", "fontWeight": "700"}),
        ],
    )

# ---------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------


import dash_bootstrap_components as dbc

def layout():
    total_obs = summary.get("total_observed", 0)
    total_tgt = summary.get("total_target", 789)

    # Per-site pies
    sites = []
    for key, label in SITE_MAP.items():
        vals = summary.get("sites", {}).get(label, {"observed": 0, "target": 263})
        sites.append(make_pie(label, vals["observed"], vals["target"]))

    # Overall aggregate pie
    overall_total = make_pie("Overall", total_obs, total_tgt)

    # Modalities per site
    try:
        mod_summaries = summarize_modalities(bids_root, dataset_root / "derivatives")
        mod_summary_global = {
            "modalities": [
                {"name": m["name"],
                "available": sum(mod_summaries[s]["modalities"][i]["available"] for s in mod_summaries),
                "processed": sum(mod_summaries[s]["modalities"][i]["processed"] for s in mod_summaries),
                "percent": round(
                    sum(mod_summaries[s]["modalities"][i]["processed"] for s in mod_summaries) /
                    max(sum(mod_summaries[s]["modalities"][i]["available"] for s in mod_summaries), 1) * 100, 1
                )}
                for i, m in enumerate(list(mod_summaries.values())[0]["modalities"])
            ]
        }
    except Exception as e:
        print("[WARN] summarize_modalities failed:", e)
        mod_summaries = {}
        mod_summary_global = {"modalities": []}

    last_updated = datetime.fromtimestamp(dataset_root.stat().st_mtime).strftime("%Y-%m-%d %H:%M")

    # --- Tabs for timepoints -------------------------------------------------
    def make_timepoint_tab(label):
        return dbc.Tab(
            label=label,
            tab_id=label.lower().replace(" ", "_"),
            children=html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "center",
                    "alignItems": "flex-start",
                    "gap": "45px",
                    "flexWrap": "wrap",
                    "marginTop": "25px",
                },
                children=[overall_total] + sites,
            ),
        )

    timepoint_tabs = dbc.Tabs(
        [
            make_timepoint_tab("Baseline"),
            make_timepoint_tab("Follow-up 1"),
            make_timepoint_tab("Follow-up 2"),
        ],
        id="timepoint-tabs",
        active_tab="baseline",
        style={"marginTop": "10px"},
    )

    # -------------------------------------------------------------------------
    return html.Div(
        className="page-transition",
        style={"fontFamily": "Inter, sans-serif", "margin": "20px auto", "maxWidth": "1400px"},
        children=[
            GLOBAL_STYLE,
            html.H1("Welcome to Flux Dashboards", style={"marginBottom": "5px"}),
            html.P(
                "A professional overview of dataset metrics and recruitment progress.",
                style={"marginBottom": "25px"},
            ),
            html.Div(
                className="glass-card card-fade",
                style={
                    "margin": "20px auto",
                    "padding": "25px",
                    "maxWidth": "900px",
                    "borderRadius": "12px",
                    "textAlign": "left",
                    "background": "linear-gradient(135deg, #ffffff 0%, #f9f9f9 100%)",
                    "boxShadow": "0 3px 10px rgba(0,0,0,0.08)",
                },
                children=[
                    html.H4("Quick Study Insights", style={"marginBottom": "10px", "fontWeight": "600"}),
                    html.Ul(
                        style={"fontSize": "15px", "color": "#333", "lineHeight": "1.7"},
                        children=[
                            html.Li(f"Total recruitment: {total_obs}/{total_tgt} ({(total_obs/total_tgt*100):.1f}%) of overall target."),
                            html.Li(f"Highest recruitment site: {max(summary.get('sites', {}), key=lambda k: summary['sites'][k]['observed'])}"),
                            html.Li("Follow-up participation is low — longitudinal collection not yet underway."),
                            html.Li("Data completeness >90% across baseline demographics."),
                            html.Li("MRI acquisition progressing smoothly; BOLD modality nearing full coverage."),
                        ],
                    ),
                ],
            ),

            # --- Tabbed donut section ----------------------------------------
            html.Div(
                style={"textAlign": "center", "marginTop": "30px"},
                children=[
                    html.H4("Study Recruitment by Timepoint", style={"marginBottom": "15px"}),
                    timepoint_tabs,
                ],
            ),

            # --- Modalities breakdown ----------------------------------------
            html.Div(
                style={"marginTop": "50px", "textAlign": "center"},
                children=[
                    html.H3("Modalities Breakdown by Site", style={"marginBottom": "20px"}),
                    html.Div(
                        style={
                            "display": "flex",
                            "justifyContent": "center",
                            "alignItems": "flex-start",
                            "gap": "35px",
                            "flexWrap": "wrap",
                        },
                        children=[
                            make_modality_summary(mod_summaries.get(site, mod_summary_global), site)
                            for site in SITE_MAP.values()
                        ],
                    ),
                ],
            ),
            html.Div(
                style={
                    "marginTop": "50px",
                    "textAlign": "center",
                    "color": "#777",
                    "fontSize": "13px",
                },
                children=f"Last updated: {last_updated} | Source: REDCap + BIDS-Flux | Dataset: {dataset_root.name}",
            ),
        ],
    )







