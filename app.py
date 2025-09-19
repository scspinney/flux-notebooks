from dash import Dash, html, dcc
import dash
import dash_bootstrap_components as dbc

#app = Dash(__name__, use_pages=True)
app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.DARKLY],  # Dark theme
)
app.title = "Flux Dashboards"

app.layout = html.Div([
    html.H1("Flux Dashboards"),
    html.Div([
        dcc.Link(page["name"], href=page["path"], style={"marginRight": "15px"})
        for page in dash.page_registry.values()
    ]),
    dash.page_container
])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=True)
