import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
import json
import time as _time
from utils.storage import list_agents, list_workflows, get_workflow
from workflow.workflow_runner import start_workflow, resume_workflow
from backend.schemas.agent_schema import AgentDefinition

st.set_page_config(page_title="Execute Workflow", page_icon="▶️", layout="wide")
st.title("▶️ Execute Workflow")

# ── Session state bootstrap ───────────────────────────────────────────────────
for _k, _v in {
    "wf_status":       "idle",      # idle | paused | completed | error
    "execution_id":    None,
    "chat_messages":   [],           # [{role, content}]
    "all_logs":        [],           # accumulated across all runs/resumes
    "final_state":     {},
    "initial_inputs":  {},
    "wf_id_active":    None,         # workflow id of active execution
    "steps_tracker":   [],           # for pipeline visual
    "wf_header":       {},
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Workflow selector ─────────────────────────────────────────────────────────
workflows = list_workflows()
if not workflows:
    st.warning("No workflows found. Build a workflow first.")
    st.stop()

agents_all = list_agents()
agent_map  = {a["id"]: a for a in agents_all}
wf_options = {wf["name"]: wf["id"] for wf in workflows}

selected_wf_name = st.selectbox("Select Workflow", list(wf_options.keys()),
                                 key="wf_selector")
selected_wf_id   = wf_options[selected_wf_name]

# Reset state when user picks a different workflow
if st.session_state.wf_id_active != selected_wf_id:
    st.session_state.wf_status      = "idle"
    st.session_state.execution_id   = None
    st.session_state.chat_messages  = []
    st.session_state.all_logs       = []
    st.session_state.final_state    = {}
    st.session_state.initial_inputs = {}
    st.session_state.steps_tracker  = []
    st.session_state.wf_header      = {}
    st.session_state.wf_id_active   = selected_wf_id

wf         = get_workflow(selected_wf_id)
wf_agents  = [agent_map[aid] for aid in wf.get("agent_ids", []) if aid in agent_map]
wf_type    = wf.get("workflow_type", "sequential")
wf_conds   = wf.get("conditions", {})
par_groups = wf.get("parallel_groups", [])

# ── Workflow badge ────────────────────────────────────────────────────────────
badge_icon   = "🔀" if wf_type == "conditional" else "➡️"
badge_color  = "#FFA726" if wf_type == "conditional" else "#42A5F5"
par_label    = f"  ⚡ {len(par_groups)} parallel group(s)" if par_groups else ""
st.markdown(
    f'<span style="background:{badge_color}22;color:{badge_color};border-radius:6px;'
    f'padding:4px 12px;font-size:13px;font-weight:600">'
    f'{badge_icon} {wf_type.upper()}{par_label}</span>',
    unsafe_allow_html=True,
)

# ── Build typed AgentDefinition objects ───────────────────────────────────────
agent_defs = []
for a in wf_agents:
    d = dict(a)
    d["run_if"] = wf_conds.get(a["id"])
    agent_defs.append(AgentDefinition(**d))

# Check if any agent is a data_collector (determines if HITL may occur)
has_dc = any(getattr(ad, "behavior", "task_executor") == "data_collector"
             for ad in agent_defs)

# ── Pipeline overview card ────────────────────────────────────────────────────
BEHAVIOR_COLOR = {
    "task_executor":  "#42A5F5",
    "data_collector": "#FFA726",
    "aggregator":     "#AB47BC",
}

if wf_agents:
    st.subheader("Pipeline")
    cols = st.columns(len(wf_agents))
    for i, (col, a) in enumerate(zip(cols, wf_agents)):
        beh   = a.get("behavior", "task_executor")
        bc    = BEHAVIOR_COLOR.get(beh, "#888")
        cond  = wf_conds.get(a["id"], "")
        label = f"*if `{cond}`*" if cond else "*always runs*"
        col.markdown(
            f"**Step {i+1}**\n\n🤖 {a['name']}\n\n"
            f'<span style="background:{bc}22;color:{bc};border-radius:3px;'
            f'padding:1px 6px;font-size:10px">{beh.upper().replace("_"," ")}</span>\n\n'
            f"{label}",
            unsafe_allow_html=True,
        )
    if has_dc:
        st.info(
            "💬 This workflow contains a **data_collector** agent. "
            "It may pause and ask follow-up questions if your initial input is incomplete."
        )

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Log/pipeline visual helpers (reused across initial run and resumes)
# ─────────────────────────────────────────────────────────────────────────────
_STATUS_STYLE = {
    "pending":  ("⏳", "#333",    "#666"),
    "running":  ("⚙️", "#0d2a4a", "#42A5F5"),
    "done":     ("✅", "#0d2e0d", "#66BB6A"),
    "skipped":  ("⏭",  "#2e1a00", "#FFA726"),
    "error":    ("❌", "#2e0000", "#EF5350"),
    "paused":   ("⏸️", "#1a1500", "#FFD600"),
}

def _pipeline_html(steps: list, total: int) -> str:
    if not steps:
        return ""
    cards = []
    for s in steps:
        icon, bg, border = _STATUS_STYLE.get(s["status"], _STATUS_STYLE["pending"])
        pulse = "animation:pulse 1s infinite;" if s["status"] == "running" else ""
        dur   = (f'<div style="font-size:10px;color:{border};margin-top:4px">'
                 f'{s["duration_ms"]:,} ms</div>') if s.get("duration_ms") else ""
        cond  = s.get("condition")
        cond_html = ""
        if cond:
            cres  = s.get("cond_result")
            c_col = "#66BB6A" if cres is True else "#EF5350" if cres is False else "#888"
            cond_html = (
                f'<div style="font-size:10px;color:{c_col};margin-top:2px;word-break:break-all">'
                f'if {cond}</div>'
            )
        beh = s.get("behavior", "")
        beh_html = ""
        if beh:
            bc = BEHAVIOR_COLOR.get(beh, "#888")
            beh_html = (
                f'<div style="font-size:9px;color:{bc};margin-top:2px">'
                f'{beh.upper().replace("_"," ")}</div>'
            )
        cards.append(
            f'<div style="background:{bg};border:2px solid {border};border-radius:12px;'
            f'padding:12px 14px;min-width:120px;max-width:160px;text-align:center;{pulse}">'
            f'<div style="font-size:20px">{icon}</div>'
            f'<div style="font-weight:700;color:#fff;font-size:12px;margin-top:4px">'
            f'{s["name"]}</div>'
            f'<div style="font-size:10px;color:#888">Step {s["step"]}/{total}</div>'
            f'{beh_html}{cond_html}{dur}'
            f'</div>'
        )
    arrow = '<span style="color:#555;font-size:20px;align-self:center">→</span>'
    row   = arrow.join(cards)
    return (
        '<style>@keyframes pulse{0%{opacity:1}50%{opacity:.4}100%{opacity:1}}</style>'
        f'<div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;'
        f'padding:14px;background:#0a0f1a;border-radius:12px;margin:10px 0">{row}</div>'
    )


def _render_log(logs: list) -> str:
    """Convert structured log entries to a readable markdown string."""
    lines = []
    for entry in logs:
        event = entry.get("event", "")
        agent = entry.get("agent", "")

        if event == "workflow_start":
            lines.append(
                f"### 🚀 Workflow Started\n"
                f"Agents: **{entry.get('num_agents', '?')}** | "
                f"Inputs: `{'`, `'.join(entry.get('initial_inputs', []))}`"
            )
        elif event == "workflow_resume":
            lines.append(
                f"### ↩️ Workflow Resumed\n"
                f"Paused agent: **{entry.get('paused_agent', '?')}** | "
                f"New input: *{entry.get('new_input_preview', '')}*"
            )
        elif event == "agent_sequence":
            lines.append(
                f"---\n#### ⬇️ Step {entry.get('step')}/{entry.get('total')} — 🤖 **{agent}**"
            )
        elif event == "condition_check":
            cond = entry.get("condition")
            lines.append(
                f"&nbsp;&nbsp;📋 Condition: `{cond}`" if cond
                else "&nbsp;&nbsp;📋 No condition — always runs"
            )
        elif event == "condition_result":
            r = entry.get("result")
            lines.append(
                f"&nbsp;&nbsp;📋 Condition → {'✅ True' if r else '❌ False'}"
            )
        elif event == "agent_skipped":
            lines.append(f"&nbsp;&nbsp;⏭ **Skipped** (condition false)")
        elif event == "branch_data_collector":
            lines.append("&nbsp;&nbsp;💬 Mode: **data_collector** (structured extraction)")
        elif event == "branch_task_executor":
            lines.append("&nbsp;&nbsp;🔧 Mode: **task_executor**")
        elif event == "branch_aggregator":
            lines.append("&nbsp;&nbsp;🔗 Mode: **aggregator**")
        elif event == "dc_prompt_built":
            lines.append(
                f"&nbsp;&nbsp;🧠 Already collected: "
                f"`{'`, `'.join(entry.get('already_collected', []))  or 'nothing yet'}`"
            )
        elif event == "dc_complete":
            lines.append(
                f"&nbsp;&nbsp;✅ All required fields collected: "
                f"`{'`, `'.join(entry.get('extracted', []))}`"
            )
        elif event == "dc_incomplete":
            lines.append(
                f"&nbsp;&nbsp;⚠️ Still missing: `{'`, `'.join(entry.get('missing', []))}`\n\n"
                f"&nbsp;&nbsp;💬 Follow-up: *{entry.get('follow_up', '')}*"
            )
        elif event == "data_collector_status":
            status = entry.get("collection_status", "?")
            lines.append(
                f"&nbsp;&nbsp;📊 Collection status: **{status}**"
                + (f" | Missing: `{'`, `'.join(entry.get('missing', []))}`"
                   if entry.get("missing") else "")
            )
        elif event == "inputs_extracted":
            inp = entry.get("inputs", {})
            lines.append(
                "📥 **Inputs:**\n" +
                "\n".join(f"&nbsp;&nbsp;• `{k}` = {v}" for k, v in inp.items())
            )
        elif event == "llm_start":
            lines.append(
                f"&nbsp;&nbsp;🔮 LLM `{entry.get('model', '?')}` thinking…"
            )
        elif event == "llm_complete":
            lines.append("&nbsp;&nbsp;🔮 LLM responded")
        elif event == "tool_call":
            lines.append(
                f"&nbsp;&nbsp;🔧 Tool `{entry.get('tool')}` called"
            )
        elif event == "tool_response":
            lines.append(f"&nbsp;&nbsp;🔧 Tool responded")
        elif event == "outputs_produced":
            out = entry.get("outputs", {})
            lines.append(
                "📤 **Outputs:**\n" +
                "\n".join(f"&nbsp;&nbsp;• `{k}` = {v}" for k, v in out.items())
            )
        elif event == "agent_complete":
            dur = entry.get("duration_ms")
            lines.append(
                f"&nbsp;&nbsp;✅ Agent completed"
                + (f" in **{dur:,} ms**" if dur else "")
            )
        elif event == "workflow_paused":
            lines.append(
                f"\n---\n### ⏸️ Workflow Paused\n"
                f"Agent **{agent}** needs more information."
            )
        elif event == "workflow_complete":
            skipped = entry.get("skipped_agents", [])
            lines.append(
                f"\n---\n### ✅ Workflow Complete\n"
                f"Variables: `{'`, `'.join(entry.get('final_vars', []))}`"
                + (f"\nSkipped agents: {', '.join(skipped)}" if skipped else "")
            )
        elif event in ("parallel_group_start", "parallel_group_done"):
            agents_str = ", ".join(entry.get("agents", []))
            lines.append(
                f"&nbsp;&nbsp;⚡ Parallel group {'started' if 'start' in event else 'done'}: "
                f"**{agents_str}**"
            )
        elif event == "agent_error":
            lines.append(f"&nbsp;&nbsp;❌ **Error**: {entry.get('error', '')}")
        elif event == "workflow_error":
            lines.append(f"\n---\n### ❌ Workflow Error\n{entry.get('error', '')}")

    return "\n\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# STATE: IDLE — show initial input form
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.wf_status == "idle":
    first_agent  = wf_agents[0] if wf_agents else {}
    if first_agent.get("input_schema"):
        first_inputs = [f["name"] for f in first_agent["input_schema"]]
    else:
        first_inputs = first_agent.get("inputs", [])

    st.subheader("Initial Inputs")
    with st.form("run_form"):
        initial_inputs = {}
        for var in first_inputs:
            # Find description from input_schema if available
            desc = ""
            if first_agent.get("input_schema"):
                for f in first_agent["input_schema"]:
                    if f["name"] == var:
                        desc = f.get("description", "")
                        break
            label = f"{var} *" + (f" — *{desc}*" if desc else "")
            initial_inputs[var] = st.text_area(label, height=80, key=f"init_{var}")
        run = st.form_submit_button("🚀 Run Workflow", use_container_width=True, type="primary")

    if run:
        missing = [k for k, v in initial_inputs.items() if not v.strip()]
        if missing:
            st.error(f"Missing required inputs: {', '.join(missing)}")
        else:
            st.session_state.initial_inputs = initial_inputs
            collected_logs: list = []
            steps: list         = []
            wf_header: dict     = {}

            def on_log_start(entry):
                collected_logs.append(entry)

            with st.spinner("Running workflow…"):
                try:
                    result = start_workflow(
                        agent_defs=agent_defs,
                        initial_inputs=initial_inputs,
                        workflow_id=selected_wf_id,
                        parallel_groups=par_groups,
                        log_callback=on_log_start,
                    )
                except Exception as e:
                    st.error(f"❌ Error: {e}")
                    st.stop()

            st.session_state.all_logs    = collected_logs
            st.session_state.execution_id = result["execution_id"]

            if result["status"] == "completed":
                st.session_state.wf_status   = "completed"
                st.session_state.final_state = result["state"]
            elif result["status"] == "paused":
                st.session_state.wf_status   = "paused"
                follow_up = result.get("follow_up_question", "Could you provide more details?")
                st.session_state.chat_messages.append({
                    "role": "assistant", "content": follow_up
                })

            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# STATE: PAUSED — show chat interface for human-in-the-loop
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.wf_status == "paused":

    # ── Log so far ─────────────────────────────────────────────────────────────
    with st.expander("📋 Execution Log So Far", expanded=False):
        st.markdown(_render_log(st.session_state.all_logs))

    st.markdown("---")
    st.subheader("💬 Information Needed")
    st.caption(
        f"Execution ID: `{st.session_state.execution_id}` | "
        "The workflow is paused. Please answer the question below to continue."
    )

    # ── Chat history ──────────────────────────────────────────────────────────
    for msg in st.session_state.chat_messages:
        if msg["role"] == "assistant":
            st.markdown(
                f'<div style="background:#1a2535;border-left:4px solid #FFA726;'
                f'border-radius:8px;padding:12px 16px;margin:8px 0">'
                f'<span style="color:#FFA726;font-weight:700;font-size:12px">🤖 AGENT</span>'
                f'<div style="color:#fff;margin-top:6px">{msg["content"]}</div></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="background:#0d2a1a;border-left:4px solid #66BB6A;'
                f'border-radius:8px;padding:12px 16px;margin:8px 0;text-align:right">'
                f'<span style="color:#66BB6A;font-weight:700;font-size:12px">👤 YOU</span>'
                f'<div style="color:#fff;margin-top:6px">{msg["content"]}</div></div>',
                unsafe_allow_html=True,
            )

    # ── User reply input ──────────────────────────────────────────────────────
    with st.form("resume_form", clear_on_submit=True):
        user_reply = st.text_area(
            "Your response",
            height=100,
            placeholder="Type your answer here…",
            key="user_reply_input",
        )
        send = st.form_submit_button("📤 Send", use_container_width=True, type="primary")

    if send and user_reply.strip():
        st.session_state.chat_messages.append({
            "role": "user", "content": user_reply.strip()
        })

        collected_logs: list = []

        def on_log_resume(entry):
            collected_logs.append(entry)

        with st.spinner("Continuing workflow…"):
            try:
                result = resume_workflow(
                    execution_id=st.session_state.execution_id,
                    user_input=user_reply.strip(),
                    log_callback=on_log_resume,
                )
            except Exception as e:
                st.error(f"❌ Resume failed: {e}")
                st.stop()

        # Extend the accumulated logs (runner prepends old ones, so use new logs directly)
        st.session_state.all_logs = result.get("logs", collected_logs)

        if result["status"] == "completed":
            st.session_state.wf_status   = "completed"
            st.session_state.final_state = result["state"]
        elif result["status"] == "paused":
            follow_up = result.get("follow_up_question", "Could you provide more details?")
            st.session_state.chat_messages.append({
                "role": "assistant", "content": follow_up
            })

        st.rerun()

    # ── Reset button ──────────────────────────────────────────────────────────
    if st.button("🔄 Start Over"):
        st.session_state.wf_status     = "idle"
        st.session_state.execution_id  = None
        st.session_state.chat_messages = []
        st.session_state.all_logs      = []
        st.session_state.final_state   = {}
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# STATE: COMPLETED — show final results
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.wf_status == "completed":
    final_state     = st.session_state.final_state
    initial_inputs  = st.session_state.initial_inputs

    # ── Metrics ───────────────────────────────────────────────────────────────
    logs            = st.session_state.all_logs
    ran_agents      = sum(1 for e in logs if e.get("event") == "agent_complete")
    skipped_agents  = sum(1 for e in logs if e.get("event") == "agent_skipped")
    conv_turns      = sum(1 for m in st.session_state.chat_messages if m["role"] == "user")
    output_vars     = {k: v for k, v in final_state.items()
                       if k not in initial_inputs
                       and k not in ("collection_status", "follow_up_question",
                                     "missing_fields", "partial_data")}

    cols = st.columns(4)
    cols[0].metric("✅ Agents Ran",         ran_agents)
    cols[1].metric("⏭ Agents Skipped",      skipped_agents)
    cols[2].metric("💬 Conversation Turns",  conv_turns)
    cols[3].metric("📦 Output Variables",   len(output_vars))

    # ── Chat history if there was human-in-the-loop ───────────────────────────
    if st.session_state.chat_messages:
        st.subheader("💬 Conversation History")
        for msg in st.session_state.chat_messages:
            if msg["role"] == "assistant":
                st.markdown(
                    f'<div style="background:#1a2535;border-left:4px solid #FFA726;'
                    f'border-radius:8px;padding:10px 14px;margin:6px 0">'
                    f'<span style="color:#FFA726;font-size:11px;font-weight:600">🤖 AGENT</span>'
                    f'<div style="color:#fff;margin-top:4px">{msg["content"]}</div></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div style="background:#0d2a1a;border-left:4px solid #66BB6A;'
                    f'border-radius:8px;padding:10px 14px;margin:6px 0;text-align:right">'
                    f'<span style="color:#66BB6A;font-size:11px;font-weight:600">👤 YOU</span>'
                    f'<div style="color:#fff;margin-top:4px">{msg["content"]}</div></div>',
                    unsafe_allow_html=True,
                )

    # ── Final outputs ─────────────────────────────────────────────────────────
    st.subheader("📤 Final Outputs")
    if not output_vars:
        st.warning("No output variables produced. Check your workflow conditions.")
    else:
        # Find type info from agent output schemas
        all_agent_output_schemas: dict = {}
        for a in wf_agents:
            for f in a.get("output_schema", []):
                all_agent_output_schemas[f["name"]] = f

        for key, value in output_vars.items():
            schema_field = all_agent_output_schemas.get(key, {})
            field_type   = schema_field.get("type", "str") if schema_field else "str"
            field_desc   = schema_field.get("description", "") if schema_field else ""
            type_color   = {
                "str": "#42A5F5", "int": "#66BB6A", "float": "#AB47BC",
                "bool": "#FFA726", "list": "#EF5350", "dict": "#26C6DA",
            }.get(field_type, "#888")

            st.markdown(
                f'<div style="background:#0d2e0d;border-left:4px solid #66BB6A;'
                f'border-radius:8px;padding:10px 16px;margin-bottom:4px">'
                f'<span style="color:#66BB6A;font-weight:700;font-size:14px">📄 {key}</span>'
                f'&nbsp;<span style="background:{type_color}22;color:{type_color};'
                f'border-radius:3px;padding:1px 7px;font-size:11px">{field_type}</span>'
                + (f'<span style="color:#888;font-size:11px;margin-left:8px">{field_desc}</span>'
                   if field_desc else "")
                + f'</div>',
                unsafe_allow_html=True,
            )
            with st.expander("View / Copy", expanded=True):
                if isinstance(value, (dict, list)):
                    st.json(value)
                else:
                    st.markdown(str(value))
                    st.code(str(value), language="text")

    # ── Execution log ─────────────────────────────────────────────────────────
    with st.expander("📋 Full Execution Log"):
        st.markdown(_render_log(logs))

    # ── Download ──────────────────────────────────────────────────────────────
    dl_col1, dl_col2 = st.columns(2)
    dl_col1.download_button(
        "⬇️ Download Outputs (JSON)",
        data=json.dumps(output_vars, indent=2, default=str),
        file_name="outputs.json",
        mime="application/json",
        use_container_width=True,
    )
    dl_col2.download_button(
        "⬇️ Download Full State (JSON)",
        data=json.dumps(final_state, indent=2, default=str),
        file_name="full_state.json",
        mime="application/json",
        use_container_width=True,
    )

    if st.button("🔄 Run Again", use_container_width=True):
        st.session_state.wf_status     = "idle"
        st.session_state.execution_id  = None
        st.session_state.chat_messages = []
        st.session_state.all_logs      = []
        st.session_state.final_state   = {}
        st.rerun()

