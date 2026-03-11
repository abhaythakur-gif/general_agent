import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
import json
from utils.storage import list_agents, list_workflows, get_workflow, get_agent
from workflow.workflow_runner import run_workflow
from backend.schemas.agent_schema import AgentDefinition

st.set_page_config(page_title="Execute Workflow", page_icon="▶️", layout="wide")
st.title("▶️ Execute Workflow")

workflows = list_workflows()
if not workflows:
    st.warning("No workflows found. Build a workflow first.")
    st.stop()

agents_all  = list_agents()
agent_map   = {a["id"]: a for a in agents_all}
wf_options  = {wf["name"]: wf["id"] for wf in workflows}

selected_wf_name = st.selectbox("Select Workflow", list(wf_options.keys()))
selected_wf_id   = wf_options[selected_wf_name]
wf = get_workflow(selected_wf_id)
wf_agents = [agent_map[aid] for aid in wf.get("agent_ids", []) if aid in agent_map]

# Pipeline summary
if wf_agents:
    st.subheader("Pipeline")
    cols = st.columns(len(wf_agents))
    for i, (col, a) in enumerate(zip(cols, wf_agents)):
        col.markdown(f"**Step {i+1}**\n\n🤖 {a['name']}\n\n`{a['agent_type']}`")

# Build AgentDefinition objects
agent_defs = [AgentDefinition(**a) for a in wf_agents]

# Collect initial inputs (from the first agent)
first_inputs = wf_agents[0].get("inputs", []) if wf_agents else []
st.subheader("Initial Inputs")

initial_inputs = {}
with st.form("run_form"):
    for var in first_inputs:
        initial_inputs[var] = st.text_area(f"{var} *", height=80)
    run = st.form_submit_button("🚀 Run Workflow", use_container_width=True, type="primary")

if run:
    missing = [k for k, v in initial_inputs.items() if not v.strip()]
    if missing:
        st.error(f"Missing: {', '.join(missing)}")
    else:
        st.subheader("🔄 Live Logs")
        log_box   = st.empty()
        log_lines = []

        def on_log(entry):
            event = entry.get("event", "")
            agent = entry.get("agent", "")
            if event == "agent_start":
                log_lines.append(f"▶ Starting **{agent}**...")
            elif event == "tool_call":
                log_lines.append(f"  → Tool `{entry.get('tool')}`: {str(entry.get('input',''))[:80]}")
            elif event == "tool_response":
                log_lines.append(f"  ✓ Tool result: {str(entry.get('output',''))[:100]}")
            elif event == "llm_start":
                log_lines.append(f"  → LLM ({entry.get('model','')}) thinking...")
            elif event == "llm_complete":
                log_lines.append(f"  ✓ LLM done")
            elif event == "agent_complete":
                log_lines.append(f"  ✅ {agent} done ({entry.get('duration_ms','?')}ms)")
            elif event == "state_updated":
                log_lines.append(f"  📝 Wrote: {entry.get('new_vars', [])}")
            elif event == "workflow_complete":
                log_lines.append(f"\n✅ **Workflow complete!**")
            log_box.markdown("\n\n".join(log_lines))

        try:
            final_state = run_workflow(agent_defs, initial_inputs, log_callback=on_log)
            st.success("✅ Workflow completed!")
            st.subheader("📤 Final Output")
            output_vars = {k: v for k, v in final_state.items() if k not in initial_inputs}
            for key, value in output_vars.items():
                with st.expander(f"📄 {key}", expanded=True):
                    st.markdown(str(value))
            st.download_button("⬇️ Download Output (JSON)",
                data=json.dumps(final_state, indent=2),
                file_name="output.json", mime="application/json")
        except Exception as e:
            st.error(f"❌ Error: {e}")
