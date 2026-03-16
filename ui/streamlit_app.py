import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import streamlit as st
from utils.storage import list_agents, list_workflows
from tools.tool_registry import list_tools

st.set_page_config(page_title="Universal Agent Builder", page_icon="🤖", layout="wide")

# ── Hero banner ───────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 60%,#0f3460 100%);
            border-radius:16px;padding:36px 40px;margin-bottom:24px;">
  <h1 style="color:#fff;margin:0;font-size:2.2rem">🤖 Universal Agent Builder</h1>
  <p style="color:#a0b4c8;margin:8px 0 0;font-size:1.05rem">
    Build, chain, and run AI agents — no code required.
  </p>
</div>
""", unsafe_allow_html=True)

# ── Live stats ────────────────────────────────────────────────────────────────
agents    = list_agents()
workflows = list_workflows()
tools     = list_tools()

num_agents    = len(agents)
num_workflows = len(workflows)
num_tools     = len(tools)
agent_types   = list({a.get("agent_type","?").title() for a in agents}) or ["—"]

col1, col2, col3, col4 = st.columns(4)
col1.metric("🤖 Agents",    num_agents,    help="Total agents created")
col2.metric("🔗 Workflows", num_workflows, help="Total workflows built")
col3.metric("🔧 Tools",     num_tools,     help="Tools available to agents")
col4.metric("⚡ LLMs",      "GPT-4 / GPT-4-Turbo / GPT-3.5")

st.divider()

# ── Quick-start cards ─────────────────────────────────────────────────────────
st.subheader("Quick Start")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown("""
<div style="background:#1e2a3a;border-left:4px solid #42A5F5;border-radius:8px;padding:18px 16px">
  <div style="font-size:1.4rem">🔧</div>
  <div style="font-weight:700;color:#fff;margin:6px 0 4px">Create Agent</div>
  <div style="color:#8899aa;font-size:13px">Define what an agent does — its tools, LLM, inputs and outputs.</div>
</div>""", unsafe_allow_html=True)

with c2:
    st.markdown("""
<div style="background:#1e2a3a;border-left:4px solid #66BB6A;border-radius:8px;padding:18px 16px">
  <div style="font-size:1.4rem">🔗</div>
  <div style="font-weight:700;color:#fff;margin:6px 0 4px">Build Workflow</div>
  <div style="color:#8899aa;font-size:13px">Chain agents into a sequential or conditional pipeline.</div>
</div>""", unsafe_allow_html=True)

with c3:
    st.markdown("""
<div style="background:#1e2a3a;border-left:4px solid #FFA726;border-radius:8px;padding:18px 16px">
  <div style="font-size:1.4rem">▶️</div>
  <div style="font-weight:700;color:#fff;margin:6px 0 4px">Execute Workflow</div>
  <div style="color:#8899aa;font-size:13px">Run pipelines and watch live per-step logs with condition tracking.</div>
</div>""", unsafe_allow_html=True)

with c4:
    st.markdown("""
<div style="background:#1e2a3a;border-left:4px solid #AB47BC;border-radius:8px;padding:18px 16px">
  <div style="font-size:1.4rem">🧰</div>
  <div style="font-weight:700;color:#fff;margin:6px 0 4px">Tool Explorer</div>
  <div style="color:#8899aa;font-size:13px">Browse all available tools — weather, search, and more.</div>
</div>""", unsafe_allow_html=True)

st.divider()

# ── Recent agents & workflows ─────────────────────────────────────────────────
left, right = st.columns(2)

with left:
    st.subheader("🤖 Recent Agents")
    if not agents:
        st.caption("No agents yet — go to Create Agent to get started.")
    else:
        for a in agents[-5:][::-1]:
            type_color = {"reasoning": "#42A5F5", "deterministic": "#66BB6A", "hybrid": "#FFA726"}.get(
                a.get("agent_type", ""), "#aaa")
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid #222">'
                f'<span style="background:{type_color}22;color:{type_color};border-radius:4px;'
                f'padding:2px 8px;font-size:11px;font-weight:600">{a.get("agent_type","?").upper()}</span>'
                f'<span style="color:#fff;font-weight:500">{a["name"]}</span>'
                f'<span style="color:#888;font-size:12px;margin-left:auto">in: {", ".join(a.get("inputs",[]))}'
                f' → out: {", ".join(a.get("outputs",[]))}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

with right:
    st.subheader("🔗 Recent Workflows")
    if not workflows:
        st.caption("No workflows yet — go to Build Workflow to get started.")
    else:
        for wf in workflows[-5:][::-1]:
            wf_type = wf.get("workflow_type", "sequential")
            wf_color = "#FFA726" if wf_type == "conditional" else "#42A5F5"
            wf_icon  = "🔀" if wf_type == "conditional" else "➡️"
            n_agents = len(wf.get("agent_ids", []))
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid #222">'
                f'<span style="background:{wf_color}22;color:{wf_color};border-radius:4px;'
                f'padding:2px 8px;font-size:11px;font-weight:600">{wf_icon} {wf_type.upper()}</span>'
                f'<span style="color:#fff;font-weight:500">{wf["name"]}</span>'
                f'<span style="color:#888;font-size:12px;margin-left:auto">{n_agents} agent(s)</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

st.divider()
st.caption("👈 Use the sidebar to navigate between pages.")

