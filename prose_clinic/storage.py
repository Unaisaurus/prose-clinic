"""Saving preferences, the style library and feedback as JSON files on this computer.

Everything lives in the ``user_data`` folder next to app.py (or the folder named
by the PROSE_CLINIC_DATA_DIR environment variable). API keys are never stored here.
"""

from __future__ import annotations

import copy
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

from .findings import Finding

DATA_DIR = Path(os.environ.get("PROSE_CLINIC_DATA_DIR") or Path(__file__).resolve().parent.parent / "user_data")

DEFAULT_MODEL = "claude-opus-5-5"

DEFAULT_SETTINGS: dict = {
    "rules": {},  # rule_id -> {"enabled": bool, "sensitivity": "low" | "medium" | "high"}
    "custom_phrases": [],  # [{"pattern": str, "note": str, "enabled": bool}]
    "ai": {
        "provider": "none",  # "none" | "anthropic" | "openai_compatible"
        "anthropic_model": DEFAULT_MODEL,
        "anthropic_effort": "high",
        "openai_base_url": "http://localhost:11434/v1",
        "openai_model": "llama3.1",
        "use_library": True,
        "use_feedback": True,
        "max_findings": 15,
    },
}
DEFAULT_LIBRARY: dict = {"style_notes": "", "samples": [], "pairs": []}
DEFAULT_FEEDBACK: dict = {"entries": {}}  # signature -> entry


def _path(name: str) -> Path:
    return DATA_DIR / name


def _read(name: str, default: dict) -> dict:
    path = _path(name)
    try:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else copy.deepcopy(default)
    except FileNotFoundError:
        return copy.deepcopy(default)
    except (OSError, json.JSONDecodeError):
        # Keep a copy of the unreadable file instead of silently overwriting it later.
        try:
            path.replace(path.with_suffix(f".broken-{datetime.now():%Y%m%d-%H%M%S}.json"))
        except OSError:
            pass
        return copy.deepcopy(default)


def _write(name: str, data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=DATA_DIR, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, _path(name))  # atomic: never leaves a half-written file
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _merge(defaults: dict, stored: dict) -> dict:
    merged = copy.deepcopy(defaults)
    for key, value in stored.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


# --------------------------------------------------------------------- settings
def load_settings() -> dict:
    return _merge(DEFAULT_SETTINGS, _read("settings.json", DEFAULT_SETTINGS))


def save_settings(settings: dict) -> None:
    _write("settings.json", settings)


# ---------------------------------------------------------------------- library
def load_library() -> dict:
    return _merge(DEFAULT_LIBRARY, _read("library.json", DEFAULT_LIBRARY))


def save_library(library: dict) -> None:
    _write("library.json", library)


# --------------------------------------------------------------------- feedback
def load_feedback() -> dict:
    data = _merge(DEFAULT_FEEDBACK, _read("feedback.json", DEFAULT_FEEDBACK))
    if not isinstance(data.get("entries"), dict):
        data["entries"] = {}
    return data


def save_feedback(feedback: dict) -> None:
    _write("feedback.json", feedback)


def set_verdict(feedback: dict, finding: Finding, verdict: str | None) -> None:
    """Record 'useful' / 'false_positive' for a finding (None clears it)."""
    entries = feedback.setdefault("entries", {})
    if verdict is None:
        entries.pop(finding.signature, None)
        return
    entries[finding.signature] = {
        "verdict": verdict,
        "rule_id": finding.rule_id,
        "source": finding.source,
        "title": finding.title,
        "excerpt": finding.excerpt[:300],
        "message": finding.message[:300],
        "date": datetime.now().isoformat(timespec="seconds"),
    }


def verdict_for(feedback: dict, finding: Finding) -> str | None:
    entry = feedback.get("entries", {}).get(finding.signature)
    return entry["verdict"] if entry else None


def false_positive_signatures(feedback: dict) -> set[str]:
    return {sig for sig, e in feedback.get("entries", {}).items() if e.get("verdict") == "false_positive"}


def feedback_stats(feedback: dict) -> dict[str, dict[str, int]]:
    stats: dict[str, dict[str, int]] = {}
    for entry in feedback.get("entries", {}).values():
        row = stats.setdefault(entry.get("rule_id", "?"), {"useful": 0, "false_positive": 0})
        if entry.get("verdict") in row:
            row[entry["verdict"]] += 1
    return stats


# ----------------------------------------------------------------------- drafts
def archive_draft(original: str, draft: str) -> Path | None:
    """Keep a copy of a revision draft before it is replaced."""
    if not draft.strip() or draft == original:
        return None
    folder = DATA_DIR / "drafts"
    folder.mkdir(parents=True, exist_ok=True)
    first_words = re.sub(r"[^A-Za-z0-9]+", "-", " ".join(original.split()[:5])).strip("-")[:40] or "draft"
    path = folder / f"{datetime.now():%Y-%m-%d_%H%M%S}_{first_words}.txt"
    path.write_text(f"=== REVISED DRAFT ===\n\n{draft}\n\n=== ORIGINAL ===\n\n{original}\n", encoding="utf-8")
    return path


# ----------------------------------------------------------------------- backup
def export_all(settings: dict, library: dict, feedback: dict) -> str:
    return json.dumps(
        {"app": "prose-clinic", "version": 1, "settings": settings, "library": library, "feedback": feedback},
        ensure_ascii=False,
        indent=2,
    )


def parse_backup(raw: bytes | str) -> tuple[dict, dict, dict]:
    """Validate a backup file. Raises ValueError with a readable message."""
    try:
        data = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise ValueError("That file isn't valid JSON.") from exc
    if not isinstance(data, dict) or data.get("app") != "prose-clinic":
        raise ValueError("That doesn't look like a Prose Clinic backup file.")
    settings = _merge(DEFAULT_SETTINGS, data.get("settings") or {})
    library = _merge(DEFAULT_LIBRARY, data.get("library") or {})
    feedback = _merge(DEFAULT_FEEDBACK, data.get("feedback") or {})
    return settings, library, feedback
