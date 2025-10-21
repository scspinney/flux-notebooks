# flux_notebooks/pages/assistant_sandbox.py
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
import requests
import dash

dash.register_page(
    __name__,
    path="/assistant_sandbox",
    name="Flux Assistant Sandbox",
    order=999,
    include_in_navbar=False,
)

LLM_API = "http://llm:8081/chat"

layout = html.Div(
    className="flux-assistant-sandbox p-4",
    children=[
        html.H2("🧠 Flux-Assistant Sandbox", className="mb-3 fw-bold"),
        html.P(
            "This is the full-screen mode for the Flux-Assistant. "
            "Ask anything about your dataset — it uses the same tools as the sidebar.",
            className="text-muted mb-4"
        ),
        dbc.Row([
            dbc.Col([
                dcc.Textarea(
                    id="sandbox-input",
                    style={
                        "width": "100%",
                        "height": "150px",
                        "borderRadius": "8px",
                        "border": "1px solid #cbd5e1",
                        "padding": "8px",
                        "fontFamily": "'Inter', 'Segoe UI', sans-serif",
                        "fontSize": "1rem",
                    },
                    placeholder="Ask the assistant anything about your dataset…",
                ),
                html.Div(
                    dbc.Spinner(
                        children=[
                            dbc.Button(
                                "Send",
                                id="sandbox-send",
                                color="info",
                                className="mt-3 fw-semibold px-4",
                            )
                        ],
                        type="grow",
                        color="info",
                        spinner_style={"marginLeft": "10px"},
                        id="sandbox-spinner",
                    ),
                    className="d-flex align-items-center",
                ),
                # Output container
                html.Div(id="sandbox-response", className="mt-4"),
            ])
        ])
    ]
)


@callback(
    Output("sandbox-response", "children"),
    Input("sandbox-send", "n_clicks"),
    State("sandbox-input", "value"),
    prevent_initial_call=True,
)
def query_assistant(n_clicks, user_input):
    """Handles sandbox messages to the LLM and renders both text and image responses."""
    if not user_input:
        return dbc.Alert("Please enter a message.", color="warning")

    try:
        payload = {"message": user_input}
        resp = requests.post(LLM_API, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        print(f"[DEBUG][Sandbox] Assistant returned keys: {list(data.keys())}")

        # 🧠 Text response
        if "response" in data:
            return dcc.Markdown(
                data["response"],
                className="flux-chat-markdown",
                style={
                    "whiteSpace": "pre-wrap",
                    "backgroundColor": "#f8fafc",
                    "padding": "18px",
                    "borderRadius": "10px",
                    "border": "1px solid #e2e8f0",
                    "fontFamily": "'Inter', 'Segoe UI', sans-serif",
                    "lineHeight": "1.55",
                },
            )

        # 🖼️ Image response
        elif "image_base64" in data:
            return html.Img(
                src=f"data:image/png;base64,{data['image_base64']}",
                style={
                    "maxWidth": "100%",
                    "borderRadius": "12px",
                    "boxShadow": "0 2px 6px rgba(0,0,0,0.25)",
                    "marginTop": "10px",
                },
            )

        # 🧩 Any other structured response
        elif isinstance(data, dict):
            return dcc.Markdown(
                f"```\n{data}\n```",
                style={
                    "backgroundColor": "#f1f5f9",
                    "padding": "12px",
                    "borderRadius": "8px",
                    "whiteSpace": "pre-wrap",
                },
            )

        # ⚠️ Fallback
        else:
            return dbc.Alert(f"Unexpected response: {data}", color="danger")

    except requests.exceptions.Timeout:
        return dbc.Alert("⚠️ The assistant took too long to respond.", color="warning")
    except Exception as e:
        return dbc.Alert(f"⚠️ Error contacting assistant: {e}", color="danger")
