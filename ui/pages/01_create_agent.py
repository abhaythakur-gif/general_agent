import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
from utils.storage import save_agent, list_agents, delete_agent
from tools.tool_registry import list_tools
from llm.llm_provider import list_models

st.set_page_config(page_title="Create Agent", page_icon="🔧", layout="wide")
st.title("🔧 Create Agent")
st.markdown("Define a new AI agent. No code required.")

all_tools = list_tools()
tool_names  = [t["name"] for t in all_tools]
tool_descs  = {t["name"]: t["description"] for t in all_tools}
models      = list_models()

with st.form("create_agent_form"):
    name        = st.text_input("Agent Name *", placeholder="e.g. Research Agent")
    description = st.text_area("Description *",
        placeholder="Describe what this agent does.", height=100)

    col1, col2 = st.columns(2)
    agent_type = col1.selectbox("Agent Type *",
        ["reasoning", "hybrid", "deterministic"],
        help="Deterministic: single tool call, no LLM.  Reasoning/Hybrid: LLM decides.")
    llm_model = col2.selectbox("LLM Model", models)

    selected_tools = st.multiselect("Tools (agent can ONLY use these)", tool_names)
    if selected_tools:
        with st.expander("Tool descriptions"):
            for t in selected_tools:
                st.markdown(f"- **{t}**: {tool_descs.get(t)}")

    col3, col4 = st.columns(2)
    inputs_raw  = col3.text_input("Input Variables *",  placeholder="e.g. topic, city")
    outputs_raw = col4.text_input("Output Variables *", placeholder="e.g. research_notes")

    submitted = st.form_submit_button("💾 Save Agent", use_container_width=True)

if submitted:
    if not name or not description or not inputs_raw or not outputs_raw:
        st.error("All fields are required.")
    else:
        agent = {
            "name": name,
            "description": description,
            "agent_type": agent_type,
            "llm_model": llm_model if agent_type != "deterministic" else None,
            "tools": selected_tools,
            "inputs":  [x.strip() for x in inputs_raw.split(",")  if x.strip()],
            "outputs": [x.strip() for x in outputs_raw.split(",") if x.strip()],
        }
        saved = save_agent(agent)
        st.success(f"✅ Agent \'{name}\' saved!  ID: `{saved['id']}`")

st.divider()
st.subheader("📋 Existing Agents")
if st.button("🔄 Refresh"):
    st.rerun()

for a in list_agents():
    with st.expander(f"🤖 {a['name']} — {a['agent_type'].title()}"):
        c1, c2 = st.columns(2)
        c1.markdown(f"**Description:** {a['description']}")
        c1.markdown(f"**LLM:** {a.get('llm_model') or 'None'}")
        c2.markdown(f"**Tools:** {', '.join(a.get('tools', [])) or 'None'}")
        c2.markdown(f"**Inputs:** {', '.join(a.get('inputs', []))}")
        c2.markdown(f"**Outputs:** {', '.join(a.get('outputs', []))}")
        if st.button("🗑️ Delete", key=f"del_{a['id']}"):
            delete_agent(a["id"])
            st.rerun()
