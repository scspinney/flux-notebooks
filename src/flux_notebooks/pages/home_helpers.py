"""
Helper functions for Home page.

This module contains utility functions extracted from pages/home.py
to support the home dashboard with recruitment progress and imaging coverage.
"""

from pathlib import Path
import pandas as pd
import plotly.graph_objs as go
from dash import html, dcc


def summarize_sessions(bids_root: Path, participants_file: Path):
    """
    Count subjects by session and site.

    Args:
        bids_root: Path to BIDS root directory
        participants_file: Path to participants.tsv file

    Returns:
        Dict with keys 'baseline', 'followup1', 'followup2', each containing
        'sites' dict and 'total' count
    """
    summary = {
        "baseline": {"sites": {}, "total": 0},
        "followup1": {"sites": {}, "total": 0},
        "followup2": {"sites": {}, "total": 0},
    }
    if not bids_root.exists():
        return summary
    try:
        df = pd.read_csv(participants_file, sep="\t")
        site_lookup = dict(zip(df["participant_id"], df["site_name"]))
    except Exception as e:
        print(f"[WARN] Failed to load participants.tsv: {e}")
        site_lookup = {}
    for subdir in bids_root.glob("sub-*"):
        if not subdir.is_dir():
            continue
        sub = subdir.name
        site = site_lookup.get(sub, "Unknown")
        sessions = [p.name for p in subdir.glob("ses-*") if p.is_dir()]
        for ses in sessions:
            key = {"ses-1a": "baseline", "ses-2a": "followup1", "ses-3a": "followup2"}.get(ses)
            if not key:
                continue
            summary[key]["total"] += 1
            summary[key]["sites"][site] = summary[key]["sites"].get(site, 0) + 1
    return summary


def modality_icon_src(modality: str) -> str:
    """
    Return the icon path for a modality.

    Args:
        modality: Modality name (e.g., "T1W", "DWI", "task-partlycloudy")

    Returns:
        URL path to icon image in assets/icons/
    """
    icon_map = {
        "T1W": "/assets/icons/t1w.png",
        "T2W": "/assets/icons/t2w.jpg",
        "task-partlycloudy": "/assets/icons/task.jpg",
        "task-laluna": "/assets/icons/task.jpg",
        "DWI": "/assets/icons/dwi.jpeg",
    }
    return icon_map.get(modality, "/assets/icons/t1w.png")


def height_to_css(height):
    """
    Convert height specification to CSS value.

    Args:
        height: None, int (pixels), or str (CSS value)

    Returns:
        CSS-compatible height string
    """
    if height is None:
        return "calc(100vh - 260px)"
    if isinstance(height, int):
        return f"{height}px"
    return str(height)


def redcap_fig_or_msg(figs: dict, key: str, msg: str, height: int | str | None = 400, style_extra=None):
    """
    Render a REDCap figure if present and non-empty; otherwise show placeholder.

    Args:
        figs: Dictionary of plotly figures
        key: Key to lookup figure in figs dict
        msg: Message to display if figure not available
        height: Height specification (None, int pixels, or CSS string)
        style_extra: Additional CSS styles to apply

    Returns:
        dcc.Graph component with figure or placeholder div
    """
    fig = figs.get(key)
    style = {"height": height_to_css(height)}
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
    """
    Create a styled card component for REDCap content.

    Args:
        children: Dash components to render inside card
        style_extra: Additional CSS styles to merge with base card style

    Returns:
        html.Div component with card styling
    """
    base = {
        "background": "white",
        "padding": "16px",
        "borderRadius": "12px",
        "border": "1px solid #e5e7eb",
    }
    if style_extra:
        base.update(style_extra)
    return html.Div(children, className="shadow-sm", style=base)


def make_pie(label: str, enrolled: int, target: int, site_colors: dict, emphasize: bool = False):
    """
    Create a pie chart showing enrollment progress.

    Args:
        label: Site name or label
        enrolled: Number of enrolled participants
        target: Target enrollment number
        site_colors: Dictionary mapping site names to color hex codes
        emphasize: If True, make the chart larger and more prominent

    Returns:
        html.Div component with pie chart and enrollment stats
    """
    enrolled_pct = round((enrolled / target * 100), 1) if target else 0
    site_color = site_colors.get(label, "#0F0B01")

    # sizes that fit inside card
    size = 300 if emphasize else 160
    size_factor = 2.2 if emphasize else 1.5
    fig = go.Figure()
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
    fig.update_traces(marker_line=dict(color="white", width=2))
    fig.update_layout(
        height=size,
        width=size,
        margin=dict(t=10, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        annotations=[
            dict(
                text=f"<b>{enrolled_pct:.1f}%</b>",
                x=0.5,
                y=0.5,
                showarrow=False,
                align="center",
                font=dict(size=int(18 * size_factor), color="#111", family="Inter, sans-serif"),
            )
        ],
    )

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
            "textAlign": "center",
            "margin": "10px",
            "padding": "12px",
            "borderRadius": "12px",
            "background": gradient_color,
            "boxShadow": "0 5px 14px rgba(0,0,0,0.15)" if emphasize else "0 3px 8px rgba(0,0,0,0.1)",
        },
        children=[
            html.H5(label, style={"marginBottom": "4px", "color": site_color, "fontWeight": "600"}),
            html.Div(
                dcc.Graph(figure=fig, config={"displayModeBar": False}, style={"height": "100%", "width": "100%"}),
                style={"width": f"{size}px", "height": f"{size}px", "margin": "0 auto"},
            ),
            html.Div(
                f"{enrolled}/{target} enrolled",
                style={
                    "fontSize": "16px" if emphasize else "15px",
                    "color": "#333",
                    "fontWeight": "600",
                    "marginTop": "4px",
                },
            ),
        ],
    )


def make_modality_summary(mod_data: dict, site_name: str, site_colors: dict):
    """
    Create a modality summary card showing imaging coverage per modality.

    Args:
        mod_data: Dict with 'modalities' list and 'total' count
        site_name: Name of the site
        site_colors: Dictionary mapping site names to color hex codes

    Returns:
        html.Div component with modality coverage card
    """
    site_color = site_colors.get(site_name, "#444")
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
                        style={
                            "flexGrow": 1,
                            "display": "flex",
                            "justifyContent": "space-between",
                            "alignItems": "center",
                        },
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
                                style={
                                    "fontWeight": "700",
                                    "color": color,
                                    "fontSize": "16px",
                                    "whiteSpace": "nowrap",
                                    "paddingLeft": "10px",
                                },
                            ),
                        ],
                    ),
                ],
            )
        )

    return html.Div(
        className="glass-card card-fade",
        style={
            "padding": "26px 30px",
            "borderRadius": "16px",
            "minWidth": "380px",
            "maxWidth": "440px",
            "minHeight": "320px",
            "textAlign": "left",
            "boxShadow": "0 4px 16px rgba(0,0,0,0.12)",
            "background": "linear-gradient(135deg, #ffffff 0%, #f7f7f7 100%)",
        },
        children=[
            html.H4(
                site_name,
                style={"textAlign": "center", "marginBottom": "12px", "color": site_color, "fontWeight": "700"},
            ),
            html.Div(className="site-line", style={"backgroundColor": site_color}),
            html.Div(rows),
            html.Div(
                f"Total subjects: {total}" if total else "No subjects found",
                style={"marginTop": "6px", "fontSize": "13px", "color": "#6b7280"},
            ),
        ],
    )


def make_info_panel(dataset_root: Path, last_updated: str):
    """
    Create collapsible right-side info panel with usage notes.

    Args:
        dataset_root: Path to dataset root directory
        last_updated: Last update timestamp string

    Returns:
        html.Div component with collapsible info panel
    """
    return html.Div(
        [
            # Toggle button (small side tab)
            html.Div(
                "ℹ️",
                id="toggle-panel-btn",
                className="info-toggle-tab",
                n_clicks=0,
                title="Show / Hide usage notes",
            ),
            # Main panel content
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
