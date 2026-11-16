"""Repetition and rhythm: openers, sentence lengths, paragraph shapes, echoes."""

from __future__ import annotations

import re
import statistics
from collections import Counter, defaultdict

from ..text import Document, Sentence
from .base import Pattern, PatternRule, Rule, RuleContext, register

SUBJECT_PRONOUNS = {"i", "you", "he", "she", "it", "we", "they"}

# Very common words that are not worth flagging as echoes.
COMMON_WORDS = set(
    """
    that this with from have were what when where which while there their they them then than
    been into onto over just like back down only even still about after again never always
    very much more most some such your yours hers ours said says asked would could should
    will shall must might each every both either neither other another these those because
    though although until since before also here know knew felt feel thought think looked
    look turned turn something nothing anything everything someone anyone everyone came come
    went made make took take didn't wasn't couldn't wouldn't don't it's that's there's she'd
    he'd they'd i'm i've she's he's they're we're you're upon onto toward towards around
    against through across behind beside under above below between without within almost
    really maybe perhaps away long little first last once twice ever yet same own going
    being having doing done well good right left time times way ways thing things
    """.split()
)

_CLASSES = {
    "P": {"i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them",
          "my", "your", "his", "its", "our", "their"},
    "D": {"the", "a", "an", "this", "that", "these", "those", "some", "any", "every", "each", "no"},
    "R": {"at", "in", "on", "to", "from", "with", "without", "into", "onto", "over", "under",
          "through", "across", "toward", "towards", "against", "between", "behind", "beside",
          "beneath", "above", "below", "around", "along", "past", "near", "by", "of", "for",
          "about", "off", "out", "up", "down", "inside", "outside", "upon", "within"},
    "C": {"and", "but", "or", "so", "yet", "nor"},
    "S": {"as", "when", "while", "because", "though", "although", "if", "until", "before",
          "after", "since", "which", "who"},
    "A": {"was", "were", "is", "are", "had", "has", "have", "did", "does", "do", "would",
          "could", "should", "will", "can", "might", "must", "been", "be", "being", "am"},
    "N": {"not", "never"},
}
_WORD_CLASS = {w: c for c, words in _CLASSES.items() for w in words}
_SKELETON_TOKEN = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*|[,;:—–]")


def _stem(word: str) -> str:
    w = re.sub(r"['’]s$", "", word.lower())
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    for suffix in ("ing", "ed", "ly", "es", "s"):
        if w.endswith(suffix) and not w.endswith("ss") and len(w) - len(suffix) >= 3:
            return w[: -len(suffix)]
    return w


def _subject_start(sentence: Sentence, names: set[str]) -> bool:
    if not sentence.words:
        return False
    first = re.sub(r"['’]s$", "", sentence.words[0])
    return first.lower() in SUBJECT_PRONOUNS or first in names


@register
class RepeatedOpeners(Rule):
    id = "repeated_openers"
    name = "Repeated sentence openings"
    category = "repetition"
    description = "Consecutive sentences that start the same way (“She… She… She…”)."
    has_sensitivity = True
    sensitivity_help = "Sentences in a row with the same first word (low: 4, medium: 3, high: 3; high also checks two-word openers more strictly)."

    def check(self, doc: Document, ctx: RuleContext):
        need = ctx.pick(4, 3, 3)
        results = []
        sents = doc.sentences
        covered: set[int] = set()
        i = 0
        while i < len(sents):
            s = sents[i]
            if not s.is_narration or not s.words:
                i += 1
                continue
            key = s.first_word
            j = i + 1
            while (
                j < len(sents)
                and sents[j].is_narration
                and sents[j].words
                and sents[j].first_word == key
                and sents[j].paragraph - sents[j - 1].paragraph <= 1
            ):
                j += 1
            run = sents[i:j]
            required = need + (1 if key in {"the", "a", "an"} else 0)
            if len(run) >= required:
                covered.update(x.index for x in run)
                avg = sum(x.word_count for x in run) / len(run)
                results.append(
                    self.finding(
                        doc,
                        run[0].start,
                        run[-1].end,
                        f"{len(run)} sentences in a row begin with “{s.words[0]}”. Repeated openers "
                        "flatten rhythm and make the prose feel assembled.",
                        "Vary the entry point: start with an action, a detail, a time marker, or merge two sentences.",
                        severity="high" if len(run) >= 4 else "medium",
                        note="Could be deliberate anaphora (repetition for emphasis); keep it if it is."
                        if avg <= 9
                        else "",
                        marks=[(x.word_spans[0][0], x.word_spans[0][1]) for x in run],
                    )
                )
                i = j
            else:
                i += 1

        # Same two-word opening ("She felt", "He looked") clustered within six narration sentences.
        narration = [s for s in sents if s.is_narration and s.word_count >= 2]
        need_pairs = ctx.pick(4, 3, 3)
        window = ctx.pick(6, 6, 8)
        reported: set[int] = set()
        for k in range(len(narration)):
            chunk = narration[k : k + window]
            counts = Counter(" ".join(w.lower() for w in s.words[:2]) for s in chunk)
            for key, count in counts.items():
                if count < need_pairs:
                    continue
                hits = [s for s in chunk if " ".join(w.lower() for w in s.words[:2]) == key]
                if any(h.index in covered or h.index in reported for h in hits):
                    continue
                reported.update(h.index for h in hits)
                opener = " ".join(hits[0].words[:2])
                results.append(
                    self.finding(
                        doc,
                        hits[0].start,
                        hits[-1].end,
                        f"“{opener}” opens {count} of {len(chunk)} nearby sentences.",
                        "Rephrase some of these so they don't share the same subject-verb opening.",
                        title="Repeated two-word opening",
                        severity="medium",
                        marks=[(h.word_spans[0][0], h.word_spans[1][1]) for h in hits],
                    )
                )
        return results


@register
class OpenerProfile(Rule):
    id = "opener_profile"
    name = "Sentence-opening habits"
    category = "repetition"
    description = "Passage-wide habits: most sentences starting with the subject, or many “-ing” openers (“Turning, she…”)."
    has_sensitivity = True
    sensitivity_help = "How dominant a habit must be before it is reported."

    _PARTICIPLE = re.compile(r"^[\"“‘']?([A-Z][a-z]+ing)\b[^,.!?]{0,60},")
    _NOT_PARTICIPLES = {
        "nothing", "something", "everything", "anything", "during", "morning", "evening",
        "king", "thing", "spring", "string", "ceiling", "bring", "ring", "wing", "sing",
        "darling", "according", "including", "notwithstanding",
    }

    def check(self, doc: Document, ctx: RuleContext):
        results = []
        narration = [s for s in doc.sentences if s.is_narration and s.word_count >= 3]
        if len(narration) >= 10:
            subject_share = sum(_subject_start(s, doc.names) for s in narration) / len(narration)
            if subject_share >= ctx.pick(0.8, 0.7, 0.6):
                results.append(
                    self.doc_finding(
                        f"{subject_share:.0%} of narrative sentences start with the subject (a pronoun or "
                        "name). The result is a steady “She did. He did. She did.” rhythm.",
                        "Open some sentences with a detail, a sound, a time or place, or a subordinate clause.",
                        title="Most sentences start with the subject",
                    )
                )
            counts = Counter(s.first_word for s in narration)
            word, count = counts.most_common(1)[0]
            share = count / len(narration)
            if share >= ctx.pick(0.4, 0.3, 0.25) and count >= 5:
                results.append(
                    self.doc_finding(
                        f"“{word.capitalize()}” opens {count} of {len(narration)} narrative sentences ({share:.0%}).",
                        "Vary sentence openings across the passage.",
                        title=f"“{word.capitalize()}” is the default opener",
                    )
                )

        participles = []
        for s in narration:
            m = self._PARTICIPLE.match(s.text)
            if m and m.group(1).lower() not in self._NOT_PARTICIPLES:
                participles.append((s, m))
        if narration and len(participles) >= ctx.pick(4, 3, 2) and len(participles) / len(narration) >= ctx.pick(0.12, 0.08, 0.05):
            for s, m in participles:
                results.append(
                    self.finding(
                        doc,
                        s.start,
                        s.start + m.end(1),
                        f"Participial opener (“{m.group(1)}…, she…”), {len(participles)} in this passage. "
                        "AI prose leans on these; they also imply two actions happen at once, which is "
                        "sometimes physically impossible.",
                        "Split into two actions, or start with the subject and a stronger verb.",
                        title="“-ing” sentence opener",
                        severity="low",
                    )
                )
        return results


@register
class SentenceRhythm(Rule):
    id = "sentence_rhythm"
    name = "Monotonous sentence length"
    category = "repetition"
    description = "Runs of sentences that are all roughly the same length."
    has_sensitivity = True
    sensitivity_help = "How similar the lengths must be before a run is flagged."

    WINDOW = 6

    def check(self, doc: Document, ctx: RuleContext):
        results = []
        sents = doc.sentences
        lengths = [s.word_count for s in sents]
        cv_max = ctx.pick(0.12, 0.18, 0.25)
        windows = []
        for i in range(len(sents) - self.WINDOW + 1):
            chunk = lengths[i : i + self.WINDOW]
            mean = sum(chunk) / len(chunk)
            if mean >= 8 and statistics.pstdev(chunk) / mean < cv_max:
                windows.append([i, i + self.WINDOW - 1])
        merged: list[list[int]] = []
        for w in windows:
            if merged and w[0] <= merged[-1][1]:
                merged[-1][1] = w[1]
            else:
                merged.append(w)
        for a, b in merged:
            chunk = lengths[a : b + 1]
            results.append(
                self.finding(
                    doc,
                    sents[a].start,
                    sents[b].end,
                    f"{len(chunk)} sentences in a row are all {min(chunk)}–{max(chunk)} words long. "
                    "Even-length sentences create a lulling, mechanical rhythm.",
                    "Break the pattern: a short sentence for impact, or a longer one that lets a moment breathe.",
                    severity="medium" if len(chunk) >= 9 else "low",
                )
            )

        if len(lengths) >= 15:
            mean = sum(lengths) / len(lengths)
            cv = statistics.pstdev(lengths) / mean if mean else 0
            if cv < ctx.pick(0.3, 0.38, 0.45):
                ordered = sorted(lengths)
                lo, hi = ordered[len(ordered) // 5], ordered[(len(ordered) * 4) // 5]
                results.append(
                    self.doc_finding(
                        f"Sentence lengths vary little across the passage: most are {lo}–{hi} words "
                        f"(variation score {cv:.2f}; lively prose is often above 0.5).",
                        "Mix very short and long sentences where the scene's tension calls for it.",
                        title="Narrow range of sentence lengths",
                    )
                )
        return results


@register
class ParagraphRhythm(Rule):
    id = "paragraph_rhythm"
    name = "Paragraph rhythm"
    category = "repetition"
    description = "Uniform paragraph sizes, frequent one-line “punch” paragraphs, and paragraphs that all end on a short zinger."
    has_sensitivity = True
    sensitivity_help = "How often a paragraph habit must recur before it is flagged."

    def check(self, doc: Document, ctx: RuleContext):
        results = []
        sents = doc.sentences
        paras = [p for p in doc.paragraphs if p.sentence_ids]

        narrative = [p for p in paras if not p.has_dialogue and len(p.sentence_ids) >= 2]
        if len(narrative) >= 6:
            sizes = [len(p.text.split()) for p in narrative]
            mean = sum(sizes) / len(sizes)
            if mean and statistics.pstdev(sizes) / mean < ctx.pick(0.2, 0.28, 0.35):
                results.append(
                    self.doc_finding(
                        f"Narrative paragraphs are nearly uniform in size (mostly {min(sizes)}–{max(sizes)} words). "
                        "Evenly portioned paragraphs are a hallmark of generated text.",
                        "Let paragraph length follow the content: compress quick action, expand what matters.",
                        title="Uniform paragraph sizes",
                    )
                )

        def inside_exchange(i: int) -> bool:
            before = paras[i - 1].has_dialogue if i > 0 else False
            after = paras[i + 1].has_dialogue if i + 1 < len(paras) else False
            return before and after  # e.g. 'Mr. Bennet made no answer.' between two speeches

        one_liners = [
            p for i, p in enumerate(paras)
            if len(p.sentence_ids) == 1
            and not p.has_dialogue
            and sents[p.sentence_ids[0]].word_count <= 10
            and not inside_exchange(i)
        ]
        if len(one_liners) >= ctx.pick(4, 3, 2) and len(one_liners) / max(len(paras), 1) >= 0.1:
            for p in one_liners:
                results.append(
                    self.finding(
                        doc,
                        p.start,
                        p.end,
                        f"A one-line paragraph used for emphasis ({len(one_liners)} in this passage). "
                        "One can land hard; several dilute each other and feel like a formula.",
                        "Keep the strongest one or two; fold the others into neighbouring paragraphs.",
                        title="One-line “punch” paragraph",
                        severity="low",
                    )
                )

        multi = [p for p in paras if len(p.sentence_ids) >= 3]
        closers = [
            sents[p.sentence_ids[-1]]
            for p in multi
            if sents[p.sentence_ids[-1]].word_count <= 6 and sents[p.sentence_ids[-1]].is_narration
        ]
        if multi and len(closers) >= ctx.pick(4, 3, 3) and len(closers) / len(multi) >= ctx.pick(0.5, 0.4, 0.3):
            for s in closers:
                results.append(
                    self.finding(
                        doc,
                        s.start,
                        s.end,
                        f"{len(closers)} of {len(multi)} longer paragraphs end on a short, punchy sentence.",
                        "Vary paragraph endings; not every paragraph needs a button.",
                        title="Paragraph ends on a zinger",
                        severity="low",
                    )
                )
        return results


def _skeleton(sentence: Sentence) -> tuple[str, ...]:
    tokens = []
    for tok in _SKELETON_TOKEN.findall(sentence.text):
        cls = tok if tok in ",;:—–" else _WORD_CLASS.get(tok.lower(), "w")
        if cls == "w" and tokens and tokens[-1] == "w":
            continue
        tokens.append(cls)
    return tuple(tokens)


@register
class SyntaxEcho(Rule):
    id = "syntax_echo"
    name = "Repeated sentence shapes"
    category = "repetition"
    description = "Nearby sentences built on the same grammatical template (“She looked at the door, her heart pounding.” / “He turned to the window, his breath catching.”)."
    has_sensitivity = True
    sensitivity_help = "How many same-shaped sentences within twelve before flagging (low: 4, medium: 3, high: 2)."

    WINDOW = 12

    def check(self, doc: Document, ctx: RuleContext):
        need = ctx.pick(4, 3, 2)
        positions: dict[tuple, list[int]] = defaultdict(list)
        for s in doc.sentences:
            if s.word_count >= 6 and s.is_narration:
                sk = _skeleton(s)
                if len(sk) >= 7:
                    positions[sk].append(s.index)
        results = []
        for sk, idxs in positions.items():
            best: list[int] = []
            for k in range(len(idxs)):
                group = [i for i in idxs[k:] if i - idxs[k] < self.WINDOW]
                if len(group) > len(best):
                    best = group
            if len(best) < need:
                continue
            examples = " / ".join(f"“{doc.sentences[i].text}”" for i in best[:3])
            for i in best:
                s = doc.sentences[i]
                results.append(
                    self.finding(
                        doc,
                        s.start,
                        s.end,
                        f"{len(best)} nearby sentences share the same grammatical shape: {examples}",
                        "Recast one or two: change the order, cut a clause, or join with a neighbour.",
                        severity="medium" if len(best) >= 3 else "low",
                    )
                )
        return results


@register
class ParticipleTails(PatternRule):
    id = "participle_tails"
    name = "Trailing “-ing” clauses"
    category = "repetition"
    description = "Sentences that end in “…, her heart pounding” or “…, sending a chill down her spine”."
    has_sensitivity = True
    sensitivity_help = "How many before flagging (low: 4, medium: 3, high: 2)."
    min_matches = (4, 3, 2)
    scope = "narration"
    severity = "low"
    patterns = (
        Pattern(
            r",\s+(?:his|her|their|my|its)\s+[a-z]+(?:\s+[a-z]+)?\s+[a-z]+ing\b",
            title="Trailing absolute phrase",
            message="A trailing absolute phrase (“…, her heart pounding”). A staple of AI rhythm when repeated.",
            suggestion="Give the detail its own sentence, or cut it if it's a stock reaction.",
        ),
        Pattern(
            r",\s+(?:sending|making|leaving|causing|forcing|drawing|filling|casting|bathing|throwing)\s+[a-z]+",
            title="Trailing consequence clause",
            message="A trailing “-ing” clause that tacks a consequence onto the sentence (“…, sending a shiver through her”).",
            suggestion="Make the consequence its own beat, or trust the reader to infer it.",
        ),
    )


@register
class WordEcho(Rule):
    id = "word_echo"
    name = "Echoed words"
    category = "repetition"
    description = "The same distinctive word used several times within a few lines of narration."
    has_sensitivity = True
    sensitivity_help = "Window size for repeats (low: 30 words, medium: 45, high: 70)."

    def check(self, doc: Document, ctx: RuleContext):
        window = ctx.pick(30, 45, 70)
        names = {n.lower() for n in doc.names}
        positions: dict[str, list[int]] = defaultdict(list)
        for idx, (start, end, word) in enumerate(doc.words):
            lw = word.lower()
            if len(lw) < 4 or lw in COMMON_WORDS or lw in names or doc.in_dialogue(start, end):
                continue  # dialogue echoes are often natural (speakers repeat each other)
            positions[_stem(lw)].append(idx)
        results = []
        for stem, idxs in positions.items():
            k = 0
            while k < len(idxs):
                group = [i for i in idxs[k:] if i - idxs[k] <= window]
                if len(group) >= 3:
                    words = [doc.words[i] for i in group]
                    results.append(
                        self.finding(
                            doc,
                            words[0][0],
                            words[-1][1],
                            f"“{words[0][2].lower()}” appears {len(group)} times within {group[-1] - group[0] + 1} words.",
                            "Keep the instance that matters most; cut or vary the others (unless the repetition is a deliberate refrain).",
                            severity="low" if len(group) == 3 else "medium",
                            marks=[(w[0], w[1]) for w in words],
                        )
                    )
                    k += len(group)
                else:
                    k += 1
        return results


_NGRAM_STOP = set(
    """
    a an the and or but so of to in on at by for with from into onto up down out over as is was
    were are be been had has have it its he she they i we you him her them me us his their my our
    your that this then than there not no just like said did do does would could should will can
    """.split()
)


@register
class RepeatedPhrases(Rule):
    id = "repeated_phrases"
    name = "Repeated phrases"
    category = "repetition"
    description = "Multi-word phrases that recur in the narration (“a flicker of”, “for a long moment”). Dialogue is skipped: a character's pet phrase is voice, not a tic."
    has_sensitivity = True
    sensitivity_help = "Uses before flagging: three-word phrases (low: 4, medium: 3, high: 3); longer phrases (low: 3, medium: 3, high: 2)."

    def check(self, doc: Document, ctx: RuleContext):
        tokens = [(s, e, w.lower().replace("’", "'")) for s, e, w in doc.words if not doc.in_dialogue(s, e)]
        # Longer texts naturally repeat more, so the bar rises with length.
        need3 = ctx.pick(4, 3, 3) + doc.word_count // 2500
        need_long = ctx.pick(3, 3, 2) + doc.word_count // 4000
        covered: set[int] = set()
        results = []
        for n in range(6, 2, -1):
            grams: dict[tuple, list[int]] = defaultdict(list)
            for i in range(len(tokens) - n + 1):
                gram = tuple(t[2] for t in tokens[i : i + n])
                if sum(1 for g in gram if g not in _NGRAM_STOP) < 2:
                    continue
                if any(i + k in covered for k in range(n)):
                    continue
                if grams[gram] and i - grams[gram][-1] < n:
                    continue  # overlapping occurrence
                grams[gram].append(i)
            need = need3 if n == 3 else need_long
            for gram, starts in grams.items():
                if len(starts) < need:
                    continue
                phrase = " ".join(gram)
                for i in starts:
                    covered.update(range(i, i + n))
                    results.append(
                        self.finding(
                            doc,
                            tokens[i][0],
                            tokens[i + n - 1][1],
                            f"The phrase “{phrase}” appears {len(starts)} times in this passage.",
                            "Unless it's a deliberate motif, rephrase all but one occurrence.",
                            title=f"Repeated phrase: “{phrase}”",
                            severity="low" if n == 3 else "medium",
                        )
                    )
        return results
