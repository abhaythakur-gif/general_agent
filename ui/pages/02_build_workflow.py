import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
from utils.storage import list_agents, save_workflow, list_workflows, delete_workflow
from workflow.workflow_validator import validate_workflow
from backend.schemas.agent_schema import AgentDefinition

st.set_page_config(page_title="Build Workflow", page_icon="🔗", layout="wide")
st.title("🔗 Build Workflow")
st.markdown("Chain agents into a sequential pipeline.")

agents = list_agents()
if not agents:
    st.warning("No agents found. Create agents first.")
    st.stop()

agent_map     = {a["id"]: a for a in agents}
agent_options = {a["name"]: a["id"] for a in agents}

with st.form("wf_form"):
    wf_name = st.text_input("Workflow Name *", placeholder="e.g. Blog Content Pipeline")
    wf_desc = st.text_area("Description *", height=80)
    selected_names = st.multiselect("Select agents in execution order *",
        list(agent_options.keys()))
    submitted = st.form_submit_button("💾 Save Workflow", use_container_width=True)

if selected_names:
    ordered = [agent_map[agent_options[n]] for n in selected_names]
    st.subheader("Pipeline Preview")
    for i, a in enumerate(ordered):
        prefix = "▶" if i == 0 else "⬇️"
        st.markdown(
            f"{prefix} **Step {i+1}: {a['name']}** `{a['agent_type']}`  —  "
            f"In: `{', '.join(a.get('inputs', []))}`  →  Out: `{', '.join(a.get('outputs', []))}`"
        )
    # Validate
    defs = [AgentDefinition(**a) for a in ordered]
    errors = validate_workflow(defs)
    if errors:
        st.error("⚠️ Validation errors:\n" + "\n".join(f"- {e}" for e in errors))
    else:
        st.success("✅ Input/output alignment valid.")

if submitted:
    if not wf_name or not selected_names:
        st.error("Name and at least one agent required.")
    else:
        wf = save_workflow({
            "name": wf_name,
            "description": wf_desc,
            "agent_ids": [agent_options[n] for n in selected_names],
        })
        st.success(f"✅ Workflow saved!  ID: `{wf['id']}`")

st.divider()
st.subheader("📋 Existing Workflows")
if st.button("🔄 Refresh"):
    st.rerun()

for wf in list_workflows():
    with st.expander(f"🔗 {wf['name']}"):
        for i, aid in enumerate(wf.get("agent_ids", [])):
            aname = agent_map.get(aid, {}).get("name", aid)
            st.markdown(f"  Step {i+1}: {aname}")
        if st.button("🗑️ Delete Workflow", key=f"delwf_{wf['id']}"):
            delete_workflow(wf["id"])
            st.rerun()
