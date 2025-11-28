# flux_notebooks/pages/assistant_sandbox.py
import os
import socket
import json
import uuid

from dash import html, dcc, Input, Output, State, callback, no_update
import dash_bootstrap_components as dbc
import dash
from typing import Dict, List, Optional
import requests

# Import helper functions from dedicated module
from flux_notebooks.pages.assistant_helpers import (
    autoscroll_script,
    prepare_history,
    resolve_llm_api,
    post_llm,
    toolresult_to_markdown,
    clean_markdown_text,
    render_bubble,
    render_chip,
    ux_script,
    SUGGESTED_PROMPTS,
)

# ---------------------------------------------------------------------
# Page registration
# ---------------------------------------------------------------------
dash.register_page(
    __name__,
    path="/assistant_sandbox",
    name="Flux Assistant Sandbox",
    order=999,
    include_in_navbar=False,
)

# Resolve LLM API endpoint once at module load
LLM_API = resolve_llm_api()
print(f"[Flux-Dash] Using LLM API at: {LLM_API}")


# ---------------------------------------------------------------------
# Compatibility aliases (callbacks use _ prefix internally)
# ---------------------------------------------------------------------
_autoscroll_script = autoscroll_script
_prepare_history = prepare_history
_post_llm = post_llm
_toolresult_to_markdown = toolresult_to_markdown
_clean_markdown_text = clean_markdown_text
_bubble = render_bubble
_chip = render_chip
_ux_script = ux_script
SUGGESTED = SUGGESTED_PROMPTS


layout = html.Div(
    className="flux-assistant-sandbox",
    children=[

        # -------------------------------------------------
        # Header
        # -------------------------------------------------
        html.H2("🧠 Flux-Assistant Sandbox", className="fw-bold mb-2"),
        html.P(
            "Full-screen chat interface for multi-turn exploration of your dataset.",
            className="text-muted mb-4",
        ),

        # -------------------------------------------------
        # Model selector
        # -------------------------------------------------
        html.Div(
            [
                html.Label("Backend Model:", className="fw-semibold"),
                dcc.Dropdown(
                    id="sandbox-model",
                    options=[
                        {"label": "GPT-5", "value": "gpt-5"},
                        {"label": "GPT-4o", "value": "gpt-4o"},
                        {"label": "GPT-4o-mini", "value": "gpt-4o-mini"},
                        {"label": "GPT-4o-nano", "value": "gpt-4o-nano"},
                    ],
                    value="gpt-5",
                    clearable=False,
                    style={"width": "200px"},
                ),
                html.Span(f" (LLM API: {LLM_API})", className="text-muted ms-2"),
            ],
            className="mb-3",
        ),

        # -------------------------------------------------
        # Suggested prompts
        # -------------------------------------------------
        html.Div(
            [
                html.H5("Try asking:", className="fw-semibold mb-2"),
                html.Div(
                    [_chip(p) for p in SUGGESTED],
                    className="sandbox-suggestion-row"
                ),
            ],
            className="mb-3",
        ),

        # -------------------------------------------------
        # Chat window + thinking indicator
        # -------------------------------------------------
        html.Div(
            [
                html.Div(id="flux-thinking-bar", className="flux-thinking-bar"),
                html.Div(id="sandbox-chat-window", className="sandbox-chat-window"),
            ],
            style={"position": "relative"},
        ),

        html.Br(),

        # -------------------------------------------------
        # Input row
        # -------------------------------------------------
        dbc.InputGroup(
            [
                dbc.Input(
                    id="sandbox-input",
                    placeholder="Ask something…",
                    type="text",
                    debounce=False,
                ),
                dbc.Button(
                    "Send",
                    id="sandbox-send",
                    color="info",
                ),
            ],
            className="mb-3",
        ),

        # -------------------------------------------------
        # Hidden store
        # -------------------------------------------------
        dcc.Store(id="sandbox-history", data=[]),

        # -------------------------------------------------
        # CLICK-TO-ZOOM MODAL
        # -------------------------------------------------
        html.Div(
            id="flux-image-modal",
            style={
                "display": "none",
                "position": "fixed",
                "top": "0",
                "left": "0",
                "width": "100vw",
                "height": "100vh",
                "backgroundColor": "rgba(0,0,0,0.75)",
                "justifyContent": "center",
                "alignItems": "center",
                "zIndex": "9999",
                "cursor": "zoom-out",
            },
            children=[
                html.Img(
                    id="flux-modal-image",
                    style={
                        "maxWidth": "95%",
                        "maxHeight": "95%",
                        "borderRadius": "12px",
                    },
                )
            ],
        ),

        # -------------------------------------------------
        # UX Script: click-to-zoom, Esc-to-close, Enter-to-send
        # -------------------------------------------------
        _ux_script(),
    ],
)

# ---------------------------------------------------------------------
# Chips → autofill
# ---------------------------------------------------------------------
@callback(
    Output("sandbox-input", "value"),
    Output("sandbox-send", "n_clicks"),
    Input({"type": "sandbox-suggest", "text": dash.ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def use_suggested_prompt(n_clicks):
    if not n_clicks or all(v is None for v in n_clicks):
        return no_update, no_update
    trig = dash.ctx.triggered_id
    return trig["text"], 1

# ---------------------------------------------------------
# Stage 1 — user message arrives → add bubble + placeholder
# ---------------------------------------------------------
@callback(
    Output("sandbox-history", "data"),
    Output("sandbox-chat-window", "children", allow_duplicate=True),
    Output("flux-thinking-bar", "className", allow_duplicate=True),
    Input("sandbox-send", "n_clicks"),
    State("sandbox-input", "value"),
    State("sandbox-history", "data"),
    prevent_initial_call=True,
)
def stage1_user_input(n_clicks, message, history):
    if not message:
        return no_update, no_update, no_update

    history = history or []
    turn_id = str(uuid.uuid4())

    # User bubble
    history.append({
        "role": "user",
        "type": "final",
        "content": message,
        "turn_id": turn_id
    })

    # Placeholder bubble
    history.append({
        "role": "assistant",
        "typing": True,
        "content": "",
        "turn_id": turn_id
    })

    rendered = [_bubble(h) for h in history]
    rendered.append(_autoscroll_script())

    return history, rendered, "flux-thinking-bar show"


# ---------------------------------------------------------
# Stage 2 — replace placeholder with LLM response
# ---------------------------------------------------------
@callback(
    Output("sandbox-chat-window", "children", allow_duplicate=True),
    Output("sandbox-history", "data", allow_duplicate=True),
    Output("flux-thinking-bar", "className", allow_duplicate=True),
    Input("sandbox-history", "data"),
    State("sandbox-model", "value"),
    prevent_initial_call=True,
)
def stage2_llm_call(history, model):
    if not history:
        return no_update, no_update, no_update

    # Find active placeholder
    placeholder_idx = next((i for i, h in enumerate(history) if h.get("typing")), None)
    if placeholder_idx is None:
        # No pending work
        rendered = [_bubble(h) for h in history] + [_autoscroll_script()]
        return rendered, history, "flux-thinking-bar"

    turn_id = history[placeholder_idx]["turn_id"]

    # Resolve matching user message
    user_message = next(
        (h["content"] for h in reversed(history)
         if h.get("turn_id") == turn_id and h["role"] == "user"),
        ""
    )

    # Clean history for backend
    backend_history = _prepare_history(history)

    # Backend call
    try:
        resp = requests.post(
            LLM_API,
            json={"message": user_message, "model": model, "history": backend_history},
            timeout=90,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        history[placeholder_idx] = {
            "role": "assistant",
            "type": "final",
            "content": f"⚠ Error contacting assistant:\n```\n{e}\n```",
            "turn_id": turn_id
        }
        rendered = [_bubble(h) for h in history] + [_autoscroll_script()]
        return rendered, history, "flux-thinking-bar"

    # ✅ IMAGE RESULT
    if isinstance(data, dict) and isinstance(data.get("images"), dict):
        images = data["images"]
        explanation = data.get("explanation_md", "").strip()
        reasoning = data.get("reasoning_md", "").strip()

        history[placeholder_idx] = {
            "role": "assistant",
            "type": "image",
            "images": images,
            "explanation_md": explanation,
            "reasoning_md": reasoning,
            "turn_id": turn_id
        }

    # ✅ TOOL RESULT
    elif data.get("type") == "tool_result":
        pretty = _toolresult_to_markdown(data.get("content"))
        history[placeholder_idx] = {
            "role": "assistant",
            "type": "final",
            "content": pretty,
            "turn_id": turn_id
        }

    # ✅ TEXT RESULT
    else:
        text = _clean_markdown_text(data.get("content", "") or "*(no content)*")
        reasoning = data.get("reasoning_md", "")
        if reasoning:
            text += f"\n\n---\n**Reasoning Summary**\n\n{reasoning.strip()}"

        history[placeholder_idx] = {
            "role": "assistant",
            "type": "final",
            "content": text,
            "turn_id": turn_id
        }

    rendered = [_bubble(h) for h in history]
    rendered.append(_autoscroll_script())

    return rendered, history, "flux-thinking-bar"
