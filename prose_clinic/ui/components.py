"""Reusable UI pieces: finding cards, feedback buttons, highlighted text panels."""

from __future__ import annotations

import streamlit as st

from .. import storage
from ..findings import SEVERITY_ICONS, SEVERITY_LABELS, Finding, category_label
from ..highlight import legend, render_highlighted, render_in_context
from .state import escape_md, flash, save_feedback

FEEDBACK_LABELS = {"useful": "👍 Useful", "false_positive": "🚫 False positive"}
PAGE_SIZE = 25


def _on_feedback(finding_data: dict, key: str) -> None:
    verdict = st.session_state.get(key)
    finding = Finding.from_dict(finding_data)
    storage.set_verdict(st.session_state.feedback, finding, verdict)
    save_feedback()
    if verdict == "false_positive":
        flash("toast", "Marked as a false positive and hidden. Restore it from “Show hidden findings”.")


def _on_select(finding_data: dict, key: str) -> None:
    selected = st.session_state.selected
    if st.session_state.get(key):
        selected[finding_data["uid"]] = finding_data
    else:
        selected.pop(finding_data["uid"], None)


def finding_card(finding: Finding, number: int | str, text: str, prefix: str, *, selectable: bool = True) -> None:
    data = finding.to_dict()
    with st.container(border=True):
        head, tag = st.columns([0.72, 0.28], vertical_alignment="top")
        head.markdown(
            f"**{number}.** {SEVERITY_ICONS.get(finding.severity, '')} **{escape_md(finding.title)}**",
            help=SEVERITY_LABELS.get(finding.severity),
        )
        tag.caption(category_label(finding.category))
        if not finding.is_document_level:
            st.html(render_in_context(text, finding))
        elif finding.excerpt:
            st.caption(f"Quoted: “{escape_md(finding.excerpt[:300])}” (not found exactly in the text)")
        if finding.message:
            st.markdown(escape_md(finding.message))
        if finding.suggestion:
            st.markdown(f"**Try:** {escape_md(finding.suggestion)}")
        if finding.note:
            st.caption(f"💡 {escape_md(finding.note)}")
        if finding.replacement is not None:
            st.caption(
                f"⚡ Quick fix available: “{escape_md(finding.excerpt)}” → “{escape_md(finding.replacement)}” "
                "(add it to the revision list to apply it)."
            )
        left, right = st.columns([0.62, 0.38], vertical_alignment="center")
        fb_key = f"{prefix}_fb_{finding.uid}"
        with left:
            st.segmented_control(
                "Feedback",
                options=list(FEEDBACK_LABELS),
                format_func=FEEDBACK_LABELS.get,
                default=storage.verdict_for(st.session_state.feedback, finding),
                key=fb_key,
                on_change=_on_feedback,
                args=(data, fb_key),
                label_visibility="collapsed",
            )
        if selectable and not finding.is_document_level:
            sel_key = f"{prefix}_sel_{finding.uid}"
            with right:
                st.checkbox(
                    "Add to revision list",
                    value=finding.uid in st.session_state.selected,
                    key=sel_key,
                    on_change=_on_select,
                    args=(data, sel_key),
                )


def numbering(findings: list[Finding]) -> dict[str, int]:
    return {f.uid: i + 1 for i, f in enumerate(findings)}


def findings_panel(findings: list[Finding], text: str, prefix: str, numbers: dict[str, int], height: int) -> None:
    """Passage-wide notes first, then paginated finding cards."""
    doc_level = [f for f in findings if f.is_document_level]
    spans = [f for f in findings if not f.is_document_level]
    pages = max(1, (len(spans) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = 1
    if pages > 1:
        key = f"{prefix}_page"
        if st.session_state.get(key, 1) > pages:
            st.session_state[key] = pages  # filters shrank the list
        page = st.number_input(f"Page (of {pages})", min_value=1, max_value=pages, step=1, key=key)
    with st.container(height=height, border=False):
        if doc_level and page == 1:
            st.markdown("##### Passage-wide patterns")
            for f in doc_level:
                finding_card(f, numbers.get(f.uid, "•"), text, prefix, selectable=False)
            if spans:
                st.markdown("##### In the text")
        for f in spans[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]:
            finding_card(f, numbers.get(f.uid, "•"), text, prefix)
        if not findings:
            st.success("Nothing flagged with the current filters.")


def text_panel(text: str, findings: list[Finding], numbers: dict[str, int], height: int) -> None:
    categories = []
    for f in findings:
        if not f.is_document_level and f.category not in categories:
            categories.append(f.category)
    if categories:
        st.html(legend(categories, {c: category_label(c) for c in categories}))
    with st.container(height=height):
        st.html(render_highlighted(text, findings, numbers))


def hidden_findings(suppressed: list[Finding], prefix: str) -> None:
    if not suppressed:
        return
    with st.expander(f"Show hidden findings ({len(suppressed)} marked as false positives)"):
        for f in suppressed:
            cols = st.columns([0.8, 0.2], vertical_alignment="center")
            cols[0].markdown(f"**{escape_md(f.title)}** · “{escape_md(f.excerpt[:120] or f.message[:120])}”")
            if cols[1].button("Restore", key=f"{prefix}_restore_{f.uid}"):
                storage.set_verdict(st.session_state.feedback, f, None)
                save_feedback()
                st.session_state.pop(f"{prefix}_fb_{f.uid}", None)
                st.rerun()
