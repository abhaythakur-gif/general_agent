import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import streamlit as st

st.set_page_config(page_title="Universal Agent Builder", page_icon="🤖", layout="wide")
st.title("🤖 Universal Agent Builder Platform")
st.markdown("""
| Page | Purpose |
|------|---------|
| 🔧 **Create Agent** | Define agents with tools, LLM, inputs and outputs |
| 🔗 **Build Workflow** | Chain agents into sequential pipelines |
| ▶️ **Execute Workflow** | Run workflows and watch live execution logs |
| 🧰 **Tool Explorer** | Browse all available tools |
""")
st.info("👈 Use the sidebar to navigate.")
c1, c2, c3 = st.columns(3)
c1.metric("Tools", "16")
c2.metric("LLMs", "GPT-4 / GPT-4-Turbo / GPT-3.5")
c3.metric("Agent Types", "Deterministic · Reasoning · Hybrid")
