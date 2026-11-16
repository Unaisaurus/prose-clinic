"""Formulaic constructions: rhetorical templates AI prose reaches for."""

from __future__ import annotations

import re

from ..text import Document
from .base import Pattern, PatternRule, Rule, RuleContext, register

# A clause after "but" that starts with a pronoun is ordinary contrast
# ("I didn't know, but I guessed"), not the "not X, but Y" template.
_NEW_CLAUSE = r"(?!(?:i|you|he|she|it|we|they|there|that|this|nobody|someone|everyone|somebody|everybody)\b)"
_NOT = r"(?:\bnot|n['’]t)"
_ITEM = r"[^.!?;:\n—–,]{1,45}?"
# "was not", "isn't", "felt not"...: the copular form typical of the rhetorical template.
_NOT_COPULA = (
    r"(?:\b(?:was|is|were|are|be|been|felt|feels|seemed|seems|sounded|looked)\s+not"
    r"|\b(?:wasn|isn|weren|aren)['’]t|\b(?:it|that|this)['’]s\s+not)"
)


@register
class NotXButY(PatternRule):
    id = "not_x_but_y"
    name = "“Not X, but Y”"
    category = "formulaic"
    description = "Corrective framings such as “not X, but Y” and “not X, not Y, but Z”."
    message = (
        "A “not X, but Y” framing: the sentence sets up something only to knock it down. "
        "Used sparingly it clarifies; AI prose uses it constantly to sound insightful."
    )
    suggestion = "State Y directly, or show it. Ask whether the reader actually expected X."
    patterns = (
        Pattern(
            rf"{_NOT}\s+(?:just\s+|only\s+|merely\s+|simply\s+|because\s+|about\s+)?{_ITEM},\s*(?:and\s+)?"
            rf"not\s+(?:just\s+|only\s+|because\s+|about\s+)?{_ITEM},?\s*(?:but|only|just)\s+{_NEW_CLAUSE}",
            title="“Not X, not Y, but Z”",
            message=(
                "A triple “not X, not Y, but Z” build-up, one of the most recognisable AI rhetorical "
                "templates. It delays the point and signals profundity instead of earning it."
            ),
            severity="high",
        ),
        Pattern(
            rf"{_NOT_COPULA}\s+(?:merely\s+|simply\s+|just\s+|only\s+)?{_ITEM}\s*[,—–]\s*but\s+(?:rather\s+|instead\s+)?{_NEW_CLAUSE}",
        ),
        Pattern(
            rf"\bnot\s+(?:because|about|with|for|in|from|by|out\s+of|to)\b{_ITEM}\s*[,—–]\s*but\s+(?:rather\s+)?{_NEW_CLAUSE}",
        ),
        Pattern(
            rf"{_NOT_COPULA}\s+(?:\w+\s+){{0,3}}\w+\s+but\s+(?:rather\s+)?{_NEW_CLAUSE}(?=\w)",
            severity="low",
        ),
        Pattern(
            r"\bnot\s+(?:just|only|merely|simply)\b[^.!?;\n]{1,60}?,?\s*but\s+(?:also\s+)?",
            title="“Not just X, but Y”",
            message=(
                "“Not just X, but Y” is standard English, but AI prose leans on it to inflate small "
                "observations (“not just a house, but a home”)."
            ),
            severity="low",
        ),
    )


_SUBJECT = r"(?P<subj>it|this|that|he|she|they|i|we|you|[A-Z][a-z]+)"
_NEG_FORMS = (
    r"(?:\s+(?:was\s+not|wasn['’]t|is\s+not|isn['’]t|were\s+not|weren['’]t|are\s+not|aren['’]t|"
    r"am\s+not|had\s+not|hadn['’]t)|['’]s\s+not|['’]re\s+not|['’]m\s+not)\b"
)
_POS_FORMS = r"(?:\s+(?:was|is|were|are|am|had)|['’]s|['’]re|['’]m)\b"
_DIDNT = r"\s+(?:didn['’]t|did\s+not|doesn['’]t|does\s+not|couldn['’]t|could\s+not|wouldn['’]t|would\s+not)\b"
_FIRST = re.compile(r"^[\"“‘']?" + _SUBJECT + _NEG_FORMS, re.IGNORECASE)
_SECOND_TEMPLATE = r"^[\"“‘']?(?P<subj>{subj})" + _POS_FORMS + r"(?!\s+not\b|\s+never\b)"
_SECOND = re.compile(_SECOND_TEMPLATE.format(subj=r"[A-Za-z]+"), re.IGNORECASE)
_FIRST_DIDNT = re.compile(r"^[\"“‘']?" + _SUBJECT + _DIDNT, re.IGNORECASE)
_INLINE = re.compile(
    r"\b(?:it|this|that|he|she|they)" + _NEG_FORMS + r"[^.!?;\n]{1,60}?[;,—–]\s*(?:it|this|that|he|she|they)"
    + _POS_FORMS + r"(?!\s+not\b)",
    re.IGNORECASE,
)
_DEMONSTRATIVES = {"it", "this", "that"}


def _same_subject(a: str, b: str) -> bool:
    a, b = a.lower(), b.lower()
    return a == b or (a in _DEMONSTRATIVES and b in _DEMONSTRATIVES)


@register
class NegationReveal(Rule):
    id = "negation_reveal"
    name = "“It wasn't X. It was Y.”"
    category = "formulaic"
    description = "The negate-then-reveal pattern: “It wasn't anger. It was grief.” / “He didn't shout. He whispered.”"

    def check(self, doc: Document, ctx: RuleContext):
        results = []
        sents = doc.sentences
        for a, b in zip(sents, sents[1:]):
            if a.paragraph != b.paragraph or a.word_count > 16:
                continue
            m1 = _FIRST.match(a.text)
            if m1:
                second = _SECOND.match(b.text)
                if second and _same_subject(m1.group("subj"), second.group("subj")):
                    results.append(
                        self.finding(
                            doc,
                            a.start,
                            b.end,
                            "Negate-then-reveal: the first sentence denies something so the second can "
                            "“correct” it. A signature AI move; it reads as a magic trick the reader can see coming.",
                            "Lead with what it actually was, and let the contrast emerge from the scene if it matters.",
                            severity="high",
                        )
                    )
                continue
            m2 = _FIRST_DIDNT.match(a.text)
            if m2 and a.word_count <= 6 and b.word_count <= 8:
                second = re.compile(r"^[\"“‘']?(?P<subj>[A-Za-z]+)\b", re.IGNORECASE).match(b.text)
                if second and _same_subject(m2.group("subj"), second.group("subj")) and not _FIRST_DIDNT.match(b.text):
                    results.append(
                        self.finding(
                            doc,
                            a.start,
                            b.end,
                            "“She didn't X. She Y.”: a staccato denial followed by the real action. "
                            "Effective once; as a habit it becomes a tic.",
                            "Consider simply narrating what the character did.",
                            title="“She didn't X. She Y.”",
                            severity="low",
                            note="Could be deliberate if the expected action matters to the reader.",
                        )
                    )
        flagged = [(f.start, f.end) for f in results]
        for m in _INLINE.finditer(doc.text):
            if any(s <= m.start() < e for s, e in flagged):
                continue
            results.append(
                self.finding(
                    doc,
                    m.start(),
                    m.end(),
                    "Negate-then-reveal inside one sentence (“It wasn't fear—it was relief”).",
                    "Say what it was. If the contrast matters, dramatise it rather than announce it.",
                    severity="high",
                )
            )
        return results


@register
class NotFragmentChain(Rule):
    id = "not_fragment_chain"
    name = "“Not X. Not Y. Just Z.”"
    category = "formulaic"
    description = "Chains of clipped “Not…”/“No…” fragments resolved by “But/Just/Only…”."

    _NEG_START = re.compile(r"^[\"“‘']?(?:not|no|never|nothing)\b", re.IGNORECASE)
    _RESOLVE = re.compile(r"^[\"“‘']?(?:but|just|only|simply|instead|something|still)\b", re.IGNORECASE)

    def check(self, doc: Document, ctx: RuleContext):
        results = []
        sents = doc.sentences
        i = 0
        while i < len(sents):
            run = []
            j = i
            while (
                j < len(sents)
                and sents[j].word_count <= 6
                and self._NEG_START.match(sents[j].text)
                and (not run or sents[j].paragraph == run[-1].paragraph)
            ):
                run.append(sents[j])
                j += 1
            resolved = (
                j < len(sents)
                and run
                and sents[j].paragraph == run[-1].paragraph
                and sents[j].word_count <= 8
                and self._RESOLVE.match(sents[j].text)
            )
            if len(run) >= 2 or (len(run) == 1 and resolved and run[0].word_count <= 4):
                end = sents[j].end if resolved else run[-1].end
                severity = "high" if len(run) >= 2 and resolved else "medium"
                results.append(
                    self.finding(
                        doc,
                        run[0].start,
                        end,
                        "A chain of clipped negations (“Not X. Not Y. But Z.”). It mimics dramatic restraint "
                        "but follows a template readers increasingly recognise as AI.",
                        "Name the thing once, precisely. If the hesitation matters, show it through the character.",
                        severity=severity,
                    )
                )
                i = j + (1 if resolved else 0)
            else:
                i += 1
        return results


@register
class KindOfXThat(PatternRule):
    id = "kind_of_x_that"
    name = "“The kind of X that…”"
    category = "formulaic"
    description = "“It was the kind of silence that…”: generic categorising in place of a specific detail."
    has_sensitivity = True
    sensitivity_help = "How many uses before it is flagged (low: 3, medium: 2, high: 1)."
    min_matches = (3, 2, 1)
    message = (
        "“The kind of X that…” describes a category instead of the thing itself. AI prose uses it "
        "to sound observant."
    )
    suggestion = "Describe this particular silence/man/smile directly, with one concrete detail."
    severity = "low"
    patterns = (
        Pattern(r"\b(?:the|a)\s+(?:kind|sort|type)\s+of\s+(?:[\w'’-]+\s+){1,3}?(?:that|which|where|you|who)\b"),
    )


@register
class ParadoxPairs(PatternRule):
    id = "paradox_pairs"
    name = "Paradox pairs (“both X and Y”)"
    category = "formulaic"
    description = "“Both a warning and a promise”, “half plea, half prayer”, “less a question than an accusation”."
    message = (
        "A neat paradox pair. It sounds profound but often hedges: the writing describes two things "
        "instead of committing to one precise observation."
    )
    suggestion = "Pick the truer of the two, or replace both with the concrete detail that suggested them."
    patterns = (
        Pattern(r"\bboth\s+(?:a|an)\s+[\w'’-]+(?:\s+[\w'’-]+)?\s+and\s+(?:a|an)\s+[\w'’-]+"),
        Pattern(r"\bhalf[\s-][\w'’-]+,\s*half[\s-][\w'’-]+"),
        Pattern(r"\bequal\s+parts\s+[\w'’-]+(?:\s+[\w'’-]+)?\s+and\s+[\w'’-]+"),
        Pattern(r"\bsomewhere\s+between\s+(?:a\s+|an\s+)?[\w'’-]+(?:\s+[\w'’-]+)?\s+and\s+(?:a\s+|an\s+)?[\w'’-]+"),
        Pattern(r"\bpart\s+[\w'’-]+,\s*part\s+[\w'’-]+"),
        Pattern(r"\bless\s+(?:of\s+)?(?:a|an)\s+[\w'’-]+(?:\s+[\w'’-]+)?\s+than\s+(?:a|an)\s+[\w'’-]+"),
        Pattern(r"\bmore\s+(?:of\s+)?(?:a|an)\s+[\w'’-]+\s+than\s+(?:a|an)\s+[\w'’-]+", severity="low"),
    )


@register
class RhetoricalQuestions(Rule):
    id = "rhetorical_questions"
    name = "Rhetorical question cascades"
    category = "formulaic"
    description = "Several questions in a row in the narration (“What did it mean? Was she wrong?”)."
    has_sensitivity = True
    sensitivity_help = "Questions in a row before flagging (low: 4, medium: 3, high: 2)."

    def check(self, doc: Document, ctx: RuleContext):
        need = ctx.pick(4, 3, 2)
        results = []
        run = []
        for s in doc.sentences + [None]:
            if s is not None and s.is_narration and s.text.rstrip("\"”’' ").endswith("?"):
                run.append(s)
                continue
            if len(run) >= need:
                results.append(
                    self.finding(
                        doc,
                        run[0].start,
                        run[-1].end,
                        f"{len(run)} rhetorical questions in a row in the narration. AI prose often "
                        "simulates introspection this way; the questions tell the reader what to wonder.",
                        "Keep the one question that matters, or let the character act on the doubt instead.",
                        severity="medium" if len(run) >= 3 else "low",
                    )
                )
            run = []
        return results


@register
class Tricolons(Rule):
    id = "tricolons"
    name = "Rule-of-three lists"
    category = "formulaic"
    description = "Frequent triplets (“tired, broken, and alone”; “—sharp, sudden, almost painful”)."
    has_sensitivity = True
    sensitivity_help = "Triplets per 1,000 words before flagging (low: 9, medium: 6, high: 4)."

    _SYNDETIC = re.compile(r"\b[\w'’-]+(?:\s[\w'’-]+)?,\s+[\w'’-]+(?:\s[\w'’-]+)?,\s+(?:and|or)\s+[\w'’-]+(?:\s[\w'’-]+)?\b")
    _ASYNDETIC = re.compile(r"(?<=[—,:])\s*[\w'’-]+(?:\s[\w'’-]+)?,\s+[\w'’-]+(?:\s[\w'’-]+)?,\s+[\w'’-]+(?:\s[\w'’-]+)?(?=[.!?])")

    # Items starting with these are clauses ("he said, and laughed, and I laughed"), not list items.
    _CLAUSE_STARTS = {"i", "you", "he", "she", "it", "we", "they", "then", "so", "said", "asked", "there"}

    def _is_list(self, match: re.Match) -> bool:
        items = re.split(r",\s+(?:and\s+|or\s+)?", match.group().strip(" ,—:"))
        return len(items) == 3 and not any(item.split()[0].lower() in self._CLAUSE_STARTS for item in items if item.split())

    def check(self, doc: Document, ctx: RuleContext):
        spans = []
        for regex in (self._SYNDETIC, self._ASYNDETIC):
            for m in regex.finditer(doc.text):
                s, e = m.span()
                s += len(m.group()) - len(m.group().lstrip())
                if not self._is_list(m) or doc.in_dialogue(s, e) or any(a < e and s < b for a, b in spans):
                    continue
                spans.append((s, e))
        if not doc.word_count:
            return []
        per_1000 = len(spans) / doc.word_count * 1000
        if len(spans) < 3 or per_1000 < ctx.pick(9, 6, 4):
            return []
        spans.sort()
        return [
            self.finding(
                doc,
                s,
                e,
                f"A list of three. Triplets give prose a satisfying rhythm, which is why AI uses them "
                f"constantly ({len(spans)} here, {per_1000:.0f} per 1,000 words).",
                "Vary the count: one precise item, a pair, or a longer, messier list.",
                severity="low",
            )
            for s, e in spans
        ]


@register
class ReversalTags(Rule):
    id = "reversal_tags"
    name = "Reversal tags (“Except it wasn't.”)"
    category = "formulaic"
    description = "Short twist sentences: “Except it wasn't.”, “Or so she thought.”, “Little did she know.”"

    _PATTERNS = [
        re.compile(
            r"^[\"“‘']?(?:except|only|but|until)\s+(?:it|he|she|they|this|that|i|you|we)\s+(?:wasn['’]t|weren['’]t|"
            r"didn['’]t|isn['’]t|doesn['’]t|couldn['’]t|hadn['’]t|wouldn['’]t|won['’]t)[.!]",
            re.IGNORECASE,
        ),
        re.compile(
            r"^[\"“‘']?or\s+so\s+(?:she|he|they|i|we)\s+(?:thought|believed|hoped|told\s+(?:herself|himself|themselves|myself))",
            re.IGNORECASE,
        ),
        re.compile(r"^[\"“‘']?until\s+(?:now|today|tonight)[.!]", re.IGNORECASE),
        re.compile(r"^[\"“‘']?and\s+yet[.!]", re.IGNORECASE),
        re.compile(r"\blittle\s+did\s+(?:she|he|they|i|we)\s+know\b", re.IGNORECASE),
    ]

    def check(self, doc: Document, ctx: RuleContext):
        results = []
        for s in doc.sentences:
            for regex in self._PATTERNS:
                m = regex.search(s.text)
                if m:
                    start = s.start + m.start()
                    results.append(
                        self.finding(
                            doc,
                            start,
                            s.end,
                            "A stock twist-tag sentence. It announces a reversal instead of letting events deliver it.",
                            "Cut it and let the next beat reveal the surprise, or make the reversal specific.",
                        )
                    )
                    break
        return results
