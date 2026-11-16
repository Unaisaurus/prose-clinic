"""Session state shared by every page, plus small helpers."""

from __future__ import annotations

import json

import streamlit as st

from .. import storage
from ..analyzer import Analysis, apply_feedback, run_rules
from ..llm import LLMConfig, build_config


def init() -> None:
    ss = st.session_state
    if "settings" not in ss:
        ss.settings = storage.load_settings()
        ss.library = storage.load_library()
        ss.feedback = storage.load_feedback()
    ss.setdefault("input_text", "")
    ss.setdefault("analyzed_text", "")
    ss.setdefault("draft_text", "")
    ss.setdefault("selected", {})  # finding uid -> finding dict, for the revision list
    ss.setdefault("critique", None)  # AI critique of analyzed_text
    ss.setdefault("rewrites", {})  # finding uid -> RewriteResult
    ss.setdefault("revision", None)  # full-passage revision
    ss.setdefault("session_keys", {})  # provider -> API key pasted this session (memory only)
    ss.setdefault("flash", [])  # messages to show after a callback


def flash(kind: str, message: str) -> None:
    st.session_state.flash.append((kind, message))


def show_flash() -> None:
    for kind, message in st.session_state.flash:
        getattr(st, kind, st.info)(message)
    st.session_state.flash = []


def save_settings() -> None:
    storage.save_settings(st.session_state.settings)


def save_library() -> None:
    storage.save_library(st.session_state.library)


def save_feedback() -> None:
    storage.save_feedback(st.session_state.feedback)


def rules_config(settings: dict) -> str:
    return json.dumps(
        {"rules": settings.get("rules", {}), "custom_phrases": settings.get("custom_phrases", [])}, sort_keys=True
    )


@st.cache_data(max_entries=32, show_spinner=False)
def _cached_rules(text: str, config_json: str):
    return run_rules(text, json.loads(config_json))


def analysis_for(text: str) -> Analysis | None:
    if not text.strip():
        return None
    ss = st.session_state
    doc, findings, errors = _cached_rules(text, rules_config(ss.settings))
    return apply_feedback(doc, findings, errors, storage.false_positive_signatures(ss.feedback))


def current_analysis() -> Analysis | None:
    return analysis_for(st.session_state.get("analyzed_text", ""))


def secrets() -> dict:
    """Keys from .streamlit/secrets.toml, or {} if there is no secrets file."""
    try:
        return {key: st.secrets[key] for key in st.secrets.keys()}
    except Exception:
        return {}


def llm_config() -> LLMConfig | None:
    ss = st.session_state
    return build_config(ss.settings["ai"], ss.session_keys, secrets())


def escape_md(text: str) -> str:
    """Show text literally inside st.markdown (no accidental bold, links, maths or HTML)."""
    for ch in "\\`*_[]<>#$~|":
        text = text.replace(ch, "\\" + ch)
    return text
