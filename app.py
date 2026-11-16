"""Prose Clinic: spot and fix formulaic, AI-style habits in fiction.

Start it with:  streamlit run app.py
"""

import streamlit as st

from prose_clinic.llm import PROVIDER_LABELS
from prose_clinic.ui import analyze_page, help_page, library_page, nav, revise_page, settings_page, state

st.set_page_config(page_title="Prose Clinic", page_icon="🩺", layout="wide")
state.init()

nav.PAGES.update(
    analyze=st.Page(analyze_page.render, title="Analyze", icon="🔍", url_path="analyze", default=True),
    revise=st.Page(revise_page.render, title="Revise", icon="✏️", url_path="revise"),
    library=st.Page(library_page.render, title="Style library", icon="📚", url_path="library"),
    settings=st.Page(settings_page.render, title="Settings", icon="⚙️", url_path="settings"),
    help=st.Page(help_page.render, title="Help", icon="❓", url_path="help"),
)
page = st.navigation(list(nav.PAGES.values()))

with st.sidebar:
    st.markdown("### 🩺 Prose Clinic")
    st.caption("An editorial assistant for spotting formulaic, AI-style habits in fiction.")
    selected = len(st.session_state.selected)
    if selected:
        st.caption(f"✏️ {selected} finding{'s' if selected != 1 else ''} on your revision list")
    provider = st.session_state.settings["ai"].get("provider", "none")
    st.caption("🔒 Rule-based checks run offline." + ("" if provider == "none" else f"  \n🤖 AI: {PROVIDER_LABELS[provider]}"))

page.run()
