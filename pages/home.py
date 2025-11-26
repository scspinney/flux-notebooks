import dash
from dash import html, dcc
from pathlib import Path
import os
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime
import dash_bootstrap_components as dbc
import urllib.parse

from flux_notebooks.redcap.summarize_targets import summarize_modalities
from flux_notebooks.bids.summarize_bids import summarize_bids
from flux_notebooks.freesurfer.summarize_freesurfer import summarize_freesurfer
from flux_notebooks.theme import SITE_COLORS
from flux_notebooks.redcap.summarize_redcap import summarize_redcap

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


def modality_icon_src(modality: str) -> str:
    """
    Return the icon path for a modality. Place your custom images in
    flux-notebooks/assets/icons and reference them here.
    """
    icon_map = {
        "T1W": "/assets/icons/t1w.png",           # T1 icon
        "T2W": "/assets/icons/t2w.jpg",           # T2 icon
        "task-partlycloudy": "/assets/icons/task.jpg",  # task icon (shared)
        "task-laluna": "/assets/icons/task.jpg",        # task icon (shared)
        "DWI": "/assets/icons/dwi.jpeg",          # DWI icon
    }
    return icon_map.get(modality, "/assets/icons/t1w.png")


# ---------------------------------------------------------------------
# REDCap helpers (reused from redcap page, simplified)
# ---------------------------------------------------------------------
def _height_to_css(height):
    if height is None:
        return "calc(100vh - 260px)"
    if isinstance(height, int):
        return f"{height}px"
    return str(height)


def redcap_fig_or_msg(figs, key: str, msg: str, height: int | str | None = 400, style_extra=None):
    fig = figs.get(key)
    style = {"height": _height_to_css(height)}
    if style_extra:
        style.update(style_extra)
    if fig is not None and getattr(fig, "data", None):
        return dcc.Graph(
            figure=fig,
            style=style,
            config={
                "displaylogo": False,
                "modeBarButtonsToRemove": [
                    "lasso2d",
                    "select2d",
                    "autoScale2d",
                    "toggleSpikelines",
                    "zoomIn2d",
                    "zoomOut2d",
                    "hoverClosestCartesian",
                ],
                "toImageButtonOptions": {
                    "format": "png",
                    "filename": key.replace(" ", "_"),
                    "scale": 2,
                },
                "displayModeBar": True,
                "responsive": True,
            },
        )
    return html.Div(
        msg,
        style={
            **style,
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center",
            "color": "#6b7280",
            "background": "#f8fafc",
            "border": "1px dashed #e5e7eb",
            "borderRadius": "10px",
        },
    )


def redcap_card(children, style_extra=None):
    base = {
        "background": "white",
        "padding": "16px",
        "borderRadius": "12px",
        "border": "1px solid #e5e7eb",
    }
    if style_extra:
        base.update(style_extra)
    return html.Div(children, className="shadow-sm", style=base)



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



def make_modality_summary(mod_data, site_name=None):
    site_color = SITE_COLORS.get(site_name, "#444")
    modality_labels = ["T1W", "T2W", "task-partlycloudy", "task-laluna", "DWI"]
    counts = {m["name"]: m.get("count", 0) for m in mod_data.get("modalities", [])}
    total = mod_data.get("total", 0)

    rows = []
    for label in modality_labels:
        count = counts.get(label, 0)
        color = site_color if count else "#9ca3af"
        rows.append(
            html.Div(
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "14px",
                    "marginBottom": "12px",
                    "fontSize": "15px",
                    "color": "#1f2937",
                    "padding": "8px 10px",
                    "borderRadius": "12px",
                    "background": "rgba(0,0,0,0.02)",
                },
                children=[
                    html.Img(
                        src=modality_icon_src(label),
                        style={
                            "width": "120px",
                            "height": "82px",
                            "borderRadius": "10px",
                            "flexShrink": 0,
                        },
                    ),
                    html.Div(
                        style={"flexGrow": 1, "display": "flex", "justifyContent": "space-between", "alignItems": "center"},
                        children=[
                            html.Span(
                                label,
                                style={
                                    "fontWeight": "700" if count else "600",
                                    "color": color,
                                    "fontSize": "16px",
                                    "paddingLeft": "4px",
                                },
                            ),
                            html.Span(
                                f"{count} / {total}" if total else f"{count}",
                                style={"fontWeight": "700", "color": color, "fontSize": "16px", "whiteSpace": "nowrap", "paddingLeft": "10px"},
                            ),
                        ],
                    ),
                ],
            )
        )

    return html.Div(
        className="glass-card card-fade",
        style={"padding": "26px 30px", "borderRadius": "16px", "minWidth": "380px",
               "maxWidth": "440px", "minHeight": "320px", "textAlign": "left",
               "boxShadow": "0 4px 16px rgba(0,0,0,0.12)",
               "background": "linear-gradient(135deg, #ffffff 0%, #f7f7f7 100%)"},
        children=[
            html.H4(site_name, style={"textAlign": "center", "marginBottom": "12px",
                                      "color": site_color, "fontWeight": "700"}),
            html.Div(className="site-line", style={"backgroundColor": site_color}),
            html.Div(rows),
            html.Div(
                f"Total subjects: {total}" if total else "No subjects found",
                style={"marginTop": "6px", "fontSize": "13px", "color": "#6b7280"},
            ),
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
