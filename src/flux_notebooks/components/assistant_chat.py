from dash import html, dcc
import dash_bootstrap_components as dbc

def render_chat():
    """Left slide-out chat under navbar."""
    return html.Div(
        [
            # ─────────────────────────────
            # ✅ NEW: Conversation history store
            # Holds OpenAI-style [{"role": "...", "content": "..."}]
            # ─────────────────────────────
            dcc.Store(id="chat-message-store", data=[]),

            html.Div(id="chat-backdrop", className="flux-chat-backdrop"),

            # Vertical tab stays pinned under navbar
            html.Div(
                "Flux Assistant",
                id="chat-tab",
                n_clicks=0,
                className="flux-chat-tab",
                title="Open Flux Assistant",
            ),

            html.Div(
                id="chat-sidebar",
                className="flux-chat-sidebar",
                children=[
                    # ─────────────────────────────
                    # Header with title + Sandbox button
                    # ─────────────────────────────
                    html.Div(
                        [
                            html.H4("🤖 Flux Assistant", className="flux-chat-title mb-0"),
                            dbc.Button(
                                "🧠 Sandbox",
                                id="open-sandbox",
                                href="/assistant_sandbox",
                                color="secondary",
                                size="sm",
                                className="flux-chat-sandbox-btn me-2",
                            ),
                            html.Button("✕", id="close-chat-btn", className="flux-chat-close"),
                        ],
                        className=(
                            "flux-chat-header d-flex align-items-center "
                            "justify-content-between pe-2 ps-3"
                        ),
                    ),

                    # ─────────────────────────────
                    # Chat history
                    # ─────────────────────────────
                    html.Div(id="chat-history", className="flux-chat-history"),

                    # ─────────────────────────────
                    # Input + Send button + Spinner
                    # ─────────────────────────────
                    html.Div(
                        [
                            dbc.Input(
                                id="chat-input",
                                placeholder="Ask something…",
                                type="text",
                                debounce=True,
                                className="me-2 flex-grow-1 flux-chat-input",
                            ),
                            dbc.Spinner(
                                children=[
                                    dbc.Button(
                                        "Send",
                                        id="chat-send-btn",
                                        color="primary",
                                        className="flux-chat-send",
                                    )
                                ],
                                color="info",
                                type="grow",
                                size="sm",
                                spinner_style={"marginLeft": "6px"},
                                delay_hide=250,
                                id="chat-send-spinner",
                            ),
                        ],
                        className="flux-chat-footer d-flex align-items-center",
                    ),
                ],
            ),
        ],
        style={"position": "relative", "zIndex": "1"},
    )
