import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
from utils.storage import list_agents, save_workflow, list_workflows, delete_workflow
from workflow.workflow_validator import validate_workflow
from backend.schemas.agent_schema import AgentDefinition

st.set_page_config(page_title="Build Workflow", page_icon="🔗", layout="wide")
st.title("🔗 Build Workflow")
st.markdown("Chain agents into a sequential, conditional, or parallel pipeline.")

agents = list_agents()
if not agents:
    st.warning("No agents found. Create agents first.")
    st.stop()

agent_map     = {a["id"]: a for a in agents}
agent_options = {a["name"]: a["id"] for a in agents}

BEHAVIOR_COLOR = {
    "task_executor":  "#42A5F5",
    "data_collector": "#FFA726",
    "aggregator":     "#AB47BC",
}

# ── Workflow type ──────────────────────────────────────────────────────────────
workflow_type = st.radio(
    "Workflow type",
    ["Sequential", "Conditional"],
    horizontal=True,
    help=(
        "**Sequential** — all agents always run in order.\n\n"
        "**Conditional** — each agent (except the first) can have a `run_if` expression."
    ),
)
is_conditional = workflow_type == "Conditional"

# ── Build form ─────────────────────────────────────────────────────────────────
with st.form("wf_form"):
    wf_name = st.text_input("Workflow Name *", placeholder="e.g. Travel Planning Pipeline")
    wf_desc = st.text_area("Description *", height=60)
    selected_names = st.multiselect(
        "Select agents in execution order *",
        list(agent_options.keys()),
    )
    submitted = st.form_submit_button("💾 Save Workflow", use_container_width=True)

# ── Pipeline preview, conditions, parallel groups ──────────────────────────────
conditions:      dict       = {}   # {agent_id: expression_string}
parallel_groups: list[list] = []   # [[agent_id, agent_id], ...]

if selected_names:
    ordered = [agent_map[agent_options[n]] for n in selected_names]

    st.subheader("Pipeline Configuration")

    # Accumulate available variables across the pipeline
    available_vars: dict = {}   # {var_name: type_str}

    for i, a in enumerate(ordered):
        behavior   = a.get("behavior", "task_executor")
        beh_color  = BEHAVIOR_COLOR.get(behavior, "#888")
        type_badge = f'`{a["agent_type"]}`'

        # Effective output vars from rich schema if available
        if a.get("output_schema"):
            out_vars = [f["name"] for f in a["output_schema"]]
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

        # Condition input (conditional workflows, not first agent)
        if is_conditional and i > 0:
            hint = (
                f"Variables available: `{', '.join(sorted(available_vars.keys()))}`"
                if available_vars else "No variables available yet."
            )
            expr = st.text_input(
                f"Condition for step {i+1} ({a['name']})",
                key=f"cond_{a['id']}",
                placeholder="e.g. collection_status == 'complete'",
                help=hint,
            )
            st.caption(f"💡 {hint}")
            if expr.strip():
                conditions[a["id"]] = expr.strip()
        elif i == 0 and is_conditional:
            st.caption("⚡ Always runs — first agent")

        # Add DC implicit outputs so downstream conditions can use them
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
        "Select agents that should run **at the same time** (they must not depend on each other's outputs). "
        "Only add a group if 2+ agents can run concurrently."
    )

    n_groups = st.number_input("Number of parallel groups", min_value=0, max_value=5,
                               value=0, step=1, key="n_par_groups")
    for g in range(int(n_groups)):
        chosen = st.multiselect(
            f"Parallel group {g+1} — select agents to run simultaneously",
            selected_names,
            key=f"par_group_{g}",
        )
        if len(chosen) >= 2:
            parallel_groups.append([agent_options[n] for n in chosen])
        elif len(chosen) == 1:
            st.warning(f"Group {g+1}: select at least 2 agents to form a parallel group.")

    # ── Visual pipeline diagram ────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Pipeline Diagram")

    # Build a flat -> group membership map
    par_agent_ids: dict = {}
    for grp in parallel_groups:
        fs = frozenset(grp)
        for aid in grp:
            par_agent_ids[aid] = fs

    seen_groups: set = set()
    diagram_rows: list = []

    for i, a in enumerate(ordered):
        group_key = par_agent_ids.get(a["id"])
        if group_key and group_key in seen_groups:
            continue   # already rendered this group
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
        else:  # parallel
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

    # Remove trailing arrow
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

    messages   = validate_workflow(defs)
    hard_errors = [m for m in messages if not m.startswith("[WARNING]")]
    warnings    = [m[len("[WARNING] "):] for m in messages if m.startswith("[WARNING]")]

    if hard_errors:
        st.error("⚠️ Validation errors:\n" + "\n".join(f"- {e}" for e in hard_errors))
    else:
        st.success("✅ Input/output alignment valid.")
    for w in warnings:
        st.warning(f"⚠️ {w}")

# ── Handle save ────────────────────────────────────────────────────────────────
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
        wf = save_workflow(wf_payload)
        st.success(f"✅ Workflow saved!  ID: `{wf['id']}`")

# ── Existing workflows list ────────────────────────────────────────────────────
st.divider()
st.subheader("📋 Existing Workflows")
if st.button("🔄 Refresh"):
    st.rerun()

for wf in list_workflows():
    wf_type_badge  = wf.get("workflow_type", "sequential").upper()
    badge_icon     = "🔀" if wf_type_badge == "CONDITIONAL" else "➡️"
    par_groups     = wf.get("parallel_groups", [])
    par_badge      = f" ⚡ {len(par_groups)} parallel group(s)" if par_groups else ""
    with st.expander(f"{badge_icon} {wf['name']}  [{wf_type_badge}]{par_badge}"):
        wf_conditions = wf.get("conditions", {})
        for i, aid in enumerate(wf.get("agent_ids", [])):
            a         = agent_map.get(aid, {})
            aname     = a.get("name", aid)
            behavior  = a.get("behavior", "task_executor")
            bc        = BEHAVIOR_COLOR.get(behavior, "#888")
            cond_str  = wf_conditions.get(aid, "")
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
        if st.button("🗑️ Delete Workflow", key=f"delwf_{wf['id']}"):
            delete_workflow(wf["id"])
            st.rerun()

