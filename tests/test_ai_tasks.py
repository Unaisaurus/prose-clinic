"""AI features, tested with a fake model (no network, no API key)."""

import json

import pytest

from prose_clinic import ai_tasks, llm
from prose_clinic.analyzer import analyze
from prose_clinic.findings import Finding
from prose_clinic.llm import LLMConfig, LLMError, parse_json_reply
from prose_clinic.sample_text import SAMPLE_PASSAGE

CONFIG = LLMConfig(provider="anthropic", model="claude-opus-5-5", api_key="test")
AI = {"use_library": True, "use_feedback": True, "max_findings": 10}


@pytest.fixture()
def fake_model(monkeypatch):
    calls = []

    def install(reply):
        def fake_complete(config, system, user, *, json_schema=None, max_tokens=32000):
            calls.append({"system": system, "user": user, "schema": json_schema})
            return reply(user) if callable(reply) else reply

        monkeypatch.setattr(ai_tasks, "complete", fake_complete)
        return calls

    return install


def test_critique_locates_quotes_and_uses_library(fake_model):
    reply = json.dumps({
        "summary": "Over-polished.",
        "strengths": ["Clear scene."],
        "findings": [
            {"quote": "your feelings are valid", "category": "dialogue", "issue": "Therapy-speak",
             "explanation": "Nobody talks like this.", "suggestion": "Deflect.", "severity": "high",
             "possibly_intentional": False},
            {"quote": "You’re right,” Mara admitted", "category": "conflict", "issue": "Caves too fast",
             "explanation": "x", "suggestion": "y", "severity": "medium", "possibly_intentional": True},
            {"quote": "a sentence that is not there at all", "category": "nonsense", "issue": "?",
             "explanation": "", "suggestion": "", "severity": "weird", "possibly_intentional": False},
        ],
    })
    calls = fake_model(reply)
    library = {"style_notes": "Dry humour.", "samples": [{"title": "S", "text": "My prose.", "active": True}], "pairs": []}
    feedback = {"entries": {"x": {"verdict": "false_positive", "title": "Clichés", "excerpt": "time stood still"}}}
    critique = ai_tasks.run_critique(CONFIG, SAMPLE_PASSAGE, analyze(SAMPLE_PASSAGE, {}).findings, library, feedback, AI)
    assert critique.summary == "Over-polished."
    first, second, third = critique.findings
    assert SAMPLE_PASSAGE[first.start : first.end] == "your feelings are valid"
    assert second.start is not None and "Mara admitted" in second.excerpt  # curly quotes normalised
    assert second.note  # possibly intentional
    assert third.start is None and third.category == "other" and third.severity == "medium"
    assert critique.unlocated == 1
    prompt = calls[0]["user"]
    assert "Dry humour." in prompt and "My prose." in prompt and "time stood still" in prompt
    assert calls[0]["schema"] == ai_tasks.CRITIC_SCHEMA


def test_library_and_feedback_can_be_excluded(fake_model):
    calls = fake_model(json.dumps({"summary": "", "strengths": [], "findings": []}))
    library = {"style_notes": "SECRET-NOTES", "samples": [], "pairs": []}
    ai_tasks.run_critique(CONFIG, SAMPLE_PASSAGE, [], library, {"entries": {}}, {"use_library": False, "use_feedback": False})
    assert "SECRET-NOTES" not in calls[0]["user"]


def test_rewrite_targets_whole_sentence_and_rechecks(fake_model):
    reply = json.dumps({
        "options": [
            {"text": "She nodded.", "approach": "Trim"},
            {"text": "She nodded, her heart pounding. The silence stretched.", "approach": "Cliché-laden"},
        ],
        "keep_original_reason": "",
    })
    fake_model(reply)
    finding = next(f for f in analyze(SAMPLE_PASSAGE, {}).findings if f.excerpt == "nodded her head")
    result = ai_tasks.suggest_rewrite(CONFIG, SAMPLE_PASSAGE, finding, {}, AI, {})
    assert result.target_text == "She nodded her head slowly."
    assert result.checks[0] == []
    assert result.checks[1]  # the second option introduces flagged habits


def test_rewrite_rejects_document_level(fake_model):
    fake_model("{}")
    doc_finding = Finding("em_dashes", "punctuation", "Heavy em dashes", "m", "s")
    with pytest.raises(LLMError):
        ai_tasks.suggest_rewrite(CONFIG, SAMPLE_PASSAGE, doc_finding, {}, AI, {})


def test_full_revision_parsing_and_comparison(fake_model):
    revised = SAMPLE_PASSAGE.replace("She nodded her head slowly.", "She nodded.")
    fake_model(f"<revised_passage>\n{revised}\n</revised_passage>\n<change_notes>\n- Trimmed redundancy\n- Kept plot\n</change_notes>")
    rev = ai_tasks.revise_passage(CONFIG, SAMPLE_PASSAGE, [], "Light", "Keep the ending.", {}, AI)
    assert rev.text == revised and rev.notes == ["Trimmed redundancy", "Kept plot"]
    rows, new = ai_tasks.compare_runs(SAMPLE_PASSAGE, rev.text, {})
    assert any(r["Change"] < 0 for r in rows)
    assert new == []


def test_truncated_revision_is_an_error(fake_model):
    fake_model("<revised_passage>\nThe start of a revision that never")
    with pytest.raises(LLMError):
        ai_tasks.revise_passage(CONFIG, SAMPLE_PASSAGE, [], "Light", "", {}, AI)


def test_locate_quote_variants():
    text = "He said, “It’s fine—really.”\nShe left."
    assert ai_tasks.locate_quote(text, "It's fine-really.") is not None
    s, e = ai_tasks.locate_quote(text, "She left.")
    assert text[s:e] == "She left."
    assert ai_tasks.locate_quote(text, "completely different words entirely") is None


def test_parse_json_reply():
    assert parse_json_reply('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_reply('Sure! {"a": 2} hope that helps') == {"a": 2}
    with pytest.raises(LLMError):
        parse_json_reply("no json here")


def test_find_api_key_order(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "from-env")
    assert llm.find_api_key("anthropic", {}, {})[0] == "from-env"
    assert llm.find_api_key("anthropic", {}, {"ANTHROPIC_API_KEY": "from-secrets"})[0] == "from-secrets"
    assert llm.find_api_key("anthropic", {"anthropic": "typed"}, {"ANTHROPIC_API_KEY": "x"})[0] == "typed"


def test_anthropic_request_shape(monkeypatch):
    """The Claude request uses streaming, structured output, effort and refusal fallbacks."""
    import anthropic

    captured = {}

    class FakeStream:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get_final_message(self):
            block = type("B", (), {"type": "text", "text": '{"ok": true}'})()
            return type("M", (), {"stop_reason": "end_turn", "content": [block]})()

    class FakeMessages:
        def stream(self, **kwargs):
            captured.update(kwargs)
            return FakeStream()

    class FakeClient:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.beta = type("Beta", (), {"messages": FakeMessages()})()

    monkeypatch.setattr(anthropic, "Anthropic", FakeClient)
    reply = llm.complete(
        LLMConfig("anthropic", "claude-opus-5-5", api_key="k", effort="high"), "sys", "user", json_schema={"type": "object"}
    )
    assert reply == '{"ok": true}'
    assert captured["client"] == {"api_key": "k"}
    assert captured["output_config"] == {"effort": "high", "format": {"type": "json_schema", "schema": {"type": "object"}}}
    assert captured["fallbacks"] == "default" and captured["betas"] == ["server-side-fallback-2026-07-01"]
    assert "temperature" not in captured
    captured.clear()
    llm.complete(LLMConfig("anthropic", "claude-haiku-5-5", api_key="k", effort="default"), "s", "u")
    assert "fallbacks" not in captured and "output_config" not in captured


def test_openai_compatible_request(monkeypatch):
    import requests

    captured = {}

    class FakeResponse:
        status_code, ok = 200, True

        def json(self):
            return {"choices": [{"message": {"content": "<think>hmm</think>Hello"}}]}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured.update(url=url, json=json, headers=headers)
        return FakeResponse()

    monkeypatch.setattr(requests, "post", fake_post)
    cfg = LLMConfig("openai_compatible", "llama3.1", base_url="http://localhost:11434/v1/")
    assert llm.complete(cfg, "sys", "user") == "Hello"
    assert captured["url"] == "http://localhost:11434/v1/chat/completions"
    assert "Authorization" not in captured["headers"]


def test_openai_compatible_connection_error(monkeypatch):
    import requests

    def boom(*a, **k):
        raise requests.exceptions.ConnectionError("refused")

    monkeypatch.setattr(requests, "post", boom)
    with pytest.raises(LLMError, match="running"):
        llm.complete(LLMConfig("openai_compatible", "m", base_url="http://localhost:9"), "s", "u")
