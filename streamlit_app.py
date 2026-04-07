from __future__ import annotations

import uuid

import streamlit as st
import streamlit.components.v1 as components

from agent_registry import ChatRequest, get_agent, list_agents

st.set_page_config(page_title="ADK Agent Chat", page_icon="🤖", layout="wide")


def _ensure_state() -> None:
    st.session_state.setdefault("chat_user_id", "streamlit-user")
    st.session_state.setdefault("chat_messages", {})
    st.session_state.setdefault("chat_sessions", {})


def _inject_styles() -> None:
    st.markdown(
        """
<style>
/* ── Page background ───────────────────────────────────────────── */
.stApp {
    background: linear-gradient(160deg, #f0f4ff 0%, #e8edf8 100%);
}

.block-container {
    max-width: 860px;
    padding-top: 1.5rem;
    padding-bottom: 12rem;  /* leave room for fixed composer */
}

/* ── Sidebar ────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e3a8a 100%);
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stSidebar"] h3 { color: #93c5fd !important; }
[data-testid="stSidebar"] .stCodeBlock { border-radius: 10px; }
[data-testid="stSidebar"] button {
    border-radius: 10px;
    background: rgba(255,255,255,0.10) !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
}

/* ── Hero banner ───────────────────────────────────────────────── */
.hero-card {
    background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 100%);
    border-radius: 20px;
    padding: 1.25rem 1.5rem 1.3rem;
    margin-bottom: 1.25rem;
    color: white;
}
.hero-title {
    font-size: 1.65rem;
    font-weight: 800;
    margin: 0 0 0.25rem;
    letter-spacing: -0.02em;
}
.hero-sub {
    font-size: 0.9rem;
    color: rgba(255,255,255,0.72);
    margin: 0 0 0.9rem;
}
.meta-row { display: flex; flex-wrap: wrap; gap: 0.6rem; }
.meta-pill {
    background: rgba(255,255,255,0.13);
    border: 1px solid rgba(255,255,255,0.18);
    border-radius: 999px;
    padding: 0.3rem 0.75rem;
    font-size: 0.8rem;
}

/* ── Section label ─────────────────────────────────────────────── */
.section-label {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: #64748b;
    margin: 0 0 0.6rem;
}

/* ── Chat messages ─────────────────────────────────────────────── */
[data-testid="stChatMessage"] {
    border-radius: 16px;
    padding: 0.1rem 0.2rem;
}
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] * {
    color: #0f172a !important;
}
[data-testid="stChatMessage"][aria-label="Chat message from user"] {
    background: rgba(37,99,235,0.10);
}
[data-testid="stChatMessage"][aria-label="Chat message from assistant"] {
    background: rgba(255,255,255,0.72);
}

/* ── Empty state ───────────────────────────────────────────────── */
.empty-state {
    border: 1px dashed rgba(148,163,184,0.6);
    background: rgba(255,255,255,0.7);
    border-radius: 14px;
    padding: 0.9rem 1rem;
    color: #64748b;
    font-size: 0.92rem;
    margin-bottom: 1rem;
}

/* ── Fixed composer form – position/width set by JS ────────────── */
div[data-testid="stForm"] {
    position: fixed !important;
    bottom: 0.9rem !important;
    /* left/width injected by JS to match .block-container exactly */
    box-sizing: border-box !important;
    z-index: 999 !important;
    background: rgba(240,244,255,0.92) !important;
    backdrop-filter: blur(6px) !important;
    border: 1px solid rgba(148,163,184,0.28) !important;
    border-radius: 16px !important;
    padding: 0.6rem 0.7rem 0.45rem !important;
    box-shadow: 0 14px 30px rgba(15,23,42,0.12) !important;
}

/* Stretch every Streamlit wrapper inside the form to full width */
div[data-testid="stForm"] > div,
div[data-testid="stForm"] [data-testid="stVerticalBlock"],
div[data-testid="stForm"] [data-testid="stVerticalBlock"] > *,
div[data-testid="stForm"] [data-testid="stTextArea"],
div[data-testid="stForm"] [data-testid="stTextArea"] > div,
div[data-testid="stForm"] [data-baseweb="textarea"],
div[data-testid="stForm"] [data-baseweb="textarea"] > div {
    width: 100% !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
}

div[data-testid="stForm"] [data-testid="stTextArea"] textarea {
    width: 100% !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
    min-height: calc(4 * 1.4rem + 1.1rem) !important;
    max-height: calc(4 * 1.4rem + 1.1rem) !important;
    resize: none !important;
    overflow-y: auto !important;
    border-radius: 12px !important;
    font-size: 0.97rem !important;
    line-height: 1.4rem !important;
    border: 1px solid rgba(148,163,184,0.38) !important;
    background: #ffffff !important;
    color: #0f172a !important;
    caret-color: #1d4ed8 !important;
}
div[data-testid="stForm"] [data-testid="stTextArea"] textarea:focus {
    border-color: rgba(37,99,235,0.5) !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.13) !important;
    outline: none !important;
}
div[data-testid="stForm"] [data-testid="stTextArea"] textarea::placeholder {
    color: #94a3b8 !important;
    opacity: 1 !important;
}
div[data-testid="stForm"] button[kind="secondaryFormSubmit"] {
    border-radius: 10px !important;
    background: #1d4ed8 !important;
    color: #ffffff !important;
    border: none !important;
    box-shadow: none !important;
    padding-inline: 1rem !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )


# ── Bootstrap ────────────────────────────────────────────────────────────────
_ensure_state()
_inject_styles()

# JS: snap the fixed form to exactly match the .block-container left/width
components.html(
    """
<script>
(function () {
    const TEXTAREA_HEIGHT = "112px";

    function getMainBlockContainer(doc) {
        const candidates = Array.from(doc.querySelectorAll(".block-container"));
        const visible = candidates.filter((el) => {
            const rect = el.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0;
        });
        return visible.sort(
            (a, b) => b.getBoundingClientRect().width - a.getBoundingClientRect().width
        )[0] || null;
    }

    function stretchComposer(form) {
        const selectors = [
            '[data-testid="stVerticalBlock"]',
            '[data-testid="stTextArea"]',
            '[data-testid="stTextArea"] > div',
            '[data-baseweb="textarea"]',
            '[data-baseweb="textarea"] > div',
        ];
        selectors.forEach((selector) => {
            form.querySelectorAll(selector).forEach((el) => {
                el.style.setProperty("width", "100%", "important");
                el.style.setProperty("max-width", "100%", "important");
                el.style.setProperty("box-sizing", "border-box", "important");
            });
        });

        const textarea = form.querySelector("textarea");
        if (!textarea) return;
        textarea.style.setProperty("width", "100%", "important");
        textarea.style.setProperty("max-width", "100%", "important");
        textarea.style.setProperty("height", TEXTAREA_HEIGHT, "important");
        textarea.style.setProperty("min-height", TEXTAREA_HEIGHT, "important");
        textarea.style.setProperty("max-height", TEXTAREA_HEIGHT, "important");
        textarea.style.setProperty("overflow-y", "auto", "important");
        textarea.style.setProperty("resize", "none", "important");
        textarea.style.setProperty("box-sizing", "border-box", "important");
    }

    function syncForm() {
        const doc   = window.parent.document;
        const bc    = getMainBlockContainer(doc);
        const form  = doc.querySelector('div[data-testid="stForm"]');
        if (!bc || !form) { setTimeout(syncForm, 120); return; }
        const r = bc.getBoundingClientRect();
        form.style.setProperty("left",  r.left + "px", "important");
        form.style.setProperty("width", r.width + "px", "important");
        form.style.setProperty("max-width", r.width + "px", "important");
        stretchComposer(form);
    }
    syncForm();
    window.addEventListener("resize", syncForm);
    // Re-sync after Streamlit rerenders (MutationObserver on body)
    new MutationObserver(syncForm).observe(
        window.parent.document.body,
        { childList: true, subtree: true, attributes: true }
    );
})();
</script>
""",
    height=0,
)

agents = list_agents()
if not agents:
    st.error("No agents are registered yet. Add an entry to `agents.json` and reload.")
    st.stop()

agent_options = {agent.title: agent.key for agent in agents}

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🤖 ADK Agent Chat")
    selected_title = st.selectbox("Choose an agent", tuple(agent_options.keys()))
    selected_key   = agent_options[selected_title]
    selected_agent = get_agent(selected_key)

    messages_by_agent: dict[str, list[dict[str, str]]] = st.session_state["chat_messages"]
    sessions_by_agent: dict[str, str]                  = st.session_state["chat_sessions"]
    messages   = messages_by_agent.setdefault(selected_key, [])
    session_id = sessions_by_agent.setdefault(selected_key, str(uuid.uuid4()))

    st.markdown("### Agent details")
    st.write(selected_agent.description)

    if selected_agent.prompt_hint:
        st.markdown("### Prompt hint")
        st.code(selected_agent.prompt_hint, language="text")

    st.code(f"agent_key  = {selected_key}\nsession_id = {session_id}", language="text")

    if st.button("🔄  New conversation", use_container_width=True):
        messages_by_agent[selected_key] = []
        sessions_by_agent[selected_key] = str(uuid.uuid4())
        st.rerun()

    with st.expander("➕  How to add an agent"):
        st.markdown(
            """
1. Create your agent module.
2. Add one entry in **`agents.json`**.
3. Set `module` to the file exposing `run_prompt(...)`.
4. Optionally add a `prompt_hint`.
5. Reload Streamlit and pick it from the dropdown.
            """.strip()
        )

# ── Main area ────────────────────────────────────────────────────────────────

st.markdown('<p class="section-label">Conversation</p>', unsafe_allow_html=True)

if not messages:
    st.markdown(
        '<div class="empty-state">💬  Start the conversation below — history will appear here in order.</div>',
        unsafe_allow_html=True,
    )

for message in messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ── Fixed-bottom composer: 4-line constant input ─────────────────────────────
placeholder = selected_agent.prompt_hint or f"Message {selected_agent.title}…"
with st.form("chat_composer_form", clear_on_submit=True):
    prompt = st.text_area(
        label="Message",
        placeholder=placeholder,
        height=112,
        label_visibility="collapsed",
    )
    submitted = st.form_submit_button("Send")

if submitted:
    clean_prompt = prompt.strip()
    if clean_prompt:
        messages.append({"role": "user", "content": clean_prompt})

        with st.spinner(f"Waiting for {selected_agent.title}…"):
            try:
                answer = selected_agent.run(
                    ChatRequest(
                        prompt=clean_prompt,
                        user_id=st.session_state["chat_user_id"],
                        session_id=sessions_by_agent[selected_key],
                    )
                )
            except Exception as exc:  # noqa: BLE001
                answer = f"⚠️ Error: {exc}"

        messages.append({"role": "assistant", "content": answer})
        st.rerun()
