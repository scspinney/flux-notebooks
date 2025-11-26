# flux_notebooks/pages/assistant_sandbox.py
import os
import socket
import json
import requests
import ast
import uuid

from dash import html, dcc, Input, Output, State, callback, no_update
import dash_bootstrap_components as dbc
import dash
from typing import Any, Dict, List, Optional

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


# helper
def _autoscroll_script():
    return html.Script(
        """
        (function() {
            function scroll() {
                var modal = document.getElementById("flux-image-modal");
                if (modal && modal.style.display === "flex") return;

                var el = document.getElementById("sandbox-chat-window");
                if (!el) return;
                el.scrollTop = el.scrollHeight;
            }
            requestAnimationFrame(scroll);
            setTimeout(scroll, 80);
        })();
        """
    )

def _prepare_history(history: List[dict]) -> List[dict]:
    """
    Convert Dash's internal bubble history to clean OpenAI messages.
    Removes typing placeholders and frontend-only fields.
    """
    cleaned = []
    for h in history or []:
        if h.get("typing"):
            continue  # never send placeholders to backend

        role = h.get("role")
        content = h.get("content") or ""

        # Some assistant image messages also have content
        if role == "assistant" and h.get("type") == "image":
            # The backend ignores history content anyway; keep minimal
            content = content or ""

        cleaned.append({
            "role": role,
            "content": content,
        })

    return cleaned


# ---------------------------------------------------------------------
# LLM endpoint resolution
# ---------------------------------------------------------------------
def _resolve_llm_api() -> str:
    """
    Decide which URL to use for the LLM service.

    Priority:
      1) LLM_API_URL env var if set
      2) If running in Docker (/.dockerenv present): http://llm:8081/chat
      3) Else: http://localhost:8081/chat

    Additionally, if the env var points at http://localhost:... but we are in Docker,
    rewrite it to http://llm:8081/chat to avoid loopback mistakes.
    """
    env_url = os.getenv("LLM_API_URL", "").strip()
    in_docker = os.path.exists("/.dockerenv")

    if env_url:
        if in_docker and "localhost" in env_url:
            # Don’t loop back inside the Dash container
            return "http://llm:8081/chat"
        return env_url

    return "http://llm:8081/chat" if in_docker else "http://localhost:8081/chat"


LLM_API = _resolve_llm_api()

# ---------------------------------------------------------------------
# Small helper to call the LLM API with basic robustness
# ---------------------------------------------------------------------
def _post_llm(message: str, model: str, timeout_s: int = 60) -> dict:
    try:
        r = requests.post(
            LLM_API,
            json={"message": message, "model": model},
            timeout=timeout_s,
        )
        r.raise_for_status()
        # Be tolerant to non-JSON replies:
        try:
            return r.json()
        except Exception:
            return {"response": r.text}
    except requests.exceptions.Timeout:
        return {"response": "⚠️ The assistant timed out."}
    except Exception as e:
        return {"response": f"⚠️ Error contacting assistant at {LLM_API}: {e}"}


def _toolresult_to_markdown(obj: Any) -> str:
    """
    Convert a raw tool_result JSON payload into polished Markdown.

    Handles:
    - dict          → key/value listing + collapsible for nested
    - list[dict]    → markdown table
    - list[...]     → collapsible bullet list
    - primitives    → inline code
    """
    try:
        # ============ HELPERS ============

        def fmt_val(v):
            if v is None:
                return "`null`"
            if isinstance(v, bool):
                return "✅" if v else "❌"
            if isinstance(v, (int, float)):
                return f"{v}"
            if isinstance(v, str):
                if len(v) > 80:
                    return f"<details><summary>string ({len(v)} chars)</summary>\n\n`{v}`\n\n</details>"
                return f"`{v}`"
            if isinstance(v, dict):
                return render_dict(v)
            if isinstance(v, list):
                return render_list(v)
            return f"`{str(v)}`"

        def render_dict(d: Dict[str, Any]) -> str:
            if not d:
                return "_empty object_"

            lines = []
            for k, v in d.items():
                if isinstance(v, (dict, list)):
                    # Collapsible block for nested structures
                    lines.append(
                        f"<details><summary>**{k}**</summary>\n\n{fmt_val(v)}\n\n</details>"
                    )
                else:
                    lines.append(f"**{k}:** {fmt_val(v)}")
            return "\n".join(lines)

        def render_table(rows: List[Dict[str, Any]]) -> str:
            if not rows:
                return "_empty table_"

            # Collect all columns across rows
            cols = []
            for r in rows:
                if isinstance(r, dict):
                    for c in r.keys():
                        if c not in cols:
                            cols.append(c)

            # Markdown table header
            out = ["|" + "|".join(f"**{c}**" for c in cols) + "|"]
            out.append("|" + "|".join("---" for _ in cols) + "|")

            # Rows
            for r in rows:
                row = []
                for c in cols:
                    val = r.get(c, None)
                    cell = fmt_val(val)
                    # Avoid breaking pipes in markdown
                    cell = str(cell).replace("|", "\\|")
                    row.append(cell)
                out.append("|" + "|".join(row) + "|")

            return "\n".join(out)

        def render_list(lst: List[Any]) -> str:
            if not lst:
                return "_empty list_"

            # If list of dicts → render as table
            if all(isinstance(x, dict) for x in lst):
                return render_table(lst)

            # If long list, collapse
            if len(lst) > 12:
                items = "\n".join(f"- {fmt_val(x)}" for x in lst)
                return (
                    f"<details><summary>List with {len(lst)} items</summary>\n\n"
                    f"{items}\n\n</details>"
                )

            # Short list
            return "\n".join(f"- {fmt_val(x)}" for x in lst)

        # ============ ROOT DISPATCH ============

        if isinstance(obj, dict):
            return render_dict(obj)

        if isinstance(obj, list):
            return render_list(obj)

        # Primitive
        return fmt_val(obj)

    except Exception as e:
        # Fallback safe mode
        return f"```\n{json.dumps(obj, indent=2, ensure_ascii=False)}\n```\n\n*(formatting error: {e})*"


def _clean_markdown_text(text: str) -> str:
    """
    Clean up LLM text output into tidy, display-ready Markdown.

    Handles:
    - stray escaped quotes: \" → "
    - normalize list-like content (["a","b"]) into Markdown bullet lists
    - fix spacing issues: '",' → '", '
    - strip excessive leading newlines
    """
    if not isinstance(text, str):
        return str(text)

    cleaned = text

    # 1) Unescape quotes
    cleaned = cleaned.replace("\\\"", "\"")

    # 2) Ensure commas have spaces
    cleaned = cleaned.replace('",', '", ')

    # 3) Detect array-like structures and expand to bullets
    try:
        # find [...something...]
        if "[" in cleaned and "]" in cleaned:
            start = cleaned.index("[")
            end = cleaned.index("]") + 1
            segment = cleaned[start:end]

            arr = ast.literal_eval(segment)
            if isinstance(arr, list):
                bullets = "\n" + "\n".join(f"- {x}" for x in arr) + "\n"
                cleaned = cleaned.replace(segment, bullets)
    except Exception:
        pass

    # 4) Strip leading blank lines but keep meaningful indentation
    cleaned = cleaned.lstrip("\n")

    return cleaned


# ---------------------------------------------------------------------
# Chat UI helpers
# ---------------------------------------------------------------------
def _bubble(msg):
    # Typing indicator bubble
    if msg.get("typing"):
        return html.Div(
            html.Div(
                html.Div(className="typing-dots"),
                className="sandbox-bubble sandbox-bubble-assistant typing-bubble"
            ),
            className="sandbox-bubble-row"
        )

    role = msg.get("role")
    mtype = msg.get("type")
    content = msg.get("content", "")
    explanation = msg.get("explanation_md", "")
    reasoning = msg.get("reasoning_md", "")
    images = msg.get("images", {})

    if role == "user":
        return html.Div(
            html.Div(
                dcc.Markdown(content),
                className="sandbox-bubble sandbox-bubble-user"
            ),
            className="sandbox-bubble-row sandbox-bubble-row-user"
        )

    # Image bubble
    if mtype == "image":
        thumbs = []
        for label, img in images.items():
            thumbs.append(
                html.Div(
                    html.Img(
                        src=f"data:image/png;base64,{img['image_base64']}",
                        className="flux-plot-thumb",
                        **{"data-fullres": img["image_base64"]},
                    ),
                    className="sandbox-img-wrapper"
                )
            )

        blocks = [html.Div(thumbs, className="sandbox-image-grid")]
        if explanation:
            blocks.append(dcc.Markdown(explanation, className="sandbox-explanation-md"))
        if reasoning:
            blocks.append(
                html.Details(
                    [
                        html.Summary("Reasoning Summary"),
                        dcc.Markdown(reasoning, className="sandbox-reasoning-md"),
                    ],
                    className="sandbox-reasoning-container",
                )
            )

        return html.Div(
            html.Div(blocks, className="sandbox-bubble sandbox-bubble-assistant"),
            className="sandbox-bubble-row"
        )

    # Normal assistant text
    return html.Div(
        html.Div(
            dcc.Markdown(content),
            className="sandbox-bubble sandbox-bubble-assistant"
        ),
        className="sandbox-bubble-row"
    )

SUGGESTED = [
    "Plot the age distribution.",
    "Show a scatter plot of age vs. sex.",
    "List all columns in participants.tsv.",
    "How many participants do we have?",
    "Show me the male vs. female count.",
    "Plot a histogram of participant weight.",
    "Generate a scatter of age vs. handedness.",
]

def _chip(text: str):
    return html.Div(text, id={"type": "sandbox-suggest", "text": text}, n_clicks=0, className="sandbox-suggestion")

def _ux_script():
    """
    Click-to-zoom (thumbnails) + Esc to close + Enter-to-send.
    """
    return html.Script(
        """
        (function(){
          function qs(id){ return document.getElementById(id); }

          // Click-to-zoom (delegate)
          document.addEventListener('click', function(e){
            const img = e.target.closest('.flux-plot-thumb');
            if (!img) return;
            const full = img.dataset.fullres || '';
            const modal = qs('flux-image-modal');
            const modalImg = qs('flux-modal-image');
            if (!modal || !modalImg) return;
            modalImg.src = 'data:image/png;base64,' + full;
            modal.style.display = 'flex';
          });

          // Close modal on backdrop click
          document.addEventListener('click', function(e){
            const modal = qs('flux-image-modal');
            if (!modal) return;
            if (e.target === modal) modal.style.display = 'none';
          });

          // Keyboard: Esc closes modal; Enter sends message
          document.addEventListener('keydown', function(e){
            const modal = qs('flux-image-modal');
            if (e.key === 'Escape' && modal && modal.style.display === 'flex') {
              modal.style.display = 'none';
              return;
            }
            if (e.key === 'Enter') {
              const input = qs('sandbox-input');
              const btn = qs('sandbox-send');
              if (document.activeElement === input && !e.shiftKey) {
                e.preventDefault();
                btn && btn.click();
              }
            }
          });
        })();
        """
    )

# ---------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------

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
