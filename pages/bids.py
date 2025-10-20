import dash
from dash import html, dcc
from pathlib import Path
import os
import json
import pandas as pd

dash.register_page(__name__, path="/bids", name="BIDS Summary")

dataset_root = Path(os.environ.get("FLUX_DATASET_ROOT", "superdemo_real")).resolve()

# ---------------------------------------------------------------------
# Helper: recursively build directory tree as Dash components
# ---------------------------------------------------------------------
# def render_dir_tree(path: Path, level=0):
#     """Recursively render a collapsible tree structure from a path."""
#     if not path.exists():
#         return html.Div(f"⚠️ Path not found: {path}", style={"color": "red"})

#     # Visual indentation
#     indent = 20 * level

#     # Sort: directories first
#     #entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
#     # Skip hidden files and directories (dotfiles)
#     entries = sorted(
#         [p for p in path.iterdir() if not p.name.startswith(".")],
#         key=lambda p: (not p.is_dir(), p.name.lower())
#     )

#     children = []

#     for entry in entries:
#         icon = "📁" if entry.is_dir() else "📄"
#         color = "#2563eb" if entry.is_dir() else "#555"
#         hover_bg = "rgba(37,99,235,0.05)" if entry.is_dir() else "transparent"

#         style = {
#             "marginLeft": f"{indent}px",
#             "fontFamily": "Menlo, monospace",
#             "cursor": "pointer" if entry.is_dir() else "default",
#             "padding": "4px 6px",
#             "borderRadius": "6px",
#             "transition": "all 0.15s ease-in-out",
#         }

#         # Directory node (expandable)
#         if entry.is_dir():
#             children.append(
#                 html.Details(
#                     open=False,
#                     style={"marginBottom": "2px"},
#                     children=[
#                         html.Summary(
#                             [
#                                 html.Span(icon + " ", style={"color": color}),
#                                 html.Span(entry.name, style={"color": color, "fontWeight": "600"}),
#                             ],
#                             style=style,
#                         ),
#                         html.Div(render_dir_tree(entry, level + 1)),
#                     ],
#                 )
#             )
#         else:
#             children.append(
#                 html.Div(
#                     [html.Span(icon + " ", style={"color": "#aaa"}), html.Span(entry.name)],
#                     style={**style, "color": "#444", "paddingLeft": "6px"},
#                 )
#             )
#     return children



def render_dir_tree(path: Path, level=0):
    """Recursively render a collapsible tree structure from a path with previews for JSON/TSV files."""
    if not path.exists():
        return html.Div(f"⚠️ Path not found: {path}", style={"color": "red"})

    indent = 20 * level
    entries = sorted(
        [p for p in path.iterdir() if not p.name.startswith(".")],
        key=lambda p: (not p.is_dir(), p.name.lower())
    )

    children = []

    for entry in entries:
        icon = "📁" if entry.is_dir() else "📄"
        color = "#2563eb" if entry.is_dir() else "#555"
        style = {
            "marginLeft": f"{indent}px",
            "fontFamily": "Menlo, monospace",
            "cursor": "pointer" if entry.is_dir() else "default",
            "padding": "4px 6px",
            "borderRadius": "6px",
            "transition": "all 0.15s ease-in-out",
        }

        # Handle directories recursively
        if entry.is_dir():
            children.append(
                html.Details(
                    open=False,
                    style={"marginBottom": "2px"},
                    children=[
                        html.Summary(
                            [
                                html.Span(icon + " ", style={"color": color}),
                                html.Span(entry.name, style={"color": color, "fontWeight": "600"}),
                            ],
                            style=style,
                        ),
                        html.Div(render_dir_tree(entry, level + 1)),
                    ],
                )
            )
        else:
            # File previews for .json and .tsv
            preview = None
            if entry.suffix.lower() == ".json":
                try:
                    with open(entry, "r") as f:
                        parsed = json.load(f)
                    formatted = json.dumps(parsed, indent=2)
                    preview = html.Pre(
                        formatted,
                        style={
                            "backgroundColor": "#f3f4f6",
                            "padding": "10px",
                            "borderRadius": "8px",
                            "overflowX": "auto",
                            "fontSize": "13px",
                            "marginLeft": f"{indent + 25}px",
                        },
                    )
                except Exception as e:
                    preview = html.Div(f"⚠️ Could not parse JSON: {e}",
                                       style={"color": "red", "marginLeft": f"{indent + 25}px"})
            
            elif entry.suffix.lower() == ".tsv":
                try:
                    df = pd.read_csv(entry, sep="\t")
                    preview = html.Div(
                        [
                            html.Table(
                                [
                                    html.Thead(html.Tr([html.Th(col) for col in df.columns])),
                                    html.Tbody([
                                        html.Tr([html.Td(str(df.iloc[i, j])) for j in range(len(df.columns))])
                                        for i in range(min(10, len(df)))
                                    ])
                                ],
                                style={
                                    "borderCollapse": "collapse",
                                    "width": "90%",
                                    "marginLeft": f"{indent + 25}px",
                                    "backgroundColor": "#fafafa",
                                    "fontSize": "13px",
                                },
                            ),
                            html.Div(
                                f"Showing first {min(10, len(df))} of {len(df)} rows",
                                style={
                                    "color": "#6b7280",
                                    "fontSize": "12px",
                                    "marginLeft": f"{indent + 25}px",
                                    "marginTop": "4px",
                                },
                            ),
                        ]
                    )
                except Exception as e:
                    preview = html.Div(f"⚠️ Could not read TSV: {e}",
                                       style={"color": "red", "marginLeft": f"{indent + 25}px"})

            # File entry (collapsible if preview available)
            if preview:
                children.append(
                    html.Details(
                        style={"marginBottom": "3px"},
                        children=[
                            html.Summary(
                                [
                                    html.Span(icon + " ", style={"color": "#aaa"}),
                                    html.Span(entry.name, style={"color": "#333"}),
                                ],
                                style=style,
                            ),
                            preview,
                        ],
                    )
                )
            else:
                # Plain file with no preview
                children.append(
                    html.Div(
                        [html.Span(icon + " ", style={"color": "#aaa"}), html.Span(entry.name)],
                        style={**style, "color": "#444", "paddingLeft": "6px"},
                    )
                )

    return children


# ---------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------
def layout():
    return html.Div(
        style={
            "fontFamily": "Inter, sans-serif",
            "margin": "30px auto",
            "maxWidth": "1200px",
        },
        children=[
            html.H2("🧠 BIDS Dataset Summary", style={"marginBottom": "10px"}),
            html.P(
                f"Directory structure of BIDS dataset",
                style={"color": "#6b7280", "marginBottom": "25px"},
            ),
            html.Div(
                style={
                    "backgroundColor": "#f9fafb",
                    "padding": "20px 30px",
                    "borderRadius": "10px",
                    "boxShadow": "0 4px 12px rgba(0,0,0,0.08)",
                    "overflowY": "auto",
                    "maxHeight": "75vh",
                },
                children=render_dir_tree(dataset_root),
            ),
        ],
    )
