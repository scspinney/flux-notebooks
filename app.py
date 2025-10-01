# app.py
import os
import logging
from pathlib import Path

from dash import Dash, dcc, html
import dash
import dash_bootstrap_components as dbc

# ── Safe env defaults so pages that read settings don't explode ───────────────
ROOT = Path(__file__).resolve().parent
os.environ.setdefault("FLUX_DATASET_ROOT", str(ROOT / "superdemo"))
os.environ.setdefault("FLUX_REDCAP_ROOT", str(ROOT / "data" / "redcap"))

# ── Fancy navbar (pill-style links, brand, responsive wrap) ───────────────────
def nav_bar():
    items = [
        dbc.NavItem(
            dbc.NavLink(
                page["name"],
                href=page["path"],
                active="exact",         # auto-highlight current page
                class_name="px-3 py-2", # comfy hitbox
            )
        )
        for page in sorted(dash.page_registry.values(), key=lambda p: p["path"])
    ]

    return dbc.Navbar(
        dbc.Container(
            [
                dbc.NavbarBrand("Flux Dashboards", class_name="fs-2 fw-bold"),
                dbc.Nav(items, pills=True, class_name="ms-2 flex-wrap"),
            ],
            fluid=True,
        ),
        color="dark",
        dark=True,
        class_name="mb-3 shadow-sm",
    )

# ── App ───────────────────────────────────────────────────────────────────────
app = Dash(
    __name__,
    use_pages=True,
    suppress_callback_exceptions=True,          # pages may reference ids not in initial layout
    external_stylesheets=[dbc.themes.DARKLY],   # dark theme
    title="Flux Dashboards",
)

# Optional: louder logs while debugging
app.logger.setLevel(logging.DEBUG)
app.server.logger.setLevel(logging.DEBUG)

# ── Layout (must exist before app.run) ────────────────────────────────────────
app.layout = html.Div(
    [
        dcc.Location(id="url"),     # keeps URL/router in sync (helps with Dash Pages)
        nav_bar(),                  # pretty navbar with pills
        html.Div(dash.page_container, className="container-fluid px-3"),  # active page content
    ]
)

# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Dash ≥2.17 prefers app.run over app.run_server
    app.run(host="0.0.0.0", port=8050, debug=True)
