"""Punctuation habits: dash and ellipsis density, dramatic fragments."""

from __future__ import annotations

import re

from ..text import Document, Sentence
from .base import Rule, RuleContext, register

# Em dashes, spaced en dashes and double hyphens used as dashes.
_DASH = re.compile(r"—|(?<=\s)–(?=\s)|(?<=[\w\s])--(?=[\w\s])")
_INTERRUPTION_AFTER = re.compile(r"[\"”’']")
_ELLIPSIS = re.compile(r"\.\s?\.\s?\.|…")

# Common finite verbs (mostly irregular past tense) for the fragment heuristic.
_FINITE_VERBS = set(
    """
    am is are was were be been has have had do does did go goes went come comes came get gets got
    make makes made take takes took see sees saw know knows knew think thinks thought say says said
    tell tells told feel feels felt leave leaves left stand stands stood sit sits sat run runs ran
    hold holds held keep keeps kept give gives gave find finds found fall falls fell rise rises rose
    shake shakes shook break breaks broke speak speaks spoke begin begins began bring brings brought
    buy bought catch caught choose chose draw drew drink drank drive drove eat ate fight fought fly
    flew forget forgot freeze froze grow grew hang hung hear hears heard hide hid hit hurt lay laid
    lead led lie lay lose lost meet met pay paid put read ride rode ring rang seek sought sell sold
    send sent set shine shone shoot shot shut sing sang sink sank sleep slept slide slid sling slung
    spend spent spin spun spit spat split spread spring sprang steal stole stick stuck sting stung
    stride strode strike struck swear swore sweep swept swim swam swing swung teach taught tear tore
    throw threw wake woke wear wore weep wept win won wind wound write wrote can could will would
    shall should may might must let lets dies died lies lied cries cried tries tried
    """.split()
)
_SUBJECTS = {"i", "you", "he", "she", "it", "we", "they", "this", "that", "there", "who", "nobody", "everyone", "someone"}
_PERSONAL_SUBJECTS = {"i", "you", "he", "she", "we", "they"}
_DETERMINERS = {"the", "a", "an", "his", "her", "their", "my", "your", "our", "its", "this", "that"}
_NOT_SUBJECTS = {"the", "a", "an", "not", "no", "so", "too", "very", "just", "then", "and", "but", "or", "almost", "still"}


def looks_like_fragment(sentence: Sentence, names: set[str]) -> bool:
    """Short narration sentences without an apparent subject + verb ("Silence." "Not yet.")."""
    words = sentence.words
    if not words or len(words) > 5 or sentence.text.rstrip("\"”’' ").endswith("?"):
        return False
    if len(words) == 1:
        return True
    lower = [w.lower() for w in words]
    if any(w in _FINITE_VERBS for w in lower):
        return False
    for i in range(1, len(lower)):
        word, prev = lower[i], lower[i - 1]
        if prev in _PERSONAL_SUBJECTS:
            return False  # "I call Reyes." "She runs."
        named_or_pronoun = prev in _SUBJECTS or words[i - 1] in names
        noun_like = not prev.endswith("ly") and prev not in _NOT_SUBJECTS
        if word.endswith("ed") and (named_or_pronoun or noun_like):
            return False  # "The door opened."
        if word.endswith("s") and not word.endswith(("ss", "us")):
            if named_or_pronoun or (i >= 2 and lower[i - 2] in _DETERMINERS):
                return False  # "Tom waits." "The radiator knocks."
    return True


def _density_rule_findings(rule, doc, ctx, spans, label, thresholds, per_word_note):
    if not doc.word_count or not spans:
        return []
    per_1000 = len(spans) / doc.word_count * 1000
    if len(spans) < 3 or per_1000 < ctx.pick(*thresholds):
        return []
    results = [
        rule.doc_finding(
            f"{len(spans)} {label} ({per_1000:.0f} per 1,000 words). {per_word_note}",
            "Keep the ones doing real work (an interruption, a sharp turn) and replace the rest with commas, "
            "full stops, or restructured sentences.",
            title=f"Heavy {label}",
            severity="medium",
            note="Some writers use this deliberately as a signature; if that's you, lower the sensitivity.",
        )
    ]
    by_sentence: dict[int, list[tuple[int, int]]] = {}
    for s, e in spans:
        sent = doc.sentence_at(s)
        if sent:
            by_sentence.setdefault(sent.index, []).append((s, e))
    for idx, marks in by_sentence.items():
        sent = doc.sentences[idx]
        results.append(
            rule.finding(
                doc,
                sent.start,
                sent.end,
                f"{len(marks)} of the passage's {len(spans)} {label} {'is' if len(marks) == 1 else 'are'} in this sentence.",
                "Could a comma, a full stop, or a restructure do the same job?",
                title=f"{label.capitalize()} here",
                severity="medium" if len(marks) >= 2 else "low",
                marks=marks,
            )
        )
    return results


@register
class EmDashes(Rule):
    id = "em_dashes"
    name = "Em-dash density"
    category = "punctuation"
    description = "Frequent em dashes (—). Interrupted speech (“I just—”) is not counted."
    has_sensitivity = True
    sensitivity_help = "Dashes per 1,000 words before flagging (low: 12, medium: 7, high: 4)."

    def check(self, doc: Document, ctx: RuleContext):
        spans = []
        for m in _DASH.finditer(doc.text):
            after = doc.text[m.end() : m.end() + 1]
            if _INTERRUPTION_AFTER.match(after):
                continue  # interrupted speech: '—"'
            spans.append(m.span())
        return _density_rule_findings(
            self,
            doc,
            ctx,
            spans,
            "em dashes",
            (12, 7, 4),
            "Heavy dash use is one of the most recognisable AI habits; much published fiction uses far fewer.",
        )


@register
class Ellipses(Rule):
    id = "ellipses"
    name = "Ellipsis density"
    category = "punctuation"
    description = "Frequent ellipses (… or ...)."
    has_sensitivity = True
    sensitivity_help = "Ellipses per 1,000 words before flagging (low: 8, medium: 5, high: 3)."

    def check(self, doc: Document, ctx: RuleContext):
        spans = [m.span() for m in _ELLIPSIS.finditer(doc.text)]
        return _density_rule_findings(
            self,
            doc,
            ctx,
            spans,
            "ellipses",
            (8, 5, 3),
            "Frequent trailing-off makes characters sound breathy and the prose hesitant.",
        )


@register
class DramaticFragments(Rule):
    id = "dramatic_fragments"
    name = "Dramatic fragments"
    category = "punctuation"
    description = "Clipped narration fragments for effect (“Silence.” “Then nothing.”) and runs of them."
    has_sensitivity = True
    sensitivity_help = "Fragments per 1,000 words before each is flagged (low: 10, medium: 6, high: 3). Runs of three or more short sentences are always checked."

    def check(self, doc: Document, ctx: RuleContext):
        results = []
        narration = [s for s in doc.sentences if s.is_narration]
        fragments = [s for s in narration if looks_like_fragment(s, doc.names)]
        if doc.word_count:
            per_1000 = len(fragments) / doc.word_count * 1000
            if len(fragments) >= ctx.pick(4, 3, 2) and per_1000 >= ctx.pick(10, 6, 3):
                for s in fragments:
                    results.append(
                        self.finding(
                            doc,
                            s.start,
                            s.end,
                            f"A dramatic sentence fragment ({len(fragments)} in this passage). Fragments hit hard "
                            "when rare; used constantly they become a tic that signals “this is important”.",
                            "Keep fragments for genuine shocks; attach the others to the sentence before or after.",
                            title="Dramatic fragment",
                            severity="low",
                        )
                    )
        run: list[Sentence] = []
        for s in doc.sentences + [None]:
            if s is not None and s.is_narration and 0 < s.word_count <= 4 and (not run or s.paragraph == run[-1].paragraph):
                run.append(s)
                continue
            if len(run) >= 3 and sum(looks_like_fragment(x, doc.names) for x in run) >= 2:
                results.append(
                    self.finding(
                        doc,
                        run[0].start,
                        run[-1].end,
                        f"{len(run)} clipped sentences in a row, mostly fragments. Staccato runs read as manufactured tension when overused.",
                        "Vary it: combine two of them, or let one breathe into a longer sentence.",
                        title="Staccato run",
                        severity="medium",
                        note="Could be deliberate in a fast action beat.",
                    )
                )
            run = [s] if s is not None and s.is_narration and 0 < s.word_count <= 4 else []
        return results
