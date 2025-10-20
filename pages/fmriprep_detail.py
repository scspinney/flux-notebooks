import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from pathlib import Path
from flux_notebooks.config import Settings

dash.register_page(
    __name__,
    path_template="/fmriprep-detail/<subject>",
    name="fMRIPrep Detail",
)

S = Settings.from_env()
DATA_ROOT = Path(S.dataset_root) / "derivatives" / "fmriprep"

# def layout(subject=None, **kwargs):
#     subj_root = DATA_ROOT / subject
#     html_reports = sorted((DATA_ROOT.glob(f"{subject}.html"))) or sorted(subj_root.glob("*.html"))
#     fig_dir = subj_root / "figures"

#     if not subj_root.exists():
#         return dbc.Container(
#             html.H4(f"No fMRIPrep data found for {subject}", className="text-center mt-4 text-danger"),
#             fluid=True,
#         )

#     report_links = []
#     for f in html_reports:
#         rel = f.relative_to(DATA_ROOT)
#         report_links.append(
#             html.Li(
#                 html.A(
#                     f.name,
#                     href=f"/fmriprep_files/{rel}",
#                     target="_blank",
#                     style={"color": "#0d6efd", "textDecoration": "none"},
#                 )
#             )
#         )

#     fig_links = []
#     if fig_dir.exists():
#         for f in sorted(fig_dir.glob("*.svg")):
#             rel = f.relative_to(DATA_ROOT)
#             fig_links.append(
#                 html.Li(
#                     html.A(
#                         f.name,
#                         href=f"/fmriprep_files/{rel}",
#                         target="_blank",
#                         style={"color": "#198754", "textDecoration": "none"},
#                     )
#                 )
#             )

#     return dbc.Container(
#         [
#             html.H2(f"fMRIPrep Detail: {subject}", className="mt-4 mb-3 text-center"),
#             dbc.Row(
#                 [
#                     dbc.Col(
#                         [
#                             html.H5("Reports"),
#                             html.Ul(report_links if report_links else [html.Li("No reports found")]),
#                         ],
#                         md=6,
#                     ),
#                     dbc.Col(
#                         [
#                             html.H5("Figures"),
#                             html.Ul(fig_links if fig_links else [html.Li("No figures found")]),
#                         ],
#                         md=6,
#                     ),
#                 ],
#                 className="mb-4",
#             ),
#             dbc.Row(
#                 [
#                     dbc.Col(
#                         dbc.Button("← Back to Subject", href=f"/subject/{subject}", color="danger", className="me-2"),
#                         md="auto",
#                     ),
#                     dbc.Col(
#                         dbc.Button("🧠 Back to fMRIPrep Reports", href="/fmriprep", color="success"),
#                         md="auto",
#                     ),
#                 ],
#                 justify="center",
#             ),
#         ],
#         fluid=True,
#     )

def layout(subject=None, **kwargs):
    subj_root = DATA_ROOT / subject
    # 🔧 fix: check both possible locations
    html_reports = sorted(DATA_ROOT.glob(f"{subject}.html")) or sorted(subj_root.glob("*.html"))
    fig_dir = subj_root / "figures"

    if not subj_root.exists() and not html_reports:
        return dbc.Container(
            html.H4(f"No fMRIPrep data found for {subject}", className="text-center mt-4 text-danger"),
            fluid=True,
        )

    report_links = []
    for f in html_reports:
        rel = f.relative_to(DATA_ROOT)
        report_links.append(
            html.Li(
                html.A(
                    f.name,
                    href=f"/fmriprep_files/{rel}",
                    target="_blank",
                    style={"color": "#0d6efd", "textDecoration": "none"},
                )
            )
        )

    fig_links = []
    if fig_dir.exists():
        for f in sorted(fig_dir.glob("*.svg")):
            rel = f.relative_to(DATA_ROOT)
            fig_links.append(
                html.Li(
                    html.A(
                        f.name,
                        href=f"/fmriprep_files/{rel}",
                        target="_blank",
                        style={"color": "#198754", "textDecoration": "none"},
                    )
                )
            )

    return dbc.Container(
        [
            html.H2(f"fMRIPrep Detail: {subject}", className="mt-4 mb-3 text-center"),
            dbc.Row(
                [
                    dbc.Col([html.H5("Reports"), html.Ul(report_links or [html.Li("No reports found")])], md=6),
                    dbc.Col([html.H5("Figures"), html.Ul(fig_links or [html.Li("No figures found")])], md=6),
                ],
                className="mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(dbc.Button("← Back to Subject", href=f"/subject/{subject}", color="danger", className="me-2"), md="auto"),
                    dbc.Col(dbc.Button("🧠 Back to fMRIPrep Reports", href="/fmriprep", color="success"), md="auto"),
                ],
                justify="center",
            ),
        ],
        fluid=True,
    )
