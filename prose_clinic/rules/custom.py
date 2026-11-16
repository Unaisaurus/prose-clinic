"""Your own list of phrases and constructions to avoid (managed in Settings).

Pattern syntax
--------------
* Plain text matches that phrase, ignoring capitalisation:  ``heart pounding``
* ``*`` stands for one to four words:                      ``not * but *``
* ``re:`` starts a regular expression for experts:          ``re:\\bsuddenly\\b``
"""

from __future__ import annotations

import re

from ..text import Document
from .base import Rule, RuleContext, register

_WILDCARD = r"[\w'’-]+(?:\s+[\w'’-]+){0,3}?"


def compile_custom_pattern(pattern: str) -> re.Pattern | None:
    """Turn a user's phrase into a regex. Raises re.error for invalid regexes."""
    pattern = pattern.strip()
    if not pattern:
        return None
    if pattern.lower().startswith("re:"):
        return re.compile(pattern[3:].strip(), re.IGNORECASE)
    parts = []
    for token in pattern.split():
        if token == "*":
            parts.append(_WILDCARD)
        else:
            escaped = re.escape(token).replace("'", "['’]").replace("’", "['’]")
            parts.append(escaped.replace(r"\*", _WILDCARD))
    body = r"\s+".join(parts)
    if re.match(r"\w", pattern):
        body = r"\b" + body
    if re.search(r"\w$", pattern):
        body += r"\b"
    return re.compile(body, re.IGNORECASE)


def pattern_error(pattern: str) -> str | None:
    """A readable error for an invalid pattern, or None if it is fine."""
    try:
        compiled = compile_custom_pattern(pattern)
    except re.error as exc:
        return f"Invalid regular expression: {exc}"
    if compiled is not None and compiled.search("") is not None:
        return "This pattern matches empty text; make it more specific."
    return None


@register
class CustomPhrases(Rule):
    id = "custom_phrases"
    name = "Your custom phrases"
    category = "custom"
    description = "Phrases and constructions you've added in Settings → Custom phrases."

    def check(self, doc: Document, ctx: RuleContext):
        results = []
        for entry in ctx.custom_phrases:
            if not entry.get("enabled", True):
                continue
            pattern = (entry.get("pattern") or "").strip()
            try:
                regex = compile_custom_pattern(pattern)
            except re.error:
                continue
            if regex is None:
                continue
            note = (entry.get("note") or "").strip()
            for m in regex.finditer(doc.text):
                if m.end() <= m.start():
                    continue
                results.append(
                    self.finding(
                        doc,
                        m.start(),
                        m.end(),
                        note or "On your list of phrases and constructions to avoid.",
                        "Rephrase this in a way that sounds like you.",
                        title=f"Your list: “{pattern}”",
                    )
                )
        return results
