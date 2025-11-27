"""
Helper functions for BIDS page.

This module contains utility functions extracted from pages/bids.py
to support the BIDS directory tree visualization and file preview interface.
"""

from pathlib import Path
import json
import pandas as pd
from dash import html


def render_dir_tree(path: Path, level: int = 0):
    """
    Recursively render a collapsible tree structure from a path with previews for JSON/TSV files.

    Args:
        path: Path to directory or file to render
        level: Current depth level for indentation (default: 0)

    Returns:
        List of Dash HTML components representing the directory tree
    """
    if not path.exists():
        return html.Div(f"⚠️ Path not found: {path}", style={"color": "red"})

    indent = 20 * level
    entries = sorted(
        [p for p in path.iterdir() if not p.name.startswith(".")],
        key=lambda p: (not p.is_dir(), p.name.lower()),
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
                    preview = html.Div(
                        f"⚠️ Could not parse JSON: {e}",
                        style={"color": "red", "marginLeft": f"{indent + 25}px"},
                    )

            elif entry.suffix.lower() == ".tsv":
                try:
                    df = pd.read_csv(entry, sep="\t")
                    preview = html.Div(
                        [
                            html.Table(
                                [
                                    html.Thead(html.Tr([html.Th(col) for col in df.columns])),
                                    html.Tbody(
                                        [
                                            html.Tr([html.Td(str(df.iloc[i, j])) for j in range(len(df.columns))])
                                            for i in range(min(10, len(df)))
                                        ]
                                    ),
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
                    preview = html.Div(
                        f"⚠️ Could not read TSV: {e}",
                        style={"color": "red", "marginLeft": f"{indent + 25}px"},
                    )

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


def make_bids_info_panel(dataset_root: Path, last_updated: str):
    """
    Create collapsible right-side info panel for the BIDS Summary page.

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
                id="toggle-panel-btn-bids",
                className="info-toggle-tab",
                n_clicks=0,
                title="Show / Hide usage notes",
            ),
            # Panel content
            html.Div(
                id="info-panel-content-bids",
                className="floating-info-panel collapsed",
                children=[
                    html.H5("💡 Understanding the BIDS Summary", style={"marginBottom": "0.6rem"}),
                    html.P(
                        [
                            "BIDS (Brain Imaging Data Structure) is a community standard for organizing and describing neuroimaging data. ",
                            html.A(
                                "Read the official BIDS specification →",
                                href="https://bids.neuroimaging.io/",
                                target="_blank",
                                style={
                                    "color": "#2563eb",
                                    "fontWeight": "600",
                                    "textDecoration": "none",
                                },
                            ),
                        ],
                        style={"fontSize": "0.95rem", "color": "#374151", "lineHeight": "1.5"},
                    ),
                    html.P(
                        "The panel below explains how to navigate and interpret your dataset's directory structure, "
                        "preview metadata files, and verify BIDS compliance at a glance.",
                        style={"fontSize": "0.9rem", "color": "#4b5563", "marginTop": "10px"},
                    ),
                    html.Hr(),
                    html.H6("📁 Directory Tree"),
                    html.Ul(
                        [
                            html.Li("Click folders to expand or collapse them."),
                            html.Li("Blue folder icons indicate directories; gray icons indicate files."),
                            html.Li("Hidden (dot) files are omitted by default."),
                        ],
                        style={"fontSize": "0.9rem", "color": "#4b5563", "paddingLeft": "1.1rem"},
                    ),
                    html.H6("🧾 File Previews", style={"marginTop": "0.8rem"}),
                    html.Ul(
                        [
                            html.Li("JSON files show key-value metadata in readable form."),
                            html.Li("TSV files preview the first 10 rows for quick inspection."),
                            html.Li("Large files or invalid formats will display a parsing warning."),
                        ],
                        style={"fontSize": "0.9rem", "color": "#4b5563", "paddingLeft": "1.1rem"},
                    ),
                    html.H6("🧠 BIDS Structure Tips", style={"marginTop": "0.8rem"}),
                    html.Ul(
                        [
                            html.Li("All subjects are named `sub-XXXX` and sessions `ses-YY`."),
                            html.Li("Anatomical data are under `/anat`, functional under `/func`, etc."),
                            html.Li(
                                "Check that required files like `dataset_description.json` and `participants.tsv` are present."
                            ),
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
