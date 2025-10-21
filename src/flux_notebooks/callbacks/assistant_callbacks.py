# flux_notebooks/callbacks/assistant_callbacks.py
from dash import Input, Output, State, html, ctx, dcc
import dash_bootstrap_components as dbc
import requests
import os, json

LLM_API_URL = os.getenv("LLM_API_URL")

# Auto-detect fallback if not explicitly set
if not LLM_API_URL:
    # If running inside Docker (detected via hostname), use llm:8081
    if os.path.exists("/.dockerenv"):
        LLM_API_URL = "http://llm:8081/chat"
    else:
        LLM_API_URL = "http://localhost:8081/chat"

print(f"[Flux-Dash] Using LLM API at: {LLM_API_URL}")


def register_assistant_callbacks(app):
    """Attach callbacks for sidebar toggle and LLM chat behavior."""

    # ───────────────────────────────────────────────
    # Sidebar open/close logic
    # ───────────────────────────────────────────────
    @app.callback(
        Output("chat-sidebar", "className"),
        Output("chat-backdrop", "className"),
        Input("chat-tab", "n_clicks"),
        Input("close-chat-btn", "n_clicks"),
        State("chat-sidebar", "className"),
        prevent_initial_call=True,
    )
    def toggle_sidebar(tab_clicks, close_clicks, current):
        current = current or "flux-chat-sidebar"
        triggered = ctx.triggered_id
        is_open = "show" in current

        if triggered == "chat-tab":
            if not is_open:
                return "flux-chat-sidebar show", "flux-chat-backdrop show"
            return "flux-chat-sidebar", "flux-chat-backdrop"

        if triggered == "close-chat-btn":
            return "flux-chat-sidebar", "flux-chat-backdrop"

        return current, "flux-chat-backdrop show" if is_open else "flux-chat-backdrop"

    # ───────────────────────────────────────────────
    # Chat interaction: send → LLM → receive
    # ───────────────────────────────────────────────
    @app.callback(
        Output("chat-history", "children"),
        Input("chat-send-btn", "n_clicks"),
        State("chat-input", "value"),
        State("chat-history", "children"),
        prevent_initial_call=True,
    )
    def send_message(n_clicks, message, history):
        if not message:
            return history

        history = history or []

        # Helper: consistent chat bubble styling
        def bubble(role, content, color=None, bg=None, is_image=False):
            base_style = {
                "margin": "8px 0",
                "padding": "10px 12px",
                "borderRadius": "10px",
                "whiteSpace": "pre-wrap",
                "fontFamily": "'Inter', 'Segoe UI', sans-serif",
                "fontSize": "0.95rem",
                "lineHeight": "1.5",
            }
            if bg:
                base_style["backgroundColor"] = bg
            if color:
                base_style["color"] = color

            prefix = "🧑 You:" if role == "user" else "🤖 Flux:"

            if is_image:
                return html.Div(
                    [
                        html.Strong(prefix),
                        html.Img(
                            src=f"data:image/png;base64,{content}",
                            style={
                                "maxWidth": "100%",
                                "borderRadius": "10px",
                                "marginTop": "8px",
                                "boxShadow": "0 1px 4px rgba(0,0,0,0.1)",
                            },
                        ),
                    ],
                    style=base_style,
                )

            return html.Div(
                [html.Strong(prefix + " "), dcc.Markdown(str(content))],
                style=base_style,
            )

        # Add user message
        history.append(bubble("user", message, color="#0f172a", bg="#f8fafc"))

        # Add temporary spinner
        spinner = html.Div(
            dcc.Loading(type="dot", color="#0b74de"),
            style={"margin": "8px 0", "textAlign": "center"},
        )
        history.append(spinner)

        app._cached_layout = app.layout

        # ───────────────────────────────────────────────
        # Send query to LLM
        # ───────────────────────────────────────────────
        try:
            r = requests.post(LLM_API_URL, json={"message": message}, timeout=90)
            r.raise_for_status()
            data = r.json()
            print(f"[DEBUG] Assistant returned keys: {list(data.keys())}")

            # Detect direct image response
            if "image_base64" in data:
                reply = html.Img(
                    src=f"data:image/png;base64,{data['image_base64']}",
                    style={
                        "maxWidth": "100%",
                        "borderRadius": "12px",
                        "boxShadow": "0 2px 6px rgba(0,0,0,0.25)",
                        "marginTop": "10px",
                    },
                )
            else:
                reply = data.get("response", data.get("detail", "No reply."))

        except requests.exceptions.Timeout:
            reply = "⚠️ The assistant took too long to respond."
        except Exception as e:
            reply = f"⚠️ Error contacting assistant: {e}"

        # Remove spinner
        history = [
            h
            for h in history
            if not isinstance(h, html.Div)
            or not h.children
            or not isinstance(h.children[0], dcc.Loading)
        ]

        # ───────────────────────────────────────────────
        # Render assistant reply
        # ───────────────────────────────────────────────
        if isinstance(reply, html.Img):
            history.append(bubble("assistant", data["image_base64"], is_image=True))
        elif isinstance(reply, dict) and "response" in reply:
            history.append(bubble("assistant", reply["response"], color="#0b74de", bg="#f0f6ff"))
        else:
            history.append(bubble("assistant", str(reply), color="#0b74de", bg="#f0f6ff"))

        # 🧩 Sandbox-safe fallback — if sandbox expects components not wrapped in chat bubbles
        if isinstance(reply, dict) and "image_base64" in reply:
            return [html.Img(
                src=f"data:image/png;base64,{reply['image_base64']}",
                style={
                    "maxWidth": "100%",
                    "borderRadius": "10px",
                    "marginTop": "8px"
                },
            )]

        return history

