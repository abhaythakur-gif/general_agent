import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
import time as _time
from app.core.storage import list_workflows
from app.llm.provider import get_llm

st.set_page_config(page_title="Smart Execute", page_icon="🧭", layout="wide")

# ── Auth guard ────────────────────────────────────────────────────────────────
if "user_id" not in st.session_state or not st.session_state["user_id"]:
    st.warning("⚠️ Please go to the Home page and enter your User ID first.")
    st.stop()

user_id = st.session_state["user_id"]

st.title("🧭 Smart Execute")
st.markdown(f"`👤 {user_id}`")
st.markdown(
    "Describe what you want to do — the system will automatically pick the right workflow for you."
)

# ── Fetch workflows ───────────────────────────────────────────────────────────
workflows = list_workflows(user_id)

if not workflows:
    st.warning("No workflows found. Please build a workflow first.")
    st.stop()

# ── Single workflow shortcut ──────────────────────────────────────────────────
if len(workflows) == 1:
    wf = workflows[0]
    st.info(f"ℹ️ You only have one workflow: **{wf['name']}**. Redirecting you there…")
    st.session_state["pre_selected_workflow_id"] = wf["id"]
    _time.sleep(1)
    st.switch_page("pages/03_execute_workflow.py")

# ── Main UI — only reached when user has 2+ workflows ────────────────────────
st.markdown("### 💬 Tell me what you want to do")

# Show available workflows for reference
with st.expander("📋 Available Workflows", expanded=False):
    for wf in workflows:
        wf_type = wf.get("workflow_type", "sequential")
        badge_color = "#FFA726" if wf_type == "conditional" else "#42A5F5"
        st.markdown(
            f'<div style="padding:10px 0;border-bottom:1px solid #222">'
            f'<span style="background:{badge_color}22;color:{badge_color};border-radius:4px;'
            f'padding:2px 8px;font-size:11px;font-weight:600">{wf_type.upper()}</span>'
            f' &nbsp;<strong style="color:#fff">{wf["name"]}</strong><br>'
            f'<span style="color:#888;font-size:13px">{wf.get("description", "No description provided.")}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown("")

# ── Query form ────────────────────────────────────────────────────────────────
with st.form("smart_router_form"):
    query = st.text_area(
        "Your query",
        placeholder="e.g. I want to find flights to Paris and book a hotel…",
        height=110,
    )
    submit = st.form_submit_button("🔍 Find & Run Best Workflow", use_container_width=True)

if submit:
    query = query.strip()
    if not query:
        st.warning("Please enter a query before submitting.")
        st.stop()

    with st.spinner("Analysing your query and selecting the best workflow…"):
        # Build the routing prompt
        wf_list_text = "\n".join(
            f"{i + 1}. ID: {wf['id']} | Name: {wf['name']} | Description: {wf.get('description', 'No description')}"
            for i, wf in enumerate(workflows)
        )

        prompt = (
            "You are a workflow routing assistant. "
            "Based on the user's query, select the single most relevant workflow from the list below.\n\n"
            f"User Query: {query}\n\n"
            f"Available Workflows:\n{wf_list_text}\n\n"
            "Respond with ONLY the exact workflow ID (a UUID string). "
            "Do not add any explanation, punctuation, or extra text."
        )

        try:
            llm = get_llm("gpt-4")
            response = llm.invoke(prompt)
            matched_id = response.content.strip().strip('"').strip("'")

            # Validate — exact match first
            valid_ids = {wf["id"]: wf for wf in workflows}

            # Fallback: partial prefix match (first 8 chars) in case of truncation
            if matched_id not in valid_ids:
                matched_id = next(
                    (wid for wid in valid_ids if wid.startswith(matched_id[:8])),
                    None,
                )

            if matched_id and matched_id in valid_ids:
                matched_wf = valid_ids[matched_id]
                st.success(
                    f"✅ You are being redirected to **{matched_wf['name']}** — "
                    f"best match for your query."
                )
                # Pass the selected workflow ID to the execute page
                st.session_state["pre_selected_workflow_id"] = matched_id
                # Small pause so the user can read the message
                _time.sleep(2)
                st.switch_page("pages/03_execute_workflow.py")
            else:
                st.error(
                    "⚠️ Could not determine the best workflow from your query. "
                    "Please use the **Execute Workflow** page to select manually."
                )

        except Exception as exc:
            st.error(f"⚠️ Routing failed: {exc}")
