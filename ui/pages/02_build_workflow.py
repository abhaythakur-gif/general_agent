import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
from app.core.storage import list_agents, save_workflow, update_workflow, list_workflows, delete_workflow
from app.engine.workflow.validator import validate_workflow
from app.schemas.agent import AgentDefinition

st.set_page_config(page_title="Build Workflow", page_icon="🔗", layout="wide")

# ── Auth guard ────────────────────────────────────────────────────────────────
if "user_id" not in st.session_state or not st.session_state["user_id"]:
    st.warning("⚠️ Please go to the Home page and enter your User ID first.")
    st.stop()
user_id = st.session_state["user_id"]

# ── Edit mode session state ───────────────────────────────────────────────────
if "wf_editing" not in st.session_state:
    st.session_state["wf_editing"] = None   # None = create mode; dict = edit mode

editing_wf = st.session_state["wf_editing"]
is_edit_mode = editing_wf is not None

# ── Page header ───────────────────────────────────────────────────────────────
if is_edit_mode:
    st.title("✏️ Edit Workflow")
    st.markdown(
        f"Updating **{editing_wf['name']}** &nbsp; `👤 {user_id}`"
    )
    if st.button("✕ Cancel Edit", type="secondary"):
        st.session_state["wf_editing"] = None
        st.rerun()
else:
    st.title("🔗 Build Workflow")
    st.markdown(f"Chain agents into a sequential, conditional, or parallel pipeline. &nbsp; `👤 {user_id}`")

agents = list_agents(user_id)
if not agents:
    st.warning("No agents found. Create agents first.")
    st.stop()

agent_map     = {a["id"]: a for a in agents}
agent_options = {a["name"]: a["id"] for a in agents}
id_to_name    = {v: k for k, v in agent_options.items()}

BEHAVIOR_COLOR = {
    "task_executor":  "#42A5F5",
    "data_collector": "#FFA726",
    "aggregator":     "#AB47BC",
}

# ── Derive defaults from the workflow being edited (or blank for create) ──────
default_name       = editing_wf.get("name", "")          if is_edit_mode else ""
default_desc       = editing_wf.get("description", "")   if is_edit_mode else ""
default_wf_type    = editing_wf.get("workflow_type", "sequential") if is_edit_mode else "sequential"
default_agent_ids  = editing_wf.get("agent_ids", [])     if is_edit_mode else []
default_conditions = editing_wf.get("conditions", {})    if is_edit_mode else {}
default_par_groups = editing_wf.get("parallel_groups", []) if is_edit_mode else []

# Pre-selected agent names in correct order (filter out deleted agents)
default_selected_names = [
    id_to_name[aid] for aid in default_agent_ids if aid in id_to_name
]

# ── Workflow type ─────────────────────────────────────────────────────────────
wf_type_options = ["Sequential", "Conditional"]
wf_type_index   = 1 if default_wf_type == "conditional" else 0

workflow_type = st.radio(
    "Workflow type",
    wf_type_options,
    index=wf_type_index,
    horizontal=True,
    key="wf_type_radio",
    help=(
        "**Sequential** — all agents always run in order.\n\n"
        "**Conditional** — each agent (except the first) can have a `run_if` expression."
    ),
)
is_conditional = workflow_type == "Conditional"

# ── Build / Edit form ─────────────────────────────────────────────────────────
form_key = "wf_edit_form" if is_edit_mode else "wf_form"
with st.form(form_key):
    wf_name = st.text_input(
        "Workflow Name *",
        value=default_name,
        placeholder="e.g. Travel Planning Pipeline",
    )
    wf_desc = st.text_area(
        "Description *",
        value=default_desc,
        height=60,
    )
    selected_names = st.multiselect(
        "Select agents in execution order *",
        list(agent_options.keys()),
        default=default_selected_names,
    )
    btn_label = "💾 Update Workflow" if is_edit_mode else "💾 Save Workflow"
    submitted = st.form_submit_button(btn_label, use_container_width=True)

# ── Pipeline preview, conditions, parallel groups ─────────────────────────────
conditions:      dict       = {}
parallel_groups: list[list] = []

if selected_names:
    ordered = [agent_map[agent_options[n]] for n in selected_names]

    st.subheader("Pipeline Configuration")
    available_vars: dict = {}

    for i, a in enumerate(ordered):
        behavior   = a.get("behavior", "task_executor")
        beh_color  = BEHAVIOR_COLOR.get(behavior, "#888")
        type_badge = f'`{a["agent_type"]}`'

        if a.get("output_schema"):
            out_vars  = [f["name"] for f in a["output_schema"]]
            out_types = {f["name"]: f["type"] for f in a["output_schema"]}
        else:
            out_vars  = a.get("outputs", [])
            out_types = {n: "str" for n in out_vars}

        if a.get("input_schema"):
            in_vars = [f["name"] for f in a["input_schema"]]
        else:
            in_vars = a.get("inputs", [])

        prefix = "▶" if i == 0 else "⬇️"
        st.markdown(
            f"{prefix} **Step {i+1}: {a['name']}** {type_badge} "
            f'<span style="background:{beh_color}22;color:{beh_color};border-radius:4px;'
            f'padding:1px 7px;font-size:11px;font-weight:600">{behavior.upper().replace("_"," ")}</span>'
            f"  \n&nbsp;&nbsp;&nbsp;&nbsp;📥 `{'`, `'.join(in_vars) or '—'}`"
            f"  →  📤 `{'`, `'.join(out_vars) or '—'}`",
            unsafe_allow_html=True,
        )

        if is_conditional and i > 0:
            hint = (
                f"Variables available: `{', '.join(sorted(available_vars.keys()))}`"
                if available_vars else "No variables available yet."
            )
            # Pre-fill condition from existing workflow when editing
            existing_cond = default_conditions.get(a["id"], "")
            expr = st.text_input(
                f"Condition for step {i+1} ({a['name']})",
                value=existing_cond,
                key=f"cond_{a['id']}",
                placeholder="e.g. sentiment == 'negative'",
                help=hint,
            )
            st.caption(f"💡 {hint}")
            if expr.strip():
                conditions[a["id"]] = expr.strip()
        elif i == 0 and is_conditional:
            st.caption("⚡ Always runs — first agent")

        if behavior == "data_collector":
            available_vars["collection_status"]  = "str"
            available_vars["follow_up_question"] = "str"
            available_vars["missing_fields"]     = "list"

        for var_name, var_type in out_types.items():
            available_vars[var_name] = var_type

    # ── Parallel groups selector ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### ⚡ Parallel Groups *(optional)*")
    st.caption(
        "Select agents that should run **at the same time** (must not depend on each other). "
        "Only add a group if 2+ agents can run concurrently."
    )

    # Pre-fill number of parallel groups when editing
    default_n_groups = len(default_par_groups) if is_edit_mode else 0
    n_groups = st.number_input(
        "Number of parallel groups",
        min_value=0, max_value=5,
        value=default_n_groups,
        step=1,
        key="n_par_groups",
    )
    for g in range(int(n_groups)):
        # Pre-fill which agents were in each group when editing
        default_group_names = []
        if is_edit_mode and g < len(default_par_groups):
            default_group_names = [
                id_to_name[aid] for aid in default_par_groups[g]
                if aid in id_to_name and id_to_name[aid] in selected_names
            ]
        chosen = st.multiselect(
            f"Parallel group {g+1} — select agents to run simultaneously",
            selected_names,
            default=default_group_names,
            key=f"par_group_{g}",
        )
        if len(chosen) >= 2:
            parallel_groups.append([agent_options[n] for n in chosen])
        elif len(chosen) == 1:
            st.warning(f"Group {g+1}: select at least 2 agents to form a parallel group.")

    # ── Visual pipeline diagram ────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Pipeline Diagram")

    par_agent_ids: dict = {}
    for grp in parallel_groups:
        fs = frozenset(grp)
        for aid in grp:
            par_agent_ids[aid] = fs

    seen_groups: set  = set()
    diagram_rows: list = []

    for i, a in enumerate(ordered):
        group_key = par_agent_ids.get(a["id"])
        if group_key and group_key in seen_groups:
            continue
        if group_key:
            seen_groups.add(group_key)
            group_agents = [ag for ag in ordered if ag["id"] in group_key]
            diagram_rows.append(("parallel", group_agents, i + 1))
        else:
            diagram_rows.append(("sequential", a, i + 1))

    def _node_html(a, step_n, show_cond=True):
        beh = a.get("behavior", "task_executor")
        bc  = BEHAVIOR_COLOR.get(beh, "#888")
        tc  = {"reasoning": "#42A5F5", "deterministic": "#66BB6A",
               "hybrid": "#FFA726"}.get(a.get("agent_type", ""), "#888")
        cond = conditions.get(a["id"], "")
        cond_html = (
            f'<div style="font-size:10px;color:#FFA726;margin-top:4px;word-break:break-all">'
            f'if {cond}</div>'
        ) if (cond and show_cond) else (
            f'<div style="font-size:10px;color:#555;margin-top:4px">always runs</div>'
            if show_cond else ""
        )
        return (
            f'<div style="background:#1a2535;border:2px solid {bc};border-radius:10px;'
            f'padding:10px 14px;min-width:130px;max-width:160px;text-align:center">'
            f'<div style="font-size:10px;color:#555;margin-bottom:2px">Step {step_n}</div>'
            f'<div style="font-weight:700;color:#fff;font-size:13px">{a["name"]}</div>'
            f'<div style="margin-top:3px">'
            f'<span style="background:{tc}22;color:{tc};border-radius:3px;padding:1px 6px;font-size:10px">'
            f'{a["agent_type"].upper()}</span>&nbsp;'
            f'<span style="background:{bc}22;color:{bc};border-radius:3px;padding:1px 6px;font-size:10px">'
            f'{beh.upper().replace("_"," ")}</span></div>'
            f'{cond_html}'
            f'</div>'
        )

    arrow = '<span style="color:#444;font-size:22px;align-self:center;padding:0 4px">→</span>'
    parallel_badge = '<span style="color:#FFA726;font-size:10px;font-weight:600">⚡ PARALLEL</span>'

    rows_html = []
    for row in diagram_rows:
        kind = row[0]
        if kind == "sequential":
            rows_html.append(_node_html(row[1], row[2]))
        else:
            group_nodes = "".join(
                f'<div style="display:flex;flex-direction:column;align-items:center;gap:6px">'
                f'{parallel_badge}'
                f'{_node_html(ag, row[2], show_cond=False)}'
                f'</div>'
                for ag in row[1]
            )
            rows_html.append(
                f'<div style="background:#1a1d25;border:1px dashed #FFA726;border-radius:10px;'
                f'padding:10px;display:flex;gap:10px;align-items:flex-start">'
                f'{group_nodes}</div>'
            )
        rows_html.append(arrow)

    if rows_html and rows_html[-1] == arrow:
        rows_html.pop()

    st.markdown(
        '<style>@keyframes pulse{0%{opacity:1}50%{opacity:.4}100%{opacity:1}}</style>'
        f'<div style="display:flex;flex-wrap:wrap;align-items:center;gap:6px;'
        f'padding:16px;background:#0a0f1a;border-radius:12px">'
        + "".join(rows_html) + "</div>",
        unsafe_allow_html=True,
    )

    # ── Live validation ────────────────────────────────────────────────────────
    defs = []
    for a in ordered:
        d = dict(a)
        d["run_if"] = conditions.get(a["id"])
        defs.append(AgentDefinition(**d))

    messages    = validate_workflow(defs)
    hard_errors = [m for m in messages if not m.startswith("[WARNING]")]
    warnings    = [m[len("[WARNING] "):] for m in messages if m.startswith("[WARNING]")]

    if hard_errors:
        st.error("⚠️ Validation errors:\n" + "\n".join(f"- {e}" for e in hard_errors))
    else:
        st.success("✅ Input/output alignment valid.")
    for w in warnings:
        st.warning(f"⚠️ {w}")

# ── Handle save / update ──────────────────────────────────────────────────────
if submitted:
    if not wf_name or not selected_names:
        st.error("Name and at least one agent required.")
    else:
        wf_payload = {
            "name":            wf_name,
            "description":     wf_desc,
            "agent_ids":       [agent_options[n] for n in selected_names],
            "workflow_type":   workflow_type.lower(),
            "conditions":      conditions,
            "parallel_groups": parallel_groups,
        }

        if is_edit_mode:
            updated = update_workflow(editing_wf["id"], wf_payload, user_id)
            if updated:
                st.success(f"✅ Workflow **{wf_name}** updated successfully!")
                st.session_state["wf_editing"] = None   # exit edit mode
                st.rerun()
            else:
                st.error("❌ Update failed — workflow not found.")
        else:
            wf = save_workflow(wf_payload, user_id)
            st.success(f"✅ Workflow saved!  ID: `{wf['id']}`")

# ── Existing workflows list ────────────────────────────────────────────────────
st.divider()
st.subheader("📋 Existing Workflows")
if st.button("🔄 Refresh"):
    st.rerun()

for wf in list_workflows(user_id):
    wf_type_badge = wf.get("workflow_type", "sequential").upper()
    badge_icon    = "🔀" if wf_type_badge == "CONDITIONAL" else "➡️"
    par_groups    = wf.get("parallel_groups", [])
    par_badge     = f" ⚡ {len(par_groups)} parallel group(s)" if par_groups else ""
    is_being_edited = is_edit_mode and editing_wf.get("id") == wf.get("id")

    with st.expander(
        f"{badge_icon} {wf['name']}  [{wf_type_badge}]{par_badge}"
        + (" ✏️ *editing*" if is_being_edited else "")
    ):
        wf_conditions = wf.get("conditions", {})
        for i, aid in enumerate(wf.get("agent_ids", [])):
            a          = agent_map.get(aid, {})
            aname      = a.get("name", aid)
            behavior   = a.get("behavior", "task_executor")
            bc         = BEHAVIOR_COLOR.get(behavior, "#888")
            cond_str   = wf_conditions.get(aid, "")
            cond_label = f"  *(if `{cond_str}`)*" if cond_str else "  *(always runs)*"
            st.markdown(
                f"  Step {i+1}: **{aname}**"
                f' <span style="background:{bc}22;color:{bc};border-radius:3px;'
                f'padding:1px 6px;font-size:10px">{behavior.upper().replace("_"," ")}</span>'
                f"{cond_label}",
                unsafe_allow_html=True,
            )
        if par_groups:
            for gi, grp in enumerate(par_groups):
                names = [agent_map.get(aid, {}).get("name", aid) for aid in grp]
                st.caption(f"⚡ Parallel group {gi+1}: {' & '.join(names)}")

        col_edit, col_del = st.columns(2)
        with col_edit:
            if st.button("✏️ Edit", key=f"editwf_{wf['id']}", use_container_width=True):
                st.session_state["wf_editing"] = wf
                st.rerun()
        with col_del:
            if st.button("🗑️ Delete", key=f"delwf_{wf['id']}", use_container_width=True):
                # If we're editing this workflow, cancel edit mode first
                if is_edit_mode and editing_wf.get("id") == wf.get("id"):
                    st.session_state["wf_editing"] = None
                delete_workflow(wf["id"], user_id)
                st.rerun()


