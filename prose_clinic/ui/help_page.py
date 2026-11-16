"""Help page."""

from __future__ import annotations

import streamlit as st

from ..analyzer import CATEGORY_ORDER
from ..findings import SEVERITY_ICONS, SEVERITY_LABELS, category_label
from ..rules import all_rules


def render() -> None:
    st.title("❓ Help")
    st.markdown(
        """
### The workflow
1. **Analyze**: paste a passage and click **Analyze**. Flagged phrases are highlighted in the text; numbers
   match the cards on the right. Hover over a highlight to see what it's about.
2. **Review**: for each finding, decide whether it's a real problem. Mark it 👍 *Useful* or 🚫 *False positive*
   (false positives are hidden in future analyses, and you can restore them any time).
3. **Revise**: tick **Add to revision list** on findings you want to fix, then open **Revise**. You get
   one-click *quick fixes* for simple redundancies, AI rewrite suggestions (optional), or a full-passage AI revision.
   Everything lands in a separate **revision draft**, shown side by side with your original, which is never changed.
4. **Tune**: in **Settings**, switch checks off or adjust their sensitivity, and add your own disliked phrases.
   In the **Style library**, save writing samples and before → after examples for the AI.

### This is an editor's assistant, not a rulebook
Every finding is a *possible* problem. The checks are written to separate habits from choices:
many only fire when a device is **repeated** or **dense** (one em dash or one fragment is never flagged), and
cards note when something **could be deliberate**. If a pattern is part of your voice, mark it as a false
positive, lower the sensitivity, or describe it in your style notes so the AI leaves it alone.

It is **not an AI detector**. Plenty of human writers use these devices, and the findings-per-1,000-words number is
only useful for comparing drafts of the same piece.

### Rule-based vs. AI analysis
- **Rule-based checks** measure things a program can count reliably: constructions, repetition, punctuation density,
  stock phrases, dialogue statistics. They run instantly and completely offline.
- **The AI critic** (optional) judges what rules can't: whether dialogue sounds human, whether characters sound
  distinct, tone, stakes, emotional telling. It's shown in its own tab. AI rewrites are re-checked by the rules, so a
  suggestion that sneaks in a new cliché is flagged before you apply it.
"""
    )
    st.markdown("### Severity")
    st.markdown("\n".join(f"- {SEVERITY_ICONS[s]} **{s.title()}**: {SEVERITY_LABELS[s]}" for s in ("high", "medium", "low")))
    st.markdown("### All checks")
    rules = all_rules()
    for category in CATEGORY_ORDER:
        group = [r for r in rules if r.category == category]
        if group:
            with st.expander(f"{category_label(category)} ({len(group)})"):
                st.markdown("\n".join(f"- **{r.name}**: {r.description}" for r in group))
    st.markdown(
        """
### Where things are saved
Settings, custom phrases, your style library and feedback are saved as JSON files in the **user_data** folder
inside the app folder. Archived revision drafts go to **user_data/drafts**. API keys are never written there.
Use **Settings → Backup** to export or restore everything.

### Privacy
Rule-based analysis never sends your text anywhere. AI features send the passage (and, if enabled, your style
library and feedback) to the provider you configure. With Ollama or LM Studio, that "provider" is a program on
your own computer, so nothing leaves it.
"""
    )
