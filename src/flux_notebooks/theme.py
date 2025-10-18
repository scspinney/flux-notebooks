# src/flux_notebooks/theme.py
"""
Flux Dashboards theme definitions
Centralized colors and style constants for consistent theming across pages.
"""

# ---------------------------------------------------------------------
# Site colors (used for pies, bars, highlights)
# ---------------------------------------------------------------------
SITE_COLORS = {
    "Montreal": "#1976D2",   # Deep Blue
    "Calgary":  "#E53935",   # Red
    "Toronto":  "#08701B",   # 
}

# ---------------------------------------------------------------------
# Accent colors (used in cards, bars, highlights)
# ---------------------------------------------------------------------
ACCENT_GREEN = "#4CAF50"  # Bright green used for "processed" metrics
ACCENT_GRAY  = "#E0E0E0"  # Neutral background gray

# ---------------------------------------------------------------------
# Typography and base style
# ---------------------------------------------------------------------
BASE_FONT = {
    "family": "Inter, sans-serif",
    "color": "#222",
}

# ---------------------------------------------------------------------
# Glassmorphism card style shared across components
# ---------------------------------------------------------------------
GLASS_CARD_STYLE = {
    "background": "rgba(255,255,255,0.75)",
    "border": "1px solid rgba(255,255,255,0.3)",
    "backdropFilter": "blur(6px)",
    "boxShadow": "0 2px 6px rgba(0,0,0,0.08)",
    "borderRadius": "10px",
    "padding": "15px",
    "margin": "10px",
}

# ---------------------------------------------------------------------
# Utility function for retrieving site color
# ---------------------------------------------------------------------
def get_site_color(site: str) -> str:
    """Return consistent color for a given site (case-insensitive)."""
    for key, val in SITE_COLORS.items():
        if key.lower() == site.lower():
            return val
    return "#9E9E9E"  # fallback gray
