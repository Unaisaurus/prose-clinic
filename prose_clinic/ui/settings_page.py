"""Settings: rules, sensitivity, custom phrases, feedback, AI connection and backups."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import storage
from ..analyzer import CATEGORY_ORDER
from ..findings import category_label
from ..highlight import render_highlighted
from ..llm import PROVIDER_LABELS, LLMError, find_api_key, test_connection
from ..rules import all_rules, get_rule
from ..rules.custom import CustomPhrases, pattern_error
from ..rules.base import RuleContext
from ..text import Document
from .state import escape_md, flash, llm_config, save_feedback, save_library, save_settings, secrets, show_flash

SENSITIVITY = ["low", "medium", "high"]

ANTHROPIC_MODELS = """\
- `claude-opus-5-5`: most capable (default)
- `claude-sonnet-5-5`: faster and cheaper
- `claude-haiku-5-5`: fastest and cheapest"""

OPENAI_PRESETS = {
    "Ollama (free, runs on your computer)": ("http://localhost:11434/v1", "llama3.1"),
    "LM Studio (free, runs on your computer)": ("http://localhost:1234/v1", "local-model"),
    "OpenAI": ("https://api.openai.com/v1", "gpt-4.1"),
    "OpenRouter": ("https://openrouter.ai/api/v1", "meta-llama/llama-3.1-70b-instruct"),
}


# --------------------------------------------------------------- callbacks
def _rule_cfg(rule_id: str) -> dict:
    return st.session_state.settings.setdefault("rules", {}).setdefault(rule_id, {})


def _set_rule(rule_id: str, field: str, key: str) -> None:
    _rule_cfg(rule_id)[field] = st.session_state[key]
    save_settings()


def _clear_rule_widgets() -> None:
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith(("rule_on_", "rule_sens_")):
            del st.session_state[key]


def _set_all_sensitivity() -> None:
    level = st.session_state["all_sensitivity"]
    for rule in all_rules():
        if rule.has_sensitivity:
            _rule_cfg(rule.id)["sensitivity"] = level
    save_settings()
    _clear_rule_widgets()
    flash("toast", f"All adjustable checks set to “{level}” sensitivity.")


def _enable_all() -> None:
    for rule in all_rules():
        _rule_cfg(rule.id)["enabled"] = True
    save_settings()
    _clear_rule_widgets()


def _reset_rules() -> None:
    st.session_state.settings["rules"] = {}
    save_settings()
    _clear_rule_widgets()
    flash("toast", "All checks reset to their defaults.")


def _set_ai(field: str, key: str) -> None:
    st.session_state.settings["ai"][field] = st.session_state[key]
    save_settings()


def _apply_preset() -> None:
    name = st.session_state["ai_preset"]
    if name in OPENAI_PRESETS:
        url, model = OPENAI_PRESETS[name]
        ai = st.session_state.settings["ai"]
        ai["openai_base_url"], ai["openai_model"] = url, model
        save_settings()
        st.session_state.pop("ai_openai_base_url", None)
        st.session_state.pop("ai_openai_model", None)


def _set_session_key(provider: str, key: str) -> None:
    value = st.session_state.get(key, "").strip()
    if value:
        st.session_state.session_keys[provider] = value
    else:
        st.session_state.session_keys.pop(provider, None)


# -------------------------------------------------------------------- page
def render() -> None:
    st.title("⚙️ Settings")
    st.caption("Changes save automatically to the user_data folder on this computer.")
    show_flash()
    tabs = st.tabs(
        ["🧪 Detection rules", "🚫 Custom phrases", "👍 Feedback", "🤖 AI connection", "💾 Backup"],
        key="settings_tab",
        on_change="rerun",
    )
    for tab, render_tab in zip(tabs, (_rules_tab, _custom_tab, _feedback_tab, _ai_tab, _backup_tab)):
        with tab:
            if tab.open:
                render_tab()


def _rules_tab() -> None:
    settings = st.session_state.settings
    stats = storage.feedback_stats(st.session_state.feedback)
    st.markdown(
        "Turn individual checks on or off. **Sensitivity** controls how readily a check fires: *high* flags "
        "more (including borderline cases), *low* flags only clear, repeated patterns."
    )
    c1, c2, c3 = st.columns([2.2, 1, 1], vertical_alignment="bottom")
    with c1:
        inner = st.columns([1.4, 1], vertical_alignment="bottom")
        inner[0].select_slider("Set every sensitivity to", SENSITIVITY, value="medium", key="all_sensitivity")
        inner[1].button("Apply to all", on_click=_set_all_sensitivity)
    c2.button("Turn all on", on_click=_enable_all, width="stretch")
    c3.button("Reset defaults", on_click=_reset_rules, width="stretch")

    rules = all_rules()
    for category in CATEGORY_ORDER:
        group = [r for r in rules if r.category == category]
        if not group:
            continue
        enabled = sum(settings["rules"].get(r.id, {}).get("enabled", r.default_enabled) for r in group)
        with st.expander(f"**{category_label(category)}** · {enabled} of {len(group)} on"):
            for rule in group:
                cfg = settings["rules"].get(rule.id, {})
                row = st.columns([0.5, 0.3, 0.2], vertical_alignment="center")
                on_key, sens_key = f"rule_on_{rule.id}", f"rule_sens_{rule.id}"
                row[0].toggle(
                    rule.name,
                    value=cfg.get("enabled", rule.default_enabled),
                    key=on_key,
                    on_change=_set_rule,
                    args=(rule.id, "enabled", on_key),
                )
                if rule.has_sensitivity:
                    row[1].select_slider(
                        f"Sensitivity for {rule.name}",
                        SENSITIVITY,
                        value=cfg.get("sensitivity", "medium"),
                        key=sens_key,
                        on_change=_set_rule,
                        args=(rule.id, "sensitivity", sens_key),
                        label_visibility="collapsed",
                        help=rule.sensitivity_help or None,
                    )
                s = stats.get(rule.id)
                if s:
                    row[2].caption(f"👍 {s['useful']} · 🚫 {s['false_positive']}")
                st.caption(rule.description)


def _custom_tab() -> None:
    settings = st.session_state.settings
    st.markdown(
        "Add words, phrases or constructions you never want to see. They're flagged under **Your custom phrases**.\n\n"
        "- Plain text matches that phrase anywhere, ignoring capitals: `heart pounding`\n"
        "- `*` stands for one to four words: `not * but *` or `her * eyes`\n"
        "- Experts can start with `re:` to write a regular expression: `re:\\bsuddenly\\b`"
    )
    with st.form("add_phrase", clear_on_submit=True):
        pattern = st.text_input("Phrase or pattern", placeholder="e.g.  orbs   or   a * of relief")
        note = st.text_input("Why you avoid it / what to do instead (optional)", placeholder="e.g. Nobody calls eyes 'orbs'.")
        submitted = st.form_submit_button("Add to my list", type="primary")
    if submitted:
        error = pattern_error(pattern) if pattern.strip() else "Type a phrase first."
        if error:
            st.error(error)
        else:
            settings["custom_phrases"].append({"pattern": pattern.strip(), "note": note.strip(), "enabled": True})
            save_settings()
            st.success(f"Added “{pattern.strip()}”.")

    phrases = settings["custom_phrases"]
    if not phrases:
        st.caption("Your list is empty.")
    for i, entry in enumerate(list(phrases)):
        cols = st.columns([0.12, 0.38, 0.38, 0.12], vertical_alignment="center")
        enabled = cols[0].toggle("On", value=entry.get("enabled", True), key=f"cp_on_{i}_{entry['pattern']}", label_visibility="collapsed")
        if enabled != entry.get("enabled", True):
            entry["enabled"] = enabled
            save_settings()
        cols[1].code(entry["pattern"], language=None)
        cols[2].caption(escape_md(entry.get("note") or "—"))
        if cols[3].button("Delete", key=f"cp_del_{i}_{entry['pattern']}"):
            phrases.pop(i)
            save_settings()
            st.rerun()

    with st.expander("Test your list on some text"):
        sample = st.text_area("Sample text", key="cp_test_text", height=100, placeholder="Paste a sentence or two…")
        if sample.strip():
            doc = Document(sample)
            found = CustomPhrases().check(doc, RuleContext(custom_phrases=phrases))
            if found:
                st.html(render_highlighted(sample, found, {f.uid: i + 1 for i, f in enumerate(found)}))
                st.caption(f"{len(found)} match(es).")
            else:
                st.caption("No matches.")


def _feedback_tab() -> None:
    feedback = st.session_state.feedback
    entries = feedback.get("entries", {})
    st.markdown(
        "When you mark findings as 👍 useful or 🚫 false positive, they're recorded here. False positives are hidden "
        "from future analyses (the same check flagging the same words). If the AI critic is on, your feedback is "
        "also shared with it as guidance (you can turn that off in **AI connection**)."
    )
    stats = storage.feedback_stats(feedback)
    if stats:
        rows = []
        for rule_id, s in stats.items():
            rule = get_rule(rule_id)
            rows.append({
                "Check": rule.name if rule else ("AI critic" if rule_id == "ai_critic" else rule_id),
                "👍 Useful": s["useful"],
                "🚫 False positive": s["false_positive"],
            })
        st.dataframe(pd.DataFrame(rows).sort_values("🚫 False positive", ascending=False), hide_index=True, width="stretch")
        st.caption("A check with many false positives is a good candidate for lower sensitivity or switching off.")
    else:
        st.caption("No feedback yet.")

    hidden = [(sig, e) for sig, e in entries.items() if e.get("verdict") == "false_positive"]
    if hidden:
        st.markdown(f"**Hidden findings ({len(hidden)})**")
        for sig, entry in hidden:
            cols = st.columns([0.82, 0.18], vertical_alignment="center")
            cols[0].markdown(f"**{escape_md(entry.get('title', ''))}** · “{escape_md((entry.get('excerpt') or '')[:140])}”")
            if cols[1].button("Restore", key=f"fb_restore_{sig}"):
                entries.pop(sig, None)
                save_feedback()
                st.rerun()
    if entries:
        st.divider()
        confirm = st.checkbox("I want to delete all my feedback", key="confirm_clear_feedback")
        if st.button("Clear all feedback", disabled=not confirm):
            feedback["entries"] = {}
            save_feedback()
            for key in list(st.session_state.keys()):
                if isinstance(key, str) and "_fb_" in key:
                    del st.session_state[key]
            st.rerun()


def _key_status(provider: str) -> None:
    key, source = find_api_key(provider, st.session_state.session_keys, secrets())
    if key:
        st.success(f"API key found ({source}).", icon="🔑")
    elif provider == "anthropic":
        st.warning(
            "No API key found. Create one at console.anthropic.com, then either put it in "
            "`.streamlit/secrets.toml` (see the README) or paste it below for this session.",
            icon="🔑",
        )
    else:
        st.caption("No API key found. Local servers such as Ollama and LM Studio don't need one.")
    session_key = f"session_key_{provider}"
    st.text_input(
        "Paste an API key for this session only (kept in memory, never saved)",
        type="password",
        key=session_key,
        on_change=_set_session_key,
        args=(provider, session_key),
    )


def _ai_tab() -> None:
    ai = st.session_state.settings["ai"]
    st.markdown(
        "AI features are **optional**. Rule-based analysis always works offline. When AI is on, the passage you "
        "analyze (plus your style notes and samples, if enabled below) is sent to the provider you choose."
    )
    options = list(PROVIDER_LABELS)
    st.radio(
        "AI provider",
        options,
        index=options.index(ai.get("provider", "none")) if ai.get("provider") in options else 0,
        format_func=PROVIDER_LABELS.get,
        key="ai_provider",
        on_change=_set_ai,
        args=("provider", "ai_provider"),
    )
    provider = ai.get("provider", "none")
    if provider == "anthropic":
        st.text_input(
            "Model", value=ai["anthropic_model"], key="ai_anthropic_model",
            on_change=_set_ai, args=("anthropic_model", "ai_anthropic_model"),
        )
        st.markdown(ANTHROPIC_MODELS)
        efforts = ["low", "medium", "high", "default"]
        st.select_slider(
            "Effort", efforts,
            value=ai.get("anthropic_effort", "high") if ai.get("anthropic_effort") in efforts else "high",
            key="ai_anthropic_effort", on_change=_set_ai, args=("anthropic_effort", "ai_anthropic_effort"),
            help="Higher effort means more careful (and slower, pricier) answers. Choose “default” for older models that reject this setting.",
        )
        _key_status("anthropic")
    elif provider == "openai_compatible":
        st.selectbox(
            "Quick setup", ["Choose a preset…", *OPENAI_PRESETS], key="ai_preset", on_change=_apply_preset,
            help="Fills in the address and a typical model name. Ollama and LM Studio run models on your own computer for free.",
        )
        st.text_input(
            "Server address (base URL)", value=ai["openai_base_url"], key="ai_openai_base_url",
            on_change=_set_ai, args=("openai_base_url", "ai_openai_base_url"),
        )
        st.text_input(
            "Model name", value=ai["openai_model"], key="ai_openai_model",
            on_change=_set_ai, args=("openai_model", "ai_openai_model"),
            help="For Ollama, use a model you've pulled, e.g. llama3.1 (run `ollama pull llama3.1`).",
        )
        _key_status("openai_compatible")

    if provider != "none":
        if st.button("Test connection", key="test_connection"):
            with st.spinner("Contacting the model…"):
                try:
                    reply = test_connection(llm_config())
                    st.success(f"Connected. The model replied: “{reply}”")
                except LLMError as exc:
                    st.error(str(exc))
        st.divider()
        st.markdown("**What the AI receives**")
        st.checkbox(
            "Include my style notes, writing samples and before → after examples",
            value=ai.get("use_library", True), key="ai_use_library",
            on_change=_set_ai, args=("use_library", "ai_use_library"),
        )
        st.checkbox(
            "Include my 👍 / 🚫 feedback so the critic learns what I consider a problem",
            value=ai.get("use_feedback", True), key="ai_use_feedback",
            on_change=_set_ai, args=("use_feedback", "ai_use_feedback"),
        )
        st.slider(
            "Maximum AI critic findings", 5, 40, value=int(ai.get("max_findings", 15)), key="ai_max_findings",
            on_change=_set_ai, args=("max_findings", "ai_max_findings"),
        )


def _backup_tab() -> None:
    ss = st.session_state
    st.markdown(f"Your settings, style library and feedback are stored in:\n\n`{storage.DATA_DIR}`")
    st.download_button(
        "Download a backup",
        storage.export_all(ss.settings, ss.library, ss.feedback),
        file_name="prose-clinic-backup.json",
        mime="application/json",
        help="Saves settings, custom phrases, style library and feedback in one file. API keys are never included.",
    )
    uploaded = st.file_uploader("Restore from a backup file", type=["json"], key="backup_upload")
    if uploaded is not None:
        try:
            settings, library, feedback = storage.parse_backup(uploaded.getvalue())
        except ValueError as exc:
            st.error(str(exc))
            return
        st.info(
            f"Backup contains {len(settings.get('custom_phrases', []))} custom phrases, "
            f"{len(library.get('samples', []))} writing samples, {len(library.get('pairs', []))} examples and "
            f"{len(feedback.get('entries', {}))} feedback entries."
        )
        if st.button("Replace my current data with this backup", type="primary"):
            ss.settings, ss.library, ss.feedback = settings, library, feedback
            save_settings()
            save_library()
            save_feedback()
            for key in list(ss.keys()):
                if isinstance(key, str) and key.startswith(("rule_", "ai_", "lib_", "cp_")):
                    del ss[key]
            st.success("Backup restored.")
