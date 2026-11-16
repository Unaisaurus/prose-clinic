"""Splitting prose into paragraphs, sentences, words and dialogue.

Every position is a character offset into the ORIGINAL text, so findings can be
highlighted exactly where they occur. The splitting is heuristic (no external
NLP libraries) but tuned for fiction: dialogue tags, ellipses, interrupted
speech and common abbreviations are handled.

Conventions:
* Each non-empty line is a paragraph. Lines without letters (``***``, ``#``)
  are treated as scene breaks, and Markdown headings are skipped.
* Dialogue is text inside double quotes (straight or curly) or guillemets.
  If a passage has no double quotes at all, British-style single quotes are
  detected instead.
"""

from __future__ import annotations

import re
from bisect import bisect_left
from collections import Counter, defaultdict
from dataclasses import dataclass, field

WORD_RE = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*")
LETTER_RE = re.compile(r"[^\W\d_]")

# Words that look like the end of a sentence but are not.
ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "st", "jr", "sr", "prof", "rev", "gen", "col", "capt",
    "lt", "sgt", "mt", "ft", "vs", "etc", "e.g", "i.e", "vol", "approx", "inc",
    "ltd", "co", "corp", "dept", "gov", "sen", "rep", "pres", "hon", "cf",
    "ave", "blvd", "rd", "esq",
}
# Only abbreviations when a number follows ("No. 5", "Vol. 2").
NUMERIC_ABBREVIATIONS = {"no", "vol", "fig", "op", "p", "pp"}

_CLOSERS = "\"'”’»)]"
_BOUNDARY_RE = re.compile(
    r"""
    (?: (?:\.{3}|…|[.!?])+ [\"'”’»)\]]*     # terminal punctuation + closing quotes
      | (?:—|–|--)[\"”’']                    # interrupted speech: —"
    )
    (?=\s|$)
    """,
    re.VERBOSE,
)

# Capitalised words that are not character names.
_NOT_NAMES = set(
    """
    i i'm i'd i'll i've the a an he she it they we you his her hers their theirs its our
    ours your yours my mine me him them us this that these those then there here but and
    or so yet nor for when while if as in on at by to of with without after before now
    what why how who whom whose where which maybe perhaps yes no not oh ah well just still
    even only again once okay ok hey hi hello please thanks thank sorry sure nothing
    something someone everyone everything anything anyone nobody somewhere somehow some
    any all every each both neither either none one two three four five six seven eight
    nine ten first last next never always sometimes outside inside above below behind
    beyond through across around over under up down out off into onto from until since
    because although though unless whatever whenever wherever however instead besides
    meanwhile later soon today tonight tomorrow yesterday morning evening night
    monday tuesday wednesday thursday friday saturday sunday january february march april
    june july august september october november december mr mrs ms dr miss sir madam
    st mt ft jr sr prof rev gen col capt lt sgt dept
    ma'am um uh hmm huh wow whoa damn shit fuck hell jesus christ god lord don't can't
    won't it's that's there's what's let's you're we're they're didn't doesn't isn't
    wasn't aren't weren't couldn't wouldn't shouldn't haven't hasn't hadn't he's she's
    let look listen wait stop come go get tell take give keep stay run see remember
    forget do did does is are was were will would could should can may might must have
    has had be been being am chapter part book prologue epilogue english french god's
    whatever's who's where's how's here's
    """.split()
)

SPEECH_VERBS = (
    "said|says|say|asked|asks|replied|replies|answered|answers|whispered|whispers|"
    "murmured|murmurs|muttered|mutters|shouted|shouts|yelled|yells|screamed|screams|"
    "cried|cries|called|calls|snapped|snaps|hissed|hisses|growled|growls|barked|"
    "sighed|sighs|laughed|laughs|chuckled|chuckles|breathed|breathes|added|adds|"
    "continued|continues|began|begins|insisted|insists|admitted|admits|explained|"
    "explains|demanded|demands|pleaded|pleads|begged|begs|warned|warns|agreed|agrees|"
    "offered|offers|suggested|suggests|repeated|repeats|announced|announces|declared|"
    "protested|countered|retorted|quipped|teased|stammered|stuttered|gasped|croaked|"
    "rasped|purred|drawled|mused|wondered|observed|noted|remarked|conceded|interrupted|"
    "corrected|told|tells|informed|assured|promised|sneered|scoffed|grumbled|whimpered|"
    "sobbed|ventured|prompted|pressed|urged|deadpanned|joked|smirked|grinned|smiled|"
    "snorted|huffed|spat|managed|finished|went\\s+on|shot\\s+back"
)

_TITLE = r"(?:(?:Mr|Mrs|Ms|Dr|Miss|Captain|Sir|Lady|Lord|Aunt|Uncle|Professor)\.?\s+)?"
_NAME_TOKEN = _TITLE + r"([A-Z][\w'’-]*)"
_TAG_AFTER_RE = re.compile(rf"^\s*,?\s*{_NAME_TOKEN}\s+(?:\w+ly\s+)?(?:{SPEECH_VERBS})\b")
_TAG_AFTER_INVERTED_RE = re.compile(rf"^\s*,?\s*(?:{SPEECH_VERBS})\s+{_NAME_TOKEN}")
_TAG_BEFORE_RE = re.compile(
    rf"{_NAME_TOKEN}\s+(?:\w+ly\s+)?(?:{SPEECH_VERBS})(?:\s+\w+ly)?\s*[,:]?\s*$"
)


@dataclass
class Paragraph:
    start: int
    end: int
    text: str
    index: int
    sentence_ids: list[int] = field(default_factory=list)
    has_dialogue: bool = False


@dataclass
class Sentence:
    start: int
    end: int
    text: str
    index: int
    paragraph: int
    words: list[str]
    word_spans: list[tuple[int, int]]
    dialogue_ratio: float

    @property
    def word_count(self) -> int:
        return len(self.words)

    @property
    def is_dialogue(self) -> bool:
        return self.dialogue_ratio >= 0.5

    @property
    def is_narration(self) -> bool:
        return self.dialogue_ratio < 0.5

    @property
    def first_word(self) -> str:
        return self.words[0].lower() if self.words else ""


@dataclass
class DialogueLine:
    start: int  # includes the quote marks
    end: int
    text: str
    paragraph: int
    speech: str  # the spoken words, without quote marks
    speaker: str | None = None
    attribution: str = ""  # "tag", "beat", "alternation" or ""


def _trim(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _split_paragraphs(text: str) -> list[tuple[int, int]]:
    spans = []
    for m in re.finditer(r"[^\n]+", text):
        start, end = _trim(text, m.start(), m.end())
        if start >= end:
            continue
        line = text[start:end]
        if not LETTER_RE.search(line) or line.startswith("#"):
            continue
        spans.append((start, end))
    return spans


def _is_abbreviation(text: str, match: re.Match, next_char: str) -> bool:
    punct = match.group().rstrip(_CLOSERS)
    if punct != ".":
        return False
    j = match.start()
    k = j
    while k > 0 and (text[k - 1].isalpha() or text[k - 1] == "."):
        k -= 1
    raw = text[k:j]
    word = raw.lower().strip(".")
    if word in ABBREVIATIONS:
        return True
    if word in NUMERIC_ABBREVIATIONS:
        return next_char.isdigit()
    return len(raw) == 1 and raw.isupper() and raw != "I"


# '"Run!" Tom shouted.' is one sentence: a capitalised name followed by a speech verb.
_NAMED_TAG_RE = re.compile(rf"(?:{_NAME_TOKEN}\s+(?:\w+ly\s+)?(?:{SPEECH_VERBS})|(?:{SPEECH_VERBS})\s+{_NAME_TOKEN})\b")


def _split_sentences(text: str, start: int, end: int) -> list[tuple[int, int]]:
    spans = []
    current = start
    for m in _BOUNDARY_RE.finditer(text, start, end):
        nxt = m.end()
        while nxt < end and text[nxt].isspace():
            nxt += 1
        if nxt < end:
            if text[nxt].islower() or _is_abbreviation(text, m, text[nxt]):
                continue
            if m.group()[-1] in "\"”’'" and _NAMED_TAG_RE.match(text, nxt, end):
                continue
        s, e = _trim(text, current, m.end())
        if s < e:
            spans.append((s, e))
        current = nxt
    s, e = _trim(text, current, end)
    if s < e:
        spans.append((s, e))
    return spans


def _find_closing(text: str, start: int, end: int, closers: str) -> int:
    best = -1
    for ch in closers:
        pos = text.find(ch, start, end)
        if pos != -1 and (best == -1 or pos < best):
            best = pos
    return best


def _double_quote_spans(text: str, start: int, end: int) -> list[tuple[int, int]]:
    spans = []
    i = start
    while i < end:
        ch = text[i]
        if ch in "“\"«":
            closers = "»" if ch == "«" else "”\""
            close = _find_closing(text, i + 1, end, closers)
            stop = end if close == -1 else close + 1
            spans.append((i, stop))
            i = stop
        else:
            i += 1
    return spans


def _single_quote_spans(text: str, start: int, end: int) -> list[tuple[int, int]]:
    """British-style 'dialogue', telling quote marks apart from apostrophes."""
    spans = []
    i = start
    while i < end:
        ch = text[i]
        opens = (
            ch in "‘'"
            and (i == start or text[i - 1].isspace() or text[i - 1] in "—–-([")
            and i + 1 < end
            and (text[i + 1].isalpha() or text[i + 1] in "…—")
        )
        if not opens:
            i += 1
            continue
        close = -1
        j = i + 1
        while j < end:
            if (
                text[j] in "’'"
                and text[j - 1] in ",.!?…—–-"
                and (j + 1 == end or not text[j + 1].isalnum())
            ):
                close = j + 1
                break
            if text[j] in "‘'" and text[j - 1].isspace() and j + 1 < end and text[j + 1].isalpha():
                break  # another opening quote: the first mark was an apostrophe ('Tis)
            j += 1
        if close == -1:  # probably an apostrophe ('tis, 'em): not dialogue
            i += 1
            continue
        spans.append((i, close))
        i = close
    return spans


class Document:
    """A passage of prose, segmented for analysis."""

    def __init__(self, text: str):
        self.text = text
        self.words = [(m.start(), m.end(), m.group()) for m in WORD_RE.finditer(text)]
        self._word_starts = [w[0] for w in self.words]

        para_spans = _split_paragraphs(text)
        self.dialogue_mode = "double" if sum(text.count(q) for q in "\"“”«") >= 2 else "single"
        self._mask = bytearray(len(text))
        self.dialogue: list[DialogueLine] = []
        self.paragraphs: list[Paragraph] = []
        for p_index, (ps, pe) in enumerate(para_spans):
            para = Paragraph(ps, pe, text[ps:pe], p_index)
            finder = _double_quote_spans if self.dialogue_mode == "double" else _single_quote_spans
            for ds, de in finder(text, ps, pe):
                self._mask[ds:de] = b"\x01" * (de - ds)
                speech = text[ds:de].strip("\"“”«»‘’' \t")
                self.dialogue.append(DialogueLine(ds, de, text[ds:de], p_index, speech))
                para.has_dialogue = True
            self.paragraphs.append(para)

        self.sentences: list[Sentence] = []
        for para in self.paragraphs:
            for ss, se in _split_sentences(text, para.start, para.end):
                spans = self.word_spans_in(ss, se)
                sentence = Sentence(
                    start=ss,
                    end=se,
                    text=text[ss:se],
                    index=len(self.sentences),
                    paragraph=para.index,
                    words=[text[a:b] for a, b in spans],
                    word_spans=spans,
                    dialogue_ratio=self.dialogue_fraction(ss, se),
                )
                para.sentence_ids.append(sentence.index)
                self.sentences.append(sentence)

        self.names = self._detect_names()
        self._attribute_speakers()

    # ------------------------------------------------------------------ basics
    @property
    def word_count(self) -> int:
        return len(self.words)

    @property
    def narration_sentences(self) -> list[Sentence]:
        return [s for s in self.sentences if s.is_narration]

    def word_spans_in(self, start: int, end: int) -> list[tuple[int, int]]:
        i = bisect_left(self._word_starts, start)
        out = []
        while i < len(self.words) and self.words[i][0] < end:
            if self.words[i][1] <= end:
                out.append((self.words[i][0], self.words[i][1]))
            i += 1
        return out

    def dialogue_fraction(self, start: int, end: int) -> float:
        if end <= start:
            return 0.0
        return self._mask[start:end].count(1) / (end - start)

    def in_dialogue(self, start: int, end: int) -> bool:
        return self.dialogue_fraction(start, end) >= 0.5

    def sentence_at(self, pos: int) -> Sentence | None:
        for s in self.sentences:
            if s.start <= pos < s.end:
                return s
        return None

    def sentences_overlapping(self, start: int, end: int) -> list[Sentence]:
        return [s for s in self.sentences if s.start < end and s.end > start]

    def paragraph_index_at(self, pos: int) -> int | None:
        for p in self.paragraphs:
            if p.start <= pos <= p.end:
                return p.index
        return None

    def sentence_bounds(self, start: int, end: int) -> tuple[int, int]:
        """Expand a span to whole sentences (used for rewrites and context)."""
        overlapping = self.sentences_overlapping(start, end)
        if not overlapping:
            return start, end
        return overlapping[0].start, overlapping[-1].end

    # ------------------------------------------------------------ names/speech
    def _detect_names(self) -> set[str]:
        initial = set()
        for s in self.sentences:
            if s.word_spans:
                initial.add(s.word_spans[0][0])
        for d in self.dialogue:
            spans = self.word_spans_in(d.start, d.end)
            if spans:
                initial.add(spans[0][0])
        counts: Counter[str] = Counter()
        mid: Counter[str] = Counter()
        for start, _end, word in self.words:
            if not word[0].isupper() or (len(word) > 1 and word.isupper()):
                continue
            base = re.sub(r"['’]s$", "", word)
            if base.lower() in _NOT_NAMES or len(base) < 2:
                continue
            counts[base] += 1
            if start not in initial:
                mid[base] += 1
        return {w for w, c in counts.items() if mid[w] >= 1 or c >= 3}

    def _name_or_none(self, token: str | None) -> str | None:
        if not token:
            return None
        base = re.sub(r"['’]s$", "", token)
        return base if base in self.names else None

    def _speaker_from_tags(self, para: Paragraph, lines: list[DialogueLine]) -> str | None:
        for i, line in enumerate(lines):
            after_end = lines[i + 1].start if i + 1 < len(lines) else para.end
            after = self.text[line.end:after_end]
            for regex in (_TAG_AFTER_RE, _TAG_AFTER_INVERTED_RE):
                m = regex.match(after)
                if m and (name := self._name_or_none(m.group(1))):
                    return name
            before_start = lines[i - 1].end if i > 0 else para.start
            before = self.text[before_start:line.start]
            m = _TAG_BEFORE_RE.search(before)
            if m and (name := self._name_or_none(m.group(1))):
                return name
        return None

    def _speaker_from_beat(self, para: Paragraph) -> str | None:
        """'Mara set down her cup. "We should go."' -> Mara."""
        for sid in para.sentence_ids:
            s = self.sentences[sid]
            if not s.words or self.text[s.start] in "\"“«‘'":
                continue
            if name := self._name_or_none(s.words[0]):
                return name
        return None

    def _attribute_speakers(self) -> None:
        by_para: dict[int, list[DialogueLine]] = defaultdict(list)
        for line in self.dialogue:
            by_para[line.paragraph].append(line)
        chain: list[str | None] = []
        narration_run = 0
        for para in self.paragraphs:
            lines = by_para.get(para.index)
            if not lines:
                narration_run += len(para.sentence_ids)
                if narration_run >= 5:
                    chain = []  # a long stretch of narration ends the exchange
                continue
            narration_run = 0
            speaker, how = self._speaker_from_tags(para, lines), "tag"
            if not speaker:
                speaker, how = self._speaker_from_beat(para), "beat"
            if not speaker and len(chain) >= 2 and chain[-1] and chain[-2] and chain[-1] != chain[-2]:
                speaker, how = chain[-2], "alternation"
            for line in lines:
                line.speaker = speaker
                line.attribution = how if speaker else ""
            chain.append(speaker)

    def speech_by_speaker(self) -> dict[str, list[DialogueLine]]:
        grouped: dict[str, list[DialogueLine]] = defaultdict(list)
        for line in self.dialogue:
            if line.speaker:
                grouped[line.speaker].append(line)
        return dict(grouped)


def split_sentences(text: str) -> list[str]:
    """Convenience helper: the sentences of a piece of text, as strings."""
    return [s.text for s in Document(text).sentences]


def normalize_for_match(text: str) -> str:
    """Lower-case, straighten quotes and collapse whitespace (for comparisons)."""
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"\s+", " ", text.lower()).strip()
    return text.strip(" .,;:!?\"'—–-…")
