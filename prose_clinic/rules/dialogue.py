"""Dialogue: therapy-speak, agreeable or polished speech, forced wit, voice sameness."""

from __future__ import annotations

import re
import statistics

from ..text import WORD_RE, Document, split_sentences
from .base import Pattern, PatternRule, Rule, RuleContext, register


@register
class TherapySpeak(PatternRule):
    id = "therapy_speak"
    name = "Therapy-speak in dialogue"
    category = "dialogue"
    description = "Characters talking like a counsellor or self-help book (“your feelings are valid”, “I'm here for you”)."
    scope = "dialogue"
    message = (
        "Therapeutic language in dialogue. Unless this character would talk this way, people under "
        "pressure are rarely this articulate or emotionally literate. It's a strong AI tell."
    )
    suggestion = "What would this person actually say: deflect, joke, get practical, say the wrong thing?"
    patterns = (
        Pattern(r"\bI\s+hear\s+you\b"),
        Pattern(r"\b(?:your|those|these|my)\s+feelings\s+are\s+valid\b", severity="high"),
        Pattern(r"\bthat{APOS}s\s+(?:so\s+|totally\s+|completely\s+)?valid\b"),
        Pattern(r"\bhold(?:ing)?\s+space\b", severity="high"),
        Pattern(r"\bsafe\s+space\b"),
        Pattern(r"\b(?:set|setting|respect|need|have|my|your)\s+(?:\w+\s+)?boundar(?:y|ies)\b"),
        Pattern(r"\bit{APOS}s\s+okay\s+(?:to\s+(?:feel|be|not|cry|grieve)|not\s+to\s+be)\b"),
        Pattern(r"\byou{APOS}re\s+allowed\s+to\s+(?:feel|be|grieve|cry|want)\b"),
        Pattern(r"\bthat\s+must\s+(?:have\s+been|be)\s+(?:so\s+|really\s+|incredibly\s+)?(?:hard|difficult|painful)\b"),
        Pattern(r"\bI{APOS}m\s+(?:so\s+)?proud\s+of\s+you\s+for\b"),
        Pattern(r"\byou\s+don{APOS}t\s+have\s+to\s+(?:carry|do|face|go\s+through|bear)\s+(?:this|it|that)\s+alone\b", severity="high"),
        Pattern(r"\bI{APOS}m\s+(?:always\s+)?here\s+for\s+you\b"),
        Pattern(r"\bprocess(?:ing)?\s+(?:this|that|it|everything|my\s+feelings|your\s+feelings|what\s+happened)\b"),
        Pattern(r"\bunpack(?:ing)?\s+(?:this|that|it)\b"),
        Pattern(r"\bthank\s+you\s+for\s+(?:sharing|telling\s+me|being\s+(?:honest|vulnerable)|trusting\s+me)\b"),
        Pattern(r"\bI\s+appreciate\s+you\s+(?:telling|sharing|saying|being)\b"),
        Pattern(r"\bwhat\s+I{APOS}m\s+hearing\s+is\b", severity="high"),
        Pattern(r"\bI\s+want\s+to\s+acknowledge\b"),
        Pattern(r"\bI\s+need\s+you\s+to\s+(?:understand|know|hear)\b", severity="low"),
        Pattern(r"\bwe{APOS}ll\s+(?:get\s+through|figure)\s+(?:this|it)\s+(?:out\s+)?together\b"),
        Pattern(r"\byou\s+(?:matter|deserve\s+(?:better|to\s+be\s+happy|happiness|to\s+heal))\b"),
        Pattern(r"\blet\s+(?:yourself|myself)\s+(?:feel|grieve)\b"),
        Pattern(r"\bsit\s+with\s+(?:that|this|it|the\s+feeling)\b"),
        Pattern(r"\b(?:healing|trauma|toxic|gaslighting|gaslit|triggered|self-care|closure|emotional\s+labou?r|emotionally\s+(?:available|unavailable)|my\s+truth|your\s+truth)\b", severity="low"),
        Pattern(r"\b(?:communicat(?:e|ing|ion)|vulnerab(?:le|ility))\b", severity="low"),
    )


@register
class AgreeableDialogue(PatternRule):
    id = "agreeable_dialogue"
    name = "Over-agreeable dialogue"
    category = "dialogue"
    description = "Characters conceding or validating each other too readily (“You're right.”, “That's fair.”). Flagged when they pile up."
    scope = "dialogue"
    has_sensitivity = True
    sensitivity_help = "How many before any are flagged (low: 4, medium: 3, high: 2)."
    min_matches = (4, 3, 2)
    message = (
        "Characters agree, concede or validate each other readily. One “you're right” is fine; several make "
        "conflict evaporate. Real people deflect, dig in, change the subject, or apologise badly."
    )
    suggestion = "Let a character resist, misunderstand, or agree only partly and grudgingly."
    patterns = (
        Pattern(r"\byou{APOS}re\s+(?:absolutely\s+|completely\s+|totally\s+)?right\b"),
        Pattern(r"\bthat{APOS}s\s+(?:fair|a\s+fair\s+point|completely\s+fair|true)\b"),
        Pattern(r"\bfair\s+enough\b"),
        Pattern(r"\bI\s+(?:completely\s+|totally\s+)?understand\b"),
        Pattern(r"\bI\s+couldn{APOS}t\s+agree\s+more\b"),
        Pattern(r"\bthat\s+makes\s+(?:a\s+lot\s+of\s+|total\s+|complete\s+)?sense\b"),
        Pattern(r"\bthank\s+you\s+for\s+understanding\b"),
        Pattern(r"\bI\s+appreciate\s+(?:that|it|you)\b"),
        Pattern(r"\bI{APOS}m\s+sorry,?\s+(?:you{APOS}re\s+right|I\s+shouldn{APOS}t\s+have)\b"),
        Pattern(r"\blet{APOS}s\s+(?:talk\s+about\s+it|work\s+through\s+this|figure\s+this\s+out)\b"),
        Pattern(r"\bgood\s+point\b"),
        Pattern(r"\bI\s+see\s+(?:your\s+point|what\s+you\s+mean|where\s+you{APOS}re\s+coming\s+from)\b"),
        Pattern(r"\bI\s+get\s+it\b"),
        Pattern(r"\bI\s+forgive\s+you\b"),
    )


@register
class Speechifying(PatternRule):
    id = "speechifying"
    name = "Aphorisms & speeches in dialogue"
    category = "dialogue"
    description = "Characters stating the theme or a life lesson (“Maybe that's what love is.”, “The thing about grief is…”)."
    scope = "dialogue"
    message = (
        "A character delivers a polished aphorism or the story's theme. It sounds written, not spoken, "
        "and does the reader's interpreting for them."
    )
    suggestion = "Cut the summary line; let the scene imply the idea, or make the line rougher and more personal."
    patterns = (
        Pattern(r"\b(?:maybe|perhaps)\s+(?:that{APOS}s|that\s+is|this\s+is)\s+(?:what|the\s+point|all|okay|enough)\b"),
        Pattern(r"\bthe\s+(?:thing|truth|problem)\s+(?:about|with)\s+[\w'’-]+\s+is\b"),
        Pattern(r"\bsometimes,?\s+the\s+(?:bravest|hardest|strongest|best|kindest|most\s+[\w'’-]+)\s+thing\b", severity="high"),
        Pattern(r"\bthat{APOS}s\s+what\s+(?:love|family|friendship|courage|home|life|grief)\s+(?:is|means)\b", severity="high"),
        Pattern(r"\b(?:love|grief|life|hope|fear|courage|family|forgiveness)\s+(?:isn{APOS}t|is\s+not)\s+about\b"),
        Pattern(r"\bwe{APOS}re\s+all\s+just\b"),
        Pattern(r"\bwhat\s+matters\s+is\b"),
        Pattern(r"\bthe\s+(?:real|true)\s+[\w'’-]+\s+(?:was|is)\s+(?:the|what)\b"),
    )


@register
class ForcedWit(PatternRule):
    id = "forced_wit"
    name = "Forced wit & banter"
    category = "dialogue"
    description = "Stock quips (“Well, that went well.”, “Note to self…”) and narration that announces humour (“he quipped”, “smirked”). Flagged when they pile up."
    has_sensitivity = True
    sensitivity_help = "How many before any are flagged (low: 4, medium: 3, high: 2)."
    min_matches = (4, 3, 2)
    message = (
        "Stock banter or narration that announces a joke. AI dialogue reaches for the same quips and then "
        "tells you they were funny; it reads as performed rather than genuinely witty."
    )
    suggestion = "Ground humour in this character's specific outlook and situation, and let it land without commentary."
    patterns = (
        Pattern(r"\b(?:well,?\s+)?that\s+went\s+well\b", scope="dialogue"),
        Pattern(r"\bwell,?\s+that\s+happened\b", scope="dialogue"),
        Pattern(r"\bso\s+that{APOS}s\s+a\s+thing\b", scope="dialogue"),
        Pattern(r"\bnote\s+to\s+self\b", scope="dialogue"),
        Pattern(r"\bfamous\s+last\s+words\b", scope="dialogue"),
        Pattern(r"\bI{APOS}ll\s+take\s+that\s+as\s+a\s+(?:yes|no|compliment)\b", scope="dialogue"),
        Pattern(r"\bis\s+that\s+supposed\s+to\s+make\s+me\s+feel\s+better\b", scope="dialogue"),
        Pattern(r"\bsays\s+the\s+(?:guy|girl|man|woman|person|one)\s+who\b", scope="dialogue"),
        Pattern(r"\b(?:not\s+helping|noted|rude|touché|cute)\s*[.!]", scope="dialogue"),
        Pattern(r"\bsaid\s+no\s+one\s+ever\b", scope="dialogue"),
        Pattern(r"\bplot\s+twist\b", scope="dialogue"),
        Pattern(r"\bI{APOS}m\s+going\s+to\s+pretend\s+(?:you\s+didn{APOS}t|I\s+didn{APOS}t)\b", scope="dialogue"),
        Pattern(r"\bremind\s+me\s+(?:never|not)\s+to\b", scope="dialogue"),
        Pattern(r"\bthanks,?\s+I\s+hate\s+it\b", scope="dialogue"),
        Pattern(r"\byou\s+had\s+one\s+job\b", scope="dialogue"),
        Pattern(r"\bin\s+my\s+defen[cs]e\b", scope="dialogue"),
        Pattern(r"\bfor\s+the\s+record\b", scope="dialogue"),
        Pattern(r"\bnice\s+try\b", scope="dialogue"),
        Pattern(r"\b(?:big|bold)\s+words\s+from\b", scope="dialogue"),
        Pattern(r"\b(?:quipped|deadpanned|wisecracked)\b", scope="narration"),
        Pattern(r"\bsaid\s+(?:dryly|wryly|sardonically|teasingly|playfully)\b", scope="narration"),
        Pattern(r"\b(?:a\s+)?wry\s+(?:smile|grin|look)\b", scope="narration"),
        Pattern(r"\b(?:smirked|smirking|smirk)\b", scope="narration", severity="low"),
        Pattern(r"\b(?:amusement|mischief|humou?r)\s+(?:danced|sparkled|glinted|flickered|twinkled)\s+in\s+{PRON}\s+eyes\b", scope="narration"),
        Pattern(r"\beyes\s+(?:sparkling|sparkled|glinting|glinted|twinkling|twinkled|dancing|danced)\s+with\s+(?:amusement|mischief|humou?r|laughter)\b", scope="narration"),
        Pattern(r"\bwith\s+a\s+(?:playful\s+|knowing\s+)?wink\b", scope="narration"),
        Pattern(r"\b{PRON}\s+(?:mouth|lips)\s+quirked\b", scope="narration"),
    )


@register
class AsYouKnow(PatternRule):
    id = "as_you_know"
    name = "“As you know…” exposition"
    category = "dialogue"
    description = "Characters telling each other things they both already know, for the reader's benefit."
    scope = "dialogue"
    message = "“As you know” exposition: characters explain shared history to each other so the reader can overhear it."
    suggestion = "Move the information into narration, or let it surface through conflict (one character gets it wrong)."
    patterns = (
        Pattern(r"\bas\s+(?:you|we\s+both)\s+(?:well\s+)?know\b"),
        Pattern(r"\bas\s+you{APOS}re\s+(?:well\s+)?aware\b"),
        Pattern(r"\bas\s+I\s+(?:told|said\s+to)\s+you\b"),
        Pattern(r"\bremember\s+when\s+(?:we|you)\b", severity="low"),
        Pattern(r"\byou\s+remember\s+(?:how|when|that)\b", severity="low"),
        Pattern(r"\bdon{APOS}t\s+you\s+remember\b", severity="low"),
        Pattern(r"\bas\s+we\s+discussed\b"),
        Pattern(r"\byou\s+know\s+as\s+well\s+as\s+I\s+do\b"),
    )


_TAG_VERBS_PLAIN = {"said", "says", "asked", "asks", "replied", "answered", "told"}
_TAG_FANCY = (
    "hissed|growled|purred|snarled|barked|breathed|chuckled|laughed|sighed|smirked|grinned|smiled|"
    "giggled|snorted|scoffed|huffed|gasped|spat|sneered|croaked|rasped|drawled|crooned|chirped|"
    "quipped|retorted|countered|exclaimed|intoned|opined|interjected|mused|teased|growled"
)
_ACTION_AS_TAG = re.compile(
    r"[,!?…—][\"”’'][ \t]+(?:she|he|they|i|we|[A-Z][a-z]+)[ \t]+(?P<verb>smirked|grinned|smiled|laughed|chuckled|"
    r"sighed|giggled|snorted|huffed|scoffed|shrugged|nodded|frowned|winced)\b"
)
_BASE_FORMS = {
    "smirked": "smirk", "grinned": "grin", "smiled": "smile", "laughed": "laugh", "chuckled": "chuckle",
    "sighed": "sigh", "giggled": "giggle", "snorted": "snort", "huffed": "huff", "scoffed": "scoff",
    "shrugged": "shrug", "nodded": "nod", "frowned": "frown", "winced": "wince",
}
_TAG_ADVERB = re.compile(
    r"[\"”’'][ \t]*,?[ \t]*(?:she|he|they|i|we|[A-Z][a-z]+)[ \t]+(?:said|asked|replied|whispered|murmured|muttered|"
    r"answered|called|added|admitted|insisted)[ \t]+(?P<adv>[a-z]+ly)\b"
    r"|\b(?:said|asked|replied|whispered|murmured|muttered|answered|admitted)\s+(?:she|he|they|[A-Z][a-z]+)\s+(?P<adv2>[a-z]+ly)\b"
)
_ANY_TAG = re.compile(
    rf"[\"”’'][ \t]*,?[ \t]*(?:she|he|they|i|we|[A-Z][a-z]+)[ \t]+(?P<verb>said|says|asked|asks|replied|answered|told|{_TAG_FANCY}|"
    r"whispered|murmured|muttered|shouted|yelled|called|added|admitted|insisted)\b"
)


@register
class DialogueTags(Rule):
    id = "dialogue_tags"
    name = "Dialogue tag habits"
    category = "dialogue"
    description = "Adverbs on tags (“said softly”), actions used as tags (“‘Fine,’ he smirked.”), and a high share of fancy tags."
    has_sensitivity = True
    sensitivity_help = "Share of fancy tags (hissed, purred, chuckled…) before they are flagged (low: 60%, medium: 45%, high: 30%)."

    def check(self, doc: Document, ctx: RuleContext):
        results = []
        for m in _ACTION_AS_TAG.finditer(doc.text):
            verb = m.group("verb")
            start = m.start("verb")
            results.append(
                self.finding(
                    doc,
                    start,
                    m.end("verb"),
                    f"“{verb}” is used as a dialogue tag, but you can't {_BASE_FORMS.get(verb.lower(), verb)} a sentence.",
                    f"Use “said” plus a separate action beat (“He {verb}.”), or just the beat.",
                    title="Action used as a dialogue tag",
                    severity="low",
                )
            )
        for m in _TAG_ADVERB.finditer(doc.text):
            group = "adv" if m.group("adv") else "adv2"
            adverb = m.group(group)
            if adverb.lower() in {"only", "early", "finally", "simply", "really"}:
                continue
            start = m.start(group)
            results.append(
                self.finding(
                    doc,
                    start,
                    m.end(group),
                    f"An adverb propping up a dialogue tag (“{adverb}”). It tells the reader how the line "
                    "sounds instead of letting the words or a beat show it.",
                    "Cut the adverb; if tone is unclear, rework the line or add a small action.",
                    title="Adverb on a dialogue tag",
                    severity="low",
                )
            )
        tags = [m for m in _ANY_TAG.finditer(doc.text)]
        fancy = [m for m in tags if m.group("verb").lower() not in _TAG_VERBS_PLAIN]
        if len(tags) >= 5 and len(fancy) >= 3 and len(fancy) / len(tags) >= ctx.pick(0.6, 0.45, 0.3):
            for m in fancy:
                results.append(
                    self.finding(
                        doc,
                        m.start("verb"),
                        m.end("verb"),
                        f"{len(fancy)} of {len(tags)} dialogue tags are something other than “said/asked”. "
                        "Plain tags disappear; showy ones pull focus from the dialogue itself.",
                        "Default to “said”, and let the words carry the tone.",
                        title="Showy dialogue tag",
                        severity="low",
                    )
                )
        return results


@register
class VocativeOveruse(Rule):
    id = "vocative_overuse"
    name = "Names in dialogue"
    category = "dialogue"
    description = "Characters addressing each other by name far more than people really do (“I know, Sarah. But Sarah, listen.”)."
    has_sensitivity = True
    sensitivity_help = "Share of dialogue lines that use a name before flagging (low: 35%, medium: 25%, high: 15%)."

    def check(self, doc: Document, ctx: RuleContext):
        if not doc.names or len(doc.dialogue) < 4:
            return []
        names = "|".join(sorted((re.escape(n) for n in doc.names), key=len, reverse=True))
        vocative = re.compile(rf"(?:,\s*(?P<a>{names})\s*[.!?,—…]|^[\"“‘']?(?P<b>{names}),|(?:Hey|Oh|Look|Listen|Please|Yes|No|Well),\s*(?P<c>{names})\b)")
        hits = []
        for line in doc.dialogue:
            for m in vocative.finditer(line.text):
                group = next(g for g in ("a", "b", "c") if m.group(g))
                hits.append((line, line.start + m.start(group), line.start + m.end(group)))
        lines_with = {id(h[0]) for h in hits}
        share = len(lines_with) / len(doc.dialogue)
        if len(hits) < 3 or share < ctx.pick(0.35, 0.25, 0.15):
            return []
        return [
            self.finding(
                doc,
                s,
                e,
                f"Characters address each other by name in {share:.0%} of dialogue lines. In real "
                "conversation, people rarely use the name of the person they're talking to.",
                "Cut most of these; keep one where the name carries weight (anger, intimacy, a plea).",
                title="Name used in dialogue",
                severity="low",
            )
            for _line, s, e in hits
        ]


_UNCONTRACTED = re.compile(
    r"\b(?:I\s+am|I\s+have\s+not|I\s+will|I\s+would|you\s+are|we\s+are|they\s+are|it\s+is|that\s+is|"
    r"there\s+is|do\s+not|does\s+not|did\s+not|is\s+not|are\s+not|was\s+not|were\s+not|have\s+not|"
    r"has\s+not|had\s+not|will\s+not|would\s+not|could\s+not|should\s+not|cannot|let\s+us)\b",
    re.IGNORECASE,
)
_CONTRACTION = re.compile(r"\b[a-z]+['’](?:t|s|re|ve|ll|d|m)\b", re.IGNORECASE)


@register
class PolishedDialogue(Rule):
    id = "polished_dialogue"
    name = "Over-polished dialogue"
    category = "dialogue"
    description = "Speech that reads as written: long complete sentences, semicolons, few contractions, no interruptions."
    has_sensitivity = True
    sensitivity_help = "How long a single spoken sentence can get before it is flagged (low: 40 words, medium: 30, high: 24)."

    def check(self, doc: Document, ctx: RuleContext):
        results = []
        max_len = ctx.pick(40, 30, 24)
        total_contracted = total_uncontracted = 0
        spoken_sentences = []
        for line in doc.dialogue:
            speech = line.speech
            total_contracted += len(_CONTRACTION.findall(speech))
            uncontracted = list(_UNCONTRACTED.finditer(line.text))
            total_uncontracted += len(uncontracted)
            sentences = split_sentences(speech)
            spoken_sentences.extend(sentences)
            if ";" in speech:
                pos = line.text.index(";")
                results.append(
                    self.finding(
                        doc,
                        line.start,
                        line.end,
                        "A semicolon in speech. People don't talk in semicolons; it signals written, composed dialogue.",
                        "Split it into two spoken sentences, or let one half go unsaid.",
                        title="Semicolon in dialogue",
                        severity="low",
                        note="Fine for a deliberately formal or period voice.",
                        marks=[(line.start + pos, line.start + pos + 1)],
                    )
                )
            longest = max((len(WORD_RE.findall(s)) for s in sentences), default=0)
            if longest >= max_len:
                results.append(
                    self.finding(
                        doc,
                        line.start,
                        line.end,
                        f"A single spoken sentence of {longest} words. Speech under pressure is usually shorter, "
                        "broken, and less grammatical.",
                        "Break it up, let the other character interrupt, or cut to the one line that matters.",
                        title="Speech-like monologue",
                        severity="medium",
                        note="Fine if this character is meant to hold forth.",
                    )
                )
            if len(uncontracted) >= 2:
                results.append(
                    self.finding(
                        doc,
                        line.start,
                        line.end,
                        "Several uncontracted forms (“I am”, “do not”) in one line. Unless the character is "
                        "formal, this sounds stilted.",
                        "Contract them, unless the formality is part of this character's voice.",
                        title="Uncontracted speech",
                        severity="low",
                        marks=[(line.start + m.start(), line.start + m.end()) for m in uncontracted],
                    )
                )
        opportunities = total_contracted + total_uncontracted
        if opportunities >= 8 and total_contracted / opportunities < 0.3:
            results.append(
                self.doc_finding(
                    f"Dialogue is mostly uncontracted ({total_contracted} contractions vs {total_uncontracted} "
                    "full forms). Characters will sound formal or stiff unless that's intended.",
                    "Use contractions for most characters; keep full forms for deliberate formality or emphasis.",
                    title="Few contractions in dialogue",
                    severity="medium",
                )
            )
        if len(spoken_sentences) >= 15:
            broken = sum(
                1 for s in spoken_sentences
                if len(WORD_RE.findall(s)) <= 3 or s.rstrip("\"”’' ").endswith(("—", "–", "…", "...", "-"))
            )
            if broken / len(spoken_sentences) < 0.08:
                results.append(
                    self.doc_finding(
                        f"Only {broken} of {len(spoken_sentences)} spoken sentences are clipped, interrupted or "
                        "trailing off. Everyone speaks in complete, well-formed sentences, which real people rarely do.",
                        "Let characters interrupt, trail off, answer a different question, or reply with a fragment.",
                        title="Dialogue is grammatically perfect",
                        severity="low",
                    )
                )
        return results


_FILLERS = re.compile(r"\b(?:um+|uh+|er+|like|well|you\s+know|I\s+mean|kind\s+of|sort\s+of|okay|ok|yeah|gonna|wanna|gotta)\b", re.IGNORECASE)
_PROFANITY = re.compile(r"\b(?:damn|hell|shit|fuck\w*|bloody|crap|bastard|christ|god)\b", re.IGNORECASE)


def _voice_profile(lines) -> dict | None:
    text = " ".join(line.speech for line in lines)
    words = WORD_RE.findall(text)
    if len(words) < 40 or len(lines) < 3:
        return None
    sentences = [s for s in split_sentences(text) if WORD_RE.search(s)]
    lengths = [len(WORD_RE.findall(s)) for s in sentences] or [len(words)]
    per100 = 100 / len(words)
    return {
        "words": len(words),
        "avg_sentence": statistics.mean(lengths),
        "contractions": len(_CONTRACTION.findall(text)) * per100,
        "questions": sum(s.rstrip("\"”’' ").endswith("?") for s in sentences) / max(len(sentences), 1),
        "short_sentences": sum(length <= 4 for length in lengths) / len(lengths),
        "fillers": len(_FILLERS.findall(text)) * per100,
        "profanity": len(_PROFANITY.findall(text)) * per100,
        "avg_word_length": statistics.mean(len(w) for w in words),
    }


# Two speakers are "alike" when every measure differs by less than its tolerance.
_TOLERANCES = {
    "avg_sentence": 2.5,
    "contractions": 2.5,
    "questions": 0.15,
    "short_sentences": 0.15,
    "fillers": 1.0,
    "profanity": 0.5,
    "avg_word_length": 0.3,
}


@register
class VoiceSimilarity(Rule):
    id = "voice_similarity"
    name = "Indistinguishable voices"
    category = "dialogue"
    description = "Compares each speaker's measurable speech habits (sentence length, contractions, questions, fillers, word length) and flags speakers who sound statistically alike."
    has_sensitivity = True
    sensitivity_help = "How close the speech statistics must be (high flags more pairs)."

    def check(self, doc: Document, ctx: RuleContext):
        profiles = {}
        for speaker, lines in doc.speech_by_speaker().items():
            profile = _voice_profile(lines)
            if profile:
                profiles[speaker] = profile
        speakers = sorted(profiles)
        scale = ctx.pick(0.7, 1.0, 1.4)
        results = []
        for i, a in enumerate(speakers):
            for b in speakers[i + 1 :]:
                pa, pb = profiles[a], profiles[b]
                if all(abs(pa[k] - pb[k]) <= tol * scale for k, tol in _TOLERANCES.items()):
                    results.append(
                        self.doc_finding(
                            f"{a} and {b} have near-identical speech statistics: "
                            f"average spoken sentence {pa['avg_sentence']:.1f} vs {pb['avg_sentence']:.1f} words, "
                            f"contractions {pa['contractions']:.1f} vs {pb['contractions']:.1f} per 100 words, "
                            f"questions {pa['questions']:.0%} vs {pb['questions']:.0%}, "
                            f"fillers {pa['fillers']:.1f} vs {pb['fillers']:.1f} per 100 words. "
                            "If you covered the dialogue tags, could a reader tell who is speaking?",
                            "Give each a distinct verbal fingerprint: sentence length, vocabulary, what they "
                            "avoid saying, how they deflect, a recurring turn of phrase.",
                            title=f"{a} and {b} may sound alike",
                            severity="medium",
                            note="Statistics can't hear voice; read their lines aloud. The AI critic can judge this more meaningfully.",
                        )
                    )
        return results


def speaker_table(doc: Document) -> list[dict]:
    """Per-speaker speech statistics for the Stats tab."""
    rows = []
    for speaker, lines in sorted(doc.speech_by_speaker().items()):
        profile = _voice_profile(lines)
        words = sum(len(WORD_RE.findall(line.speech)) for line in lines)
        row = {"Speaker": speaker, "Lines": len(lines), "Words": words}
        if profile:
            row.update(
                {
                    "Avg sentence (words)": round(profile["avg_sentence"], 1),
                    "Contractions /100w": round(profile["contractions"], 1),
                    "Questions": f"{profile['questions']:.0%}",
                    "Short sentences": f"{profile['short_sentences']:.0%}",
                    "Fillers /100w": round(profile["fillers"], 1),
                    "Avg word length": round(profile["avg_word_length"], 2),
                }
            )
        rows.append(row)
    return rows
