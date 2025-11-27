"""
Helper functions for REDCap page.

This module contains utility functions extracted from pages/redcap.py
to support the REDCap demographics and data visualization interface.
"""

from dash import html, dcc


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


def fig_or_msg(key: str, msg: str, figs: dict, height: int | str | None = 400, style_extra=None):
    """
    Render a figure if present and non-empty; otherwise show a gentle placeholder.

    Args:
        key: Key to lookup figure in figs dict
        msg: Message to display if figure not available
        figs: Dictionary of plotly figures
        height: Height specification (None, int pixels, or CSS string)
        style_extra: Additional CSS styles to apply

    Returns:
        dcc.Graph component with figure or placeholder div
    """
    fig = figs.get(key)
    style = {"height": height_to_css(height)}
    if style_extra:
        style.update(style_extra)
    if fig is not None and getattr(fig, "data", None):  # non-empty figure
        # Smaller mode bar, no logo; figures produced upstream should already be plotly_white
        return dcc.Graph(
            figure=fig,
            style=style,
            config={
                "displaylogo": False,
                "modeBarButtonsToRemove": [
                    "lasso2d", "select2d", "autoScale2d", "toggleSpikelines",
                    # 👇 remove "toImage" from here so the download PNG button appears
                    "zoomIn2d", "zoomOut2d", "hoverClosestCartesian",
                ],
                "toImageButtonOptions": {
                    "format": "png",
                    "filename": key.replace(" ", "_"),
                    "scale": 2,          # higher = better quality
                    "width": None,       # defaults to graph width
                    "height": None,      # defaults to graph height
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
            "color": "#6b7280",           # slate-500
            "background": "#f8fafc",      # slate-50
            "border": "1px dashed #e5e7eb",
            "borderRadius": "10px",
        },
    )


def card(children, style_extra=None):
    """
    Create a styled card component with shadow and border.

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


def kpi(value, label, sub=None):
    """
    Create a KPI (Key Performance Indicator) card with value and label.

    Args:
        value: Primary value to display (number or string)
        label: Label text describing the metric
        sub: Optional subtitle text

    Returns:
        Card component with KPI layout
    """
    return card(
        [
            html.Div(f"{value}", style={"fontSize": "28px", "fontWeight": 800}),
            html.Div(label, style={"color": "#6b7280", "fontSize": "13px"}),
            html.Div(sub or "", style={"color": "#9ca3af", "fontSize": "12px", "marginTop": "4px"}),
        ],
        style_extra={"padding": "14px 16px"},
    )


def fmt_pct(num, den):
    """
    Format a percentage from numerator and denominator.

    Args:
        num: Numerator value
        den: Denominator value

    Returns:
        Formatted percentage string (e.g., "75%") or "—" if invalid
    """
    try:
        if den <= 0:
            return "—"
        return f"{(100.0 * num / den):.0f}%"
    except Exception:
        return "—"


# Common layout styles
GRID_STYLES = {
    "grid1": {"display": "grid", "gridTemplateColumns": "1fr", "gap": "16px"},
    "grid2": {"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px"},
    "grid3": {"display": "grid", "gridTemplateColumns": "repeat(3, 1fr)", "gap": "16px"},
    "grid_wrap": {
        "display": "grid",
        "gap": "16px",
        "gridTemplateColumns": "repeat(auto-fit, minmax(280px, 1fr))",
    },
}

# Tab styles
TAB_STYLES = {
    "default": {
        "padding": "10px 14px",
        "fontWeight": 600,
        "color": "#111827",
        "background": "#f3f4f6",
        "border": "1px solid #e5e7eb",
        "borderBottom": "none",
        "borderRadius": "10px 10px 0 0",
    },
    "selected": {
        "padding": "10px 14px",
        "fontWeight": 600,
        "color": "#111827",
        "background": "#ffffff",
        "border": "1px solid #e5e7eb",
        "borderBottom": "none",
        "borderRadius": "10px 10px 0 0",
        "borderTop": "3px solid #2563eb",
    },
}
