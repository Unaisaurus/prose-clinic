from prose_clinic.sample_text import SAMPLE_PASSAGE
from prose_clinic.text import Document, normalize_for_match, split_sentences


def test_sentence_splitting_handles_dialogue_tags_and_abbreviations():
    text = (
        '"Wait," she said. "Don\'t go." Mr. Smith looked up. "Why?" he asked... then paused. '
        '"I just—" "No." She left. It cost $3.50 at the St. Louis shop. "Run!" Tom shouted. See No. 5 for details.'
    )
    assert split_sentences(text) == [
        '"Wait," she said.',
        '"Don\'t go."',
        "Mr. Smith looked up.",
        '"Why?" he asked... then paused.',
        '"I just—"',
        '"No."',
        "She left.",
        "It cost $3.50 at the St. Louis shop.",
        '"Run!" Tom shouted.',
        "See No. 5 for details.",
    ]


def test_offsets_point_into_original_text():
    doc = Document(SAMPLE_PASSAGE)
    for s in doc.sentences:
        assert SAMPLE_PASSAGE[s.start : s.end] == s.text
    for p in doc.paragraphs:
        assert SAMPLE_PASSAGE[p.start : p.end] == p.text


def test_scene_breaks_and_headings_are_not_paragraphs():
    doc = Document("# Chapter One\n\nShe ran.\n\n***\n\nHe followed.")
    assert [p.text for p in doc.paragraphs] == ["She ran.", "He followed."]


def test_dialogue_detection_and_speakers():
    doc = Document(SAMPLE_PASSAGE)
    assert doc.names == {"Mara", "Elias"}
    speakers = {line.speech[:20]: line.speaker for line in doc.dialogue}
    assert speakers["You came,"] == "Mara"
    assert speakers["Of course I came."] == "Elias"  # action beat
    assert speakers["You've been grieving"] == "Elias"  # alternation across a short narration paragraph
    narration = doc.sentences[0]
    assert narration.is_narration and narration.dialogue_ratio == 0


def test_british_single_quote_dialogue_ignores_apostrophes():
    doc = Document("‘Hello,’ she said. ‘I’m here.’ The dogs’ bones lay there. ‘Tis odd, said Tom’s mother. ‘Go away!’ Tom shouted.")
    assert doc.dialogue_mode == "single"
    assert [line.text for line in doc.dialogue] == ["‘Hello,’", "‘I’m here.’", "‘Go away!’"]


def test_normalize_for_match():
    assert normalize_for_match("  “Don’t   GO…” ") == "don't go"
