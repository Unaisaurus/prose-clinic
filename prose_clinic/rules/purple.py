"""Purple prose, vague imagery, abstraction and melodrama."""

from __future__ import annotations

import re

from ..text import Document
from .base import Pattern, PatternRule, Rule, RuleContext, register

_ABSTRACT_OBJECTS = (
    r"(?:emotions?|feelings?|grief|sorrow|memories|memory|longing|desire|regret|hope|fear|light|"
    r"shadows?|silence|sounds?|loss|pain|love|thoughts|possibilit(?:y|ies)|colou?rs|time|"
    r"everything|unspoken\s+\w+|warmth|darkness|tension|meaning|secrets|promises|whispers)"
)


@register
class AbstractImagery(PatternRule):
    id = "abstract_imagery"
    name = "Vague or abstract imagery"
    category = "purple"
    description = "Grand but vague figures of speech: “a symphony of emotions”, “like a promise”, “the world itself held its breath”."
    message = (
        "Imagery that gestures at significance without giving the reader anything to see. "
        "Abstract comparisons (“like a promise”) are among the most common AI flourishes."
    )
    suggestion = "Replace it with one concrete, sensory detail that only this scene could have."
    patterns = (
        Pattern(
            r"\b(?:a|an|the)\s+(?:symphony|tapestry|kaleidoscope|mosaic|dance|maelstrom|labyrinth|crucible|"
            r"ocean|sea|storm|whirlwind|torrent|tempest|tide|river|flood|chorus|landscape|architecture|"
            r"geography|arithmetic|alchemy|language|grammar|cartography)\s+of\s+(?:[\w'’-]+\s+)?" + _ABSTRACT_OBJECTS + r"\b",
            title="Grand abstract metaphor",
        ),
        Pattern(
            r"\b(?:like|as\s+if|as\s+though)\s+(?:a|an|the)?\s*(?:[\w'’-]+\s+)?(?:promise|secret|prayer|"
            r"confession|benediction|lifeline|living\s+thing|old\s+friend|physical\s+blow|question|answer|"
            r"warning|apology|lullaby|accusation|caress|memory|dream|whisper)\b",
            title="Abstract simile",
        ),
        Pattern(
            r"\b(?:the\s+)?(?:world|universe|time|air|night|silence|room|house|earth)\s+itself\b",
            title="“The world itself…”",
            message="“The world itself” / “time itself”: an intensifier that inflates the moment without adding information.",
        ),
        Pattern(
            r"\b(?:the\s+)?(?:world|room|forest|city|night|house|air|universe|everything|street|sky)\s+"
            r"(?:seemed\s+to\s+)?(?:hold|held|holding)\s+its\s+breath\b",
            title="“The room held its breath”",
        ),
        Pattern(
            r"\b(?:the\s+)?(?:silence|tension|grief|guilt|fear|dread|hope|memory|memories|regret|sorrow|"
            r"longing|darkness|loneliness|unease|anticipation)\s+(?:stretched|settled|coiled|curled|bloomed|"
            r"blossomed|unfurled|pooled|clawed|gnawed|crept|seeped|thrummed|hummed|crackled|thickened|pressed|"
            r"wrapped|whispered|lingered|swelled)\b",
            title="Personified abstraction",
            message="An emotion or atmosphere that acts like a creature (“silence stretched”, “dread coiled”). Stock in AI prose.",
            severity="low",
        ),
    )


@register
class SimileDensity(Rule):
    id = "simile_density"
    name = "Simile density"
    category = "purple"
    description = "A high rate of “like a…/as if…” comparisons in the narration."
    has_sensitivity = True
    sensitivity_help = "Similes per 1,000 narration words before flagging (low: 14, medium: 10, high: 6)."

    _SIMILE = re.compile(r"\b(?:like\s+(?:a|an|the|some)\b|as\s+if\b|as\s+though\b)", re.IGNORECASE)

    def check(self, doc: Document, ctx: RuleContext):
        matches = [m for m in self._SIMILE.finditer(doc.text) if not doc.in_dialogue(*m.span())]
        narration_words = sum(s.word_count for s in doc.narration_sentences)
        if len(matches) < 3 or not narration_words:
            return []
        per_1000 = len(matches) / narration_words * 1000
        if per_1000 < ctx.pick(14, 10, 6):
            return []
        results = [
            self.doc_finding(
                f"{len(matches)} similes or “as if” comparisons ({per_1000:.0f} per 1,000 narration words). "
                "Dense comparison makes prose feel decorated rather than observed.",
                "Keep the freshest one or two; describe the other things directly.",
                title="Many similes",
                severity="medium",
            )
        ]
        for m in matches:
            sent = doc.sentence_at(m.start())
            if sent:
                results.append(
                    self.finding(
                        doc,
                        m.start(),
                        min(sent.end, m.end() + 40),
                        "One of many comparisons in this passage.",
                        "Is this comparison doing work a plain description couldn't?",
                        title="Simile",
                        severity="low",
                    )
                )
        return results


_ABSTRACT_NOUNS = set(
    """
    grief sorrow hope fear love longing despair truth silence darkness memory memories emotion
    emotions feeling feelings presence absence essence eternity infinity existence fate destiny soul
    spirit regret desire guilt shame doubt peace chaos weight gravity loss pain joy beauty meaning
    purpose possibility possibilities uncertainty vulnerability resilience strength courage freedom
    belonging connection understanding warmth solace comfort nostalgia melancholy serenity tranquility
    intimacy tenderness intensity finality clarity sincerity desperation determination resignation
    anticipation realization recognition frustration hesitation devotion isolation contentment
    resentment bewilderment astonishment torment abandonment fulfillment acknowledgment reverence
    defiance innocence transcendence significance ambivalence acceptance surrender permanence
    impermanence humanity reality longing yearning anguish agony ecstasy bliss wonder awe dread
    forgiveness redemption salvation betrayal trust promise promises secrets
    """.split()
)
_NESS = re.compile(r"[a-z]{3,}ness(?:es)?$")


def _is_abstract(word: str) -> bool:
    w = word.lower()
    return w in _ABSTRACT_NOUNS or bool(_NESS.match(w))


@register
class Abstraction(Rule):
    id = "abstraction"
    name = "Abstraction overload"
    category = "purple"
    description = "Sentences stacked with abstract nouns (grief, silence, weight, longing) instead of concrete detail."
    has_sensitivity = True
    sensitivity_help = "Abstract nouns per sentence before flagging (low: 4, medium: 3, high: 2)."

    def check(self, doc: Document, ctx: RuleContext):
        need = ctx.pick(4, 3, 2)
        results = []
        for s in doc.narration_sentences:
            if s.word_count < 6:
                continue
            marks = [span for span, w in zip(s.word_spans, s.words) if _is_abstract(w)]
            if len(marks) >= need:
                listed = ", ".join(doc.text[a:b].lower() for a, b in marks)
                results.append(
                    self.finding(
                        doc,
                        s.start,
                        s.end,
                        f"{len(marks)} abstract nouns in one sentence ({listed}). Abstraction tells the reader "
                        "how to feel instead of giving them something to see, hear or touch.",
                        "Swap at least one abstraction for a concrete object, action, or sensory detail.",
                        severity="medium" if len(marks) >= need + 1 else "low",
                        marks=marks,
                    )
                )
        return results


@register
class Intensifiers(PatternRule):
    id = "intensifiers"
    name = "Inflated intensifiers"
    category = "purple"
    description = "Overwrought adverbs: impossibly, achingly, unbearably, devastatingly…"
    scope = "narration"
    severity = "low"
    message = "An inflated intensifier. These push the reader to feel something the sentence hasn't earned."
    suggestion = "Cut the adverb and let a sharper noun or verb carry the intensity."
    patterns = (
        Pattern(
            r"\b(?:impossibly|achingly|unbearably|exquisitely|devastatingly|hauntingly|breathtakingly|"
            r"infinitely|unspeakably|indescribably|inexplicably|inexorably|endlessly|piercingly|"
            r"impossibly|agonizingly|agonisingly|excruciatingly|profoundly|utterly|incredibly)\s+[a-z]+"
        ),
    )


_LY_EXCEPTIONS = set(
    """
    only early family reply holy lonely likely ugly silly friendly lovely daily belly jelly rally
    fly july italy lily sally emily billy molly holly kelly ally apply supply comply bully curly
    oily wily surly burly elderly costly deadly lively orderly chilly hilly smelly woolly gully
    """.split()
)


@register
class AdverbDensity(Rule):
    id = "adverb_density"
    name = "Adverb clusters"
    category = "purple"
    description = "Sentences carrying several -ly adverbs."
    has_sensitivity = True
    sensitivity_help = "-ly adverbs per sentence before flagging (low: 4, medium: 3, high: 2)."

    def check(self, doc: Document, ctx: RuleContext):
        need = ctx.pick(4, 3, 2)
        results = []
        for s in doc.narration_sentences:
            marks = [
                span for span, w in zip(s.word_spans, s.words)
                if w.lower().endswith("ly") and len(w) > 4 and w.lower() not in _LY_EXCEPTIONS
            ]
            if len(marks) >= need:
                results.append(
                    self.finding(
                        doc,
                        s.start,
                        s.end,
                        f"{len(marks)} -ly adverbs in one sentence. Stacked adverbs usually prop up weak verbs.",
                        "Choose verbs that already contain the manner (“crept” instead of “walked quietly”).",
                        severity="low",
                        marks=marks,
                    )
                )
        return results


@register
class Melodrama(PatternRule):
    id = "melodrama"
    name = "Melodrama"
    category = "purple"
    description = "Overblown emotional language: hearts shattering, screams tearing from throats, “nothing would ever be the same”."
    message = "Melodramatic phrasing: the language is louder than the moment, so the reader stops trusting it."
    suggestion = "Undercut it: a small, specific physical detail is usually more devastating than a big declaration."
    patterns = (
        Pattern(r"\b{PRON}\s+(?:heart|world)\s+(?:shattered|crumbled|exploded|imploded|collapsed|broke\s+into\s+(?:a\s+)?(?:million|thousand)\s+pieces)\b"),
        Pattern(r"\b(?:shattered|broke|splintered)\s+into\s+(?:a\s+)?(?:million|thousand)\s+(?:pieces|shards|fragments)\b"),
        Pattern(r"\b(?:a\s+)?(?:scream|sob|cry|wail|howl)\s+(?:tore|ripped|wrenched|clawed)\s+(?:from|out\s+of|its\s+way|through)\b"),
        Pattern(r"\btears\s+(?:streamed|poured|cascaded)\s+down\s+{PRON}\s+(?:face|cheeks)\b"),
        Pattern(r"\b(?:nothing|things|life)\s+would\s+(?:ever\s+)?(?:never\s+)?be\s+the\s+same\b"),
        Pattern(r"\b(?:forever|irrevocably|irreversibly)\s+(?:changed|altered|broken|shattered)\b"),
        Pattern(r"\bthe\s+(?:most\s+[\w'’-]+|[\w'’-]+est)\s+(?:thing\s+)?(?:she|he|they|i)\s+had\s+ever\s+(?:seen|felt|known|heard|experienced)\b"),
        Pattern(r"\b(?:she|he|they|i)\s+had\s+never\s+(?:felt|been)\s+so\s+(?:alive|alone|afraid|happy|broken|lost|helpless)\b"),
        Pattern(r"\bthe\s+pain\s+was\s+(?:unbearable|excruciating|overwhelming|indescribable)\b"),
        Pattern(r"\bfor\s+what\s+(?:felt|seemed)\s+like\s+(?:an\s+)?(?:eternity|forever|hours)\b"),
        Pattern(r"\bwith\s+every\s+(?:ounce|fib(?:er|re))\s+of\b"),
        Pattern(r"\b(?:soul|heart)-?(?:crushing|shattering|wrenching|rending|stopping)\b"),
        Pattern(r"\b(?:primal|guttural|anguished|blood-?curdling)\s+(?:scream|cry|howl|sob|wail)\b"),
        Pattern(r"\b(?:sank|fell|dropped|collapsed)\s+to\s+{PRON}\s+knees\b", severity="low"),
        Pattern(r"\b(?:screamed|cried|howled|wailed)\s+(?:up\s+)?(?:to|at)\s+the\s+(?:sky|heavens|night)\b"),
        Pattern(r"\bthe\s+world\s+(?:stopped|stood\s+still|ceased\s+to\s+exist)\b"),
        Pattern(r"\bin\s+that\s+(?:moment|instant),?\s+everything\s+changed\b"),
    )


_QUALIFIERS = re.compile(
    r"\b(?:almost|somehow|slightly|somewhat|a\s+little|a\s+bit|seemed\s+to|appeared\s+to|kind\s+of|"
    r"sort\s+of|rather|faintly|vaguely|nearly|barely|just\s+enough|something\s+like)\b",
    re.IGNORECASE,
)


@register
class QualifierStacking(Rule):
    id = "qualifier_stacking"
    name = "Hedged description"
    category = "purple"
    description = "Sentences softened by several qualifiers (“almost”, “somehow”, “a little”, “seemed to”)."
    has_sensitivity = True
    sensitivity_help = "Qualifiers per sentence before flagging (low: 4, medium: 3, high: 2)."

    def check(self, doc: Document, ctx: RuleContext):
        need = ctx.pick(4, 3, 2)
        results = []
        for s in doc.narration_sentences:
            marks = [(s.start + m.start(), s.start + m.end()) for m in _QUALIFIERS.finditer(s.text)]
            if len(marks) >= need:
                results.append(
                    self.finding(
                        doc,
                        s.start,
                        s.end,
                        f"{len(marks)} qualifiers in one sentence. Hedging (“almost”, “somehow”, “seemed to”) "
                        "makes description vague; AI prose hedges to avoid committing.",
                        "Commit: say what happened, or pick one qualifier that matters.",
                        severity="low",
                        marks=marks,
                    )
                )
        return results
