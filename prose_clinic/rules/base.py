"""Building blocks for detection rules.

How to add a rule
-----------------
1. Open the module in ``prose_clinic/rules/`` that fits (or create a new one and
   import it in ``rules/__init__.py``).
2. Subclass ``PatternRule`` (a list of regular expressions) or ``Rule`` (any
   custom logic in ``check``).
3. Decorate the class with ``@register``.

The rule then shows up in Settings (with its own on/off switch) and runs
during analysis. Rules return ``Finding`` objects; use ``self.finding(...)``
for a highlighted span and ``self.doc_finding(...)`` for a passage-wide note.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..findings import Finding
from ..text import Document

# Shorthands usable inside PatternRule regexes.
PLACEHOLDERS = {
    "{PRON}": r"(?:her|his|my|their|your|our|its)",
    "{SUBJ}": r"(?:she|he|they|i|we|you|it)",
    "{OBJ}": r"(?:her|him|them|me|us|you|it)",
    "{REFL}": r"(?:herself|himself|themselves|myself|yourself|ourselves|itself)",
    "{APOS}": r"['’]",
}

SENSITIVITY_LEVELS = ("low", "medium", "high")


def expand(pattern: str) -> str:
    for key, value in PLACEHOLDERS.items():
        pattern = pattern.replace(key, value)
    return pattern


@dataclass
class RuleContext:
    sensitivity: str = "medium"
    custom_phrases: list[dict] = field(default_factory=list)

    def pick(self, low, medium, high):
        """Choose a threshold for the current sensitivity (high = flags more)."""
        return {"low": low, "medium": medium, "high": high}.get(self.sensitivity, medium)


class Rule:
    id: str = ""
    name: str = ""
    category: str = ""
    description: str = ""
    default_enabled: bool = True
    has_sensitivity: bool = False
    sensitivity_help: str = ""

    def check(self, doc: Document, ctx: RuleContext) -> list[Finding]:
        raise NotImplementedError

    def finding(
        self,
        doc: Document,
        start: int,
        end: int,
        message: str,
        suggestion: str,
        *,
        title: str | None = None,
        severity: str = "medium",
        note: str = "",
        replacement: str | None = None,
        marks: list[tuple[int, int]] | None = None,
    ) -> Finding:
        return Finding(
            rule_id=self.id,
            category=self.category,
            title=title or self.name,
            message=message,
            suggestion=suggestion,
            start=start,
            end=end,
            severity=severity,
            excerpt=doc.text[start:end],
            note=note,
            replacement=replacement,
            marks=marks,
        )

    def doc_finding(
        self, message: str, suggestion: str, *, title: str | None = None, severity: str = "low", note: str = ""
    ) -> Finding:
        return Finding(
            rule_id=self.id,
            category=self.category,
            title=title or self.name,
            message=message,
            suggestion=suggestion,
            severity=severity,
            note=note,
        )


@dataclass(frozen=True)
class Pattern:
    """One regex inside a PatternRule. Empty fields fall back to the rule's defaults."""

    regex: str
    message: str = ""
    suggestion: str = ""
    title: str = ""
    severity: str = ""
    replacement: str | None = None  # re-style template, e.g. r"\g<verb>"
    scope: str = ""  # "", "all", "narration" or "dialogue"


class PatternRule(Rule):
    """A rule defined by a list of regular expressions."""

    patterns: tuple[Pattern, ...] = ()
    scope: str = "all"  # where matches count: "all", "narration" or "dialogue"
    message: str = ""
    suggestion: str = ""
    severity: str = "medium"
    note: str = ""
    flags: int = re.IGNORECASE
    # Density gating: (low, medium, high) minimum number of matches in the passage,
    # or matches per 1,000 words, before any are reported. None = report every match.
    min_matches: tuple[int, int, int] | None = None
    min_per_1000: tuple[float, float, float] | None = None

    def compiled(self) -> list[tuple[Pattern, re.Pattern]]:
        cache = self.__dict__.get("_compiled_cache")
        if cache is None:
            cache = [(p, re.compile(expand(p.regex), self.flags)) for p in self.patterns]
            self.__dict__["_compiled_cache"] = cache
        return cache

    def matches(self, doc: Document) -> list[tuple[Pattern, re.Match]]:
        found = []
        for pattern, regex in self.compiled():
            scope = pattern.scope or self.scope
            for m in regex.finditer(doc.text):
                start, end = m.span()
                if end <= start:
                    continue
                if scope == "dialogue" and not doc.in_dialogue(start, end):
                    continue
                if scope == "narration" and doc.in_dialogue(start, end):
                    continue
                found.append((pattern, m))
        # Overlapping matches: keep the earliest, then the longest.
        found.sort(key=lambda pm: (pm[1].start(), -(pm[1].end() - pm[1].start())))
        kept, last_end = [], -1
        for pattern, m in found:
            if m.start() >= last_end:
                kept.append((pattern, m))
                last_end = m.end()
        return kept

    def check(self, doc: Document, ctx: RuleContext) -> list[Finding]:
        found = self.matches(doc)
        if self.min_matches and len(found) < ctx.pick(*self.min_matches):
            return []
        if self.min_per_1000:
            per_1000 = len(found) / max(doc.word_count, 1) * 1000
            if len(found) < 3 or per_1000 < ctx.pick(*self.min_per_1000):
                return []
        gated = self.min_matches or self.min_per_1000
        count_note = f" ({len(found)} in this passage.)" if gated else ""
        results = []
        for pattern, m in found:
            replacement = None
            if pattern.replacement is not None:
                replacement = m.expand(pattern.replacement)
                if m.group()[:1].isupper():
                    replacement = replacement[:1].upper() + replacement[1:]
            results.append(
                self.finding(
                    doc,
                    m.start(),
                    m.end(),
                    (pattern.message or self.message) + count_note,
                    pattern.suggestion or self.suggestion,
                    title=pattern.title or self.name,
                    severity=pattern.severity or self.severity,
                    note=self.note,
                    replacement=replacement,
                )
            )
        return results


_REGISTRY: dict[str, Rule] = {}


def register(cls: type[Rule]) -> type[Rule]:
    rule = cls()
    if not rule.id or not rule.name or not rule.category:
        raise ValueError(f"{cls.__name__} needs id, name and category")
    if rule.id in _REGISTRY:
        raise ValueError(f"Duplicate rule id: {rule.id}")
    _REGISTRY[rule.id] = rule
    return cls


def all_rules() -> list[Rule]:
    return list(_REGISTRY.values())


def get_rule(rule_id: str) -> Rule | None:
    return _REGISTRY.get(rule_id)
