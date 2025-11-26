# flux_notebooks/callbacks/assistant_callbacks.py

from dash import Input, Output, State, html, ctx, dcc
import dash_bootstrap_components as dbc
import requests
import os, json, ast

LLM_API_URL = os.getenv("LLM_API_URL")
if not LLM_API_URL:
    if os.path.exists("/.dockerenv"):
        LLM_API_URL = "http://llm:8081/chat"
    else:
        LLM_API_URL = "http://localhost:8081/chat"

print(f"[Flux-Dash] Using LLM API at: {LLM_API_URL}")


# -----------------------------
# Small helpers
# -----------------------------

def _is_placeholder(node):
    """
    Robustly detect a placeholder bubble.
    Dash serializes HTML, so we inspect className instead of id.
    """
    try:
        cls = getattr(node, "className", "") or ""
        return ("assistant" in cls) and ("placeholder" in cls)
    except Exception:
        return False

def _toolresult_to_markdown(raw):
    """
    Convert tool outputs to readable Markdown.

    Supports:
    - list[dict]  → Markdown table
    - dict        → key/value table
    - schema unwrap: if dict has keys {"name","type"}
    - generic JSON fallback

    Returns a string that is ALWAYS valid Markdown.
    """
    # Attempt JSON load if it's a str
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return f"```\n{raw}\n```"

    # 1) LIST OF DICTS → TABLE
    if isinstance(data, list) and data and isinstance(data[0], dict):
        cols = list(data[0].keys())
        header = "| " + " | ".join(cols) + " |\n"
        sep = "| " + " | ".join(["---"] * len(cols)) + " |\n"
        rows = [
            "| " + " | ".join(str(item.get(c, "")) for c in cols) + " |"
            for item in data
        ]
        return header + sep + "\n".join(rows)

    # 2) DICT → Key/Value Table
    if isinstance(data, dict):
        # Special case: schema-like dict
        if set(data.keys()) == {"name", "type"}:
            return f"| Name | Type |\n| --- | --- |\n| {data['name']} | {data['type']} |"

        # Generic dict
        header = "| Key | Value |\n| --- | --- |\n"
        rows = []
        for k, v in data.items():
            # Render nested dicts or lists as JSON
            if isinstance(v, (dict, list)):
                pretty = json.dumps(v, indent=2, ensure_ascii=False)
                rows.append(f"| {k} | `{pretty}` |")
            else:
                rows.append(f"| {k} | {v} |")
        return header + "\n".join(rows)

    # 3) Fallback: raw pretty JSON
    try:
        pretty = json.dumps(data, indent=2, ensure_ascii=False)
        return f"```json\n{pretty}\n```"
    except Exception:
        return str(data)



def _bubble(role, content, is_image=False, placeholder=False):
    wrapper = "flux-chat-bubble user" if role == "user" else "flux-chat-bubble assistant"
    label = html.Span("" if role == "user" else "🤖 Flux:", className="bubble-label")

    if placeholder:
        return html.Div(
            [label, html.Span(className="typing-dots")],
            className=f"{wrapper} placeholder",
            id="assistant-placeholder",
        )

    if is_image:
        return html.Div(
            [label, html.Img(src=f"data:image/png;base64,{content}")],
            className=wrapper,
        )

    if isinstance(content, dict):
        try:
            content = "```json\n" + json.dumps(content, indent=2) + "\n```"
        except Exception:
            content = str(content)

    return html.Div(
        [label, dcc.Markdown(str(content), className="flux-chat-markdown")],
        className=wrapper,
    )

def register_assistant_callbacks(app):

    # -----------------------------------------------
    # Slide-in chat sidebar
    # -----------------------------------------------
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

    # -----------------------------------------------
    # Main chat callback (with placeholder typing)
    # -----------------------------------------------
    @app.callback(
        Output("chat-history", "children"),
        Input("chat-send-btn", "n_clicks"),
        State("chat-input", "value"),
        State("chat-history", "children"),
        State("model-selector", "value"),
        prevent_initial_call=True,
    )
    def send_message(n_clicks, message, history, model):
        if not message:
            return history

        model = model or "gpt-4o-nano"
        history = history or []

        # 1. Immediately render user bubble + assistant placeholder
        history.append(_bubble("user", message))
        history.append(_bubble("assistant", "", placeholder=True))

        # 2. Call backend
        try:
            resp = requests.post(
                LLM_API_URL,
                json={"message": message, "model": model},
                timeout=90,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            # Replace placeholder with error text
            new_hist = []
            placeholder_seen = False

            for node in history:
                if _is_placeholder(node) and not placeholder_seen:
                    new_hist.append(
                        _bubble("assistant", f"⚠️ Error contacting assistant: {e}")
                    )
                    placeholder_seen = True
                else:
                    new_hist.append(node)

            return new_hist

        # 3. Replace placeholder based on server response type
        new_hist = []
        placeholder_seen = False

        for node in history:
            if _is_placeholder(node) and not placeholder_seen:

                # ---- IMAGE ----
                if data.get("type") == "image":
                    new_hist.append(
                        _bubble(
                            "assistant",
                            data.get("image_base64"),
                            is_image=True
                        )
                    )

                # ---- TOOL RESULT ----
                elif data.get("type") == "tool_result":
                    pretty = _toolresult_to_markdown(data.get("content", ""))
                    new_hist.append(_bubble("assistant", pretty))

                # ---- NORMAL TEXT ----
                else:
                    new_hist.append(
                        _bubble("assistant", data.get("content", "No reply."))
                    )

                placeholder_seen = True
                continue

            new_hist.append(node)

        return new_hist



# -----------------------------
# Render chat widget
# -----------------------------
from dash import html, dcc
import dash_bootstrap_components as dbc

def render_chat():
    model_selector = dcc.Dropdown(
        id="model-selector",
        options=[
            {"label": "GPT-5", "value": "gpt-5"},
            {"label": "GPT-4o", "value": "gpt-4o"},
            {"label": "GPT-4o-mini", "value": "gpt-4o-mini"},
            {"label": "GPT-4o-nano", "value": "gpt-4o-nano"},
        ],
        value="gpt-5",
        clearable=False,
        className="flux-model-selector",
    )

    return html.Div(
        [
            dcc.Store(id="chat-message-store", data=[]),
            html.Div(id="chat-backdrop", className="flux-chat-backdrop"),

            html.Div("Flux Assistant", id="chat-tab", n_clicks=0,
                     className="flux-chat-tab", title="Open Flux Assistant"),

            html.Div(
                id="chat-sidebar",
                className="flux-chat-sidebar",
                children=[
                    html.Div(
                        [
                            html.H4("🤖 Flux Assistant", className="flux-chat-title mb-0"),
                            html.Div(model_selector, style={"width": "170px", "marginRight": "12px"}),
                            dbc.Button("🧠 Sandbox", id="open-sandbox",
                                       href="/assistant_sandbox", color="secondary",
                                       size="sm", className="flux-chat-sandbox-btn me-2"),
                            html.Button("✕", id="close-chat-btn", className="flux-chat-close"),
                        ],
                        className="flux-chat-header d-flex align-items-center justify-content-between pe-2 ps-3",
                    ),
                    html.Div(id="chat-history", className="flux-chat-history"),
                    html.Div(
                        [
                            dbc.Input(id="chat-input", placeholder="Ask something…",
                                      type="text", debounce=True,
                                      className="me-2 flex-grow-1 flux-chat-input"),
                            dbc.Button("Send", id="chat-send-btn",
                                       color="primary", className="flux-chat-send"),
                        ],
                        className="flux-chat-footer d-flex align-items-center",
                    ),
                ],
            ),
        ],
        style={"position": "relative", "zIndex": "1"},
    )
