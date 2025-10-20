import plotly.graph_objects as go


def fluxify_fig(fig: go.Figure, auto_height: bool = True) -> go.Figure:
    """
    Apply Flux Dashboards' aesthetic standard to any Plotly figure.
    Ensures legible tick labels, proper margins, consistent fonts and colors.
    Removes redundant x-axis titles but keeps tick labels for all facets.
    """
    if not fig or not getattr(fig, "layout", None):
        return fig

    # === Base layout ===
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Inter, system-ui, sans-serif", size=13, color="#1e293b"),
        title=dict(
            font=dict(size=17, color="#111827", family="Inter, system-ui, sans-serif"),
            x=0.5, xanchor="center",
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)",
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5,
            font=dict(size=12),
        ),
        margin=dict(l=70, r=50, t=60, b=100),
        plot_bgcolor="white",
        paper_bgcolor="white",
        hoverlabel=dict(font_size=12, font_family="Inter, system-ui, sans-serif"),
        bargap=0.25,
    )

    # === Axis and grid cleanup ===
    for ax in fig.layout:
        if ax.startswith("xaxis") or ax.startswith("yaxis"):
            axis = fig.layout[ax]
            axis.title.font.size = 13
            axis.tickfont.size = 11
            axis.automargin = True
            axis.showgrid = True
            axis.gridcolor = "#e5e7eb"
            if ax.startswith("xaxis"):
                axis.tickangle = 30 if len(getattr(fig, "data", [])) > 3 else 0
                # ✅ Keep tick labels, remove axis title
                axis.showticklabels = True
                axis.title.text = None

    # === Dynamic height for subplot grids ===
    if auto_height:
        n_facets = sum(1 for k in fig.layout if k.startswith("yaxis"))
        fig.update_layout(height=min(250 * n_facets, 1800) if n_facets > 4 else 550)

    return fig
