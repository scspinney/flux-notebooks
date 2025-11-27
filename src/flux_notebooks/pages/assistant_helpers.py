"""
Helper functions for assistant_sandbox page.

This module contains UI rendering and LLM interaction helpers
extracted from pages/assistant_sandbox.py to improve code organization.
"""
import os
import json
import requests
import ast
from dash import html, dcc
from typing import Any, Dict, List


def autoscroll_script():
    """Generate JavaScript to auto-scroll chat window to bottom."""
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


def prepare_history(history: List[dict]) -> List[dict]:
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


def resolve_llm_api() -> str:
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
            # Don't loop back inside the Dash container
            return "http://llm:8081/chat"
        return env_url

    return "http://llm:8081/chat" if in_docker else "http://localhost:8081/chat"


def post_llm(message: str, model: str, timeout_s: int = 60) -> dict:
    """
    Call the LLM API with basic robustness.
    
    Args:
        message: The message to send to the LLM
        model: Model identifier
        timeout_s: Request timeout in seconds
        
    Returns:
        dict with 'response' key containing LLM response or error message
    """
    llm_api = resolve_llm_api()
    try:
        r = requests.post(
            llm_api,
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
        return {"response": f"⚠️ Error contacting assistant at {llm_api}: {e}"}


def toolresult_to_markdown(obj: Any) -> str:
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


def clean_markdown_text(text: str) -> str:
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


def render_bubble(msg):
    """
    Render a chat bubble based on message dict.
    
    Args:
        msg: dict with keys: role, type, content, typing, explanation_md, reasoning_md, images
        
    Returns:
        Dash html component representing the chat bubble
    """
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


def render_chip(text: str):
    """Render a suggestion chip button."""
    return html.Div(
        text, 
        id={"type": "sandbox-suggest", "text": text}, 
        n_clicks=0, 
        className="sandbox-suggestion"
    )


def ux_script():
    """
    Generate JavaScript for UX interactions:
    - Click-to-zoom thumbnails
    - Esc to close modal
    - Enter to send message
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


# Suggested prompts for the chat interface
SUGGESTED_PROMPTS = [
    "Plot the age distribution.",
    "Show a scatter plot of age vs. sex.",
    "List all columns in participants.tsv.",
    "How many participants do we have?",
    "Show me the male vs. female count.",
    "Plot a histogram of participant weight.",
    "Generate a scatter of age vs. handedness.",
]
