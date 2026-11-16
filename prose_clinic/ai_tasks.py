"""AI critic, targeted rewrites and full-passage revision (all optional).

Every AI output is checked by the rule-based analyzer afterwards, so a
"fix" that introduces new clichés or AI habits is flagged before you use it.
"""

from __future__ import annotations

import difflib
import html
import re
from dataclasses import dataclass, field

from .analyzer import run_rules
from .findings import CATEGORIES, Finding
from .llm import LLMConfig, LLMError, complete, parse_json_reply
from .text import Document

AI_CATEGORIES = ["dialogue", "voice", "emotion", "conflict", "purple", "cliche", "repetition", "formulaic", "tone", "character", "pacing", "other"]

AVOID_HABITS = """\
- "not X, but Y" or "It wasn't X. It was Y." framings; "Not X. Not Y. Just Z." fragment chains
- more em dashes or ellipses than the original used
- stock body language: jaws tightening, breath hitching, stomachs dropping, eyes widening, mouths quirking
- grand or abstract imagery: "like a promise", "a tapestry of emotions", "the weight of his words", "the silence stretched"
- naming or explaining emotions: "she felt a surge of relief", "a wave of guilt washed over him"
- therapy-speak, speechifying or over-articulate dialogue; characters who agree or apologise too readily; stock quips
- tidy reassurance, epiphanies or uplifting closing lines; weather that mirrors the mood
- rule-of-three lists, "the kind of X that", "both X and Y" paradoxes, "something shifted", "maybe, just maybe"
- AI-favoured names (Elara, Kael, Lyra, Seraphina…)"""

EDITOR_PRINCIPLES = """\
You are an editorial assistant, not a sanitizer. Distinguish deliberate stylistic choices from habits:
- A device used once, with purpose, is usually a choice. The same device used repeatedly, or in place of specificity, is usually a habit.
- Unusual is not wrong. Fragments, long sentences, repetition, formality, profanity, darkness or an unlikeable narrator can all be intentional.
- Never "fix" a story by making it nicer, safer, more resolved or more explained than the writer made it."""

CRITIC_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "quote": {"type": "string"},
                    "category": {"type": "string", "enum": AI_CATEGORIES},
                    "issue": {"type": "string"},
                    "explanation": {"type": "string"},
                    "suggestion": {"type": "string"},
                    "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                    "possibly_intentional": {"type": "boolean"},
                },
                "required": ["quote", "category", "issue", "explanation", "suggestion", "severity", "possibly_intentional"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "strengths", "findings"],
    "additionalProperties": False,
}

REWRITE_SCHEMA = {
    "type": "object",
    "properties": {
        "options": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"text": {"type": "string"}, "approach": {"type": "string"}},
                "required": ["text", "approach"],
                "additionalProperties": False,
            },
        },
        "keep_original_reason": {"type": "string"},
    },
    "required": ["options", "keep_original_reason"],
    "additionalProperties": False,
}


# ------------------------------------------------------------------- context
def _cdata(text: str) -> str:
    return text.replace("</", "<\\/")  # keep user text from closing our tags


def library_block(library: dict, ai_settings: dict) -> str:
    if not ai_settings.get("use_library", True):
        return ""
    parts = []
    notes = (library.get("style_notes") or "").strip()
    if notes:
        parts.append(f"<writer_style_notes>\n{_cdata(notes[:2500])}\n</writer_style_notes>")
    budget, chunks = 6000, []
    for sample in library.get("samples", []):
        text = (sample.get("text") or "").strip()
        if not sample.get("active", True) or not text or budget < 300:
            continue
        text = text[:budget]
        budget -= len(text)
        title = html.escape(sample.get("title") or "Sample", quote=True)
        chunks.append(f'<sample title="{title}">\n{_cdata(text)}\n</sample>')
    if chunks:
        parts.append(
            "<writer_style_samples>\nPassages showing the voice and style this writer wants. Use them to calibrate "
            "what natural, intentional prose means for this writer. Do not critique them.\n"
            + "\n".join(chunks)
            + "\n</writer_style_samples>"
        )
    budget, chunks = 5000, []
    for pair in library.get("pairs", []):
        before, after = (pair.get("before") or "").strip(), (pair.get("after") or "").strip()
        if not before or not after or budget < 200:
            continue
        why = (pair.get("why") or "").strip()
        chunk = f"<example>\n<before>{_cdata(before)}</before>\n<after>{_cdata(after)}</after>\n" + (
            f"<why>{_cdata(why)}</why>\n</example>" if why else "</example>"
        )
        budget -= len(chunk)
        chunks.append(chunk)
    if chunks:
        parts.append(
            "<before_after_examples>\nThe writer's own examples of weak prose and the improved version they prefer.\n"
            + "\n".join(chunks)
            + "\n</before_after_examples>"
        )
    return "\n\n".join(parts)


def feedback_block(feedback: dict, ai_settings: dict) -> str:
    if not ai_settings.get("use_feedback", True):
        return ""
    entries = list(feedback.get("entries", {}).values())
    false_pos = [e for e in entries if e.get("verdict") == "false_positive"][-15:]
    useful = [e for e in entries if e.get("verdict") == "useful"][-10:]
    lines = []
    if false_pos:
        lines.append("Flags the writer marked as FALSE POSITIVES (do not flag similar things):")
        lines += [f'- {e.get("title", "")}: "{_cdata(e.get("excerpt", "")[:120])}"' for e in false_pos]
    if useful:
        lines.append("Flags the writer found USEFUL (similar issues are worth raising):")
        lines += [f'- {e.get("title", "")}: "{_cdata(e.get("excerpt", "")[:120])}"' for e in useful]
    return "<writer_feedback>\n" + "\n".join(lines) + "\n</writer_feedback>" if lines else ""


def findings_digest(findings: list[Finding], limit: int = 40) -> str:
    grouped: dict[str, list[str]] = {}
    for f in findings:
        label = f.title
        excerpt = f.excerpt.strip().replace("\n", " ")
        grouped.setdefault(label, [])
        if excerpt and len(grouped[label]) < 3:
            grouped[label].append(excerpt[:90] + ("…" if len(excerpt) > 90 else ""))
    lines = []
    for label, excerpts in list(grouped.items())[:limit]:
        lines.append(f"- {label}" + (": " + " | ".join(f'"{_cdata(x)}"' for x in excerpts) if excerpts else ""))
    return "\n".join(lines)


# ------------------------------------------------------------ quote location
def _normalize_with_map(text: str) -> tuple[str, list[int]]:
    out, mapping = [], []
    replacements = {"“": '"', "”": '"', "‘": "'", "’": "'", "—": "-", "–": "-", "…": "..."}
    prev_space = False
    for i, ch in enumerate(text):
        if ch.isspace():
            if not prev_space:
                out.append(" ")
                mapping.append(i)
            prev_space = True
            continue
        prev_space = False
        for c in replacements.get(ch, ch).lower():
            out.append(c)
            mapping.append(i)
    return "".join(out), mapping


def locate_quote(text: str, quote: str) -> tuple[int, int] | None:
    """Find where an AI-quoted snippet sits in the passage (exact, normalised, then fuzzy)."""
    quote = (quote or "").strip().strip('"“”')
    if not quote:
        return None
    index = text.find(quote)
    if index != -1:
        return index, index + len(quote)
    norm_text, mapping = _normalize_with_map(text)
    norm_quote, _ = _normalize_with_map(quote)
    norm_quote = norm_quote.strip()
    index = norm_text.find(norm_quote)
    if index != -1 and norm_quote:
        return mapping[index], mapping[index + len(norm_quote) - 1] + 1
    matcher = difflib.SequenceMatcher(None, norm_text, norm_quote, autojunk=False)
    match = matcher.find_longest_match(0, len(norm_text), 0, len(norm_quote))
    if match.size >= max(12, int(len(norm_quote) * 0.6)):
        start = max(0, match.a - match.b)
        end = min(len(norm_text) - 1, start + len(norm_quote) - 1)
        return mapping[start], mapping[end] + 1
    return None


# -------------------------------------------------------------------- critic
@dataclass
class Critique:
    summary: str
    strengths: list[str]
    findings: list[Finding] = field(default_factory=list)
    unlocated: int = 0


CRITIC_SYSTEM = f"""You are an experienced fiction editor. A writer is revising prose that may have been drafted with AI help, and wants to remove habits that make fiction feel generic, formulaic, over-polished or machine-written, so the prose reads as human, varied, character-driven and stylistically intentional.

{EDITOR_PRINCIPLES}

A rule-based checker has already flagged mechanical patterns (counts of dashes, stock phrases, repeated openings and so on); they are listed for you. Concentrate on what pattern-matching cannot judge:
- dialogue: therapeutic, over-articulate, speechifying or overly agreeable lines; banter that performs wit instead of revealing character; exposition delivered as dialogue (category "dialogue")
- character voice: speakers who are interchangeable, or a voice drifting out of character (category "voice")
- emotional telling: feelings named or explained instead of conveyed through behaviour, choices and specific detail, or explained after they were already shown (category "emotion")
- conflict and stakes: tension that dissolves too easily, characters who concede or apologise too fast, endings that resolve too neatly or tell the reader how to feel (category "conflict")
- prose: purple or abstract language, vague metaphors, generic sensory detail, melodrama, stock body language (categories "purple", "cliche"); mechanical rhythm or structure ("repetition", "formulaic")
- tone and point of view slips ("tone"), flat or inconsistent characterisation ("character"), pacing problems ("pacing")

How to report:
- "quote" must be copied exactly, character for character, from the passage: the shortest span that shows the problem (a phrase or one sentence; never more than two sentences).
- Most important first. Quality over quantity: if the passage is strong, say so and report fewer findings.
- "explanation": plain language for a writer, saying why it weakens the prose. "suggestion": the direction of a fix, optionally with a very short example; do not rewrite whole paragraphs.
- If something might be a deliberate choice, set "possibly_intentional" to true and say in the explanation what would make it work.
- Repeat a rule-based flag only if you have something to add.
- "summary": two or three sentences on the passage's main AI-like habits and overall strength. "strengths": what already works and should be protected during revision."""


def run_critique(
    config: LLMConfig,
    text: str,
    rule_findings: list[Finding],
    library: dict,
    feedback: dict,
    ai_settings: dict,
) -> Critique:
    max_findings = int(ai_settings.get("max_findings", 15))
    blocks = [
        library_block(library, ai_settings),
        feedback_block(feedback, ai_settings),
        "<rule_based_flags>\n" + (findings_digest(rule_findings) or "(none)") + "\n</rule_based_flags>",
        f"<passage>\n{_cdata(text)}\n</passage>",
        f"Review the passage. Report at most {max_findings} findings.",
    ]
    reply = complete(config, CRITIC_SYSTEM, "\n\n".join(b for b in blocks if b), json_schema=CRITIC_SCHEMA)
    data = parse_json_reply(reply)
    critique = Critique(summary=str(data.get("summary", "")), strengths=[str(s) for s in data.get("strengths", [])])
    for item in data.get("findings", [])[: max_findings + 5]:
        if not isinstance(item, dict):
            continue
        quote = str(item.get("quote", ""))
        category = item.get("category") if item.get("category") in CATEGORIES else "other"
        severity = item.get("severity") if item.get("severity") in ("low", "medium", "high") else "medium"
        location = locate_quote(text, quote)
        finding = Finding(
            rule_id="ai_critic",
            category=category,
            title=str(item.get("issue", "AI critic")).strip() or "AI critic",
            message=str(item.get("explanation", "")).strip(),
            suggestion=str(item.get("suggestion", "")).strip(),
            severity=severity,
            source="ai",
            note="The critic thinks this may be deliberate; keep it if it is." if item.get("possibly_intentional") else "",
        )
        if location:
            finding.start, finding.end = location
            finding.excerpt = text[location[0] : location[1]]
        else:
            finding.excerpt = quote
            critique.unlocated += 1
        critique.findings.append(finding)
    return critique


# ------------------------------------------------------------------ rewrites
REWRITE_SYSTEM = f"""You are a careful line editor. You rewrite one small part of a work of fiction to fix a specific problem while keeping everything the writer intended.

{EDITOR_PRINCIPLES}

Non-negotiable:
- Preserve what happens, who does it, the meaning, the point of view, the tense, the character's voice and the intended tone.
- Rewrite only the target text. It must fit seamlessly between the text before and after it (no repeated or missing words at the joins).
- Do not add plot events, backstory, characters, or explanations of feelings.
- Prefer concrete, specific detail and plain, confident sentences. Keep roughly the same length unless the problem is wordiness.
- Do not introduce any of these habits:
{AVOID_HABITS}

Give two genuinely different options, each with a one-line "approach". If the target is actually effective as written (a deliberate choice that works), explain that in "keep_original_reason" and still offer two light alternatives; otherwise leave "keep_original_reason" empty."""


@dataclass
class RewriteResult:
    target_start: int
    target_end: int
    target_text: str
    options: list[dict]
    keep_original_reason: str = ""
    checks: list[list[str]] = field(default_factory=list)  # rule titles each option triggers


def rewrite_target(doc: Document, finding: Finding) -> tuple[int, int]:
    if finding.is_document_level:
        raise LLMError("Passage-wide findings can't be rewritten individually; use full-passage revision.")
    return doc.sentence_bounds(finding.start, finding.end)


def suggest_rewrite(
    config: LLMConfig,
    text: str,
    finding: Finding,
    library: dict,
    ai_settings: dict,
    settings: dict,
) -> RewriteResult:
    doc = Document(text)
    start, end = rewrite_target(doc, finding)
    target = text[start:end]
    problem = f"{finding.title}: {finding.message}"
    if finding.suggestion:
        problem += f"\nSuggested direction: {finding.suggestion}"
    blocks = [
        library_block(library, ai_settings),
        f"<context_before>\n{_cdata(text[max(0, start - 900):start])}\n</context_before>",
        f"<target>\n{_cdata(target)}\n</target>",
        f"<context_after>\n{_cdata(text[end:end + 500])}\n</context_after>",
        f'<problem flagged_text="{html.escape(finding.excerpt[:200], quote=True)}">\n{_cdata(problem)}\n</problem>',
        "Rewrite the target to fix the problem.",
    ]
    reply = complete(config, REWRITE_SYSTEM, "\n\n".join(b for b in blocks if b), json_schema=REWRITE_SCHEMA, max_tokens=16000)
    data = parse_json_reply(reply)
    options = [
        {"text": str(o.get("text", "")).strip(), "approach": str(o.get("approach", "")).strip()}
        for o in data.get("options", [])
        if isinstance(o, dict) and str(o.get("text", "")).strip()
    ][:3]
    if not options:
        raise LLMError("The AI didn't return a usable rewrite. Try again.")
    result = RewriteResult(start, end, target, options, str(data.get("keep_original_reason", "")).strip())
    result.checks = [check_new_habits(target, o["text"], settings) for o in options]
    return result


def check_new_habits(original: str, revised: str, settings: dict) -> list[str]:
    """Rule titles that fire on the revision but not on the original."""
    _d1, before, _e1 = run_rules(original, settings)
    _d2, after, _e2 = run_rules(revised, settings)
    old = {f.signature for f in before}
    titles = []
    for f in after:
        if f.signature not in old and not f.is_document_level and f.title not in titles:
            titles.append(f.title)
    return titles


# ------------------------------------------------------------ full revision
INTENSITY = {
    "Light": "Fix only the clearest problems listed below and leave everything else untouched. Expect to change roughly one sentence in six.",
    "Moderate": "Fix the listed problems and similar ones you notice, and loosen rhythm where it is mechanical. Most sentences should remain recognisable.",
    "Thorough": "Rework any sentence that reads as generic, formulaic or over-explained, keeping every story beat. Sentences may change substantially, but it must remain the same scene.",
}

REVISION_SYSTEM = f"""You are a skilled fiction editor revising a passage to remove formulaic, AI-sounding habits while preserving the writer's story and intent.

{EDITOR_PRINCIPLES}

Preserve: plot events and their order; characters, their relationships, what each knows and wants; point of view; tense; setting; and the intended tone. Keep what is said and decided in each exchange, while making the wording sound like real speech in each character's own voice. Keep the paragraph structure unless a change is clearly needed.

Do not:
- add events, backstory, characters, themes or explanations;
- soften conflict, resolve what the original leaves open, or make anyone kinder or wiser than written;
- introduce any of these habits:
{AVOID_HABITS}

Aim for prose that feels observed and specific: concrete detail, varied sentence rhythm, characters who sound distinct, subtext instead of stated feelings. Stay within about 15% of the original length.

Output format, exactly:
<revised_passage>
(the full revised passage)
</revised_passage>
<change_notes>
- (three to eight short bullets describing the main changes)
</change_notes>"""


@dataclass
class Revision:
    text: str
    notes: list[str]


def revise_passage(
    config: LLMConfig,
    text: str,
    issues: list[Finding],
    intensity: str,
    extra_instructions: str,
    library: dict,
    ai_settings: dict,
) -> Revision:
    blocks = [
        library_block(library, ai_settings),
        "<problems_to_fix>\n" + (findings_digest(issues, limit=60) or "(none listed: use your judgement)") + "\n</problems_to_fix>",
        f"<revision_intensity>{INTENSITY.get(intensity, INTENSITY['Moderate'])}</revision_intensity>",
        f"<writer_instructions>\n{_cdata(extra_instructions.strip())}\n</writer_instructions>" if extra_instructions.strip() else "",
        f"<passage>\n{_cdata(text)}\n</passage>",
        "Revise the passage.",
    ]
    reply = complete(config, REVISION_SYSTEM, "\n\n".join(b for b in blocks if b), max_tokens=64000)
    match = re.search(r"<revised_passage>\s*(.*?)\s*</revised_passage>", reply, re.DOTALL)
    if match:
        revised = match.group(1)
    elif "<revised_passage>" in reply:
        raise LLMError("The revision was cut off before it finished. Try a shorter passage.")
    else:
        revised = reply.split("<change_notes>")[0]
    revised = revised.strip().replace("<\\/", "</")
    notes_match = re.search(r"<change_notes>\s*(.*?)\s*(?:</change_notes>|$)", reply, re.DOTALL)
    notes = []
    if notes_match:
        notes = [line.strip(" -•*\t") for line in notes_match.group(1).splitlines() if line.strip(" -•*\t")]
    if not revised:
        raise LLMError("The AI returned an empty revision. Try again.")
    return Revision(revised, notes)


def compare_runs(original: str, revised: str, settings: dict) -> tuple[list[dict], list[Finding]]:
    """Rule counts before/after, and findings that are new in the revision."""
    _d1, before, _e1 = run_rules(original, settings)
    _d2, after, _e2 = run_rules(revised, settings)
    by_title_before: dict[str, int] = {}
    by_title_after: dict[str, int] = {}
    for f in before:
        by_title_before[f.title] = by_title_before.get(f.title, 0) + 1
    for f in after:
        by_title_after[f.title] = by_title_after.get(f.title, 0) + 1
    rows = []
    for title in sorted(set(by_title_before) | set(by_title_after)):
        b, a = by_title_before.get(title, 0), by_title_after.get(title, 0)
        if a != b:
            rows.append({"Issue": title, "Original": b, "Revision": a, "Change": a - b})
    rows.sort(key=lambda r: r["Change"])
    old = {f.signature for f in before}
    new = [f for f in after if not f.is_document_level and f.signature not in old]
    return rows, new
