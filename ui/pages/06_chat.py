import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import streamlit as st

st.set_page_config(page_title="Chat", page_icon="💬", layout="wide")
st.info("💬 Chat with memory has been integrated into **🧭 Smart Execute**. Please use that page.")


st.set_page_config(page_title="Chat", page_icon="💬", layout="wide")

# ── Auth guard ────────────────────────────────────────────────────────────────
if "user_id" not in st.session_state or not st.session_state["user_id"]:
    st.warning("⚠️ Please go to the Home page and enter your User ID first.")
    st.stop()

user_id: str = st.session_state["user_id"]

# ── Session-state bootstrap ───────────────────────────────────────────────────
for _k, _v in {
    "chat_active_session_id": None,   # currently selected session_id
    "chat_messages_cache":    [],     # list of {role, content, timestamp} for display
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

_repo = ChatRepository()

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _load_sessions():
    return _repo.list_sessions(user_id)


def _load_messages(session_id: str):
    return _repo.get_messages(session_id, user_id, limit=100)


def _activate_session(session_id: str):
    st.session_state["chat_active_session_id"] = session_id
    st.session_state["chat_messages_cache"] = _load_messages(session_id)


def _create_new_session(tenant_id: str, title: str, llm_model: str):
    data = ChatSessionCreate(tenant_id=tenant_id, title=title, llm_model=llm_model)
    session = chat_service.create_session(data, user_id)
    _activate_session(session.id)
    return session


# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"### 💬 Chat Memory\n`👤 {user_id}`")
    st.divider()

    # --- New chat form ---
    with st.expander("➕ New Chat Session", expanded=False):
        with st.form("new_chat_form", clear_on_submit=True):
            new_tenant_id = st.text_input(
                "Session Label (tenant_id) *",
                placeholder="e.g. travel-planner",
                help="A short human-readable label. You can reuse it later to resume this conversation.",
            )
            new_title = st.text_input(
                "Display Title (optional)",
                placeholder="e.g. Planning my Italy trip",
            )
            new_model = st.selectbox("LLM Model", list_models(), index=0)
            submit_new = st.form_submit_button("Start Chat →", use_container_width=True)

        if submit_new:
            tid = new_tenant_id.strip()
            if len(tid) < 1:
                st.error("Session label is required.")
            elif not all(c.isalnum() or c in "_-" for c in tid):
                st.error("Labels can only contain letters, numbers, hyphens and underscores.")
            else:
                try:
                    _create_new_session(tid, new_title.strip(), new_model)
                    st.success(f"Session **{tid}** created!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to create session: {e}")

    # --- Resume by tenant_id ---
    with st.expander("🔄 Resume by Label", expanded=False):
        with st.form("resume_form", clear_on_submit=True):
            resume_tid = st.text_input("Enter existing session label")
            resume_btn = st.form_submit_button("Resume →", use_container_width=True)

        if resume_btn:
            t = resume_tid.strip()
            if t:
                found = _repo.get_session_by_tenant(user_id, t)
                if found:
                    _activate_session(found["id"])
                    st.success(f"Resumed **{t}**")
                    st.rerun()
                else:
                    st.error(f"No session found with label `{t}`.")

    st.divider()
    st.markdown("**Your Sessions**")

    sessions = _load_sessions()
    if not sessions:
        st.caption("No sessions yet — create one above.")
    else:
        active_id = st.session_state["chat_active_session_id"]
        for s in sessions:
            is_active = s["id"] == active_id
            btn_label = (
                f"{'▶ ' if is_active else ''}"
                f"**{s.get('title') or s['tenant_id']}**\n"
                f"`{s['tenant_id']}` · {s.get('message_count', 0)} msgs"
            )
            if st.button(
                btn_label,
                key=f"session_btn_{s['id']}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                _activate_session(s["id"])
                st.rerun()

        # Delete session button (only shown when a session is active)
        if active_id:
            st.divider()
            col_clear, col_del = st.columns(2)
            with col_clear:
                if st.button("🗑 Clear History", use_container_width=True, key="clear_hist"):
                    chat_service.clear_session_history(active_id, user_id)
                    st.session_state["chat_messages_cache"] = []
                    st.success("Cleared!")
                    st.rerun()
            with col_del:
                if st.button("❌ Delete Session", use_container_width=True, key="del_sess"):
                    chat_service.delete_session(active_id, user_id)
                    st.session_state["chat_active_session_id"] = None
                    st.session_state["chat_messages_cache"] = []
                    st.warning("Session deleted.")
                    st.rerun()


# ─── MAIN AREA ────────────────────────────────────────────────────────────────
active_session_id = st.session_state.get("chat_active_session_id")

if not active_session_id:
    # Landing state — no session selected
    st.markdown("""
<div style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 60%,#0f3460 100%);
            border-radius:16px;padding:36px 40px;margin-bottom:24px;">
  <h1 style="color:#fff;margin:0;font-size:2rem">💬 Chat with Memory</h1>
  <p style="color:#a0b4c8;margin:8px 0 0;font-size:1.05rem">
    Every conversation is saved per session. Come back anytime to continue where you left off.
  </p>
</div>
""", unsafe_allow_html=True)

    st.info("👈 Create a new session or select an existing one from the sidebar to start chatting.")
    st.stop()

# Load the selected session metadata
session_doc = _repo.get_session(active_session_id, user_id)
if not session_doc:
    st.error("Session not found. It may have been deleted.")
    st.session_state["chat_active_session_id"] = None
    st.session_state["chat_messages_cache"] = []
    st.stop()

# Header
col_title, col_info = st.columns([3, 1])
with col_title:
    st.markdown(
        f"## 💬 {session_doc.get('title') or session_doc['tenant_id']}"
    )
with col_info:
    st.markdown(
        f"<div style='text-align:right;color:#888;font-size:13px;margin-top:12px'>"
        f"<b>Label:</b> `{session_doc['tenant_id']}`&nbsp;&nbsp;"
        f"<b>Model:</b> `{session_doc.get('llm_model','gpt-4')}`"
        f"</div>",
        unsafe_allow_html=True,
    )
st.divider()

# ── Render message history ────────────────────────────────────────────────────
messages = st.session_state.get("chat_messages_cache", [])

if not messages:
    st.caption("No messages yet — send one below to start the conversation!")
else:
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        ts = msg.get("timestamp", "")[:19].replace("T", " ")  # readable timestamp
        with st.chat_message(role):
            st.markdown(content)
            st.caption(ts)

# ── Chat input ────────────────────────────────────────────────────────────────
user_input = st.chat_input("Type your message…")

if user_input:
    # Optimistically show user message
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                result = chat_service.send_message(
                    session_id=active_session_id,
                    user_id=user_id,
                    user_content=user_input,
                )
                st.markdown(result.reply)
                # Refresh local cache from service result
                st.session_state["chat_messages_cache"] = [
                    {
                        "role": m.role,
                        "content": m.content,
                        "timestamp": m.timestamp,
                        "id": m.id,
                    }
                    for m in result.history
                ]
            except Exception as exc:
                st.error(f"❌ Error: {exc}")
    st.rerun()
