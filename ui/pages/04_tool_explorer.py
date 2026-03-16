import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
from app.tools.registry import list_tools

st.set_page_config(page_title="Tool Explorer", page_icon="🧰", layout="wide")
st.title("🧰 Tool Explorer")
st.markdown("Browse all available tools. Assign these tools to agents when creating them.")

all_tools = list_tools()

# ── Stats row ─────────────────────────────────────────────────────────────────
grouped = {}
for t in all_tools:
    grouped.setdefault(t["category"], []).append(t)

st.markdown("")
cols = st.columns(len(grouped) + 1)
cols[0].metric("🔧 Total Tools", len(all_tools))
for i, (cat, tools) in enumerate(grouped.items()):
    cols[i + 1].metric(f"📂 {cat}", len(tools))

st.divider()

# ── Search bar ────────────────────────────────────────────────────────────────
search = st.text_input("🔍 Search tools", placeholder="e.g. weather, search, summarize…")

# ── Category colors ───────────────────────────────────────────────────────────
CAT_COLORS = {
    "Weather": ("#0d2e3a", "#42A5F5"),
    "Search":  ("#1a2e0d", "#66BB6A"),
}
DEFAULT_COLOR = ("#2a1a2e", "#AB47BC")

for cat, tools in grouped.items():
    filtered = [
        t for t in tools
        if not search or search.lower() in t["name"].lower() or search.lower() in t["description"].lower()
    ]
    if not filtered:
        continue

    bg, accent = CAT_COLORS.get(cat, DEFAULT_COLOR)
    cat_icons = {"Weather": "🌤️", "Search": "🔍"}
    cat_icon  = cat_icons.get(cat, "🔧")

    st.markdown(
        f'<div style="background:{bg};border-left:4px solid {accent};border-radius:8px;'
        f'padding:10px 16px;margin:16px 0 10px">'
        f'<span style="color:{accent};font-size:1.1rem;font-weight:700">'
        f'{cat_icon} {cat} Tools</span>'
        f'<span style="color:#888;font-size:13px;margin-left:10px">({len(filtered)} tools)</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    cols_per_row = 2
    rows = [filtered[i:i + cols_per_row] for i in range(0, len(filtered), cols_per_row)]
    for row in rows:
        card_cols = st.columns(cols_per_row)
        for col, t in zip(card_cols, row):
            with col:
                inp_tags = "".join(
                    f'<span style="background:#333;color:#ccc;border-radius:4px;'
                    f'padding:2px 7px;font-size:11px;margin:2px 2px">{inp}</span>'
                    for inp in t.get("inputs", [])
                )
                no_inputs = '<span style="color:#555;font-size:11px">none</span>'
                inputs_html = inp_tags if inp_tags else no_inputs
                st.markdown(
                    f'<div style="background:#161b22;border:1px solid #2a3a4a;'
                    f'border-top:3px solid {accent};border-radius:10px;padding:16px 18px;'
                    f'margin-bottom:8px;height:100%">'
                    f'<div style="font-weight:700;color:#fff;font-size:14px;margin-bottom:6px">'
                    f'<code style="background:{accent}22;color:{accent};padding:2px 8px;'
                    f'border-radius:4px;font-size:13px">{t["name"]}</code></div>'
                    f'<div style="color:#a0b4c8;font-size:13px;margin-bottom:10px;line-height:1.5">'
                    f'{t["description"]}</div>'
                    f'<div style="margin-bottom:6px">'
                    f'<span style="color:#666;font-size:11px;font-weight:600">INPUTS &nbsp;</span>'
                    f'{inputs_html}'
                    f'</div>'
                    f'<div style="color:#555;font-size:11px">API: {t.get("api_source","—")}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    st.markdown("")

