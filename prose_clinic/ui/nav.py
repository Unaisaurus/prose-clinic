"""Page registry so pages can link to each other (filled in by app.py)."""

from __future__ import annotations

import streamlit as st

PAGES: dict = {}


def link(name: str, label: str, icon: str | None = None) -> None:
    page = PAGES.get(name)
    if page is not None:
        st.page_link(page, label=label, icon=icon)
