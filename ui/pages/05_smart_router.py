import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
import time as _time  # noqa: F401  (kept for compatibility)
from app.core.storage import list_workflows, list_agents
from app.engine.workflow.runner import start_workflow, resume_workflow
from app.schemas.agent import AgentDefinition
from app.llm.provider import get_llm
from app.repositories.repositories import ChatRepository

# ── Configurable defaults ─────────────────────────────────────────────────────
# Override via the SMART_ROUTER_LLM env variable; falls back to "gpt-4".
_SR_LLM_MODEL: str = os.getenv("SMART_ROUTER_LLM", "gpt-4")

st.set_page_config(page_title="Smart Execute", page_icon="🧭", layout="wide")

# ── Auth guard ────────────────────────────────────────────────────────────────
if "user_id" not in st.session_state or not st.session_state["user_id"]:
    st.warning("⚠️ Please go to the Home page and enter your User ID first.")
    st.stop()

user_id = st.session_state["user_id"]

# ── Session state bootstrap ───────────────────────────────────────────────────
for _k, _v in {
    "sr_phase":          "idle",  # idle | extracting | awaiting_input | running | paused | completed
    "sr_chat":           [],      # [{role, content}]
    "sr_wf_id":          None,
    "sr_wf_name":        "",
    "sr_agent_defs":     [],      # list of AgentDefinition.dict()
    "sr_par_groups":     [],
    "sr_wf_conds":       {},
    "sr_input_fields":   [],      # list[dict] — first-agent input schema fields
    "sr_original_query": "",     # raw user query used for extraction
    "sr_partial_inputs": {},     # inputs extracted so far (grows across follow-ups)
    "sr_execution_id":   None,
    "sr_all_logs":       [],
    "sr_final_state":    {},
    "sr_initial_inputs": {},
    "sr_session_id":      None,   # active MongoDB session id
    "sr_tenant_id":       "",     # human label for the active session
    "sr_pending_field":   None,   # name of the single field currently being asked
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Load user's workflows ─────────────────────────────────────────────────────
workflows = list_workflows(user_id)

# ── Chat-memory helpers ───────────────────────────────────────────────────────
_chat_repo = ChatRepository()


def _ensure_session(title: str = "Smart Execute") -> str:
    """Auto-create a MongoDB session for this conversation if one doesn't exist."""
    if st.session_state.get("sr_session_id"):
        return st.session_state["sr_session_id"]
    import time as _t
    tenant_id = f"sr-{user_id}-{int(_t.time())}"
    doc = _chat_repo.create_session(
        user_id=user_id,
        tenant_id=tenant_id,
        title=title,
        llm_model="gpt-4",
    )
    st.session_state["sr_session_id"] = doc["id"]
    st.session_state["sr_tenant_id"]  = doc["tenant_id"]
    return doc["id"]


def _update_session_title(title: str) -> None:
    sid = st.session_state.get("sr_session_id")
    if sid:
        try:
            _chat_repo._sessions.update_one({"_id": sid}, {"$set": {"title": title}})
        except Exception:
            pass


def _add_chat_msg(role: str, content: str) -> None:
    """Append to in-memory sr_chat AND persist to MongoDB."""
    st.session_state.sr_chat.append({"role": role, "content": content})
    try:
        sid = st.session_state.get("sr_session_id")
        if sid:
            _chat_repo.save_message(
                session_id=sid,
                user_id=user_id,
                tenant_id=st.session_state.get("sr_tenant_id", ""),
                role=role,
                content=content,
            )
    except Exception:
        pass  # never let DB errors break the UI


# ── Sidebar: session management ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🧭 Smart Execute")
    st.markdown(f"`👤 {user_id}`")
    st.divider()

    if st.button("➕ New Chat", use_container_width=True, key="sr_new_chat_btn"):
        for _k in list(st.session_state.keys()):
            if _k.startswith("sr_"):
                del st.session_state[_k]
        st.rerun()

    st.divider()
    st.markdown("**Past Sessions**")
    try:
        _past_sessions = _chat_repo.list_sessions(user_id)
    except Exception:
        _past_sessions = []

    if not _past_sessions:
        st.caption("No past sessions yet.")
    else:
        _active_sid = st.session_state.get("sr_session_id")
        for _sess in _past_sessions:
            _is_active = _sess["id"] == _active_sid
            _label     = _sess.get("title") or _sess.get("tenant_id", "Chat")
            _ts        = _sess.get("last_message_at", "")[:10]
            _count     = _sess.get("message_count", 0)
            if st.button(
                f"{'▶ ' if _is_active else ''}{_label}\n`{_ts} · {_count} msgs`",
                key=f"sr_sess_{_sess['id']}",
                use_container_width=True,
                type="primary" if _is_active else "secondary",
            ):
                # Load the selected session's chat history
                _msgs = _chat_repo.get_messages(_sess["id"], user_id, limit=200)
                for _k in list(st.session_state.keys()):
                    if _k.startswith("sr_"):
                        del st.session_state[_k]
                st.session_state["sr_session_id"] = _sess["id"]
                st.session_state["sr_tenant_id"]  = _sess.get("tenant_id", "")
                st.session_state["sr_chat"]        = [
                    {"role": m["role"], "content": m["content"]} for m in _msgs
                ]
                st.session_state["sr_phase"] = "completed"
                st.rerun()

# ── Page header ───────────────────────────────────────────────────────────────
st.title("🧭 Smart Execute")
st.markdown(f"`👤 {user_id}`")

if not workflows:
    st.warning("No workflows found. Please build a workflow first.")
    st.stop()

# ── Live-execution helpers ────────────────────────────────────────────────────

_TOOL_LABELS: dict = {
    "web_search":       "Searching the web",
    "search_web":       "Searching the web",
    "weather":          "Fetching weather data",
    "get_weather":      "Fetching weather data",
    "travel":           "Looking up travel info",
    "get_flights":      "Looking up flights",
    "get_hotels":       "Looking up hotels",
    "calculator":       "Running a calculation",
    "code_interpreter": "Running code",
    "file_read":        "Reading a file",
    "file_write":       "Writing to a file",
    "send_email":       "Sending an email",
    "database_query":   "Querying the database",
    "api_call":         "Calling an external API",
}

_EVENT_META: dict = {
    "workflow_start":       ("🚀", "#0d2a1a"),
    "workflow_resume":      ("↩️",  "#0d1a2e"),
    "agent_sequence":       ("🤖", "#0d1a2e"),
    "tool_call":            ("🔧", "#2e1a0d"),
    "agent_complete":       ("✅", "#0d2e0d"),
    "agent_skipped":        ("⏭",  "#2e1a00"),
    "parallel_group_start": ("⚡", "#0d1a2e"),
    "workflow_complete":    ("🎉", "#0d2e0d"),
    "workflow_error":       ("❌", "#2e0000"),
    "workflow_paused":      ("⏸️",  "#1a1500"),
}


def _action_label(entry: dict) -> str:
    event = entry.get("event", "")
    if event == "workflow_start":
        n = entry.get("num_agents", "?")
        return f"Workflow started with {n} agent{'s' if n != 1 else ''}"
    if event == "workflow_resume":
        return "Workflow resumed"
    if event == "agent_sequence":
        name = entry.get("agent", "Agent")
        step, total = entry.get("step", 0), entry.get("total", 0)
        return f"**{name}** is working · step {step} of {total}"
    if event == "tool_call":
        raw = entry.get("tool", "")
        return _TOOL_LABELS.get(raw, raw.replace("_", " ").title()) + "…"
    if event == "agent_complete":
        name = entry.get("agent", "Agent")
        dur  = entry.get("duration_ms")
        return f"**{name}** finished" + (f" · {dur/1000:.1f}s" if dur else "")
    if event == "agent_skipped":
        return f"**{entry.get('agent', 'Agent')}** was skipped"
    if event == "parallel_group_start":
        agents = entry.get("agents", [])
        return f"Running {', '.join(f'**{a}**' for a in agents)} in parallel"
    if event == "workflow_complete":
        return "Workflow completed successfully"
    if event == "workflow_error":
        return f"Something went wrong — {str(entry.get('error', ''))[:100]}"
    if event == "workflow_paused":
        return "Paused — waiting for your input"
    return ""


def _render_feed(placeholder, events: list):
    if not events:
        placeholder.empty()
        return
    recent = events[-8:]
    rows = []
    for ev in reversed(recent):
        icon, bg = _EVENT_META.get(ev["event"], ("ℹ️", "#111"))
        rows.append(
            f'<div style="background:{bg};border-radius:8px;padding:7px 12px;'
            f'display:flex;align-items:flex-start;gap:8px;margin-bottom:4px">'
            f'<span style="font-size:14px;flex-shrink:0;margin-top:1px">{icon}</span>'
            f'<span style="color:#ddd;font-size:12px;line-height:1.6">{ev["desc"]}</span>'
            f'</div>'
        )
    placeholder.markdown(
        '<div style="background:#0a0f1a;border-radius:12px;padding:12px 14px;margin:8px 0">'
        '<div style="color:#555;font-size:10px;font-weight:700;letter-spacing:1.5px;'
        'margin-bottom:8px">ACTIVITY</div>'
        + "".join(rows)
        + "</div>",
        unsafe_allow_html=True,
    )


def _render_agent_card(placeholder, state: dict):
    name   = state.get("name", "")
    status = state.get("status", "running")
    action = state.get("action", "Working…")
    step   = state.get("step", 0)
    total  = state.get("total", 0)
    if not name:
        placeholder.empty()
        return
    if status == "done":
        color, anim, icon, badge = "#66BB6A", "", "✅", "COMPLETED"
    elif status == "skipped":
        color, anim, icon, badge = "#FFA726", "", "⏭", "SKIPPED"
    else:
        color, icon, badge = "#42A5F5", "⚙️", "RUNNING"
        anim = "animation:agent-pulse 1.5s ease-in-out infinite;"
    placeholder.markdown(
        f"""<style>@keyframes agent-pulse{{
        0%  {{box-shadow:0 0 0 0   {color}55;}}
        70% {{box-shadow:0 0 0 12px {color}00;}}
        100%{{box-shadow:0 0 0 0   {color}00;}}
        }}</style>
        <div style="background:#0d1a2e;border:2px solid {color};border-radius:14px;
                    padding:18px 22px;margin:8px 0;{anim}">
          <div style="display:flex;align-items:center;gap:12px">
            <div style="font-size:32px;line-height:1">{icon}</div>
            <div style="flex:1">
              <div style="color:{color};font-size:10px;font-weight:700;
                          letter-spacing:1.5px;text-transform:uppercase">{badge}</div>
              <div style="color:#fff;font-size:20px;font-weight:700;margin-top:2px">{name}</div>
            </div>
            <div style="text-align:right">
              <div style="color:#555;font-size:10px;font-weight:600;letter-spacing:1px">STEP</div>
              <div style="color:{color};font-size:18px;font-weight:700">{step} / {total}</div>
            </div>
          </div>
          <div style="color:#bbb;font-size:13px;margin-top:12px;padding:9px 14px;
                      background:#ffffff08;border-radius:8px;border-left:3px solid {color}55">
            {action}
          </div>
        </div>""",
        unsafe_allow_html=True,
    )


def _make_live_callback(collected_logs: list, current_state: dict,
                        status_ph, feed_ph):
    live_events: list = []

    def callback(entry: dict):
        collected_logs.append(entry)
        try:
            event = entry.get("event", "")
            if event == "agent_sequence":
                current_state.update(
                    name=entry.get("agent", ""),
                    step=entry.get("step", 0),
                    total=entry.get("total", 0),
                    status="running",
                    action="Preparing…",
                )
            elif event == "llm_start":
                current_state["action"] = "Thinking…"
            elif event == "tool_call":
                raw = entry.get("tool", "")
                current_state["action"] = (
                    _TOOL_LABELS.get(raw, raw.replace("_", " ").title()) + "…"
                )
            elif event == "tool_response":
                current_state["action"] = "Processing tool response…"
            elif event == "llm_complete":
                current_state["action"] = "Finalising output…"
            elif event == "outputs_produced":
                current_state["action"] = "Writing output…"
            elif event == "agent_complete":
                dur = entry.get("duration_ms")
                current_state["status"] = "done"
                current_state["action"] = "Completed" + (f" in {dur:,} ms" if dur else "")
            elif event == "agent_skipped":
                current_state["status"] = "skipped"
                current_state["action"] = "Skipped — condition was false"
            elif event in ("parallel_group_start", "parallel_group_done"):
                agents_str = ", ".join(entry.get("agents", []))
                current_state["action"] = (
                    f"⚡ Running in parallel: {agents_str}"
                    if "start" in event
                    else f"⚡ Parallel group finished: {agents_str}"
                )
            elif event == "workflow_complete":
                current_state.update(name="", status="complete", action="")

            import threading
            if threading.current_thread() is threading.main_thread():
                _render_agent_card(status_ph, current_state)
                desc = _action_label(entry)
                if desc and event in _EVENT_META:
                    live_events.append(
                        {"icon": _EVENT_META[event][0], "desc": desc, "event": event}
                    )
                _render_feed(feed_ph, live_events)
        except Exception:
            pass

    return callback


# ── LLM routing helper ────────────────────────────────────────────────────────

def _route_query(query: str, wf_list: list):
    """Return best-matching workflow dict or None."""
    wf_list_text = "\n".join(
        f"{i + 1}. ID: {wf['id']} | Name: {wf['name']} | "
        f"Description: {wf.get('description', 'No description')}"
        for i, wf in enumerate(wf_list)
    )
    prompt = (
        "You are a workflow routing assistant. "
        "Based on the user's query, select the single most relevant workflow.\n\n"
        f"User Query: {query}\n\n"
        f"Available Workflows:\n{wf_list_text}\n\n"
        "Respond with ONLY the exact workflow ID (a UUID string). "
        "No explanation, punctuation, or extra text."
    )
    llm      = get_llm(_SR_LLM_MODEL)
    response = llm.invoke(prompt)
    matched_id = response.content.strip().strip('"').strip("'")

    valid_ids = {wf["id"]: wf for wf in wf_list}
    if matched_id not in valid_ids:
        matched_id = next(
            (wid for wid in valid_ids if wid.startswith(matched_id[:8])),
            None,
        )
    return valid_ids.get(matched_id) if matched_id else None


# ── Build AgentDefinition list from a workflow dict ───────────────────────────

def _build_agent_defs(wf: dict, agent_map: dict):
    """Returns (agent_defs, wf_conds, par_groups)."""
    wf_conds   = wf.get("conditions", {})
    par_groups = wf.get("parallel_groups", [])
    wf_agents  = [agent_map[aid] for aid in wf.get("agent_ids", []) if aid in agent_map]
    agent_defs = []
    for a in wf_agents:
        d = dict(a)
        d["run_if"] = wf_conds.get(a["id"])
        agent_defs.append(AgentDefinition(**d))
    return agent_defs, wf_conds, par_groups


# ── Input extraction from natural language ────────────────────────────────────

def _ask_for_one_field(field: dict, partial: dict, all_fields: list) -> str:
    """
    Build a simple, direct question for exactly one field.
    Does NOT use an LLM — generates deterministically so it can never bundle
    multiple fields into one message.
    """
    label = (
        field.get("description")
        or field["name"].replace("_", " ").replace("-", " ").capitalize()
    )
    # Strip trailing punctuation from the description if present
    label = label.rstrip(".?,!")
    return f"Could you tell me: {label}?"


def _extract_single_field(reply: str, field: dict, partial: dict):
    """
    Extract the value for one specific field from the user's reply.
    Returns the extracted string value, or None if not found.
    """
    import json as _json

    prompt = (
        "You are an input extraction assistant.\n"
        f'The user was asked: about the field "{field["name"]}" '
        f'({field.get("type", "str")}'
        + (f', meaning: {field["description"]}' if field.get('description') else '')
        + f").\n"
        f'Their reply was: "{reply}"\n\n'
        "Extract the value for this field from their reply.\n"
        "Respond ONLY with a JSON object in this exact format:\n"
        '{"value": "the extracted value or null if not found"}\n'
        "Respond with valid JSON only. No explanation."
    )
    try:
        llm      = get_llm(_SR_LLM_MODEL)
        raw      = llm.invoke(prompt).content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        parsed = _json.loads(raw)
        val = parsed.get("value")
        if val is None or str(val).lower() in ("null", "none", ""):
            return None
        return str(val)
    except Exception:
        # Fallback — treat the whole reply as the value
        return reply.strip() or None


def _extract_inputs(query: str, fields: list, partial: dict = None) -> dict:
    """
    First-pass extraction: try to pull ALL fields from the initial user query.
    Returns:
      {"ok": True,  "inputs": {field: value, ...}}
      {"ok": False, "extracted": {field: value, ...},
                    "missing": [field, ...],
                    "next_field": <field dict for the first missing field>,
                    "follow_up": "conversational question for THAT ONE field"}
    """
    import json as _json

    if not fields:
        return {"ok": True, "inputs": {}}

    partial = partial or {}

    field_lines = "\n".join(
        f"- {f['name']} ({f.get('type', 'str')})"
        + (f": {f['description']}" if f.get("description") else "")
        + (" [required]" if f.get("required", True) else " [optional]")
        for f in fields
    )

    partial_str = ""
    if partial:
        partial_str = "\nAlready known from earlier messages:\n" + "\n".join(
            f"  {k}: {v}" for k, v in partial.items() if v
        ) + "\n"

    prompt = (
        "You are an input extraction assistant for an AI workflow system.\n"
        "Extract structured inputs from the user's message.\n\n"
        f'User message: "{query}"\n'
        f"{partial_str}\n"
        f"Fields to extract:\n{field_lines}\n\n"
        "Rules:\n"
        "1. Extract as many fields as possible from the message.\n"
        "2. For fields that cannot be determined, use null.\n"
        "3. Infer reasonable values when the intent is clear "
        "(e.g. 'tomorrow' for a date field is acceptable).\n"
        "4. Respond ONLY with a valid JSON object in this exact format:\n"
        "{\n"
        '  \"extracted\": {\"field_name\": \"value_or_null\", ...},\n'
        '  \"missing_required\": [\"field1\", \"field2\"]\n'
        "}\n"
        "If all required fields are present, set missing_required to [].\n"
        "Respond with valid JSON only. No explanation."
    )

    llm      = get_llm(_SR_LLM_MODEL)
    response = llm.invoke(prompt)
    raw      = response.content.strip()

    # Strip markdown code fences if the model wraps the JSON
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        parsed = _json.loads(raw)
    except _json.JSONDecodeError:
        # Fallback — treat entire query as the first required field value
        first_required = next((f for f in fields if f.get("required", True)), None)
        if first_required:
            merged = {**partial, first_required["name"]: query}
            still_missing = [
                f for f in fields
                if f.get("required", True)
                and f["name"] != first_required["name"]
                and not merged.get(f["name"])
            ]
            if not still_missing:
                return {"ok": True, "inputs": merged}
            next_f    = still_missing[0]
            follow_up = _ask_for_one_field(next_f, merged, fields)
            return {
                "ok": False,
                "extracted": merged,
                "missing": [f["name"] for f in still_missing],
                "next_field": next_f,
                "follow_up": follow_up,
            }
        return {"ok": True, "inputs": {**partial}}

    extracted_raw = parsed.get("extracted", {})

    # Merge with previously known values; nulls don't overwrite existing values
    merged: dict = {**partial}
    for k, v in extracted_raw.items():
        if v is not None:
            merged[k] = str(v) if not isinstance(v, str) else v

    # Recompute missing required fields after merge
    missing_fields = [
        f for f in fields
        if f.get("required", True)
        and not merged.get(f["name"])
    ]

    if missing_fields:
        next_f    = missing_fields[0]
        follow_up = _ask_for_one_field(next_f, merged, fields)
        return {
            "ok": False,
            "extracted": merged,
            "missing": [f["name"] for f in missing_fields],
            "next_field": next_f,
            "follow_up": follow_up,
        }

    return {"ok": True, "inputs": merged}


# ── Chat rendering helper ─────────────────────────────────────────────────────

def _render_chat():
    for msg in st.session_state.sr_chat:
        role    = msg["role"]
        content = msg["content"]
        if role == "user":
            with st.chat_message("user"):
                st.markdown(content)
        elif role == "assistant":
            with st.chat_message("assistant"):
                st.markdown(content)
        elif role == "system":
            with st.chat_message("assistant", avatar="🔗"):
                st.markdown(content)
        elif role == "output":
            with st.chat_message("assistant", avatar="📤"):
                st.markdown(content)


# ── Output summary builder ────────────────────────────────────────────────────

def _build_output_message(final_state: dict,
                          initial_inputs: dict,
                          agent_defs: list) -> str:
    # Build the set of keys that agents formally declared as outputs
    all_schemas: dict = {}
    for ad in agent_defs:
        for f in ad.output_schema:
            all_schemas[f.name] = f

    # Show only declared output fields that are present in the final state.
    # This is fully schema-driven — no hardcoded key names.
    output_vars = {
        k: v for k, v in final_state.items()
        if k in all_schemas
    }

    if not output_vars:
        return "✅ Workflow completed — no output variables were produced."

    lines = ["✅ **Workflow completed. Here are the results:**\n"]
    for key, value in output_vars.items():
        schema_field = all_schemas.get(key)
        field_desc   = schema_field.description if schema_field else ""
        header = f"**{key}**" + (f" — *{field_desc}*" if field_desc else "")
        lines.append(header)
        if isinstance(value, (dict, list)):
            import json as _json
            lines.append(f"```json\n{_json.dumps(value, indent=2, default=str)}\n```")
        else:
            lines.append(str(value))
        lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# RENDER CHAT HISTORY (always drawn first)
# ─────────────────────────────────────────────────────────────────────────────
_render_chat()

# ─────────────────────────────────────────────────────────────────────────────
# PHASE: IDLE
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.sr_phase == "idle":
    if len(workflows) == 1:
        st.info(
            f"ℹ️ You have one workflow: **{workflows[0]['name']}**. "
            "Describe your task and I'll start it for you."
        )

    user_query = st.chat_input("What do you want to do?", key="sr_chat_input_idle")

    if user_query:
        _ensure_session()
        _add_chat_msg("user", user_query)

        matched_wf = None
        with st.spinner("Finding the best workflow for your query…"):
            if len(workflows) == 1:
                matched_wf = workflows[0]
            else:
                try:
                    matched_wf = _route_query(user_query, workflows)
                except Exception as exc:
                    _add_chat_msg("assistant", f"⚠️ Could not route your query: {exc}")
                    st.rerun()

        if matched_wf is None:
            _add_chat_msg("assistant", (
                "⚠️ I couldn't determine which workflow best matches your query. "
                "Please try rephrasing, or use the **Execute Workflow** page to select manually."
            ))
            st.rerun()

        wf_type = matched_wf.get("workflow_type", "sequential")
        wf_desc = matched_wf.get("description", "")
        sys_msg = (
            f"🔗 **Connected to: {matched_wf['name']}**"
            + (f" — *{wf_desc}*" if wf_desc else "")
        )
        _update_session_title(matched_wf["name"])
        _add_chat_msg("system", sys_msg)

        agents_all = list_agents(user_id)
        agent_map  = {a["id"]: a for a in agents_all}
        agent_defs, wf_conds, par_groups = _build_agent_defs(matched_wf, agent_map)

        # Build the complete set of fields to collect upfront before running the workflow.
        # Rules (applied in agent order):
        #   1. For every agent: add input_schema fields not yet produced by earlier agents.
        #   2. For data_collector agents: ALSO add their output_schema fields as user-supplied
        #      inputs, so the Data Collector finds them already in state and skips the pause.
        #   3. Never add the same field name twice (dedup by seen_names).
        input_fields     = []
        produced_outputs = set()   # names produced by earlier agents — not user-supplied
        seen_names       = set()   # dedup

        for ad in agent_defs:
            behavior = getattr(ad, "behavior", "task_executor") or "task_executor"

            # Regular input fields (from input_schema)
            for f in ad.input_schema:
                if f.name not in produced_outputs and f.name not in seen_names:
                    input_fields.append({
                        "name":        f.name,
                        "description": f.description,
                        "required":    f.required,
                        "type":        f.type,
                    })
                    seen_names.add(f.name)

            # For data_collector agents, also collect the output fields upfront.
            # This pre-fills the workflow state so the agent returns "complete"
            # without asking the user anything itself.
            if behavior == "data_collector":
                for f in ad.output_schema:
                    if f.name not in produced_outputs and f.name not in seen_names:
                        input_fields.append({
                            "name":        f.name,
                            "description": f.description,
                            "required":    f.required,
                            "type":        f.type,
                        })
                        seen_names.add(f.name)
            else:
                for f in ad.output_schema:
                    produced_outputs.add(f.name)

        st.session_state.sr_wf_id          = matched_wf["id"]
        st.session_state.sr_wf_name        = matched_wf["name"]
        st.session_state.sr_agent_defs     = [ad.dict() for ad in agent_defs]
        st.session_state.sr_par_groups     = par_groups
        st.session_state.sr_wf_conds       = wf_conds
        st.session_state.sr_input_fields   = input_fields
        st.session_state.sr_original_query = user_query   # used by extracting phase
        st.session_state.sr_partial_inputs = {}
        st.session_state.sr_phase          = "extracting"
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# PHASE: EXTRACTING  (silent — no user interaction)
# LLM tries to map the user's query onto the first agent's input schema.
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.sr_phase == "extracting":
    fields  = st.session_state.sr_input_fields
    query   = st.session_state.sr_original_query
    partial = st.session_state.sr_partial_inputs

    # If the workflow has no inputs just run immediately
    if not fields:
        st.session_state.sr_initial_inputs = {}
        st.session_state.sr_phase = "running"
        st.rerun()

    with st.spinner("Understanding your request…"):
        try:
            result = _extract_inputs(query, fields, partial)
        except Exception as exc:
            _add_chat_msg("assistant", f"⚠️ Could not understand your request: {exc}")
            st.session_state.sr_phase = "completed"
            st.rerun()

    if result["ok"]:
        # All required inputs extracted — start workflow immediately
        st.session_state.sr_initial_inputs = result["inputs"]
        st.session_state.sr_pending_field   = None
        st.session_state.sr_phase = "running"
        st.rerun()
    else:
        # Some required fields are missing — ask about ONE field at a time
        st.session_state.sr_partial_inputs = result["extracted"]
        st.session_state.sr_pending_field  = result["next_field"]
        _add_chat_msg("assistant", result["follow_up"])
        st.session_state.sr_phase = "awaiting_input"
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# PHASE: AWAITING_INPUT
# User answers one question at a time. We extract the pending field value,
# merge it, then ask for the next missing field (or run the workflow).
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.sr_phase == "awaiting_input":
    user_reply = st.chat_input(
        "Your answer…", key="sr_chat_input_awaiting"
    )

    if user_reply and user_reply.strip():
        _add_chat_msg("user", user_reply.strip())

        fields        = st.session_state.sr_input_fields
        partial       = st.session_state.sr_partial_inputs
        pending_field = st.session_state.sr_pending_field  # the field we just asked about

        with st.spinner("Got it, let me check…"):
            try:
                # Step 1 — extract the value for the field we specifically asked about
                if pending_field:
                    extracted_val = _extract_single_field(
                        user_reply.strip(), pending_field, partial
                    )
                    if extracted_val is not None:
                        partial = {**partial, pending_field["name"]: extracted_val}
                    # If extraction failed, stay on same field and re-ask
                    else:
                        label = (
                            pending_field.get("description")
                            or pending_field["name"].replace("_", " ")
                        )
                        _add_chat_msg(
                            "assistant",
                            f"Sorry, I didn't catch that. Could you tell me the {label}?",
                        )
                        st.session_state.sr_partial_inputs = partial
                        st.rerun()

                # Step 2 — find remaining missing required fields
                still_missing = [
                    f for f in fields
                    if f.get("required", True)
                    and not partial.get(f["name"])
                ]

                st.session_state.sr_partial_inputs = partial

                if not still_missing:
                    # All fields collected — proceed to run
                    st.session_state.sr_initial_inputs = partial
                    st.session_state.sr_pending_field  = None
                    st.session_state.sr_phase          = "running"
                else:
                    # Ask about the next missing field
                    next_f    = still_missing[0]
                    follow_up = _ask_for_one_field(next_f, partial, fields)
                    st.session_state.sr_pending_field = next_f
                    _add_chat_msg("assistant", follow_up)
                    # Stay in awaiting_input

            except Exception as exc:
                _add_chat_msg("assistant", f"⚠️ Could not process your answer: {exc}")
                st.session_state.sr_phase = "completed"

        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# PHASE: RUNNING
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.sr_phase == "running":
    agent_defs     = [AgentDefinition(**d) for d in st.session_state.sr_agent_defs]
    initial_inputs = st.session_state.sr_initial_inputs
    par_groups     = st.session_state.sr_par_groups

    st.markdown("---")
    st.markdown(
        '<div style="color:#42A5F5;font-size:12px;font-weight:700;'
        'letter-spacing:1.5px;margin-bottom:4px">⚡ LIVE EXECUTION</div>',
        unsafe_allow_html=True,
    )
    status_ph = st.empty()
    feed_ph   = st.empty()

    collected_logs: list = []
    current_state:  dict = {}
    callback = _make_live_callback(collected_logs, current_state, status_ph, feed_ph)

    try:
        result = start_workflow(
            agent_defs=agent_defs,
            initial_inputs=initial_inputs,
            workflow_id=st.session_state.sr_wf_id,
            parallel_groups=par_groups,
            log_callback=callback,
            user_id=user_id,
        )
    except Exception as exc:
        status_ph.empty()
        feed_ph.empty()
        _add_chat_msg("assistant", f"❌ Workflow execution failed: {exc}")
        st.session_state.sr_phase = "completed"
        st.rerun()

    status_ph.empty()
    feed_ph.empty()

    st.session_state.sr_all_logs     = collected_logs
    st.session_state.sr_execution_id = result["execution_id"]

    if result["status"] == "completed":
        st.session_state.sr_final_state = result["state"]
        output_msg = _build_output_message(result["state"], initial_inputs, agent_defs)
        _add_chat_msg("output", output_msg)
        st.session_state.sr_phase = "completed"

    elif result["status"] == "paused":
        follow_up = result.get("follow_up_question", "Could you provide more details?")
        _add_chat_msg("assistant", follow_up)
        st.session_state.sr_phase = "paused"

    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# PHASE: PAUSED (HITL)
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.sr_phase == "paused":
    user_reply = st.chat_input("Your response…", key="sr_chat_input_paused")

    if user_reply and user_reply.strip():
        _add_chat_msg("user", user_reply.strip())

        st.markdown("---")
        st.markdown(
            '<div style="color:#42A5F5;font-size:12px;font-weight:700;'
            'letter-spacing:1.5px;margin-bottom:4px">⚡ LIVE EXECUTION</div>',
            unsafe_allow_html=True,
        )
        status_ph = st.empty()
        feed_ph   = st.empty()

        collected_logs: list = []
        current_state:  dict = {}
        callback = _make_live_callback(
            collected_logs, current_state, status_ph, feed_ph
        )

        try:
            result = resume_workflow(
                execution_id=st.session_state.sr_execution_id,
                user_input=user_reply.strip(),
                log_callback=callback,
            )
        except Exception as exc:
            status_ph.empty()
            feed_ph.empty()
            _add_chat_msg("assistant", f"❌ Resume failed: {exc}")
            st.session_state.sr_phase = "completed"
            st.rerun()

        status_ph.empty()
        feed_ph.empty()

        agent_defs = [AgentDefinition(**d) for d in st.session_state.sr_agent_defs]
        st.session_state.sr_all_logs = result.get("logs", collected_logs)

        if result["status"] == "completed":
            st.session_state.sr_final_state = result["state"]
            output_msg = _build_output_message(
                result["state"], st.session_state.sr_initial_inputs, agent_defs
            )
            _add_chat_msg("output", output_msg)
            st.session_state.sr_phase = "completed"

        elif result["status"] == "paused":
            follow_up = result.get("follow_up_question", "Could you provide more details?")
            _add_chat_msg("assistant", follow_up)

        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# PHASE: COMPLETED
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.sr_phase == "completed":
    st.markdown("---")

    # Execution log expander
    if st.session_state.sr_all_logs:
        with st.expander("📋 Full Execution Log", expanded=False):
            log_lines = []
            for entry in st.session_state.sr_all_logs:
                ev = entry.get("event", "")
                ag = entry.get("agent", "")
                if ev == "workflow_start":
                    log_lines.append(
                        f"🚀 Workflow started — {entry.get('num_agents', '?')} agents"
                    )
                elif ev == "agent_sequence":
                    log_lines.append(
                        f"🤖 Step {entry.get('step')}/{entry.get('total')} — **{ag}**"
                    )
                elif ev == "agent_complete":
                    dur = entry.get("duration_ms")
                    log_lines.append(
                        "✅ **{}** completed".format(ag)
                        + (f" in {dur:,} ms" if dur else "")
                    )
                elif ev == "agent_skipped":
                    log_lines.append(f"⏭ **{ag}** skipped")
                elif ev == "tool_call":
                    log_lines.append(f"&nbsp;&nbsp;🔧 Tool `{entry.get('tool')}` called")
                elif ev == "workflow_complete":
                    log_lines.append("🎉 Workflow completed")
                elif ev == "workflow_paused":
                    log_lines.append(f"⏸️ Paused — **{ag}** needs input")
                elif ev == "workflow_resume":
                    log_lines.append("↩️ Workflow resumed")
                elif ev in ("workflow_error", "agent_error"):
                    log_lines.append(f"❌ Error: {entry.get('error', '')}")
            st.markdown("\n\n".join(log_lines))

    # Download buttons
    final_state    = st.session_state.sr_final_state
    initial_inputs = st.session_state.sr_initial_inputs
    output_vars = {
        k: v for k, v in final_state.items()
        if k not in initial_inputs
        and k not in ("collection_status", "follow_up_question",
                      "missing_fields", "partial_data", "user_message")
    }
    if output_vars:
        import json as _json
        col1, col2 = st.columns(2)
        col1.download_button(
            "⬇️ Download Outputs (JSON)",
            data=_json.dumps(output_vars, indent=2, default=str),
            file_name="outputs.json",
            mime="application/json",
            use_container_width=True,
        )
        col2.download_button(
            "⬇️ Download Full State (JSON)",
            data=_json.dumps(final_state, indent=2, default=str),
            file_name="full_state.json",
            mime="application/json",
            use_container_width=True,
        )

    st.markdown("---")
    st.markdown(
        "💬 **Ask another query** to start a new workflow, "
        "or click Reset to clear the chat."
    )
    col_reset, _ = st.columns([1, 3])
    if col_reset.button("🔄 Reset Chat", use_container_width=True):
        for _k in list(st.session_state.keys()):
            if _k.startswith("sr_"):
                del st.session_state[_k]
        st.rerun()

    new_query = st.chat_input("Ask something else…", key="sr_chat_input_done")

    if new_query and new_query.strip():
        # Preserve chat history; reset execution state; re-route
        st.session_state.sr_wf_id          = None
        st.session_state.sr_wf_name        = ""
        st.session_state.sr_agent_defs     = []
        st.session_state.sr_par_groups     = []
        st.session_state.sr_wf_conds       = {}
        st.session_state.sr_input_fields   = []
        st.session_state.sr_original_query = ""
        st.session_state.sr_partial_inputs = {}
        st.session_state.sr_pending_field  = None
        st.session_state.sr_execution_id   = None
        st.session_state.sr_all_logs       = []
        st.session_state.sr_final_state    = {}
        st.session_state.sr_initial_inputs = {}

        _add_chat_msg("system", "---\n*Starting a new query…*")
        _add_chat_msg("user", new_query)

        matched_wf = None
        with st.spinner("Finding the best workflow…"):
            if len(workflows) == 1:
                matched_wf = workflows[0]
            else:
                try:
                    matched_wf = _route_query(new_query, workflows)
                except Exception as exc:
                    _add_chat_msg("assistant", f"⚠️ Routing failed: {exc}")
                    st.rerun()

        if matched_wf is None:
            _add_chat_msg("assistant", (
                "⚠️ I couldn't determine which workflow best matches your query. "
                "Please try rephrasing."
            ))
            st.rerun()

        wf_desc = matched_wf.get("description", "")
        sys_msg = (
            f"🔗 **Connected to: {matched_wf['name']}**"
            + (f" — *{wf_desc}*" if wf_desc else "")
        )
        _update_session_title(matched_wf["name"])
        _add_chat_msg("system", sys_msg)

        agents_all = list_agents(user_id)
        agent_map  = {a["id"]: a for a in agents_all}
        agent_defs, wf_conds, par_groups = _build_agent_defs(matched_wf, agent_map)

        input_fields     = []
        produced_outputs = set()
        seen_names       = set()
        for ad in agent_defs:
            behavior = getattr(ad, "behavior", "task_executor") or "task_executor"
            for f in ad.input_schema:
                if f.name not in produced_outputs and f.name not in seen_names:
                    input_fields.append({
                        "name":        f.name,
                        "description": f.description,
                        "required":    f.required,
                        "type":        f.type,
                    })
                    seen_names.add(f.name)
            if behavior == "data_collector":
                for f in ad.output_schema:
                    if f.name not in produced_outputs and f.name not in seen_names:
                        input_fields.append({
                            "name":        f.name,
                            "description": f.description,
                            "required":    f.required,
                            "type":        f.type,
                        })
                        seen_names.add(f.name)
            else:
                for f in ad.output_schema:
                    produced_outputs.add(f.name)

        st.session_state.sr_wf_id          = matched_wf["id"]
        st.session_state.sr_wf_name        = matched_wf["name"]
        st.session_state.sr_agent_defs     = [ad.dict() for ad in agent_defs]
        st.session_state.sr_par_groups     = par_groups
        st.session_state.sr_wf_conds       = wf_conds
        st.session_state.sr_input_fields   = input_fields
        st.session_state.sr_original_query = new_query
        st.session_state.sr_partial_inputs = {}
        st.session_state.sr_phase          = "extracting"
        st.rerun()
