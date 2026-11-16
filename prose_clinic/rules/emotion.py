"""Emotional telling: naming feelings instead of conveying them."""

from __future__ import annotations

import re

from ..text import Document
from .base import Pattern, PatternRule, RuleContext, register

EMOTION_NOUNS = (
    r"(?:anger|rage|fury|sadness|grief|sorrow|joy|happiness|fear|terror|dread|anxiety|guilt|shame|relief|"
    r"hope|despair|love|longing|jealousy|envy|frustration|confusion|embarrassment|pride|regret|loneliness|"
    r"panic|nervousness|excitement|disappointment|resentment|betrayal|warmth|tenderness|affection|gratitude|"
    r"unease|apprehension|determination|resolve|sympathy|pity|contempt|disgust|irritation|annoyance|"
    r"humiliation|helplessness|hopelessness|euphoria|elation|contentment|satisfaction|nostalgia|melancholy|"
    r"emotions?|calm|peace)"
)
EMOTION_ADJECTIVES = (
    r"(?:angry|furious|sad|happy|afraid|scared|terrified|frightened|anxious|nervous|guilty|ashamed|relieved|"
    r"hopeful|hopeless|desperate|lonely|excited|disappointed|frustrated|confused|embarrassed|proud|jealous|"
    r"envious|overwhelmed|numb|hollow|empty|helpless|worried|upset|hurt|betrayed|grateful|content|elated|"
    r"miserable|devastated|heartbroken|humiliated|irritated|annoyed|uneasy|apprehensive|vulnerable|exposed|"
    r"safe|loved|seen)"
)
_INTENSITY = r"(?:(?:so|very|incredibly|deeply|suddenly|utterly|a\s+little|strangely|oddly|almost|truly|completely)\s+)?"
_SUBJ = r"(?:she|he|they|i|we|you|(?-i:[A-Z][a-z]+))"
_FLAVOUR = r"(?:(?:sudden|deep|strange|familiar|overwhelming|profound|sharp|dull|quiet|fresh|cold|hot|sick|bitter)\s+)*"
_DOSE = r"(?:(?:surge|wave|pang|rush|flood|flicker|spark|twinge|stab|jolt|swell|burst|sense|knot|wash|tide)\s+of\s+)"

_PHYSICAL_TELL = re.compile(
    r"\b(?:shook|shaking|trembled|trembling|clenched|tightened|pounded|pounding|hammered|flushed|blushed|"
    r"tears?|wept|sobbed|gasped|swallowed|froze|flinched|winced|paled|sweat|sweating|knuckles)\b",
    re.IGNORECASE,
)


@register
class NamedEmotions(PatternRule):
    id = "named_emotions"
    name = "Named emotions"
    category = "emotion"
    description = "Telling the reader what a character feels (“She felt a surge of relief”, “A wave of guilt washed over him”)."
    message = (
        "The emotion is named rather than conveyed. Labels like this ask the reader to accept a feeling "
        "instead of experiencing it."
    )
    suggestion = (
        "Show what the character does, notices, or avoids because of the feeling: a specific action, a "
        "choice, a physical tell particular to them. Or trust the scene to imply it."
    )
    patterns = (
        Pattern(rf"\b{_SUBJ}\s+(?:felt|feels|feel|was\s+feeling|were\s+feeling|could\s+feel)\s+{_INTENSITY}{EMOTION_ADJECTIVES}\b"),
        Pattern(
            rf"\b(?:felt|feels|was\s+filled\s+with|was\s+overcome\s+(?:with|by)|was\s+consumed\s+by|"
            rf"was\s+overwhelmed\s+(?:with|by)|was\s+flooded\s+with)\s+(?:a\s+|an\s+)?{_FLAVOUR}{_DOSE}?{EMOTION_NOUNS}\b"
        ),
        Pattern(rf"\b(?:a|an|another)\s+{_FLAVOUR}{_DOSE}{EMOTION_NOUNS}\b"),
        Pattern(
            rf"\b{EMOTION_NOUNS}\s+(?:washed|flooded|surged|coursed|rippled|bloomed|blossomed|spread|swept|welled|"
            r"rose|swelled|crashed|flared|flickered)\s+(?:over|through|in|up|into|across|inside)\b"
        ),
        Pattern(r"\b(?:made|making|makes)\s+(?:her|him|them|me|us)\s+feel\b", severity="low"),
        Pattern(
            rf"\b(?:she|he|they|i|we)\s+(?:realized|realised|knew|understood)\s+(?:then\s+)?(?:that\s+)?(?:she|he|they|i|we)\s+"
            rf"(?:was|were|had\s+been|felt)\s+(?:\w+\s+)?(?:{EMOTION_ADJECTIVES}|in\s+love)\b"
        ),
        Pattern(r"\bdeep\s+down,?\s+(?:she|he|they|i|we)\s+(?:knew|felt|understood)\b"),
        Pattern(r"\ba\s+part\s+of\s+(?:her|him|them|me)\s+(?:wanted|knew|felt|hoped|wished)\b", severity="low"),
        Pattern(
            r"\ba\s+sense\s+of\s+(?:peace|calm|dread|unease|purpose|belonging|loss|wonder|urgency|relief|foreboding|"
            r"safety|hope|guilt|pride|calm)\b",
            severity="low",
        ),
        Pattern(rf"\b(?:she|he|they|i|we)\s+(?:was|were)\s+(?:so\s+|very\s+|incredibly\s+|deeply\s+)?{EMOTION_ADJECTIVES}[.!]", severity="low"),
    )

    def check(self, doc: Document, ctx: RuleContext):
        results = super().check(doc, ctx)
        for finding in results:
            sentence = doc.sentence_at(finding.start)
            if not sentence or sentence.index == 0:
                continue
            previous = doc.sentences[sentence.index - 1]
            if previous.paragraph == sentence.paragraph and _PHYSICAL_TELL.search(previous.text):
                finding.title = "Emotion explained after it was shown"
                finding.message = (
                    "The previous sentence already shows this feeling physically; naming it afterwards "
                    "explains the effect and weakens it."
                )
                finding.suggestion = "Cut the explanation and trust the physical detail."
                finding.severity = "high"
        return results


@register
class FilterWords(PatternRule):
    id = "filter_words"
    name = "Filter verbs"
    category = "emotion"
    description = "“She saw / heard / noticed / realized…” layers between reader and event. Flagged when frequent."
    has_sensitivity = True
    sensitivity_help = "Filter verbs per 1,000 words before flagging (low: 12, medium: 8, high: 5)."
    min_per_1000 = (12, 8, 5)
    scope = "narration"
    severity = "low"
    message = (
        "A filter verb: “she saw / heard / noticed X” puts the character's perception between the reader "
        "and the event."
    )
    suggestion = "Often “X happened” is more immediate. Keep the filter when the act of noticing matters."
    patterns = (
        Pattern(
            r"\b(?:she|he|they|i|we)\s+(?:could\s+)?(?:see|saw|hear|heard|feel|felt|notice|noticed|watched|sensed|"
            r"realized|realised|wondered)\s+(?!(?:a|an)\s+(?:surge|wave|pang|rush|flood|flicker|twinge|stab|jolt)\b)"
            r"(?:that\s+|how\s+|as\s+|the\s+|a\s+|an\s+|his\s+|her\s+|their\s+|its\s+|something|someone)"
        ),
    )
