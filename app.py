#!/usr/bin/env python3
"""
Flux Dashboards – unified entrypoint for all Dash pages.
Now includes a robust MRIQC HTML rewriter and a modern top navigation bar.
"""
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))


import re, mimetypes, logging
from pathlib import Path, PurePosixPath
from flask import Response, send_file, send_from_directory, abort
import dash
from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
from flux_notebooks.config import Settings

# ╭─────────────────────────────────────────────────────────────╮
# │ 1. Environment setup                                        │
# ╰─────────────────────────────────────────────────────────────╯
ROOT = Path(__file__).resolve().parent
os.environ.setdefault("FLUX_DATASET_ROOT", str(ROOT / "superdemo_real"))
os.environ.setdefault("FLUX_REDCAP_ROOT", str(ROOT / "data" / "redcap"))

S = Settings.from_env()
DATASET_ROOT = Path(S.dataset_root).resolve()
DATA_ROOT = (DATASET_ROOT / "qc" / "mriqc").resolve()

if not DATASET_ROOT.exists():
    print(f"[WARN] Dataset root missing → {DATASET_ROOT}")
else:
    print(f"[INFO] Using dataset root → {DATASET_ROOT}")

# ╭─────────────────────────────────────────────────────────────╮
# │ 2. Navbar (Flux-styled Bootstrap)                           │
# ╰─────────────────────────────────────────────────────────────╯
def build_navbar():
    """Unified top navigation bar using Bootstrap."""
    HIDDEN_PAGES = {"MRIQC Detail", "fMRIPrep Detail", "FreeSurfer Summary"}
    pages = [p for p in dash.page_registry.values() if p["name"] not in HIDDEN_PAGES]
    
    nav_links = [
        dbc.NavItem(dbc.NavLink(page["name"], href=page["path"], active="exact"))
        for page in pages
    ]
    return dbc.Navbar(
        dbc.Container(
            [
                dbc.NavbarBrand("BIDS-Flux Dashboards", href="/", class_name="fw-bold fs-4 me-4"),
                dbc.Nav(nav_links, pills=True, navbar=True),
            ],
            fluid=True,
        ),
        color="#002B4E",   # Flux navy
        dark=True,
        sticky="top",
        class_name="shadow-sm mb-4",
        style={
            "background": "linear-gradient(90deg, #002B4E 0%, #003E6B 100%)",
            "padding": "0.6rem 1.2rem",
        },
    )

# ╭─────────────────────────────────────────────────────────────╮
# │ 3. App initialization                                       │
# ╰─────────────────────────────────────────────────────────────╯
app = Dash(
    __name__,
    use_pages=True,
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.MINTY],
    title="BIDS-Flux Dashboards",
)

server = app.server
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
app.logger.setLevel(logging.DEBUG)

# Global index overrides
app.index_string = """
<!DOCTYPE html>
<html>
<head>
  {%metas%}
  <title>BIDS-Flux Dashboards</title>
  {%favicon%}
  {%css%}
  <style>
    body {
      font-family: 'Inter', sans-serif;
      background-color: #f8f9fa;
      margin: 0;
      padding: 0;
    }
    .card-fade {
      opacity: 0;
      transform: translateY(10px);
      animation: fadeInUp 0.6s ease forwards;
    }
    @keyframes fadeInUp {
      from { opacity: 0; transform: translateY(15px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .glass-card {
      background: rgba(255,255,255,0.75);
      border: 1px solid rgba(255,255,255,0.3);
      backdrop-filter: blur(6px);
      box-shadow: 0 2px 6px rgba(0,0,0,0.08);
    }
  </style>
</head>
<body>
  {%app_entry%}
  <footer>
    {%config%}
    {%scripts%}
    {%renderer%}
  </footer>
</body>
</html>
"""

# Layout: Navbar + Page container + Footer
app.layout = html.Div(
    [
        dcc.Location(id="url"),
        build_navbar(),
        html.Div(dash.page_container, id="page-content", className="container-fluid px-4"),
        html.Footer(
            "© 2025 BIDS-Flux Dashboards",
            className="text-center text-muted mt-5 mb-3 small",
        ),
    ]
)

# ╭─────────────────────────────────────────────────────────────╮
# │ 4. MRIQC HTML Rewriter Helpers                              │
# ╰─────────────────────────────────────────────────────────────╯
def _is_external(u: str) -> bool:
    u = u.strip().lower()
    return u.startswith(("http://", "https://", "data:", "mailto:", "javascript:", "#"))

def _normalize_duplicate_subdirs(path: Path) -> Path:
    parts = list(path.parts)
    for i in range(len(parts) - 1):
        if parts[i] == parts[i + 1] and parts[i].startswith("sub-"):
            del parts[i]
            break
    return Path(*parts)

def _safe_full_path(rel_or_abs: str, base_dir: Path) -> Path | None:
    tgt = PurePosixPath(rel_or_abs)
    if str(tgt).startswith("/mriqc_files/"):
        rel_part = str(tgt).removeprefix("/mriqc_files/").lstrip("/")
        full = (DATA_ROOT / rel_part).resolve()
    else:
        full = (base_dir / str(tgt)).resolve()
    full = _normalize_duplicate_subdirs(full)
    try:
        full.relative_to(DATA_ROOT)
    except ValueError:
        return None
    return full

_ATTR_PATTERN = re.compile(r'(?P<attr>\b(?:src|href|data)\b)\s*=\s*([\'"])(?P<url>[^\'"]+)\2', re.IGNORECASE)

def _rewrite_html_urls(html_text: str, html_path: Path) -> str:
    base_dir = html_path.parent.resolve()

    def repl(m: re.Match) -> str:
        attr, url = m.group("attr"), m.group("url").strip()
        url = re.sub(r"^https:/([^/])", r"https://\1", url)
        url = re.sub(r"^http:/([^/])", r"http://\1", url)
        if _is_external(url):
            return f'{attr}="{url}"'

        url = re.sub(r"^\./sub-[^/]+/\.\./\.\./sub-[^/]+/figures/", "sub-001/figures/", url)
        url = re.sub(r"^\.\./sub-[^/]+/figures/", "sub-001/figures/", url)
        url = re.sub(r"^\./sub-[^/]+/figures/", "sub-001/figures/", url)
        url = re.sub(r"^sub-[^/]+/figures/", "sub-001/figures/", url)
        url = re.sub(r"(\.\./)+", "../", url)

        full = (base_dir / url).resolve()
        parts = list(full.parts)
        for i in range(len(parts) - 1):
            if parts[i].startswith("sub-") and i + 1 < len(parts) and parts[i + 1] == parts[i]:
                del parts[i]
                break
        full = Path(*parts)

        if not full.exists():
            subj = next((p for p in html_path.parts if p.startswith("sub-")), "sub-001")
            alt = DATA_ROOT / subj / "figures" / Path(url).name
            if alt.exists():
                full = alt
            else:
                app.logger.warning(f"⚠️ Missing after rewrite: {url}")
                return m.group(0)

        rel = full.relative_to(DATA_ROOT)
        return f'{attr}="/mriqc_files/{rel.as_posix()}"'

    rewritten = _ATTR_PATTERN.sub(repl, html_text)
    return re.sub(r'(sub-[^/]+/)sub-[^/]+/', r'\1', rewritten)

def _send_any_file(full: Path):
    if not full.exists() or not full.is_file():
        app.logger.warning(f"⚠️ Missing MRIQC file: {full}")
        abort(404)
    mime, _ = mimetypes.guess_type(str(full))
    if mime == "text/html":
        txt = full.read_text(encoding="utf-8", errors="ignore")
        rewritten = _rewrite_html_urls(txt, full)
        return Response(rewritten, mimetype="text/html; charset=utf-8")
    return send_file(full)

# ╭─────────────────────────────────────────────────────────────╮
# │ 5. Flask routes                                             │
# ╰─────────────────────────────────────────────────────────────╯
@server.route("/mriqc_files/<path:relpath>")
def serve_mriqc(relpath: str):
    full = (DATA_ROOT / relpath).resolve()
    full = _normalize_duplicate_subdirs(full)
    try:
        full.relative_to(DATA_ROOT)
    except ValueError:
        abort(403)
    app.logger.info(f"📄 Serving MRIQC file: {full}")
    return _send_any_file(full)

# @server.route("/fmriprep_files/<path:relpath>")
# def serve_fmriprep(relpath: str):
#     fmriprep_root = (DATASET_ROOT / "derivatives" / "fmriprep").resolve()
#     full = (fmriprep_root / relpath).resolve()
#     try:
#         full.relative_to(fmriprep_root)
#     except ValueError:
#         abort(403)
#     app.logger.info(f"📄 Serving fMRIPrep file: {full}")
#     return send_file(full)

@app.server.route("/fmriprep_files/<path:filename>")
def serve_fmriprep(filename):
    full = Path(S.dataset_root) / "derivatives" / "fmriprep" / filename
    if not full.exists():
        return f"File not found: {full}", 404
    return send_file(full)


@server.route("/assets/<path:path>")
def serve_assets(path):
    file_path = DATASET_ROOT / path
    if not file_path.exists():
        app.logger.warning(f"[404] Asset not found: {file_path}")
        abort(404)
    return send_from_directory(DATASET_ROOT, path)

@server.route("/static/<path:subpath>")
def serve_static(subpath):
    root = Path(os.environ.get("FLUX_DATASET_ROOT", "superdemo_real")).resolve()
    full_path = (root / subpath).resolve()
    if not str(full_path).startswith(str(root)):
        abort(403)
    if not full_path.exists():
        abort(404)
    app.logger.info(f"📄 Serving static file: {full_path}")
    return send_file(str(full_path))

# ╭─────────────────────────────────────────────────────────────╮
# │ 6. Main entrypoint                                          │
# ╰─────────────────────────────────────────────────────────────╯
if __name__ == "__main__":
    print("\n🚀 Launching Flux Dashboards with navbar...")
    app.run(host="0.0.0.0", port=8050, debug=False)










# #!/usr/bin/env python3
# """
# Flux Dashboards – unified entrypoint for all Dash pages.

# Now includes a robust MRIQC HTML rewriter that fixes broken relative paths
# (e.g. "../../sub-001/figures/...") and redundant subdir nesting like
# "sub-001/sub-001/figures/...".
# """

# import os, re, mimetypes, logging
# from pathlib import Path, PurePosixPath
# from flask import Response, send_file, send_from_directory, abort
# import dash
# from dash import Dash, html, dcc
# import dash_bootstrap_components as dbc
# from flux_notebooks.config import Settings

# # ╭─────────────────────────────────────────────────────────────╮
# # │ 1. Environment setup                                        │
# # ╰─────────────────────────────────────────────────────────────╯
# ROOT = Path(__file__).resolve().parent
# os.environ.setdefault("FLUX_DATASET_ROOT", str(ROOT / "superdemo_real"))
# os.environ.setdefault("FLUX_REDCAP_ROOT", str(ROOT / "data" / "redcap"))

# S = Settings.from_env()
# DATASET_ROOT = Path(S.dataset_root).resolve()
# DATA_ROOT = (DATASET_ROOT / "qc" / "mriqc").resolve()

# if not DATASET_ROOT.exists():
#     print(f"[WARN] Dataset root missing → {DATASET_ROOT}")
# else:
#     print(f"[INFO] Using dataset root → {DATASET_ROOT}")

# # ╭─────────────────────────────────────────────────────────────╮
# # │ 2. Navbar builder                                           │
# # ╰─────────────────────────────────────────────────────────────╯
# def nav_bar():
#     pages = sorted(dash.page_registry.values(), key=lambda p: p["path"])
#     nav_items = [
#         dbc.NavItem(dbc.NavLink(page["name"], href=page["path"], active="exact"))
#         for page in pages
#     ]
#     return dbc.Navbar(
#         dbc.Container(
#             [
#                 dbc.NavbarBrand("Flux Dashboards", class_name="fs-3 fw-bold me-3"),
#                 dbc.Nav(nav_items, pills=True),
#             ],
#             fluid=True,
#         ),
#         color="dark",
#         dark=True,
#         class_name="mb-3 shadow-sm",
#     )

# # ╭─────────────────────────────────────────────────────────────╮
# # │ 3. App initialization                                       │
# # ╰─────────────────────────────────────────────────────────────╯
# app = Dash(
#     __name__,
#     use_pages=True,
#     suppress_callback_exceptions=True,
#     #external_stylesheets=[dbc.themes.BOOTSTRAP],
#     external_stylesheets=[
#         {
#             "href": "https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap",
#             "rel": "stylesheet",
#         }
#     ],
#     title="Flux Dashboards",
# )


# app.index_string = """
# <!DOCTYPE html>
# <html>
# <head>
#   {%metas%}
#   <title>Flux Dashboards</title>
#   {%favicon%}
#   {%css%}
#   <style>
#     body {
#       font-family: 'Inter', sans-serif;
#       background-color: #f8f9fa;
#     }

#     .card-fade {
#       opacity: 0;
#       transform: translateY(10px);
#       animation: fadeInUp 0.6s ease forwards;
#     }

#     @keyframes fadeInUp {
#       from { opacity: 0; transform: translateY(15px); }
#       to { opacity: 1; transform: translateY(0); }
#     }

#     .glass-card {
#       background: rgba(255,255,255,0.75);
#       border: 1px solid rgba(255,255,255,0.3);
#       backdrop-filter: blur(6px);
#       box-shadow: 0 2px 6px rgba(0,0,0,0.08);
#     }

#     .site-line {
#       height: 4px;
#       width: 40%;
#       margin: 0 auto 15px;
#       border-radius: 2px;
#     }
#   </style>
# </head>
# <body>
#   {%app_entry%}
#   <footer>
#     {%config%}
#     {%scripts%}
#     {%renderer%}
#   </footer>
# </body>
# </html>
# """


# server = app.server

# app.server.static_url_path = '/mriqc_files'
# app.server.static_folder = str(DATA_ROOT)

# logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
# app.logger.setLevel(logging.DEBUG)

# app.layout = html.Div(
#     [dcc.Location(id="url"), nav_bar(), html.Div(dash.page_container, id="page-content", className="container-fluid px-3")]
# )

# # ╭─────────────────────────────────────────────────────────────╮
# # │ 4. MRIQC HTML Rewriter Helpers                              │
# # ╰─────────────────────────────────────────────────────────────╯
# def _is_external(u: str) -> bool:
#     u = u.strip().lower()
#     return u.startswith(("http://", "https://", "data:", "mailto:", "javascript:", "#"))

# def _normalize_duplicate_subdirs(path: Path) -> Path:
#     """
#     Collapse redundant duplicate subdirs like sub-001/sub-001/figures → sub-001/figures
#     """
#     parts = list(path.parts)
#     for i in range(len(parts) - 1):
#         if parts[i] == parts[i + 1] and parts[i].startswith("sub-"):
#             del parts[i]
#             break
#     return Path(*parts)

# def _safe_full_path(rel_or_abs: str, base_dir: Path) -> Path | None:
#     tgt = PurePosixPath(rel_or_abs)
#     if str(tgt).startswith("/mriqc_files/"):
#         rel_part = str(tgt).removeprefix("/mriqc_files/").lstrip("/")
#         full = (DATA_ROOT / rel_part).resolve()
#     else:
#         full = (base_dir / str(tgt)).resolve()

#     full = _normalize_duplicate_subdirs(full)  # 🩹 critical fix

#     try:
#         full.relative_to(DATA_ROOT)
#     except ValueError:
#         return None
#     return full

# _ATTR_PATTERN = re.compile(
#     r'(?P<attr>\b(?:src|href|data)\b)\s*=\s*([\'"])(?P<url>[^\'"]+)\2', re.IGNORECASE
# )

# def _rewrite_html_urls(html_text: str, html_path: Path) -> str:
#     base_dir = html_path.parent.resolve()

#     def repl(m: re.Match) -> str:
#         attr = m.group("attr")
#         url = m.group("url").strip()

#         # Fix malformed external URLs (missing slashes)
#         url = re.sub(r"^https:/([^/])", r"https://\1", url)
#         url = re.sub(r"^http:/([^/])", r"http://\1", url)

#         # Leave valid external or anchor URLs untouched
#         if _is_external(url):
#             return f'{attr}="{url}"'

#         # 🧠 MRIQC emits crazy stuff like:
#         # ./sub-001/../../sub-001/figures/sub-001_ses-1a_desc-background_T1w.svg
#         # sub-001/../../sub-001/figures/... or ../sub-001/figures/...
#         url = re.sub(r"^\./sub-[^/]+/\.\./\.\./sub-[^/]+/figures/", "sub-001/figures/", url)
#         url = re.sub(r"^\.\./sub-[^/]+/figures/", "sub-001/figures/", url)
#         url = re.sub(r"^\./sub-[^/]+/figures/", "sub-001/figures/", url)
#         url = re.sub(r"^sub-[^/]+/figures/", "sub-001/figures/", url)

#         # Simplify redundant "../"
#         url = re.sub(r"(\.\./)+", "../", url)

#         # Build absolute path
#         full = (base_dir / url).resolve()

#         # Collapse redundant subdir duplication (sub-001/sub-001/)
#         parts = list(full.parts)
#         for i in range(len(parts) - 1):
#             if parts[i].startswith("sub-") and i + 1 < len(parts) and parts[i + 1] == parts[i]:
#                 del parts[i]
#                 break
#         full = Path(*parts)

#         # Fallback if still missing
#         if not full.exists():
#             subj = next((p for p in html_path.parts if p.startswith("sub-")), "sub-001")
#             alt = DATA_ROOT / subj / "figures" / Path(url).name
#             if alt.exists():
#                 full = alt
#             else:
#                 app.logger.warning(f"⚠️ Still missing after rewrite: {url}")
#                 return m.group(0)

#         rel = full.relative_to(DATA_ROOT)
#         new_url = f"/mriqc_files/{rel.as_posix()}"
#         return f'{attr}="{new_url}"'

#     rewritten = _ATTR_PATTERN.sub(repl, html_text)
#     rewritten = re.sub(r'(sub-[^/]+/)sub-[^/]+/', r'\1', rewritten)
#     return rewritten






# def _send_any_file(full: Path):
#     if not full.exists() or not full.is_file():
#         app.logger.warning(f"⚠️ Missing MRIQC file: {full}")
#         abort(404)
#     mime, _ = mimetypes.guess_type(str(full))
#     if mime == "text/html":
#         txt = full.read_text(encoding="utf-8", errors="ignore")
#         rewritten = _rewrite_html_urls(txt, full)
#         return Response(rewritten, mimetype="text/html; charset=utf-8")
#     return send_file(full)

# # ╭─────────────────────────────────────────────────────────────╮
# # │ 5. Routes                                                   │
# # ╰─────────────────────────────────────────────────────────────╯
# @server.route("/mriqc_files/<path:relpath>")
# def serve_mriqc(relpath: str):
#     full = (DATA_ROOT / relpath).resolve()
#     full = _normalize_duplicate_subdirs(full)  # ensure normalized even for direct requests
#     try:
#         full.relative_to(DATA_ROOT)
#     except ValueError:
#         abort(403)
#     app.logger.info(f"📄 Serving MRIQC file: {full}")
#     return _send_any_file(full)

# @server.route("/assets/<path:path>")
# def serve_assets(path):
#     file_path = DATASET_ROOT / path
#     if not file_path.exists():
#         app.logger.warning(f"[404] Asset not found: {file_path}")
#         abort(404)
#     return send_from_directory(DATASET_ROOT, path)

# @server.route("/static/<path:subpath>")
# def serve_static(subpath):
#     root = Path(os.environ.get("FLUX_DATASET_ROOT", "superdemo_real")).resolve()
#     full_path = (root / subpath).resolve()
#     if not str(full_path).startswith(str(root)):
#         app.logger.warning(f"⚠️ Illegal path traversal: {full_path}")
#         abort(403)
#     if not full_path.exists():
#         app.logger.warning(f"⚠️ Missing static file: {full_path}")
#         abort(404)
#     app.logger.info(f"📄 Serving static file: {full_path}")
#     return send_file(str(full_path))

# # ╭─────────────────────────────────────────────────────────────╮
# # │ 6. Main entrypoint                                          │
# # ╰─────────────────────────────────────────────────────────────╯
# if __name__ == "__main__":
#     print("\n🚀 Launching Flux Dashboards...")
#     app.run(host="0.0.0.0", port=8050, debug=False)
