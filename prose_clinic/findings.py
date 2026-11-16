"""The Finding record shared by rule-based checks and the AI critic."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass

from .text import normalize_for_match

# id -> (label, highlight colour as "r, g, b")
CATEGORIES: dict[str, tuple[str, str]] = {
    "formulaic": ("Formulaic constructions", "155, 89, 182"),
    "repetition": ("Repetition & rhythm", "52, 152, 219"),
    "punctuation": ("Punctuation habits", "26, 188, 156"),
    "purple": ("Purple prose & abstraction", "231, 76, 160"),
    "cliche": ("Clichés & stock phrasing", "243, 156, 18"),
    "dialogue": ("Dialogue", "39, 174, 96"),
    "emotion": ("Emotional telling", "231, 76, 60"),
    "conflict": ("Conflict & resolution", "160, 110, 70"),
    "custom": ("Your custom phrases", "120, 120, 120"),
    # Categories the AI critic may also use:
    "voice": ("Character voice", "22, 160, 133"),
    "tone": ("Tone & POV", "142, 68, 173"),
    "character": ("Characterization", "211, 84, 0"),
    "pacing": ("Pacing", "41, 128, 185"),
    "other": ("Other", "127, 140, 141"),
}

SEVERITIES = ("low", "medium", "high")
SEVERITY_ICONS = {"low": "🔹", "medium": "🔸", "high": "🔺"}
SEVERITY_LABELS = {"low": "Minor / maybe", "medium": "Worth a look", "high": "Likely issue"}


def category_label(category: str) -> str:
    return CATEGORIES.get(category, (category.title(), ""))[0]


def category_color(category: str) -> str:
    return CATEGORIES.get(category, ("", "127, 140, 141"))[1]


@dataclass
class Finding:
    rule_id: str
    category: str
    title: str  # short label, e.g. "Not X, but Y"
    message: str  # what was spotted and why it may be a problem
    suggestion: str  # how to improve it
    start: int | None = None  # None = applies to the whole passage
    end: int | None = None
    severity: str = "medium"
    excerpt: str = ""
    note: str = ""  # e.g. "Could be deliberate: ..."
    replacement: str | None = None  # offline quick fix for exactly text[start:end]
    source: str = "rule"  # "rule" or "ai"
    marks: list[tuple[int, int]] | None = None  # extra emphasis inside the span (e.g. echoed words)

    @property
    def is_document_level(self) -> bool:
        return self.start is None

    @property
    def signature(self) -> str:
        """Identifies 'the same finding' across analyses, for feedback."""
        basis = self.excerpt if not self.is_document_level else self.title
        return f"{self.rule_id}|{normalize_for_match(basis)}"

    @property
    def uid(self) -> str:
        raw = f"{self.source}:{self.rule_id}:{self.start}:{self.end}:{self.title}:{self.message}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["uid"] = self.uid
        return data

    @classmethod
    def from_dict(cls, data: dict) -> Finding:
        fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        if fields.get("marks"):
            fields["marks"] = [tuple(m) for m in fields["marks"]]
        return cls(**fields)
