"""Revise page: rewrite suggestions, full-passage revision, and the revision draft.

The original passage is never modified. Changes only reach the separate
revision draft when you click an Apply / Use button.
"""

from __future__ import annotations

import re

import pandas as pd
import streamlit as st

from .. import storage
from ..ai_tasks import compare_runs, revise_passage, suggest_rewrite
from ..findings import SEVERITY_ICONS, Finding, category_label
from ..highlight import STYLE, change_ratio, render_diff, render_in_context
from ..llm import LLMError
from . import nav
from .state import current_analysis, escape_md, flash, llm_config, save_library, show_flash

DIFF_HEIGHT = 560


def _quote_box(text: str) -> None:
    import html as _html

    st.html(STYLE + f'<div class="pc-snippet">{_html.escape(text, quote=False)}</div>')


def replace_in_draft(old: str, new: str, near: int | None) -> bool:
    draft = st.session_state.draft_text
    positions = [m.start() for m in re.finditer(re.escape(old), draft)]
    if not positions:
        return False
    pos = min(positions, key=lambda p: abs(p - near)) if near is not None else positions[0]
    st.session_state.draft_text = draft[:pos] + new + draft[pos + len(old):]
    return True


def _apply(old: str, new: str, near: int | None) -> None:
    if replace_in_draft(old, new, near):
        flash("toast", "Applied to your revision draft (see the Revision draft tab). The original is unchanged.")
    else:
        flash(
            "warning",
            "Couldn't find that passage in the draft. It may already have been edited; copy the suggestion manually.",
        )


def _remove(uid: str) -> None:
    st.session_state.selected.pop(uid, None)
    st.session_state.rewrites.pop(uid, None)
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.endswith(f"_sel_{uid}"):
            del st.session_state[key]


def _save_pair(before: str, after: str, why: str) -> None:
    st.session_state.library["pairs"].append({"before": before, "after": after, "why": why})
    save_library()
    flash("toast", "Saved to your Style library as a before → after example.")


def _use_revision() -> None:
    ss = st.session_state
    storage.archive_draft(ss.analyzed_text, ss.draft_text)
    ss.draft_text = ss.revision["text"]
    flash("toast", "The AI revision is now your revision draft. Any previous draft was archived in user_data/drafts.")


def _reset_draft() -> None:
    ss = st.session_state
    storage.archive_draft(ss.analyzed_text, ss.draft_text)
    ss.draft_text = ss.analyzed_text


def render() -> None:
    ss = st.session_state
    st.title("✏️ Revise")
    show_flash()
    original = ss.analyzed_text
    if not original:
        st.info("Analyze a passage first, then come back here to revise it.")
        nav.link("analyze", "Go to Analyze", "🔍")
        return
    if not ss.draft_text:
        ss.draft_text = original
    st.caption(
        "Your original passage is never changed. Suggestions only go into the separate **revision draft** "
        "when you click Apply, and you can edit or reset the draft at any time."
    )
    config = llm_config()
    selected = sorted((Finding.from_dict(d) for d in ss.selected.values()), key=lambda f: (f.start or 0))
    tab_sel, tab_full, tab_draft = st.tabs(
        [f"🎯 Selected findings ({len(selected)})", "📝 Full-passage revision", "📄 Revision draft"],
        key="revise_tab",
        on_change="rerun",
    )
    with tab_sel:
        if tab_sel.open:
            _selected_tab(selected, original, config)
    with tab_full:
        if tab_full.open:
            _full_tab(original, config)
    with tab_draft:
        if tab_draft.open:
            _draft_tab(original)


def _selected_tab(selected: list[Finding], original: str, config) -> None:
    ss = st.session_state
    if not selected:
        st.info("No findings selected yet. On the **Analyze** page, tick **Add to revision list** on the findings you want help with.")
        return
    if config is None:
        st.caption("AI rewrites are off; set up an AI connection in Settings to get suggestions. Quick fixes work offline.")
    else:
        pending = [f for f in selected if f.uid not in ss.rewrites]
        if pending and st.button(f"Suggest rewrites for all {len(pending)} remaining", key="rewrite_all"):
            progress = st.progress(0.0, text="Asking for suggestions…")
            for i, f in enumerate(pending, start=1):
                try:
                    ss.rewrites[f.uid] = suggest_rewrite(config, original, f, ss.library, ss.settings["ai"], ss.settings)
                except LLMError as exc:
                    st.error(f"{f.title}: {exc}")
                    break
                progress.progress(i / len(pending), text=f"{i} of {len(pending)} done")
            progress.empty()
            st.rerun()

    for f in selected:
        with st.container(border=True):
            st.markdown(
                f"{SEVERITY_ICONS.get(f.severity, '')} **{escape_md(f.title)}** · {category_label(f.category)}"
                + (" · AI critic" if f.source == "ai" else "")
            )
            st.html(render_in_context(original, f))
            st.markdown(escape_md(f.message))
            buttons = st.columns([1.4, 1.4, 1, 2.2])
            if config is not None and buttons[0].button("Suggest rewrite", key=f"rw_{f.uid}", type="primary"):
                with st.spinner("Thinking about this passage…"):
                    try:
                        ss.rewrites[f.uid] = suggest_rewrite(config, original, f, ss.library, ss.settings["ai"], ss.settings)
                    except LLMError as exc:
                        st.error(str(exc))
                    else:
                        st.rerun()
            if f.replacement is not None:
                buttons[1].button(
                    "Apply quick fix",
                    key=f"qf_{f.uid}",
                    on_click=_apply,
                    args=(f.excerpt, f.replacement, f.start),
                    help=f"“{f.excerpt}” → “{f.replacement}”",
                )
            buttons[2].button("Remove", key=f"rm_{f.uid}", on_click=_remove, args=(f.uid,))
            result = ss.rewrites.get(f.uid)
            if result is not None:
                _rewrite_result(f, result)


def _rewrite_result(f: Finding, result) -> None:
    if result.keep_original_reason:
        st.info(f"**The AI thinks the original may already work:** {escape_md(result.keep_original_reason)}")
    cols = st.columns(1 + len(result.options))
    with cols[0]:
        st.markdown("**Original**")
        _quote_box(result.target_text)
    for i, option in enumerate(result.options):
        with cols[i + 1]:
            st.markdown(f"**Option {i + 1}**")
            if option["approach"]:
                st.caption(escape_md(option["approach"]))
            _quote_box(option["text"])
            issues = result.checks[i] if i < len(result.checks) else []
            if issues:
                st.warning("This suggestion itself triggers: " + ", ".join(issues))
            st.button(
                "Apply to draft",
                key=f"apply_{f.uid}_{i}",
                on_click=_apply,
                args=(result.target_text, option["text"], result.target_start),
                type="primary",
            )
            st.button(
                "Save as example",
                key=f"pair_{f.uid}_{i}",
                on_click=_save_pair,
                args=(result.target_text, option["text"], f.title),
                help="Adds this before → after pair to your Style library, so future AI suggestions learn your taste.",
            )


def _full_tab(original: str, config) -> None:
    ss = st.session_state
    st.markdown(
        "Ask the AI to revise the **whole passage** at once, fixing the flagged habits while preserving plot, "
        "characterization, point of view, tense and tone. The result appears side by side with your original; "
        "nothing is applied until you choose to."
    )
    if config is None:
        st.info("Full-passage revision needs an AI connection.")
        nav.link("settings", "Set up an AI connection in Settings", "⚙️")
        return
    analysis = current_analysis()
    intensity = st.radio(
        "How much should change?",
        ["Light", "Moderate", "Thorough"],
        index=1,
        horizontal=True,
        key="rev_intensity",
        captions=["Only the clearest problems", "Flagged problems plus similar ones", "Rework anything generic"],
    )
    present = sorted({f.category for f in analysis.findings}, key=lambda c: category_label(c)) if analysis else []
    focus = st.multiselect(
        "Problems to address", present, default=present, format_func=category_label, key="rev_focus",
        help="Rule-based findings in these categories are sent as the list of problems to fix.",
    )
    critique = ss.critique
    include_ai = st.checkbox(
        "Also address the AI critic's findings",
        value=critique is not None,
        disabled=critique is None,
        key="rev_include_ai",
        help="Run the AI critique on the Analyze page first to enable this.",
    )
    extra = st.text_area(
        "Extra instructions (optional)",
        key="rev_extra",
        placeholder="e.g. Keep Mara's dry humour. Don't touch the final paragraph. British spelling.",
        height=80,
    )
    if st.button("Revise the full passage", type="primary", key="run_revision"):
        issues = [f for f in (analysis.findings if analysis else []) if f.category in focus]
        if include_ai and critique is not None:
            issues += critique.findings
        with st.spinner("Revising… long passages can take a few minutes."):
            try:
                revision = revise_passage(
                    config, original, issues, intensity, extra, ss.library, ss.settings["ai"]
                )
                rows, new = compare_runs(original, revision.text, ss.settings)
                ss.revision = {"text": revision.text, "notes": revision.notes, "rows": rows, "new": [x.to_dict() for x in new]}
            except LLMError as exc:
                st.error(str(exc))

    revision = ss.revision
    if not revision:
        return
    st.divider()
    ratio = change_ratio(original, revision["text"])
    st.markdown(f"#### Original vs. AI revision  ·  about {ratio:.0%} of words changed")
    left_html, right_html = render_diff(original, revision["text"])
    left, right = st.columns(2, gap="medium")
    with left:
        st.markdown("**Original** (removed words struck through)")
        with st.container(height=DIFF_HEIGHT):
            st.html(left_html)
    with right:
        st.markdown("**AI revision** (new words highlighted)")
        with st.container(height=DIFF_HEIGHT):
            st.html(right_html)
    if revision["notes"]:
        st.markdown("**What the AI says it changed:**\n" + "\n".join(f"- {escape_md(n)}" for n in revision["notes"]))
    _check_report(revision["rows"], [Finding.from_dict(d) for d in revision["new"]], revision["text"])
    cols = st.columns([1.6, 1.4, 3])
    cols[0].button("Use as my revision draft", type="primary", on_click=_use_revision, key="use_revision")
    cols[1].download_button("Download revision", revision["text"], file_name="revision.txt", mime="text/plain", key="dl_revision")


def _check_report(rows: list[dict], new: list[Finding], revised_text: str) -> None:
    st.markdown("**Rule-based check of the revision**")
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.caption("Negative numbers mean fewer flagged instances in the revision.")
    else:
        st.caption("Rule-based counts are unchanged.")
    if new:
        st.warning(
            f"The revision introduced {len(new)} newly flagged pattern(s). Review these before using it:\n\n"
            + "\n".join(f"- **{escape_md(f.title)}**: “{escape_md(f.excerpt[:100])}”" for f in new[:12])
        )
    else:
        st.success("No new rule-based patterns were introduced.")


def _draft_tab(original: str) -> None:
    ss = st.session_state
    st.caption(
        "Your working copy. Edit it freely; applied suggestions land here. Downloads let you take it back to your "
        "word processor. Replaced drafts are archived in the user_data/drafts folder."
    )
    st.text_area("Revision draft (editable)", key="draft_text", height=300, persist_state="session")
    draft = ss.draft_text
    cols = st.columns([1.2, 1.3, 1.3, 1.4, 1.8])
    recheck = cols[0].button("Re-check draft", key="recheck_draft")
    cols[1].button("Reset to original", key="reset_draft", on_click=_reset_draft)
    cols[2].download_button("Download draft", draft, file_name="revised_draft.txt", mime="text/plain", key="dl_draft")
    cols[3].download_button("Download original", original, file_name="original.txt", mime="text/plain", key="dl_original")
    if draft == original:
        st.caption("No changes yet.")
    else:
        ratio = change_ratio(original, draft)
        st.markdown(f"#### Original vs. draft  ·  about {ratio:.0%} of words changed")
        left_html, right_html = render_diff(original, draft)
        left, right = st.columns(2, gap="medium")
        with left:
            st.markdown("**Original**")
            with st.container(height=DIFF_HEIGHT):
                st.html(left_html)
        with right:
            st.markdown("**Revision draft**")
            with st.container(height=DIFF_HEIGHT):
                st.html(right_html)
    if recheck:
        rows, new = compare_runs(original, draft, ss.settings)
        _check_report(rows, new, draft)
