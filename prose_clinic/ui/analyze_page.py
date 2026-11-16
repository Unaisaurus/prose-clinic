"""Analyze page: paste text, see highlighted findings, run the optional AI critic."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import storage
from ..ai_tasks import run_critique
from ..analyzer import Analysis, text_stats
from ..findings import CATEGORIES, SEVERITY_ICONS, category_label
from ..llm import PROVIDER_LABELS, LLMError
from ..rules import get_rule
from ..rules.dialogue import speaker_table
from ..text import WORD_RE
from ..sample_text import SAMPLE_PASSAGE
from . import components, nav
from .state import current_analysis, escape_md, flash, llm_config, show_flash

PANEL_HEIGHT = 720


def _analyze() -> None:
    ss = st.session_state
    text = ss.get("input_text", "")
    if not text.strip():
        flash("warning", "Paste some text into the box first.")
        return
    if text != ss.analyzed_text:
        if ss.analyzed_text:
            storage.archive_draft(ss.analyzed_text, ss.get("draft_text", ""))
        ss.analyzed_text = text
        ss.draft_text = text
        ss.selected = {}
        ss.critique = None
        ss.rewrites = {}
        ss.revision = None


def _load_example() -> None:
    st.session_state.input_text = SAMPLE_PASSAGE
    _analyze()


def _clear() -> None:
    st.session_state.input_text = ""


def render() -> None:
    ss = st.session_state
    st.title("🔍 Analyze")
    st.caption(
        "Paste a passage of fiction and click **Analyze**. The rule-based checks run entirely on your computer; "
        "nothing is sent anywhere unless you use the optional AI critic."
    )
    show_flash()

    st.text_area(
        "Your passage",
        key="input_text",
        height=260,
        placeholder="Paste a scene, a chapter, or a few paragraphs here…",
        label_visibility="collapsed",
        persist_state="session",
    )
    words = len(WORD_RE.findall(ss.input_text))
    cols = st.columns([1.1, 1.3, 0.9, 3], vertical_alignment="center")
    cols[0].button("Analyze", type="primary", on_click=_analyze, width="stretch")
    cols[1].button("Load example", on_click=_load_example, help="Loads a deliberately AI-flavoured passage so you can try the app.")
    cols[2].button("Clear", on_click=_clear, help="Empties the box. Your last analysis stays below until you analyze something new.")
    cols[3].caption(f"{words:,} words")

    analysis = current_analysis()
    if analysis is None:
        _welcome()
        return
    if ss.input_text.strip() and ss.input_text != ss.analyzed_text:
        st.info("The text in the box has changed since the last analysis. Click **Analyze** to refresh the results.")
    if analysis.errors:
        st.warning("Some checks hit an error and were skipped:\n\n" + "\n".join(f"- {e}" for e in analysis.errors))

    _summary(analysis)
    tab_rules, tab_ai, tab_stats = st.tabs(
        ["📋 Rule-based findings", "🤖 AI critique (optional)", "📊 Statistics"], key="analyze_tab", on_change="rerun"
    )
    with tab_rules:
        if tab_rules.open:
            _rules_tab(analysis)
    with tab_ai:
        if tab_ai.open:
            _ai_tab(analysis)
    with tab_stats:
        if tab_stats.open:
            _stats_tab(analysis)


def _welcome() -> None:
    st.divider()
    left, right = st.columns(2)
    with left:
        st.markdown(
            "#### What this checks\n"
            "- **Formulaic constructions**: “not X, but Y”, “It wasn't X. It was Y.”\n"
            "- **Repetition & rhythm**: repeated openings, same-length sentences, echoed words\n"
            "- **Punctuation habits**: heavy em dashes, ellipses, dramatic fragments\n"
            "- **Purple prose**: vague metaphors, abstraction, melodrama\n"
            "- **Clichés & stock phrasing**, including phrases common in AI fiction\n"
            "- **Dialogue**: therapy-speak, over-polished or agreeable lines, forced wit, voices that sound alike\n"
            "- **Emotional telling** and **conflict that resolves too neatly**"
        )
    with right:
        st.markdown(
            "#### How to read the results\n"
            "Findings are **possible** problems, not errors. A device used once on purpose is a choice; the same "
            "device everywhere is a habit. Mark findings as 👍 useful or 🚫 false positive; false positives are "
            "hidden from future analyses.\n\n"
            "Tick **Add to revision list** on any finding, then open **Revise** to get rewrite suggestions. "
            "Your original text is never changed.\n\n"
            "New here? Click **Load example** to see it in action."
        )


def _summary(analysis: Analysis) -> None:
    words = analysis.doc.word_count
    counts = analysis.counts_by_category()
    likely = sum(1 for f in analysis.findings if f.severity == "high")
    m = st.columns(4)
    m[0].metric("Words", f"{words:,}")
    m[1].metric("Findings", len(analysis.findings), help="Hidden false positives are not counted.")
    m[2].metric("Per 1,000 words", f"{len(analysis.findings) / max(words, 1) * 1000:.0f}", help="A rough density measure for comparing drafts of the same piece, not a quality score or an AI detector.")
    m[3].metric(f"{SEVERITY_ICONS['high']} Likely issues", likely, help="Findings marked high severity: the strongest, least ambiguous signals.")
    if counts:
        top = ", ".join(f"{category_label(c)} ({n})" for c, n in counts.most_common(3))
        st.caption(f"Most frequent: {top}")
    if words > 8000:
        st.caption("📏 Long passage: everything works, but reviewing is easier a scene or chapter at a time.")


def _rules_tab(analysis: Analysis) -> None:
    text = analysis.doc.text
    findings = analysis.findings
    present = [c for c in CATEGORIES if any(f.category == c for f in findings)]
    f1, f2 = st.columns([2.2, 1.3])
    chosen = f1.multiselect(
        "Show categories",
        present,
        default=present,
        format_func=category_label,
        # A new set of categories gets a fresh filter, so newly flagged categories are never hidden.
        key="filter_categories_" + "_".join(present),
        persist_state="session",
    )
    severities = f2.pills(
        "Severity",
        ["high", "medium", "low"],
        selection_mode="multi",
        default=["high", "medium", "low"],
        format_func=lambda s: f"{SEVERITY_ICONS[s]} {s}",
        key="filter_severity",
        persist_state="session",
    )
    shown = [f for f in findings if f.category in chosen and f.severity in (severities or [])]
    numbers = components.numbering(findings)

    left, right = st.columns([1.08, 1], gap="medium")
    with left:
        st.markdown("**Your text** · hover over a highlight for details; numbers match the cards")
        components.text_panel(text, shown, numbers, PANEL_HEIGHT)
    with right:
        st.markdown(f"**{len(shown)} findings** shown")
        components.findings_panel(shown, text, "rule", numbers, PANEL_HEIGHT)
    components.hidden_findings(analysis.suppressed, "rule")


def _ai_tab(analysis: Analysis) -> None:
    ss = st.session_state
    config = llm_config()
    st.markdown(
        "The AI critic gives a **second opinion on subjective issues** a rule can't judge: whether dialogue sounds "
        "natural, whether characters sound distinct, tone, emotional telling, and stakes. It is kept separate from "
        "the rule-based findings."
    )
    if config is None:
        st.info("AI features are optional and currently off. Everything else works without them.")
        nav.link("settings", "Set up an AI connection in Settings", "⚙️")
        return
    where = PROVIDER_LABELS.get(config.provider, config.provider)
    st.caption(
        f"Using **{escape_md(config.model or '?')}** via {where}. Your passage"
        + (" and enabled style-library items" if ss.settings["ai"].get("use_library", True) else "")
        + " will be sent to this provider."
    )
    if config.provider == "anthropic" and not config.api_key:
        st.warning("No Anthropic API key found yet. Add one in Settings → AI connection.")
    if st.button("Run AI critique", type="primary", key="run_critique"):
        with st.spinner("Asking the AI critic… this can take a minute for long passages."):
            try:
                ss.critique = run_critique(
                    config, analysis.doc.text, analysis.findings, ss.library, ss.feedback, ss.settings["ai"]
                )
            except LLMError as exc:
                st.error(str(exc))
    critique = ss.critique
    if critique is None:
        return

    st.markdown(f"**Summary.** {escape_md(critique.summary)}")
    if critique.strengths:
        st.markdown("**Worth keeping:**\n" + "\n".join(f"- {escape_md(s)}" for s in critique.strengths))
    hidden = storage.false_positive_signatures(ss.feedback)
    visible = [f for f in critique.findings if f.signature not in hidden]
    suppressed = [f for f in critique.findings if f.signature in hidden]
    if critique.unlocated:
        st.caption(f"{critique.unlocated} finding(s) quoted text that couldn't be matched exactly; they appear without a highlight.")
    numbers = components.numbering(visible)
    left, right = st.columns([1.08, 1], gap="medium")
    with left:
        components.text_panel(analysis.doc.text, visible, numbers, PANEL_HEIGHT)
    with right:
        st.markdown(f"**{len(visible)} AI findings**")
        components.findings_panel(visible, analysis.doc.text, "ai", numbers, PANEL_HEIGHT)
    components.hidden_findings(suppressed, "ai")


def _stats_tab(analysis: Analysis) -> None:
    doc = analysis.doc
    stats = text_stats(doc)
    m = st.columns(5)
    m[0].metric("Sentences", stats["sentences"])
    m[1].metric("Paragraphs", stats["paragraphs"])
    m[2].metric("Avg sentence", f"{stats['avg_sentence']:.1f} words")
    m[3].metric(
        "Length variation", f"{stats['sentence_variation']:.2f}",
        help="Standard deviation ÷ mean of sentence lengths. Around 0.5 or more usually means a lively mix; low values mean sentences are similar in length.",
    )
    m[4].metric("Dialogue", f"{stats['dialogue_share']:.0%}", help="Share of words inside quotation marks.")

    if stats["sentence_lengths"]:
        st.markdown("**Sentence lengths, in order.** A flat, even skyline suggests monotonous rhythm; peaks and dips suggest variety.")
        lengths = stats["sentence_lengths"]
        st.bar_chart(
            pd.DataFrame({"Sentence": range(1, len(lengths) + 1), "Words": lengths}),
            x="Sentence", y="Words", height=220,
        )
    left, right = st.columns(2)
    with left:
        st.markdown("**Most common sentence openers** (narration)")
        if stats["top_openers"]:
            st.dataframe(
                pd.DataFrame(stats["top_openers"], columns=["First word", "Sentences"]),
                hide_index=True, width="stretch",
            )
        st.markdown("**Findings by check**")
        by_rule = analysis.counts_by_rule()
        if by_rule:
            rows = [
                {"Check": (get_rule(r).name if get_rule(r) else r), "Category": category_label(get_rule(r).category) if get_rule(r) else "", "Findings": n}
                for r, n in by_rule.most_common()
            ]
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    with right:
        st.markdown("**Speakers** (detected from dialogue tags and action beats)")
        rows = speaker_table(doc)
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
            st.caption("Speakers need about 40 words of dialogue for the voice statistics. Attribution is automatic and can miss lines.")
        else:
            st.caption("No attributed dialogue found.")
