"""Style library: notes, preferred writing samples, and before → after examples for the AI."""

from __future__ import annotations

import streamlit as st

from .state import escape_md, save_library, show_flash


def _save_notes() -> None:
    st.session_state.library["style_notes"] = st.session_state["lib_style_notes"]
    save_library()


def render() -> None:
    library = st.session_state.library
    st.title("📚 Style library")
    st.caption(
        "Teach the optional AI critic and rewriter what *your* good prose looks like. Nothing here affects the "
        "rule-based checks, and nothing is sent anywhere unless you use an AI feature (you can also exclude the "
        "library in Settings → AI connection)."
    )
    show_flash()
    tab_notes, tab_samples, tab_pairs = st.tabs(
        ["📝 Style notes", "✍️ Writing samples", "🔁 Before → after examples"], key="library_tab", on_change="rerun"
    )
    with tab_notes:
        st.markdown(
            "Describe your voice and your deliberate choices, so they aren't “fixed” away. For example: *Close third "
            "person, past tense. I use sentence fragments on purpose in action scenes. Mara is sarcastic and never "
            "says how she feels. Keep British spelling.*"
        )
        st.text_area(
            "Style notes", value=library.get("style_notes", ""), key="lib_style_notes", height=200,
            on_change=_save_notes, label_visibility="collapsed",
            placeholder="Your point of view, tense, tone, characters' voices, and habits you use on purpose…",
        )
        st.caption("Saved automatically when you click outside the box.")

    with tab_samples:
        st.markdown(
            "Paste passages that sound the way you want your prose to sound: your own best writing, or published "
            "prose you admire. **150–400 words each works best**; the AI sees up to about 6,000 characters in total."
        )
        st.caption(f"{len(library['samples'])} saved.")
        with st.form("add_sample", clear_on_submit=True):
            title = st.text_input("Title", placeholder="e.g. Chapter 3 opening (my favourite)")
            text = st.text_area("Sample text", height=180)
            submitted = st.form_submit_button("Add sample", type="primary")
        if submitted:
            if not text.strip():
                st.error("Paste some text for the sample.")
            else:
                library["samples"].append({"title": title.strip() or f"Sample {len(library['samples']) + 1}", "text": text.strip(), "active": True})
                save_library()
                st.success("Sample added.")
                st.rerun()
        for i, sample in enumerate(list(library["samples"])):
            words = len(sample.get("text", "").split())
            with st.expander(f"{'✅' if sample.get('active', True) else '⏸️'} {sample.get('title', 'Sample')} · {words} words"):
                st.markdown(escape_md(sample.get("text", "")))
                cols = st.columns([1, 1, 3])
                active = cols[0].toggle("Use in AI prompts", value=sample.get("active", True), key=f"lib_sample_on_{i}")
                if active != sample.get("active", True):
                    sample["active"] = active
                    save_library()
                    st.rerun()
                if cols[1].button("Delete", key=f"lib_sample_del_{i}"):
                    library["samples"].pop(i)
                    save_library()
                    st.rerun()

    with tab_pairs:
        st.markdown(
            "Pairs of weak and improved prose. They show the AI the kind of change you like, and that it should "
            "*not* swap one habit for another. You can also save pairs straight from the Revise page."
        )
        st.caption(f"{len(library['pairs'])} saved.")
        with st.form("add_pair", clear_on_submit=True):
            before = st.text_area("Before (weak / AI-sounding)", height=110, placeholder="She felt a surge of anger.")
            after = st.text_area("After (improved)", height=110, placeholder="She set the cup down hard enough to slop tea on the letter.")
            why = st.text_input("Why the second is better (optional)", placeholder="Shows the anger through an action with consequences.")
            submitted = st.form_submit_button("Add example", type="primary")
        if submitted:
            if not before.strip() or not after.strip():
                st.error("Fill in both the before and after text.")
            else:
                library["pairs"].append({"before": before.strip(), "after": after.strip(), "why": why.strip()})
                save_library()
                st.success("Example added.")
                st.rerun()
        for i, pair in enumerate(list(library["pairs"])):
            with st.container(border=True):
                cols = st.columns(2)
                cols[0].markdown("**Before**")
                cols[0].markdown(escape_md(pair.get("before", "")))
                cols[1].markdown("**After**")
                cols[1].markdown(escape_md(pair.get("after", "")))
                if pair.get("why"):
                    st.caption(f"Why: {escape_md(pair['why'])}")
                if st.button("Delete", key=f"lib_pair_del_{i}"):
                    library["pairs"].pop(i)
                    save_library()
                    st.rerun()
