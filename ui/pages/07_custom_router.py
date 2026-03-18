import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
import time as _time
from app.core.storage import (
    list_workflows, list_agents, get_workflow,
    save_custom_router, list_custom_routers, get_custom_router,
    update_custom_router, delete_custom_router, router_name_exists,
)
from app.engine.workflow.runner import start_workflow, resume_workflow
from app.schemas.agent import AgentDefinition
from app.llm.provider import get_llm
from app.repositories.repositories import ChatRepository

_CR_LLM_MODEL: str = os.getenv("SMART_ROUTER_LLM", "gpt-4")

st.set_page_config(page_title="Custom Routers", page_icon="🗂️", layout="wide")

# ── Auth guard ────────────────────────────────────────────────────────────────
if "user_id" not in st.session_state or not st.session_state["user_id"]:
    st.warning("⚠️ Please go to the Home page and enter your User ID first.")
    st.stop()

user_id = st.session_state["user_id"]

# ── Session state bootstrap ───────────────────────────────────────────────────
for _k, _v in {
    "cr_mode":            "list",   # "list" | "form" | "chat"
    "cr_edit_router_id":  None,     # None = new, str = editing existing
    "cr_active_router":   None,     # router dict being chatted with
    "cr_chat":            [],
    "cr_phase":           "idle",
    "cr_wf_id":           None,
    "cr_wf_name":         "",
    "cr_agent_defs":      [],
    "cr_par_groups":      [],
    "cr_wf_conds":        {},
    "cr_input_fields":    [],
    "cr_original_query":  "",
    "cr_partial_inputs":  {},
    "cr_execution_id":    None,
    "cr_all_logs":        [],
    "cr_final_state":     {},
    "cr_initial_inputs":  {},
    "cr_nl_summary":      None,    # cached natural-language output summary
    "cr_session_id":      None,
    "cr_tenant_id":       "",
    "cr_pending_field":   None,
    "cr_confirm_delete":  None,     # router_id pending confirmation
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Shared data ───────────────────────────────────────────────────────────────
all_workflows = list_workflows(user_id)
workflow_map  = {wf["id"]: wf for wf in all_workflows}

# ── Chat repository ───────────────────────────────────────────────────────────
_chat_repo = ChatRepository()


def _ensure_session(title: str = "Custom Router Chat") -> str:
    if st.session_state.get("cr_session_id"):
        return st.session_state["cr_session_id"]
    import time as _t
    router_id  = (st.session_state.get("cr_active_router") or {}).get("id", "")
    tenant_id  = f"cr-{user_id}-{router_id}-{int(_t.time())}"
    doc = _chat_repo.create_session(
        user_id=user_id,
        tenant_id=tenant_id,
        title=title,
        llm_model=_CR_LLM_MODEL,
    )
    st.session_state["cr_session_id"] = doc["id"]
    st.session_state["cr_tenant_id"]  = doc["tenant_id"]
    return doc["id"]


def _update_session_title(title: str) -> None:
    sid = st.session_state.get("cr_session_id")
    if sid:
        try:
            _chat_repo._sessions.update_one({"_id": sid}, {"$set": {"title": title}})
        except Exception:
            pass


def _add_chat_msg(role: str, content: str) -> None:
    st.session_state.cr_chat.append({"role": role, "content": content})
    try:
        sid = st.session_state.get("cr_session_id")
        if sid:
            _chat_repo.save_message(
                session_id=sid,
                user_id=user_id,
                tenant_id=st.session_state.get("cr_tenant_id", ""),
                role=role,
                content=content,
            )
    except Exception:
        pass


def _reset_chat_state():
    """Reset only chat-related cr_ keys without touching mode / router."""
    for _k in ["cr_chat", "cr_phase", "cr_wf_id", "cr_wf_name", "cr_agent_defs",
               "cr_par_groups", "cr_wf_conds", "cr_input_fields", "cr_original_query",
               "cr_partial_inputs", "cr_execution_id", "cr_all_logs", "cr_final_state",
               "cr_initial_inputs", "cr_nl_summary", "cr_session_id", "cr_tenant_id",
               "cr_pending_field"]:
        defaults = {"cr_chat": [], "cr_phase": "idle", "cr_wf_id": None,
                    "cr_wf_name": "", "cr_agent_defs": [], "cr_par_groups": [],
                    "cr_wf_conds": {}, "cr_input_fields": [], "cr_original_query": "",
                    "cr_partial_inputs": {}, "cr_execution_id": None,
                    "cr_all_logs": [], "cr_final_state": {}, "cr_initial_inputs": {},
                    "cr_nl_summary": None,
                    "cr_session_id": None, "cr_tenant_id": "", "cr_pending_field": None}
        st.session_state[_k] = defaults.get(_k, None)


# ── Live-execution helpers ────────────────────────────────────────────────────

_TOOL_LABELS: dict = {
    "web_search": "Searching the web", "search_web": "Searching the web",
    "weather": "Fetching weather data", "get_weather": "Fetching weather data",
    "travel": "Looking up travel info", "get_flights": "Looking up flights",
    "get_hotels": "Looking up hotels", "calculator": "Running a calculation",
    "code_interpreter": "Running code", "file_read": "Reading a file",
    "file_write": "Writing to a file", "send_email": "Sending an email",
    "database_query": "Querying the database", "api_call": "Calling an external API",
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
        + "".join(rows) + "</div>",
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


def _make_live_callback(collected_logs: list, current_state: dict, status_ph, feed_ph):
    live_events: list = []

    def callback(entry: dict):
        collected_logs.append(entry)
        try:
            event = entry.get("event", "")
            if event == "agent_sequence":
                current_state.update(
                    name=entry.get("agent", ""), step=entry.get("step", 0),
                    total=entry.get("total", 0), status="running", action="Preparing…",
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


# ── Routing helper ────────────────────────────────────────────────────────────

def _route_query(query: str, wf_list: list):
    """Return best-matching workflow dict from wf_list, or None."""
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
    llm        = get_llm(_CR_LLM_MODEL)
    response   = llm.invoke(prompt)
    matched_id = response.content.strip().strip('"').strip("'")

    valid_ids = {wf["id"]: wf for wf in wf_list}
    if matched_id not in valid_ids:
        matched_id = next(
            (wid for wid in valid_ids if wid.startswith(matched_id[:8])),
            None,
        )
    return valid_ids.get(matched_id) if matched_id else None


# ── Build AgentDefinition list ────────────────────────────────────────────────

def _build_agent_defs(wf: dict, agent_map: dict):
    wf_conds   = wf.get("conditions", {})
    par_groups = wf.get("parallel_groups", [])
    wf_agents  = [agent_map[aid] for aid in wf.get("agent_ids", []) if aid in agent_map]
    agent_defs = []
    for a in wf_agents:
        d = dict(a)
        d["run_if"] = wf_conds.get(a["id"])
        agent_defs.append(AgentDefinition(**d))
    return agent_defs, wf_conds, par_groups


# ── Input extraction helpers ──────────────────────────────────────────────────

def _ask_for_one_field(field: dict, partial: dict, all_fields: list) -> str:
    label = (
        field.get("description")
        or field["name"].replace("_", " ").replace("-", " ").capitalize()
    )
    label = label.rstrip(".?,!")
    return f"Could you tell me: {label}?"


def _extract_single_field(reply: str, field: dict, partial: dict):
    import json as _json
    prompt = (
        "You are an input extraction assistant.\n"
        f'The user was asked about the field "{field["name"]}" '
        f'({field.get("type", "str")}'
        + (f', meaning: {field["description"]}' if field.get("description") else "")
        + f").\n"
        f'Their reply was: "{reply}"\n\n'
        "Extract the value for this field.\n"
        'Respond ONLY with: {"value": "the extracted value or null"}\n'
        "Valid JSON only."
    )
    try:
        llm  = get_llm(_CR_LLM_MODEL)
        raw  = llm.invoke(prompt).content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = _json.loads(raw.strip())
        val = parsed.get("value")
        if val is None or str(val).lower() in ("null", "none", ""):
            return None
        return str(val)
    except Exception:
        return reply.strip() or None


def _extract_inputs(query: str, fields: list, partial: dict = None) -> dict:
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
        partial_str = "\nAlready known:\n" + "\n".join(
            f"  {k}: {v}" for k, v in partial.items() if v
        ) + "\n"
    prompt = (
        "You are an input extraction assistant.\n"
        f'User message: "{query}"\n{partial_str}\n'
        f"Fields to extract:\n{field_lines}\n\n"
        "Respond ONLY with valid JSON:\n"
        '{"extracted": {"field_name": "value_or_null"}, "missing_required": ["field1"]}\n'
        "If all required fields present, set missing_required to []."
    )
    llm      = get_llm(_CR_LLM_MODEL)
    response = llm.invoke(prompt)
    raw      = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    try:
        parsed = _json.loads(raw)
    except _json.JSONDecodeError:
        first_req = next((f for f in fields if f.get("required", True)), None)
        if first_req:
            merged = {**partial, first_req["name"]: query}
            still_missing = [
                f for f in fields
                if f.get("required", True) and f["name"] != first_req["name"]
                and not merged.get(f["name"])
            ]
            if not still_missing:
                return {"ok": True, "inputs": merged}
            next_f = still_missing[0]
            return {"ok": False, "extracted": merged,
                    "missing": [f["name"] for f in still_missing],
                    "next_field": next_f, "follow_up": _ask_for_one_field(next_f, merged, fields)}
        return {"ok": True, "inputs": {**partial}}

    extracted_raw = parsed.get("extracted", {})
    merged: dict = {**partial}
    for k, v in extracted_raw.items():
        if v is not None:
            merged[k] = str(v) if not isinstance(v, str) else v

    missing_fields = [
        f for f in fields if f.get("required", True) and not merged.get(f["name"])
    ]
    if missing_fields:
        next_f = missing_fields[0]
        return {"ok": False, "extracted": merged,
                "missing": [f["name"] for f in missing_fields],
                "next_field": next_f, "follow_up": _ask_for_one_field(next_f, merged, fields)}
    return {"ok": True, "inputs": merged}


# ── Output builders ──────────────────────────────────────────────────────────

_INTERNAL_KEYS = {
    "collection_status", "follow_up_question", "missing_fields",
    "partial_data", "user_message",
}
_ERROR_KEYWORDS = (
    "error", "exception", "failed", "failure", "unauthorized",
    "forbidden", "not found", "timeout", "connection",
    "invalid", "expired", "missing",
)


def _build_output_message_legacy(final_state: dict, initial_inputs: dict, agent_defs: list) -> str:
    """Fallback raw field-dump — used when the NL summary LLM call fails."""
    import json as _json
    all_schemas: dict = {}
    for ad in agent_defs:
        for f in ad.output_schema:
            all_schemas[f.name] = f
    output_vars = {k: v for k, v in final_state.items() if k in all_schemas}
    if not output_vars:
        return "✅ Workflow completed — no output variables were produced."
    lines = ["✅ **Workflow completed. Here are the results:**\n"]
    for key, value in output_vars.items():
        schema_field = all_schemas.get(key)
        field_desc   = schema_field.description if schema_field else ""
        header = f"**{key}**" + (f" — *{field_desc}*" if field_desc else "")
        lines.append(header)
        if isinstance(value, (dict, list)):
            lines.append(f"```json\n{_json.dumps(value, indent=2, default=str)}\n```")
        else:
            lines.append(str(value))
        lines.append("")
    return "\n".join(lines)


def _build_nl_output(
    final_state: dict,
    initial_inputs: dict,
    agent_defs: list,
    original_query: str,
    workflow_name: str,
    llm_model: str,
) -> str:
    """
    Generate a single conversational reply from workflow outputs using the LLM.
    Falls back to the legacy field-dump if the LLM call fails.
    """
    import json as _json

    # Step 1 — collect declared output fields, strip internal control keys
    all_schemas: dict = {}
    for ad in agent_defs:
        for f in ad.output_schema:
            all_schemas[f.name] = f

    output_vars = {
        k: v for k, v in final_state.items()
        if k in all_schemas and k not in _INTERNAL_KEYS
    }

    # Step 2 — early exit for empty outputs
    if not output_vars:
        return "✅ Workflow completed — no output variables were produced."

    # Step 3 — build context block, cap each value at 2000 chars
    context_lines = []
    has_errors    = False
    for key, value in output_vars.items():
        schema_field = all_schemas.get(key)
        meaning = (
            schema_field.description
            if (schema_field and schema_field.description)
            else key
        )
        raw_str = (
            _json.dumps(value, ensure_ascii=False, default=str)
            if isinstance(value, (dict, list))
            else str(value)
        )
        if any(kw in raw_str.lower() for kw in _ERROR_KEYWORDS):
            has_errors = True
        capped = raw_str[:2000] + ("…" if len(raw_str) > 2000 else "")
        context_lines.append(
            f"Field: {key}\n  Meaning: {meaning}\n  Value: {capped}"
        )
    context_block = "\n\n".join(context_lines)

    # Step 4 — agent pipeline summary
    agent_names = [ad.name for ad in agent_defs]
    pipeline = (
        f"1 agent: {agent_names[0]}"
        if len(agent_names) == 1
        else f"{len(agent_names)} agents: {' → '.join(agent_names)}"
    )

    # Step 5 — conditional error instruction
    error_instruction = (
        "\nNote: one or more output values appear to contain an error. "
        "Explain what went wrong in plain English and suggest a practical fix."
    ) if has_errors else ""

    # Step 6 — length hint
    length_hint = (
        "Keep the reply to 2–4 sentences."
        if len(output_vars) == 1
        else "Use a brief section for each distinct topic (3–4 lines per section max)."
    )

    prompt = (
        "You are a helpful AI assistant presenting workflow results to a user "
        "in a chat interface.\n\n"
        f'The user asked: "{original_query}"\n'
        f"The workflow that ran: '{workflow_name}' ran {pipeline}.\n\n"
        "Here are the raw outputs produced:\n\n"
        f"{context_block}\n"
        f"{error_instruction}\n\n"
        "Your task:\n"
        "- Write a single, clear, conversational reply that directly answers "
        "the user's question.\n"
        "- Use natural prose. Bullet points or short headers are fine if they "
        "aid clarity.\n"
        "- Do NOT reproduce raw JSON, Python dict literals, or internal variable "
        "names (like 'weather_data' or 'final_response').\n"
        "- If a value contains an error message, explain what went wrong in plain "
        "English and suggest a fix if one is obvious.\n"
        "- Do not start with 'Based on the workflow outputs…' or similar filler "
        "phrases.\n"
        f"- {length_hint}\n\n"
        "Reply:"
    )

    try:
        llm = get_llm(_CR_LLM_MODEL)
        return llm.invoke(prompt).content.strip()
    except Exception:
        return _build_output_message_legacy(final_state, initial_inputs, agent_defs)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🗂️ Custom Routers")
    st.markdown(f"`👤 {user_id}`")
    st.divider()

    if st.session_state.cr_mode == "chat":
        router_name = (st.session_state.cr_active_router or {}).get("name", "Router")
        st.markdown(f"**Active Router:** `{router_name}`")
        if st.button("⬅️ Back to My Routers", use_container_width=True):
            _reset_chat_state()
            st.session_state.cr_mode          = "list"
            st.session_state.cr_active_router = None
            st.rerun()
        if st.button("➕ New Chat", use_container_width=True, key="cr_new_chat_btn"):
            _reset_chat_state()
            st.rerun()
        st.divider()
        st.markdown("**Past Sessions**")
        try:
            _past = _chat_repo.list_sessions(user_id)
        except Exception:
            _past = []
        if not _past:
            st.caption("No past sessions yet.")
        else:
            _active_sid = st.session_state.get("cr_session_id")
            for _sess in _past:
                _is_active = _sess["id"] == _active_sid
                _label     = _sess.get("title") or _sess.get("tenant_id", "Chat")
                _ts        = _sess.get("last_message_at", "")[:10]
                _count     = _sess.get("message_count", 0)
                if st.button(
                    f"{'▶ ' if _is_active else ''}{_label}\n`{_ts} · {_count} msgs`",
                    key=f"cr_sess_{_sess['id']}",
                    use_container_width=True,
                    type="primary" if _is_active else "secondary",
                ):
                    _msgs = _chat_repo.get_messages(_sess["id"], user_id, limit=200)
                    _reset_chat_state()
                    st.session_state["cr_session_id"] = _sess["id"]
                    st.session_state["cr_tenant_id"]  = _sess.get("tenant_id", "")
                    st.session_state["cr_chat"]        = [
                        {"role": m["role"], "content": m["content"]} for m in _msgs
                    ]
                    st.session_state["cr_phase"] = "completed"
                    st.rerun()
    else:
        if st.button("➕ Create New Router", use_container_width=True, type="primary"):
            st.session_state.cr_mode           = "form"
            st.session_state.cr_edit_router_id = None
            st.rerun()
        if st.button("📋 My Routers", use_container_width=True):
            st.session_state.cr_mode = "list"
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# MODE: LIST
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.cr_mode == "list":
    st.title("🗂️ Custom Routers")
    st.markdown(
        "Create named routers scoped to a specific set of your workflows. "
        "Each router uses the same smart LLM routing logic but only routes across "
        "the workflows you select — keeping your conversations focused."
    )
    st.divider()

    routers = list_custom_routers(user_id)

    if not routers:
        st.info(
            "You haven't created any custom routers yet.\n\n"
            "Click **➕ Create New Router** in the sidebar to get started."
        )
        st.stop()

    for router in routers:
        bound_wf_ids = router.get("workflow_ids", [])
        # Resolve workflow names; skip IDs for deleted workflows
        bound_wfs = [workflow_map[wid] for wid in bound_wf_ids if wid in workflow_map]
        deleted_count = len(bound_wf_ids) - len(bound_wfs)

        with st.container(border=True):
            col_info, col_btns = st.columns([3, 1])
            with col_info:
                st.markdown(f"### {router['name']}")
                if router.get("description"):
                    st.markdown(f"*{router['description']}*")

                if bound_wfs:
                    chips = " ".join(
                        f"`{wf['name']}`" for wf in bound_wfs
                    )
                    st.markdown(f"**Workflows ({len(bound_wfs)}):** {chips}")
                else:
                    st.markdown("**Workflows:** *(none)*")

                if deleted_count:
                    st.warning(
                        f"⚠️ {deleted_count} bound workflow(s) were deleted. "
                        "Edit this router to update the list."
                    )

                ts = router.get("updated_at", router.get("created_at", ""))[:10]
                st.caption(f"Last updated: {ts}")

            with col_btns:
                st.markdown("&nbsp;", unsafe_allow_html=True)

                chat_disabled = len(bound_wfs) == 0
                if st.button(
                    "▶ Chat",
                    key=f"chat_{router['id']}",
                    use_container_width=True,
                    type="primary",
                    disabled=chat_disabled,
                ):
                    _reset_chat_state()
                    st.session_state.cr_active_router = router
                    st.session_state.cr_mode          = "chat"
                    st.rerun()

                if st.button("✏️ Edit", key=f"edit_{router['id']}", use_container_width=True):
                    st.session_state.cr_edit_router_id = router["id"]
                    st.session_state.cr_mode           = "form"
                    st.rerun()

                if st.session_state.cr_confirm_delete == router["id"]:
                    st.error("Delete this router?")
                    c1, c2 = st.columns(2)
                    if c1.button("Yes", key=f"del_yes_{router['id']}", use_container_width=True):
                        delete_custom_router(router["id"], user_id)
                        st.session_state.cr_confirm_delete = None
                        st.success("Router deleted.")
                        st.rerun()
                    if c2.button("No", key=f"del_no_{router['id']}", use_container_width=True):
                        st.session_state.cr_confirm_delete = None
                        st.rerun()
                else:
                    if st.button(
                        "🗑️ Delete", key=f"del_{router['id']}", use_container_width=True
                    ):
                        st.session_state.cr_confirm_delete = router["id"]
                        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# MODE: FORM (Create / Edit)
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.cr_mode == "form":
    edit_id = st.session_state.cr_edit_router_id
    existing = get_custom_router(edit_id, user_id) if edit_id else None

    title = f"✏️ Edit Router — *{existing['name']}*" if existing else "➕ Create New Router"
    st.title(title)

    if st.button("⬅️ Back to My Routers"):
        st.session_state.cr_mode = "list"
        st.rerun()

    st.divider()

    # Pre-fill existing values
    default_name  = existing["name"] if existing else ""
    default_desc  = existing.get("description", "") if existing else ""
    default_wf_ids = set(existing.get("workflow_ids", [])) if existing else set()

    with st.form("cr_router_form"):
        name = st.text_input(
            "Router Name *",
            value=default_name,
            placeholder="e.g. Travel Assistant, HR Ops Router",
        )
        description = st.text_area(
            "Description",
            value=default_desc,
            placeholder="What kind of queries will users send to this router?",
            height=80,
        )

        st.markdown("**Select Workflows to include** *(select at least 2)*")

        if not all_workflows:
            st.warning("You have no workflows yet. Build a workflow first.")
            st.form_submit_button("Save", disabled=True)
        else:
            selected_ids = []
            for wf in all_workflows:
                checked = wf["id"] in default_wf_ids
                label   = wf["name"]
                desc    = wf.get("description", "")
                col_cb, col_desc = st.columns([1, 4])
                with col_cb:
                    is_selected = st.checkbox(label, value=checked, key=f"wf_cb_{wf['id']}")
                with col_desc:
                    if desc:
                        st.caption(desc)
                if is_selected:
                    selected_ids.append(wf["id"])

            submitted = st.form_submit_button("💾 Save Router", type="primary", use_container_width=True)

            if submitted:
                errors = []
                if not name.strip():
                    errors.append("Router name is required.")
                if len(selected_ids) < 2:
                    errors.append("Please select at least 2 workflows.")
                if not errors and router_name_exists(user_id, name.strip(), exclude_id=edit_id):
                    errors.append(f"A router named '{name.strip()}' already exists.")

                if errors:
                    for err in errors:
                        st.error(err)
                else:
                    payload = {
                        "name": name.strip(),
                        "description": description.strip(),
                        "workflow_ids": selected_ids,
                    }
                    if edit_id:
                        update_custom_router(edit_id, payload, user_id)
                        st.success(f"✅ Router **{name.strip()}** updated!")
                    else:
                        save_custom_router(payload, user_id)
                        st.success(f"✅ Router **{name.strip()}** created!")

                    _time.sleep(0.8)
                    st.session_state.cr_mode           = "list"
                    st.session_state.cr_edit_router_id = None
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# MODE: CHAT
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.cr_mode == "chat":
    router = st.session_state.cr_active_router
    if not router:
        st.error("No active router. Please go back and select a router.")
        st.stop()

    # Resolve the scoped workflow list (skip deleted ones)
    scoped_wf_ids  = router.get("workflow_ids", [])
    scoped_workflows = [workflow_map[wid] for wid in scoped_wf_ids if wid in workflow_map]

    if not scoped_workflows:
        st.error(
            f"Router **{router['name']}** has no valid workflows. "
            "Please edit the router and add at least one workflow."
        )
        st.stop()

    # ── Page header ───────────────────────────────────────────────────────────
    st.title(f"🗂️ {router['name']}")
    if router.get("description"):
        st.markdown(f"*{router['description']}*")

    wf_chips = " · ".join(f"`{wf['name']}`" for wf in scoped_workflows)
    st.markdown(
        f"🔒 **Scoped to {len(scoped_workflows)} workflow{'s' if len(scoped_workflows) != 1 else ''}:** {wf_chips}"
    )
    st.divider()

    # ── Render chat history ───────────────────────────────────────────────────
    for msg in st.session_state.cr_chat:
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

    # ── PHASE: IDLE ───────────────────────────────────────────────────────────
    if st.session_state.cr_phase == "idle":
        if len(scoped_workflows) == 1:
            st.info(
                f"ℹ️ This router contains one workflow: **{scoped_workflows[0]['name']}**. "
                "Describe your task and I'll start it for you."
            )
        user_query = st.chat_input("What do you want to do?", key="cr_input_idle")

        if user_query:
            _ensure_session(title=router["name"])
            _add_chat_msg("user", user_query)

            matched_wf = None
            with st.spinner("Finding the best workflow for your query…"):
                if len(scoped_workflows) == 1:
                    matched_wf = scoped_workflows[0]
                else:
                    try:
                        matched_wf = _route_query(user_query, scoped_workflows)
                    except Exception as exc:
                        _add_chat_msg("assistant", f"⚠️ Could not route your query: {exc}")
                        st.rerun()

            if matched_wf is None:
                _add_chat_msg("assistant", (
                    "⚠️ I couldn't match your query to any workflow in this router. "
                    "Try rephrasing, or check that this router has the right workflows."
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
                            "name": f.name, "description": f.description,
                            "required": f.required, "type": f.type,
                        })
                        seen_names.add(f.name)
                if behavior == "data_collector":
                    for f in ad.output_schema:
                        if f.name not in produced_outputs and f.name not in seen_names:
                            input_fields.append({
                                "name": f.name, "description": f.description,
                                "required": f.required, "type": f.type,
                            })
                            seen_names.add(f.name)
                else:
                    for f in ad.output_schema:
                        produced_outputs.add(f.name)

            st.session_state.cr_wf_id          = matched_wf["id"]
            st.session_state.cr_wf_name        = matched_wf["name"]
            st.session_state.cr_agent_defs     = [ad.dict() for ad in agent_defs]
            st.session_state.cr_par_groups     = par_groups
            st.session_state.cr_wf_conds       = wf_conds
            st.session_state.cr_input_fields   = input_fields
            st.session_state.cr_original_query = user_query
            st.session_state.cr_partial_inputs = {}
            st.session_state.cr_phase          = "extracting"
            st.rerun()

    # ── PHASE: EXTRACTING ────────────────────────────────────────────────────
    elif st.session_state.cr_phase == "extracting":
        fields  = st.session_state.cr_input_fields
        query   = st.session_state.cr_original_query
        partial = st.session_state.cr_partial_inputs

        if not fields:
            st.session_state.cr_initial_inputs = {}
            st.session_state.cr_phase = "running"
            st.rerun()

        with st.spinner("Understanding your request…"):
            try:
                result = _extract_inputs(query, fields, partial)
            except Exception as exc:
                _add_chat_msg("assistant", f"⚠️ Could not understand your request: {exc}")
                st.session_state.cr_phase = "completed"
                st.rerun()

        if result["ok"]:
            st.session_state.cr_initial_inputs = result["inputs"]
            st.session_state.cr_pending_field   = None
            st.session_state.cr_phase = "running"
            st.rerun()
        else:
            st.session_state.cr_partial_inputs = result["extracted"]
            st.session_state.cr_pending_field  = result["next_field"]
            _add_chat_msg("assistant", result["follow_up"])
            st.session_state.cr_phase = "awaiting_input"
            st.rerun()

    # ── PHASE: AWAITING_INPUT ────────────────────────────────────────────────
    elif st.session_state.cr_phase == "awaiting_input":
        user_reply = st.chat_input("Your answer…", key="cr_input_awaiting")

        if user_reply and user_reply.strip():
            _add_chat_msg("user", user_reply.strip())
            fields        = st.session_state.cr_input_fields
            partial       = st.session_state.cr_partial_inputs
            pending_field = st.session_state.cr_pending_field

            with st.spinner("Got it, let me check…"):
                try:
                    if pending_field:
                        extracted_val = _extract_single_field(
                            user_reply.strip(), pending_field, partial
                        )
                        if extracted_val is not None:
                            partial = {**partial, pending_field["name"]: extracted_val}
                        else:
                            label = (
                                pending_field.get("description")
                                or pending_field["name"].replace("_", " ")
                            )
                            _add_chat_msg("assistant", f"Sorry, I didn't catch that. Could you tell me the {label}?")
                            st.session_state.cr_partial_inputs = partial
                            st.rerun()

                    still_missing = [
                        f for f in fields
                        if f.get("required", True) and not partial.get(f["name"])
                    ]
                    st.session_state.cr_partial_inputs = partial

                    if not still_missing:
                        st.session_state.cr_initial_inputs = partial
                        st.session_state.cr_pending_field  = None
                        st.session_state.cr_phase          = "running"
                    else:
                        next_f    = still_missing[0]
                        follow_up = _ask_for_one_field(next_f, partial, fields)
                        st.session_state.cr_pending_field = next_f
                        _add_chat_msg("assistant", follow_up)
                except Exception as exc:
                    _add_chat_msg("assistant", f"⚠️ Could not process your answer: {exc}")
                    st.session_state.cr_phase = "completed"
            st.rerun()

    # ── PHASE: RUNNING ───────────────────────────────────────────────────────
    elif st.session_state.cr_phase == "running":
        agent_defs     = [AgentDefinition(**d) for d in st.session_state.cr_agent_defs]
        initial_inputs = st.session_state.cr_initial_inputs
        par_groups     = st.session_state.cr_par_groups

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
                workflow_id=st.session_state.cr_wf_id,
                parallel_groups=par_groups,
                log_callback=callback,
                user_id=user_id,
            )
        except Exception as exc:
            status_ph.empty()
            feed_ph.empty()
            _add_chat_msg("assistant", f"❌ Workflow execution failed: {exc}")
            st.session_state.cr_phase = "completed"
            st.rerun()

        status_ph.empty()
        feed_ph.empty()
        st.session_state.cr_all_logs     = collected_logs
        st.session_state.cr_execution_id = result["execution_id"]

        if result["status"] == "completed":
            st.session_state.cr_final_state = result["state"]
            output_msg = _build_nl_output(
                final_state    = result["state"],
                initial_inputs = initial_inputs,
                agent_defs     = agent_defs,
                original_query = st.session_state.cr_original_query,
                workflow_name  = st.session_state.cr_wf_name,
                llm_model      = _CR_LLM_MODEL,
            )
            st.session_state.cr_nl_summary = output_msg
            _add_chat_msg("output", output_msg)
            st.session_state.cr_phase = "completed"
        elif result["status"] == "paused":
            follow_up = result.get("follow_up_question", "Could you provide more details?")
            _add_chat_msg("assistant", follow_up)
            st.session_state.cr_phase = "paused"
        st.rerun()

    # ── PHASE: PAUSED ────────────────────────────────────────────────────────
    elif st.session_state.cr_phase == "paused":
        user_reply = st.chat_input("Your response…", key="cr_input_paused")

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
            callback = _make_live_callback(collected_logs, current_state, status_ph, feed_ph)

            try:
                result = resume_workflow(
                    execution_id=st.session_state.cr_execution_id,
                    user_input=user_reply.strip(),
                    log_callback=callback,
                )
            except Exception as exc:
                status_ph.empty()
                feed_ph.empty()
                _add_chat_msg("assistant", f"❌ Resume failed: {exc}")
                st.session_state.cr_phase = "completed"
                st.rerun()

            status_ph.empty()
            feed_ph.empty()
            agent_defs = [AgentDefinition(**d) for d in st.session_state.cr_agent_defs]
            st.session_state.cr_all_logs = result.get("logs", collected_logs)

            if result["status"] == "completed":
                st.session_state.cr_final_state = result["state"]
                output_msg = _build_nl_output(
                    final_state    = result["state"],
                    initial_inputs = st.session_state.cr_initial_inputs,
                    agent_defs     = agent_defs,
                    original_query = st.session_state.cr_original_query,
                    workflow_name  = st.session_state.cr_wf_name,
                    llm_model      = _CR_LLM_MODEL,
                )
                st.session_state.cr_nl_summary = output_msg
                _add_chat_msg("output", output_msg)
                st.session_state.cr_phase = "completed"
            elif result["status"] == "paused":
                follow_up = result.get("follow_up_question", "Could you provide more details?")
                _add_chat_msg("assistant", follow_up)
            st.rerun()

    # ── PHASE: COMPLETED ─────────────────────────────────────────────────────
    elif st.session_state.cr_phase == "completed":
        st.markdown("---")

        if st.session_state.cr_all_logs:
            with st.expander("📋 Full Execution Log", expanded=False):
                log_lines = []
                for entry in st.session_state.cr_all_logs:
                    ev = entry.get("event", "")
                    ag = entry.get("agent", "")
                    if ev == "workflow_start":
                        log_lines.append(f"🚀 Workflow started — {entry.get('num_agents', '?')} agents")
                    elif ev == "agent_sequence":
                        log_lines.append(f"🤖 Step {entry.get('step')}/{entry.get('total')} — **{ag}**")
                    elif ev == "agent_complete":
                        dur = entry.get("duration_ms")
                        log_lines.append("✅ **{}** completed".format(ag) + (f" in {dur:,} ms" if dur else ""))
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

        final_state    = st.session_state.cr_final_state
        initial_inputs = st.session_state.cr_initial_inputs
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
            "💬 **Ask another query** to route to a new workflow, "
            "or click **New Chat** in the sidebar to start fresh."
        )

        new_query = st.chat_input("Ask something else…", key="cr_input_done")

        if new_query and new_query.strip():
            # Preserve chat history; reset execution state; re-route
            for _k in ["cr_wf_id", "cr_wf_name", "cr_agent_defs", "cr_par_groups",
                       "cr_wf_conds", "cr_input_fields", "cr_original_query",
                       "cr_partial_inputs", "cr_pending_field", "cr_execution_id",
                       "cr_all_logs", "cr_final_state", "cr_initial_inputs",
                       "cr_nl_summary"]:
                defaults = {
                    "cr_wf_id": None, "cr_wf_name": "", "cr_agent_defs": [],
                    "cr_par_groups": [], "cr_wf_conds": {}, "cr_input_fields": [],
                    "cr_original_query": "", "cr_partial_inputs": {},
                    "cr_pending_field": None, "cr_execution_id": None,
                    "cr_all_logs": [], "cr_final_state": {}, "cr_initial_inputs": {},
                    "cr_nl_summary": None,
                }
                st.session_state[_k] = defaults.get(_k)

            _add_chat_msg("system", "---\n*Starting a new query…*")
            _add_chat_msg("user", new_query)

            matched_wf = None
            with st.spinner("Finding the best workflow…"):
                if len(scoped_workflows) == 1:
                    matched_wf = scoped_workflows[0]
                else:
                    try:
                        matched_wf = _route_query(new_query, scoped_workflows)
                    except Exception as exc:
                        _add_chat_msg("assistant", f"⚠️ Routing failed: {exc}")
                        st.rerun()

            if matched_wf is None:
                _add_chat_msg("assistant", (
                    "⚠️ I couldn't match your query to any workflow in this router. "
                    "Try rephrasing."
                ))
                st.rerun()

            wf_desc = matched_wf.get("description", "")
            _update_session_title(matched_wf["name"])
            _add_chat_msg("system", f"🔗 **Connected to: {matched_wf['name']}**"
                          + (f" — *{wf_desc}*" if wf_desc else ""))

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
                            "name": f.name, "description": f.description,
                            "required": f.required, "type": f.type,
                        })
                        seen_names.add(f.name)
                if behavior == "data_collector":
                    for f in ad.output_schema:
                        if f.name not in produced_outputs and f.name not in seen_names:
                            input_fields.append({
                                "name": f.name, "description": f.description,
                                "required": f.required, "type": f.type,
                            })
                            seen_names.add(f.name)
                else:
                    for f in ad.output_schema:
                        produced_outputs.add(f.name)

            st.session_state.cr_wf_id          = matched_wf["id"]
            st.session_state.cr_wf_name        = matched_wf["name"]
            st.session_state.cr_agent_defs     = [ad.dict() for ad in agent_defs]
            st.session_state.cr_par_groups     = par_groups
            st.session_state.cr_wf_conds       = wf_conds
            st.session_state.cr_input_fields   = input_fields
            st.session_state.cr_original_query = new_query
            st.session_state.cr_partial_inputs = {}
            st.session_state.cr_phase          = "extracting"
            st.rerun()
