import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
from utils.storage import save_agent, list_agents, delete_agent
from tools.tool_registry import list_tools
from llm.llm_provider import list_models

st.set_page_config(page_title="Create Agent", page_icon="🔧", layout="wide")
st.title("🔧 Create Agent")
st.markdown("Define a new AI agent with typed input/output schemas. No code required.")

all_tools  = list_tools()
tool_names = [t["name"] for t in all_tools]
tool_descs = {t["name"]: t["description"] for t in all_tools}
models     = list_models()

FIELD_TYPES = ["str", "int", "float", "bool", "list", "dict"]
BEHAVIORS   = ["task_executor", "data_collector", "aggregator"]
BEHAVIOR_HELP = {
    "task_executor":  "Standard agent: uses tools and LLM to complete a task.",
    "data_collector": "Collects structured data from user messages. Pauses and asks follow-up questions until all required fields are filled.",
    "aggregator":     "Combines multiple upstream outputs into a single coherent result.",
}

# ── Session state for dynamic schema rows ──────────────────────────────────────
if "inp_fields" not in st.session_state:
    st.session_state.inp_fields = [{"name": "", "type": "str", "description": "", "required": True}]
if "out_fields" not in st.session_state:
    st.session_state.out_fields = [{"name": "", "type": "str", "description": "", "required": True}]


def _schema_builder(key_prefix: str, fields_key: str, label: str, color: str):
    """Renders a dynamic schema builder table and returns the current field list."""
    st.markdown(
        f'<div style="color:{color};font-weight:700;font-size:13px;margin-bottom:4px">'
        f'{label}</div>',
        unsafe_allow_html=True,
    )
    fields = st.session_state[fields_key]
    to_delete = None

    for i, field in enumerate(fields):
        c1, c2, c3, c4, c5 = st.columns([3, 2, 4, 1, 1])
        field["name"]        = c1.text_input("Name",        value=field["name"],
                                              key=f"{key_prefix}_name_{i}",
                                              label_visibility="collapsed",
                                              placeholder="field_name")
        field["type"]        = c2.selectbox("Type",         FIELD_TYPES,
                                             index=FIELD_TYPES.index(field.get("type", "str")),
                                             key=f"{key_prefix}_type_{i}",
                                             label_visibility="collapsed")
        field["description"] = c3.text_input("Description", value=field["description"],
                                              key=f"{key_prefix}_desc_{i}",
                                              label_visibility="collapsed",
                                              placeholder="What this field represents")
        field["required"]    = c4.checkbox("Req", value=field["required"],
                                            key=f"{key_prefix}_req_{i}")
        if len(fields) > 1:
            if c5.button("✕", key=f"{key_prefix}_del_{i}"):
                to_delete = i

    if to_delete is not None:
        del fields[to_delete]
        st.rerun()

    if st.button(f"＋ Add {label.split()[0]} Field", key=f"{key_prefix}_add"):
        fields.append({"name": "", "type": "str", "description": "", "required": True})
        st.rerun()

    return fields


# ── Two-column layout ──────────────────────────────────────────────────────────
form_col, preview_col = st.columns([3, 2], gap="large")

with form_col:
    st.subheader("Agent Details")
    name        = st.text_input("Agent Name *", placeholder="e.g. Travel Info Collector",
                                key="ag_name")
    description = st.text_area("Description *",
                               placeholder="Describe what this agent does.", height=80,
                               key="ag_desc")

    col1, col2, col3 = st.columns(3)
    agent_type = col1.selectbox(
        "Agent Type *",
        ["reasoning", "hybrid", "deterministic"],
        help="Deterministic: single tool call, no LLM.  Reasoning/Hybrid: LLM decides.",
        key="ag_type",
    )
    behavior = col2.selectbox(
        "Behavior *",
        BEHAVIORS,
        help="\n\n".join(f"**{k}**: {v}" for k, v in BEHAVIOR_HELP.items()),
        key="ag_behavior",
    )
    llm_model = col3.selectbox("LLM Model", models, key="ag_model")

    # Show behavior description
    st.info(f"ℹ️ **{behavior}**: {BEHAVIOR_HELP[behavior]}")

    selected_tools = st.multiselect("Tools (agent can ONLY use these)", tool_names,
                                    key="ag_tools")
    if selected_tools:
        with st.expander("Tool descriptions"):
            for t in selected_tools:
                st.markdown(f"- **{t}**: {tool_descs.get(t)}")

    st.markdown("---")
    
    # ── Dynamic schema builders ───────────────────────────────────────────────
    inp_fields = _schema_builder("inp", "inp_fields", "📥 Input Fields", "#42A5F5")
    st.markdown("")
    out_fields = _schema_builder("out", "out_fields", "📤 Output Fields", "#66BB6A")
     
    st.markdown("")
    save_clicked = st.button("💾 Save Agent", type="primary", use_container_width=True)

# ── Live preview card ──────────────────────────────────────────────────────────
with preview_col:
    st.subheader("Live Preview")

    p_name   = name        or "Agent Name"
    p_desc   = description or "No description yet."
    p_type   = agent_type
    p_model  = llm_model if agent_type != "deterministic" else "—"
    p_tools  = selected_tools or []
    beh_color = {"task_executor": "#42A5F5", "data_collector": "#FFA726",
                 "aggregator": "#AB47BC"}.get(behavior, "#aaa")
    type_color = {"reasoning": "#42A5F5", "deterministic": "#66BB6A",
                  "hybrid": "#FFA726"}.get(p_type, "#aaa")

    def _field_badges(fields, bg, fg):
        parts = []
        for f in fields:
            if not f["name"].strip():
                continue
            req_span = (
                '<span style="color:#EF5350;margin-left:4px;font-size:10px">required</span>'
                if f["required"] else
                '<span style="color:#555;margin-left:4px;font-size:10px">optional</span>'
            )
            desc_div = (
                f'<div style="color:#666;font-size:11px;margin-top:2px">{f["description"]}</div>'
                if f["description"] else ""
            )
            parts.append(
                f'<div style="background:{bg};border-left:3px solid {fg};border-radius:4px;'
                f'padding:4px 10px;margin:3px 0;font-size:12px">'
                f'<span style="color:{fg};font-weight:600">{f["name"] or "?"}</span>'
                f'<span style="color:#888;margin-left:6px">{f["type"]}</span>'
                f'{req_span}{desc_div}'
                f'</div>'
            )
        return "".join(parts) or '<span style="color:#555;font-size:12px">—</span>'

    tools_html = "".join(
        f'<span style="background:#333;color:#ccc;border-radius:4px;padding:2px 7px;'
        f'font-size:11px;margin:2px">{t}</span>'
        for t in p_tools
    ) or '<span style="color:#555;font-size:12px">None</span>'

    inp_html = _field_badges(st.session_state.inp_fields, "#0d2a4a", "#42A5F5")
    out_html = _field_badges(st.session_state.out_fields, "#0d2e0d", "#66BB6A")

    st.markdown(f"""
<div style="background:#1e2a3a;border:1px solid #2a3a4a;border-radius:14px;padding:22px 20px">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
    <div style="font-size:2rem">🤖</div>
    <div>
      <div style="font-weight:700;color:#fff;font-size:1.1rem">{p_name}</div>
      <div style="display:flex;gap:6px;margin-top:4px">
        <span style="background:{type_color}22;color:{type_color};border-radius:4px;padding:2px 8px;font-size:11px;font-weight:600">{p_type.upper()}</span>
        <span style="background:{beh_color}22;color:{beh_color};border-radius:4px;padding:2px 8px;font-size:11px;font-weight:600">{behavior.upper().replace("_"," ")}</span>
      </div>
    </div>
  </div>
  <div style="color:#a0b4c8;font-size:13px;margin-bottom:14px;line-height:1.5">
    {p_desc[:200]}{"…" if len(p_desc) > 200 else ""}
  </div>
  <div style="border-top:1px solid #2a3a4a;padding-top:10px;margin-bottom:10px">
    <div style="color:#888;font-size:11px;font-weight:600;margin-bottom:4px">LLM MODEL</div>
    <div style="color:#fff;font-size:13px">{p_model}</div>
  </div>
  <div style="margin-bottom:10px">
    <div style="color:#888;font-size:11px;font-weight:600;margin-bottom:4px">TOOLS</div>
    <div style="display:flex;flex-wrap:wrap;gap:4px">{tools_html}</div>
  </div>
  <div style="margin-bottom:10px">
    <div style="color:#888;font-size:11px;font-weight:600;margin-bottom:6px">📥 INPUT SCHEMA</div>
    {inp_html}
  </div>
  <div>
    <div style="color:#888;font-size:11px;font-weight:600;margin-bottom:6px">📤 OUTPUT SCHEMA</div>
    {out_html}
  </div>
</div>
""", unsafe_allow_html=True)

# ── Save handler ───────────────────────────────────────────────────────────────
if save_clicked:
    valid_inp = [f for f in st.session_state.inp_fields if f["name"].strip()]
    valid_out = [f for f in st.session_state.out_fields if f["name"].strip()]

    if not name or not description:
        st.error("Agent name and description are required.")
    elif not valid_inp:
        st.error("At least one input field is required.")
    elif not valid_out:
        st.error("At least one output field is required.")
    else:
        agent = {
            "name":         name,
            "description":  description,
            "agent_type":   agent_type,
            "behavior":     behavior,
            "llm_model":    llm_model if agent_type != "deterministic" else None,
            "tools":        selected_tools,
            # Flat lists for backward compat
            "inputs":  [f["name"].strip() for f in valid_inp],
            "outputs": [f["name"].strip() for f in valid_out],
            # Rich schemas
            "input_schema":  [
                {"name": f["name"].strip(), "type": f["type"],
                 "description": f["description"], "required": f["required"], "default": None}
                for f in valid_inp
            ],
            "output_schema": [
                {"name": f["name"].strip(), "type": f["type"],
                 "description": f["description"], "required": f["required"], "default": None}
                for f in valid_out
            ],
        }
        saved = save_agent(agent)
        st.success(f"✅ Agent **{name}** saved!  ID: `{saved['id']}`")
        # Reset schema builders for next agent
        st.session_state.inp_fields = [{"name": "", "type": "str", "description": "", "required": True}]
        st.session_state.out_fields = [{"name": "", "type": "str", "description": "", "required": True}]
        st.rerun()

st.divider()

# ── Existing agents ────────────────────────────────────────────────────────────
st.subheader("📋 Existing Agents")
if st.button("🔄 Refresh"):
    st.rerun()

existing = list_agents()
if not existing:
    st.caption("No agents yet.")
else:
    for a in existing:
        behavior_a   = a.get("behavior", "task_executor")
        type_color   = {"reasoning": "#42A5F5", "deterministic": "#66BB6A",
                        "hybrid": "#FFA726"}.get(a.get("agent_type", ""), "#aaa")
        beh_color_a  = {"task_executor": "#42A5F5", "data_collector": "#FFA726",
                        "aggregator": "#AB47BC"}.get(behavior_a, "#aaa")
        with st.expander(f"🤖 {a['name']}"):
            left, right = st.columns([3, 1])
            with left:
                st.markdown(
                    f'<span style="background:{type_color}22;color:{type_color};border-radius:4px;'
                    f'padding:2px 8px;font-size:11px;font-weight:600">{a.get("agent_type","?").upper()}</span>'
                    f'&nbsp;<span style="background:{beh_color_a}22;color:{beh_color_a};border-radius:4px;'
                    f'padding:2px 8px;font-size:11px;font-weight:600">'
                    f'{behavior_a.upper().replace("_"," ")}</span>',
                    unsafe_allow_html=True,
                )
                st.markdown(f"**{a.get('description', '')}**")

                # Show rich schema if available, else fall back to flat lists
                if a.get("input_schema"):
                    inp_summary = " | ".join(
                        f"`{f['name']}` ({f['type']}{'*' if f['required'] else '?'})"
                        for f in a["input_schema"]
                    )
                    out_summary = " | ".join(
                        f"`{f['name']}` ({f['type']}{'*' if f['required'] else '?'})"
                        for f in a.get("output_schema", [])
                    )
                else:
                    inp_summary = ", ".join(f"`{n}`" for n in a.get("inputs", []))
                    out_summary = ", ".join(f"`{n}`" for n in a.get("outputs", []))

                st.caption(
                    f"LLM: `{a.get('llm_model') or '—'}`  |  "
                    f"Tools: `{', '.join(a.get('tools', [])) or 'none'}`\n\n"
                    f"📥 {inp_summary}  →  📤 {out_summary}"
                )
            with right:
                if st.button("🗑️ Delete", key=f"del_{a['id']}", use_container_width=True):
                    delete_agent(a["id"])
                    st.rerun()

