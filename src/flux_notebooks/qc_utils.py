import pandas as pd
import plotly.express as px
from dash import html
import numpy as np

# Color mapping for human QC ratings
QC_COLOR_MAP = {1: "#E53935", 2: "#F9A825", 3: "#43A047"}

def compute_qc_summary(df):
    """
    Given a per-acquisition DataFrame:
    Columns: ['subject', 'session', 'modality', 'fd_mean', 'tsnr', 'snr_total', 'cnr', 'human_rating']
    Returns a normalized df with z-scores and combined qc_score.
    """
    metrics = ['fd_mean', 'tsnr', 'snr_total', 'cnr']
    for m in metrics:
        if m in df.columns:
            df[m] = pd.to_numeric(df[m], errors='coerce')

    # Compute z-scores per metric (higher = better for all except fd_mean)
    for m in metrics:
        if m not in df.columns:
            continue
        if m == 'fd_mean':
            df[m + '_z'] = -(df[m] - df[m].mean()) / df[m].std(ddof=0)
        else:
            df[m + '_z'] = (df[m] - df[m].mean()) / df[m].std(ddof=0)

    # Average z-scores to get MRIQC composite
    df['mriqc_score'] = df[[m + '_z' for m in metrics if m + '_z' in df]].mean(axis=1)
    df['mriqc_score'] = (df['mriqc_score'] - df['mriqc_score'].min()) / (df['mriqc_score'].max() - df['mriqc_score'].min())

    # Combine with human rating (scaled to 0–1)
    df['human_scaled'] = (df['human_rating'] - 1) / 2
    df['qc_score'] = 0.7 * df['mriqc_score'] + 0.3 * df['human_scaled']

    return df


def make_qc_card(modality, human_rating, qc_score, metrics):
    """Creates a small card representing one modality’s QC."""
    color = QC_COLOR_MAP.get(human_rating, "#999")
    tooltip = "<br>".join([f"{k}: {v:.2f}" for k, v in metrics.items() if pd.notnull(v)])

    return html.Div(
        className="glass-card",
        title=tooltip,
        style={
            "width": "120px",
            "margin": "8px",
            "padding": "8px",
            "textAlign": "center",
            "borderLeft": f"6px solid {color}"
        },
        children=[
            html.Div(modality, style={"fontWeight": "600", "marginBottom": "4px"}),
            html.Div(f"{qc_score:.2f}", style={"fontSize": "14px", "color": color}),
            html.Div(f"QC {human_rating}/3", style={"fontSize": "11px", "color": "#777"})
        ]
    )


def make_subject_qc_overview(df_subject):
    """
    Builds a composite Dash layout for one subject.
    - Session QC cards
    - QC trajectory line chart
    """
    df_subject = compute_qc_summary(df_subject)

    session_cards = []
    for ses, subdf in df_subject.groupby("session"):
        cards = [make_qc_card(row['modality'], row['human_rating'], row['qc_score'],
                              {"fd_mean": row.get("fd_mean"), "tsnr": row.get("tsnr"),
                               "snr_total": row.get("snr_total"), "cnr": row.get("cnr")})
                 for _, row in subdf.iterrows()]

        session_cards.append(html.Div(
            style={"display": "flex", "flexDirection": "row", "alignItems": "center", "marginBottom": "10px"},
            children=[html.H6(ses, style={"width": "80px", "marginRight": "10px"})] + cards
        ))

    # QC trajectory line
    df_avg = df_subject.groupby("session", as_index=False)["qc_score"].mean()
    fig = px.line(df_avg, x="session", y="qc_score", markers=True)
    fig.update_traces(line=dict(width=3), marker=dict(size=10, line=dict(width=1.5, color="white")))
    fig.update_layout(
        height=250,
        margin=dict(t=20, b=20, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(title="Mean QC Score (normalized)", range=[0, 1]),
        xaxis=dict(title="Session")
    )

    return html.Div(
        children=[
            html.H5("Longitudinal Data Quality Summary", style={"marginTop": "20px"}),
            html.Div(session_cards),
            html.Div(
                dcc.Graph(figure=fig, config={"displayModeBar": False}),
                style={"marginTop": "15px"}
            )
        ]
    )
