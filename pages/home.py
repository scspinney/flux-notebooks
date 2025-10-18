import dash
from dash import html, dcc
from pathlib import Path
import os
import plotly.graph_objs as go
from datetime import datetime
from flux_notebooks.redcap.summarize_targets import summarize_all_sites, summarize_modalities
from flux_notebooks.bids.summarize_bids import summarize_bids
from flux_notebooks.freesurfer.summarize_freesurfer import summarize_freesurfer

dash.register_page(__name__, path="/", name="Home")

# ---------------------------------------------------------------------
# Site mapping and dataset paths
# ---------------------------------------------------------------------
SITE_MAP = {"montreal": "Montreal", "calgary": "Calgary", "toronto": "Toronto"}
SITE_COLORS = {"Montreal": "#1976D2", "Calgary": "#E53935", "Toronto": "#FB8C00"}

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
body {
  font-family: 'Inter', sans-serif;
  background-color: #f8f9fa;
}

.card-fade {
  opacity: 0;
  transform: translateY(10px);
  animation: fadeInUp 0.7s ease forwards;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(15px); }
  to { opacity: 1; transform: translateY(0); }
}

.glass-card {
  background: rgba(255,255,255,0.8);
  border: 1px solid rgba(255,255,255,0.3);
  backdrop-filter: blur(6px);
  box-shadow: 0 3px 6px rgba(0,0,0,0.08);
}

.site-line {
  height: 4px;
  width: 40%;
  margin: 0 auto 15px;
  border-radius: 2px;
}

/* Optional subtle pulse for fully processed bars */
@keyframes pulseGlow {
  0% { box-shadow: 0 0 0 rgba(76, 175, 80, 0.4); }
  50% { box-shadow: 0 0 10px rgba(76, 175, 80, 0.6); }
  100% { box-shadow: 0 0 0 rgba(76, 175, 80, 0.4); }
}

.pulse-complete {
  animation: pulseGlow 1.5s infinite ease-in-out;
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
def make_pie(label, enrolled, target, processed=None):
    """Dual-layer donut: yellow for enrolled, green overlay for preprocessed."""
    processed = processed or 0
    enrolled = max(enrolled, processed)
    enrolled_pct = round((enrolled / target * 100), 1) if target else 0

    fig = go.Figure()

    # Outer ring – Enrolled
    fig.add_trace(
        go.Pie(
            values=[enrolled, max(target - enrolled, 0)],
            labels=["Enrolled", "Remaining"],
            marker_colors=["#FFB300", "#E0E0E0"],
            hole=0.5,
            sort=False,
            textinfo="none",
            showlegend=False,
        )
    )

    # Inner ring – Processed
    if processed > 0:
        fig.add_trace(
            go.Pie(
                values=[processed, max(enrolled - processed, 0)],
                labels=["Processed", "Not processed"],
                marker_colors=["#4CAF50", "rgba(255,255,255,0)"],
                hole=0.75,
                sort=False,
                textinfo="none",
                showlegend=False,
            )
        )

    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        height=160,
        width=160,
        showlegend=False,
        annotations=[
            dict(text=f"{enrolled_pct:.1f}%", x=0.5, y=0.5, font_size=14, showarrow=False)
        ],
    )

    return html.Div(
        className="card-fade glass-card",
        style={"textAlign": "center", "margin": "10px", "padding": "10px"},
        children=[
            html.H5(label, style={"marginBottom": "4px", "color": "#333"}),
            dcc.Graph(figure=fig, config={"displayModeBar": False}),
            html.Div(f"{enrolled}/{target} enrolled", style={"fontSize": "12px", "color": "#555"}),
            html.Div(f"{processed} preprocessed", style={"fontSize": "12px", "color": "#4CAF50"}),
        ],
    )

# --- Modalities per site --------------------------
def make_modality_bars(mod_data, site_name=None):
    """Horizontal bar visualization of available vs preprocessed per modality."""
    rows = []
    for m in mod_data.get("modalities", []):
        name = m["name"]
        total = m["available"]
        processed = m["processed"]
        percent = m["percent"]

        processed = min(processed, total)
        width = f"{(processed / total) * 100:.1f}%" if total else "0%"
        pulse = " pulse-complete" if total > 0 and processed == total else ""

        rows.append(
            html.Div(
                style={"marginBottom": "10px", "width": "100%"},
                children=[
                    html.Div(
                        [
                            html.Span(name, style={"fontWeight": "600"}),
                            html.Span(
                                f"{processed}/{total} ({percent:.1f}%)",
                                style={"float": "right", "fontSize": "12px", "color": "#444"},
                            ),
                        ],
                        style={
                            "marginBottom": "4px",
                            "display": "flex",
                            "justifyContent": "space-between",
                        },
                    ),
                    html.Div(
                        style={
                            "height": "12px",
                            "borderRadius": "6px",
                            "backgroundColor": "rgba(0,0,0,0.05)",
                            "overflow": "hidden",
                        },
                        children=html.Div(
                            title=f"{processed}/{total} {name} preprocessed ({percent:.1f}%)",
                            className=pulse,
                            style={
                                "width": width,
                                "height": "100%",
                                "backgroundColor": "#4CAF50",
                                "transition": "width 0.4s ease",
                                "cursor": "help",
                            },
                        ),
                    ),
                ],
            )
        )

    site_color = SITE_COLORS.get(site_name, "#444") if site_name else "#444"
    return html.Div(
        className="glass-card card-fade",
        style={
            "padding": "20px",
            "borderRadius": "10px",
            "minWidth": "280px",
            "maxWidth": "340px",
        },
        children=[
            html.Div(
                [
                    html.H4(
                        site_name if site_name else "Modalities",
                        style={
                            "textAlign": "center",
                            "marginBottom": "10px",
                            "color": "#333",
                            "fontWeight": "600",
                        },
                    ),
                    html.Div(
                        className="site-line",
                        style={"backgroundColor": site_color},
                    ),
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
        mod_summary_global = summarize_modalities(bids_root, dataset_root / "derivatives")
        mod_summaries = {
            site: summarize_modalities(bids_root / site.lower(), dataset_root / "derivatives" / site.lower())
            for site in SITE_MAP.values()
            if (bids_root / site.lower()).exists()
        }
    except Exception:
        mod_summary_global = {"modalities": []}
        mod_summaries = {}

    last_updated = datetime.fromtimestamp(dataset_root.stat().st_mtime).strftime("%Y-%m-%d %H:%M")

    return html.Div(
        style={"fontFamily": "Inter, sans-serif", "margin": "20px", "maxWidth": "1400px", "margin": "0 auto"},
        children=[
            GLOBAL_STYLE,
            html.H1("Welcome to Flux Dashboards", style={"marginBottom": "5px"}),
            html.P(
                "A professional overview of dataset metrics and recruitment progress.",
                style={"marginBottom": "25px"},
            ),
            html.Div(
                style={"display": "flex", "gap": "20px", "flexWrap": "wrap"},
                children=[
                    stat_card("Subjects", subjects),
                    stat_card("Sessions", sessions),
                    stat_card("Tasks", tasks),
                    stat_card("FreeSurfer Subjects", fs_subjects),
                ],
            ),
            html.Div(
                style={"textAlign": "center", "marginTop": "30px"},
                children=[
                    html.H4("Overall Study Progress", style={"marginBottom": "15px"}),
                    html.Div(
                        style={
                            "display": "flex",
                            "justifyContent": "center",
                            "alignItems": "flex-start",
                            "gap": "35px",
                            "flexWrap": "wrap",
                        },
                        children=[overall_total] + sites,
                    ),
                ],
            ),
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
                            make_modality_bars(mod_summaries.get(site, mod_summary_global), site)
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
