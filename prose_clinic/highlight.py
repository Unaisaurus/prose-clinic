"""HTML rendering: highlighted passages, findings in context, and side-by-side diffs."""

from __future__ import annotations

import difflib
import html
import re

from .findings import Finding, category_color

LONG_SPAN = 80  # spans longer than this are underlined instead of shaded

STYLE = """
<style>
.pc-text { font-family: Georgia, 'Iowan Old Style', 'Times New Roman', serif; font-size: 1.04rem;
           line-height: 1.8; white-space: pre-wrap; overflow-wrap: anywhere; }
.pc-hl { border-radius: 3px; padding: 1px 0; }
.pc-ul { text-decoration-line: underline; text-decoration-thickness: 2px; text-underline-offset: 4px; }
.pc-mark { font-weight: 700; border-radius: 3px; }
.pc-num { font-family: system-ui, sans-serif; font-size: 0.62em; font-weight: 700; vertical-align: super;
          padding: 0 4px; margin: 0 1px; border-radius: 8px; color: #fff; white-space: nowrap; }
.pc-snippet { font-family: Georgia, 'Times New Roman', serif; font-size: 0.98rem; line-height: 1.6;
              border-left: 3px solid rgba(127,127,127,0.45); padding: 2px 0 2px 10px; margin: 2px 0 6px 0;
              white-space: pre-wrap; overflow-wrap: anywhere; }
.pc-del { background: rgba(231, 76, 60, 0.28); text-decoration: line-through; text-decoration-color: rgba(192,57,43,0.8); }
.pc-ins { background: rgba(39, 174, 96, 0.30); text-decoration: none; }
.pc-legend span { display: inline-block; margin: 0 10px 4px 0; padding: 0 6px; border-radius: 4px;
                  font-family: system-ui, sans-serif; font-size: 0.8rem; }
</style>
"""


def _esc(text: str) -> str:
    return html.escape(text, quote=False)


def _attr(text: str) -> str:
    return html.escape(text, quote=True).replace("\n", "&#10;")


def render_highlighted(text: str, findings: list[Finding], numbers: dict[str, int]) -> str:
    """The passage with each finding shaded (short spans) or underlined (long spans)."""
    spans = [f for f in findings if not f.is_document_level and f.end > f.start]
    if not spans:
        return STYLE + f'<div class="pc-text">{_esc(text)}</div>'
    # Sweep through the text once, tracking which findings and marks cover each segment.
    opens: dict[int, list] = {}
    closes: dict[int, list] = {}
    for f in spans:
        opens.setdefault(f.start, []).append(("f", f))
        closes.setdefault(f.end, []).append(("f", f))
        for a, b in f.marks or []:
            if b > a:
                opens.setdefault(a, []).append(("m", f))
                closes.setdefault(b, []).append(("m", f))
    points = sorted({0, len(text), *opens, *closes})
    active: dict[int, Finding] = {}
    active_marks: list[Finding] = []
    out = [STYLE, '<div class="pc-text">']
    for a, b in zip(points, points[1:]):
        for kind, f in closes.get(a, []):
            if kind == "f":
                active.pop(id(f), None)
            elif f in active_marks:
                active_marks.remove(f)
        starting = []
        for kind, f in opens.get(a, []):
            if kind == "f":
                active[id(f)] = f
                starting.append(f)
            else:
                active_marks.append(f)
        for f in sorted(starting, key=lambda x: numbers.get(x.uid, 0)):
            out.append(f'<span class="pc-num" style="background: rgb({category_color(f.category)});">{numbers.get(f.uid, "")}</span>')
        segment = _esc(text[a:b])
        if not active:
            out.append(segment)
            continue
        covering = list(active.values())
        short = [f for f in covering if f.end - f.start <= LONG_SPAN]
        long = [f for f in covering if f.end - f.start > LONG_SPAN]
        styles, classes = [], []
        if short:
            innermost = min(short, key=lambda f: f.end - f.start)
            styles.append(f"background: rgba({category_color(innermost.category)}, 0.30);")
            classes.append("pc-hl")
        if long:
            outer = min(long, key=lambda f: f.end - f.start)
            styles.append(f"text-decoration-color: rgb({category_color(outer.category)});")
            classes.append("pc-ul")
        if active_marks:
            styles.append(f"background: rgba({category_color(active_marks[-1].category)}, 0.45);")
            classes.append("pc-mark")
        tip = " · ".join(f"[{numbers.get(f.uid, '?')}] {f.title}" for f in sorted(covering, key=lambda x: numbers.get(x.uid, 0)))
        out.append(f'<span class="{" ".join(classes)}" style="{" ".join(styles)}" title="{_attr(tip)}">{segment}</span>')
    out.append("</div>")
    return "".join(out)


def render_in_context(text: str, finding: Finding, context_chars: int = 140) -> str:
    """A short snippet around a finding, with the flagged part marked."""
    if finding.is_document_level:
        return ""
    start, end = finding.start, finding.end
    left = max(0, start - context_chars)
    right = min(len(text), end + context_chars)
    # Snap to sentence-ish boundaries so the snippet reads naturally.
    head = text[left:start]
    cut = max(head.rfind(". "), head.rfind("\n"), head.rfind("? "), head.rfind("! "))
    if cut != -1 and left > 0:
        left += cut + 1
    tail = text[end:right]
    stop = min((i for i in (tail.find(". "), tail.find("\n"), tail.find("? "), tail.find("! ")) if i != -1), default=-1)
    if stop != -1:
        right = end + stop + 1
    color = category_color(finding.category)
    flagged = text[start:end]
    if len(flagged) > 420:
        flagged = flagged[:200] + " … " + flagged[-180:]
    body = (
        ("…" if left > 0 else "")
        + _esc(text[left:start].lstrip())
        + f'<span class="pc-hl" style="background: rgba({color}, 0.35);">{_esc(flagged)}</span>'
        + _esc(text[end:right].rstrip())
        + ("…" if right < len(text) else "")
    )
    return STYLE + f'<div class="pc-snippet">{body}</div>'


_TOKENS = re.compile(r"\s+|[^\s]+")


def render_diff(original: str, revised: str) -> tuple[str, str]:
    """Word-level diff: deletions marked in the original, insertions in the revision."""
    a, b = _TOKENS.findall(original), _TOKENS.findall(revised)
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    left, right = [], []
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        old, new = "".join(a[i1:i2]), "".join(b[j1:j2])
        if op == "equal":
            left.append(_esc(old))
            right.append(_esc(new))
            continue
        if old:
            left.append(f'<span class="pc-del">{_esc(old)}</span>')
        if new:
            right.append(f'<span class="pc-ins">{_esc(new)}</span>')
    def wrap(parts: list[str]) -> str:
        return STYLE + '<div class="pc-text">' + "".join(parts) + "</div>"

    return wrap(left), wrap(right)


def change_ratio(original: str, revised: str) -> float:
    """Share of words changed (0 = identical, 1 = completely different)."""
    a, b = original.split(), revised.split()
    if not a and not b:
        return 0.0
    return 1 - difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def legend(categories: list[str], labels: dict[str, str]) -> str:
    chips = "".join(
        f'<span style="background: rgba({category_color(c)}, 0.30);">{_esc(labels.get(c, c))}</span>' for c in categories
    )
    return STYLE + f'<div class="pc-legend">{chips}</div>'
