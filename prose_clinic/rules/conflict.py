"""Conflict and resolution: tension that dissolves too quickly, endings that tie a bow."""

from __future__ import annotations

import re

from ..text import Document
from .base import Pattern, PatternRule, RuleContext, register

_CONFLICT = re.compile(
    r"\b(?:shouted|snapped|yelled|screamed|slammed|glared|hissed|furious|angry|argued|argument|fight|fought|"
    r"accused|betrayed|hate|hated|liar|lied|how\s+could\s+you)\b",
    re.IGNORECASE,
)


@register
class SoftenedConflict(PatternRule):
    id = "softened_conflict"
    name = "Conflict softened too fast"
    category = "conflict"
    description = "Anger that drains away, faces that soften, instant hugs, especially soon after a conflict flares."
    message = (
        "Tension dissolves on cue. AI drafts tend to defuse conflict within a few lines (“the anger drained "
        "from her”, “his expression softened”), which robs the scene of stakes."
    )
    suggestion = (
        "Let the disagreement persist, leave something unresolved, or make reconciliation cost something "
        "(a concession, a lie, a grudge that lingers)."
    )
    patterns = (
        Pattern(
            r"\b(?:the\s+|{PRON}\s+)?(?:anger|fury|rage|tension|frustration|fight|hostility|resentment|irritation|annoyance)\s+"
            r"(?:drained|melted|bled|seeped|ebbed|faded|evaporated|dissolved|left|went\s+out\s+of|eased|slipped\s+away)\b"
        ),
        Pattern(r"\b(?:{PRON}\s+)?(?:expression|face|voice|eyes|gaze|features|tone)\s+softened\b"),
        Pattern(r"\bthe\s+fight\s+went\s+out\s+of\b"),
        Pattern(r"\b(?:laughed|smiled|grinned)\s+despite\s+{REFL}\b"),
        Pattern(r"\bcouldn{APOS}t\s+stay\s+(?:mad|angry)\b"),
        Pattern(r"\bpulled\s+(?:her|him|them|me)\s+into\s+(?:a|an)\s+(?:[\w'’-]+\s+)?(?:hug|embrace)\b"),
        Pattern(r"\b(?:they\s+both|both\s+of\s+them)\s+(?:laughed|smiled|burst\s+out\s+laughing)\b"),
        Pattern(r"\bsmiled\s+through\s+{PRON}\s+tears\b"),
        Pattern(r"\b(?:a|the)\s+weight\s+(?:had\s+)?(?:lifted|been\s+lifted)\b"),
        Pattern(r"\bsomething\s+(?:eased|loosened|unknotted|unclenched)\s+in\s+{PRON}\s+chest\b"),
        Pattern(r"\btension\s+(?:between\s+them\s+)?(?:broke|eased|dissipated)\b"),
    )

    def check(self, doc: Document, ctx: RuleContext):
        results = super().check(doc, ctx)
        conflict_paragraphs = sorted(
            {i for m in _CONFLICT.finditer(doc.text) if (i := doc.paragraph_index_at(m.start())) is not None}
        )
        for finding in results:
            para = doc.paragraph_index_at(finding.start)
            earlier = [p for p in conflict_paragraphs if para is not None and p <= para]
            if earlier and para - earlier[-1] <= 4:
                finding.severity = "high"
                gap = para - earlier[-1]
                finding.message += (
                    f" Here it happens {gap} paragraph{'s' if gap != 1 else ''} after the conflict flares."
                    if gap
                    else " Here it happens in the same paragraph as the conflict."
                )
        return results


@register
class NeatResolution(PatternRule):
    id = "neat_resolution"
    name = "Tidy, hopeful ending"
    category = "conflict"
    description = "Endings that resolve with reassurance, epiphany, or clearing weather (“whatever came next, they would face it together”). Only the final part of the passage is checked."
    message = (
        "The ending ties a bow: reassurance, an epiphany, or clearing weather that mirrors the mood. "
        "AI-written scenes very often close this way."
    )
    suggestion = "End on a concrete image, an action, or an unresolved question, and let the reader decide how hopeful it is."
    patterns = (
        Pattern(r"\b(?:everything|it|things|we|they|you)\s+(?:would|was\s+going\s+to|is\s+going\s+to|are\s+going\s+to|will|{APOS}ll|{APOS}re\s+going\s+to)\s+be\s+(?:okay|ok|alright|all\s+right|fine)\b"),
        Pattern(r"\bwhatever\s+(?:came|comes|happened|happens|lay|lies)(?:\s+(?:next|ahead))?\b"),
        Pattern(r"\b(?:together|side\s+by\s+side),?\s+(?:they|we)\s+(?:would|could|will)\b"),
        Pattern(r"\b(?:face|figure\s+out|get\s+through)\s+(?:it|this|whatever\s+\w+)\s+together\b"),
        Pattern(r"\bfor\s+the\s+first\s+time\s+in\b"),
        Pattern(r"\b(?:and\s+)?(?:that|it|this)\s+was\s+enough\b"),
        Pattern(r"\b(?:a\s+)?new\s+beginning\b"),
        Pattern(r"\bthe\s+(?:start|beginning)\s+of\s+something\s+(?:new|beautiful|better)\b"),
        Pattern(r"\bready\s+to\s+face\b"),
        Pattern(r"\ba\s+(?:small|tiny|fragile|flicker\s+of|glimmer\s+of|spark\s+of)\s+hope\b"),
        Pattern(r"\bfinally\s+(?:at\s+peace|home|free|whole)\b"),
        Pattern(r"\b(?:the\s+)?(?:sun|light|dawn)\s+(?:broke|was\s+breaking|began\s+to\s+rise|rose|crept|spilled)\b"),
        Pattern(r"\bfirst\s+(?:pale\s+)?light\b"),
        Pattern(r"\b(?:she|he|they|i|we)\s+(?:finally\s+)?(?:understood|realized|realised)\b"),
        Pattern(r"\b(?:rain|storm|wind)\s+(?:began\s+to\s+|had\s+begun\s+to\s+)?(?:soften|ease|clear|stop|let\s+up|die\s+down)\b"),
    )

    def check(self, doc: Document, ctx: RuleContext):
        if doc.word_count < 120 or not doc.paragraphs:
            return []
        # "The ending" = the last fifth of the words, and always at least the final paragraph.
        cutoff = min(doc.words[int(len(doc.words) * 0.8)][0], doc.paragraphs[-1].start)
        results = [f for f in super().check(doc, ctx) if f.start >= cutoff]
        if len(results) >= 2:
            results.insert(
                0,
                self.doc_finding(
                    f"The ending contains {len(results)} resolution signals (reassurance, epiphany, hopeful "
                    "imagery). Endings that resolve this neatly are a frequent AI pattern.",
                    "Consider stopping a beat earlier, or ending on something concrete and unresolved.",
                    title="Ending resolves very neatly",
                    severity="medium",
                ),
            )
        return results
