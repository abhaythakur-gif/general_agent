import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
from tools.tool_registry import list_tools

st.set_page_config(page_title="Tool Explorer", page_icon="🧰", layout="wide")
st.title("🧰 Tool Explorer")
st.markdown("Browse all available tools. Assign these tools to agents when creating them.")

all_tools = list_tools()
grouped   = {}
for t in all_tools:
    grouped.setdefault(t["category"], []).append(t)

icons = {"Weather": "🌤️", "Search": "🔍"}
for cat, tools in grouped.items():
    st.subheader(f"{icons.get(cat, '🔧')} {cat} Tools  ({len(tools)})")
    c1, c2 = st.columns(2)
    for i, t in enumerate(tools):
        with (c1 if i % 2 == 0 else c2):
            with st.container(border=True):
                st.markdown(f"#### `{t['name']}`")
                st.markdown(t["description"])
                st.caption(f"Inputs: `{', '.join(t['inputs'])}` · API: {t['api_source']}")
    st.divider()
