from conftest import sample

from prose_clinic.analyzer import analyze, run_rules, text_stats
from prose_clinic.rules import all_rules
from prose_clinic.sample_text import SAMPLE_PASSAGE


def density(text: str) -> float:
    a = analyze(text, {})
    assert a.errors == []
    return len(a.findings) / a.doc.word_count * 1000


def test_ai_flavoured_text_is_flagged_heavily():
    a = analyze(SAMPLE_PASSAGE, {})
    rule_ids = {f.rule_id for f in a.findings}
    for expected in [
        "not_x_but_y", "negation_reveal", "not_fragment_chain", "therapy_speak", "named_emotions",
        "ai_stock_phrases", "forced_wit", "softened_conflict", "neat_resolution", "redundancy", "repeated_openers",
    ]:
        assert expected in rule_ids, expected
    assert density(SAMPLE_PASSAGE) > 100
    assert density(sample("ai_fantasy.txt")) > 80


def test_human_prose_gets_few_flags():
    """Calibration: natural human-written passages should stay quiet."""
    assert density(sample("human_a.txt")) < 15
    assert density(sample("human_b.txt")) < 15
    assert density(sample("austen.txt")) < 20  # only the (deliberately) formal dialogue


def test_disabled_rules_do_not_run():
    settings = {"rules": {r.id: {"enabled": False} for r in all_rules()}}
    assert analyze(SAMPLE_PASSAGE, settings).findings == []


def test_sensitivity_changes_results():
    text = "It was the kind of silence that hurt."
    low = analyze(text, {"rules": {"kind_of_x_that": {"sensitivity": "low"}}})
    high = analyze(text, {"rules": {"kind_of_x_that": {"sensitivity": "high"}}})
    assert not any(f.rule_id == "kind_of_x_that" for f in low.findings)
    assert any(f.rule_id == "kind_of_x_that" for f in high.findings)


def test_false_positives_are_suppressed():
    first = analyze(SAMPLE_PASSAGE, {})
    target = next(f for f in first.findings if f.rule_id == "redundancy")
    second = analyze(SAMPLE_PASSAGE, {}, false_positives={target.signature})
    assert target.signature not in {f.signature for f in second.findings}
    assert target.signature in {f.signature for f in second.suppressed}


def test_a_crashing_rule_is_reported_not_fatal(monkeypatch):
    from prose_clinic.rules import get_rule

    rule = get_rule("cliches")
    monkeypatch.setattr(rule, "check", lambda doc, ctx: 1 / 0)
    a = analyze(SAMPLE_PASSAGE, {})
    assert a.findings and any("Clichés" in e for e in a.errors)


def test_findings_are_sorted_and_within_text():
    _doc, findings, _errors = run_rules(SAMPLE_PASSAGE, {})
    spans = [f for f in findings if not f.is_document_level]
    assert spans == sorted(spans, key=lambda f: (f.start, -f.end))
    for f in spans:
        assert 0 <= f.start < f.end <= len(SAMPLE_PASSAGE)
        assert SAMPLE_PASSAGE[f.start : f.end] == f.excerpt


def test_empty_text():
    a = analyze("   ", {})
    assert a.findings == [] and a.errors == []


def test_text_stats():
    a = analyze(SAMPLE_PASSAGE, {})
    stats = text_stats(a.doc)
    assert stats["words"] == a.doc.word_count
    assert len(stats["sentence_lengths"]) == stats["sentences"]
    assert 0 < stats["dialogue_share"] < 1


def test_long_text_is_fast_enough():
    import time

    text = "\n\n".join([SAMPLE_PASSAGE] * 15)  # ~5,000 words
    start = time.perf_counter()
    analyze(text, {})
    assert time.perf_counter() - start < 10


def test_huge_texts_are_capped_and_render_quickly():
    import time

    from prose_clinic.analyzer import MAX_PER_RULE
    from prose_clinic.highlight import render_highlighted

    text = "\n\n".join([SAMPLE_PASSAGE] * 40)  # ~13,000 words of dense AI habits
    a = analyze(text, {})
    per_rule = a.counts_by_rule()
    assert max(per_rule.values()) <= MAX_PER_RULE + 2  # spans + "more not listed" note + passage-wide note
    assert any("more not listed" in f.title for f in a.findings)
    start = time.perf_counter()
    html = render_highlighted(text, a.findings, {f.uid: i for i, f in enumerate(a.findings)})
    assert time.perf_counter() - start < 2 and len(html) < 5_000_000
