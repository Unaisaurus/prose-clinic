"""Runs the enabled rules over a passage and gathers the findings."""

from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import dataclass, field

from .findings import Finding
from .rules import RuleContext, all_rules
from .text import Document

CATEGORY_ORDER = [
    "formulaic", "repetition", "punctuation", "purple", "cliche", "dialogue", "emotion", "conflict", "custom",
]


@dataclass
class Analysis:
    doc: Document
    findings: list[Finding]  # visible findings
    suppressed: list[Finding] = field(default_factory=list)  # hidden as false positives
    errors: list[str] = field(default_factory=list)

    @property
    def span_findings(self) -> list[Finding]:
        return [f for f in self.findings if not f.is_document_level]

    @property
    def document_findings(self) -> list[Finding]:
        return [f for f in self.findings if f.is_document_level]

    def counts_by_rule(self) -> Counter:
        return Counter(f.rule_id for f in self.findings)

    def counts_by_category(self) -> Counter:
        return Counter(f.category for f in self.findings)


def rule_settings(settings: dict, rule_id: str) -> dict:
    return settings.get("rules", {}).get(rule_id, {})


def run_rules(text: str, settings: dict) -> tuple[Document, list[Finding], list[str]]:
    """Run every enabled rule. A rule that crashes is reported, not fatal."""
    doc = Document(text)
    findings: list[Finding] = []
    errors: list[str] = []
    if not text.strip():
        return doc, findings, errors
    for rule in all_rules():
        cfg = rule_settings(settings, rule.id)
        if not cfg.get("enabled", rule.default_enabled):
            continue
        ctx = RuleContext(
            sensitivity=cfg.get("sensitivity", "medium"),
            custom_phrases=settings.get("custom_phrases", []),
        )
        try:
            produced = rule.check(doc, ctx)
        except Exception as exc:  # keep the app usable if one rule misbehaves
            errors.append(f"{rule.name}: {type(exc).__name__}: {exc}")
            continue
        findings.extend(_cap(rule, produced))
    findings = _dedupe(findings)
    findings.sort(key=_sort_key)
    return doc, findings, errors


def apply_feedback(doc: Document, findings: list[Finding], errors: list[str], false_positives: set[str]) -> Analysis:
    visible, hidden = [], []
    for f in findings:
        (hidden if f.signature in false_positives else visible).append(f)
    return Analysis(doc=doc, findings=visible, suppressed=hidden, errors=errors)


def analyze(text: str, settings: dict, false_positives: set[str] | None = None) -> Analysis:
    doc, findings, errors = run_rules(text, settings)
    return apply_feedback(doc, findings, errors, false_positives or set())


MAX_PER_RULE = 120
_SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2}


def _cap(rule, produced: list[Finding]) -> list[Finding]:
    """Keep very long manuscripts responsive: list at most MAX_PER_RULE spans per check."""
    spans = [f for f in produced if not f.is_document_level]
    if len(spans) <= MAX_PER_RULE:
        return produced
    omitted = len(spans) - MAX_PER_RULE
    note = Finding(
        rule_id=rule.id,
        category=rule.category,
        title=f"{rule.name}: {omitted} more not listed",
        message=f"This check found {len(spans)} instances; only the first {MAX_PER_RULE} are listed to keep the app responsive.",
        suggestion="Work through the listed ones and re-analyze, or analyze the text a scene or chapter at a time.",
        severity="low",
    )
    return [f for f in produced if f.is_document_level] + [note] + spans[:MAX_PER_RULE]


def _dedupe(findings: list[Finding]) -> list[Finding]:
    """Drop exact repeats, and keep one finding when two rules flag the identical short phrase."""
    seen, unique = set(), []
    for f in findings:
        key = (f.rule_id, f.start, f.end, f.title)
        if key not in seen:
            seen.add(key)
            unique.append(f)
    best_for_span: dict[tuple[int, int], Finding] = {}
    for f in unique:
        if f.is_document_level or (f.end - f.start) > 80:
            continue
        current = best_for_span.get((f.start, f.end))
        if current is None or _SEVERITY_RANK.get(f.severity, 0) > _SEVERITY_RANK.get(current.severity, 0):
            best_for_span[(f.start, f.end)] = f
    return [
        f for f in unique
        if f.is_document_level or (f.end - f.start) > 80 or best_for_span.get((f.start, f.end)) is f
    ]


def _sort_key(f: Finding):
    if f.is_document_level:
        return (0, CATEGORY_ORDER.index(f.category) if f.category in CATEGORY_ORDER else 99, 0)
    return (1, f.start, -(f.end or 0))


def text_stats(doc: Document) -> dict:
    lengths = [s.word_count for s in doc.sentences if s.word_count]
    narration = [s for s in doc.sentences if s.is_narration and s.words]
    openers = Counter(s.first_word for s in narration)
    dialogue_words = sum(len(line.speech.split()) for line in doc.dialogue)
    return {
        "words": doc.word_count,
        "sentences": len(doc.sentences),
        "paragraphs": len(doc.paragraphs),
        "avg_sentence": statistics.mean(lengths) if lengths else 0,
        "sentence_variation": (statistics.pstdev(lengths) / statistics.mean(lengths)) if len(lengths) > 1 else 0,
        "dialogue_share": dialogue_words / doc.word_count if doc.word_count else 0,
        "sentence_lengths": lengths,
        "top_openers": openers.most_common(8),
        "em_dashes": doc.text.count("—") + doc.text.count("--"),
        "ellipses": doc.text.count("…") + doc.text.count("..."),
    }
