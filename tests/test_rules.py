"""Each rule should catch its target pattern and leave ordinary prose alone."""

import pytest

from prose_clinic.rules import RuleContext, all_rules, get_rule
from prose_clinic.text import Document


def hits(rule_id: str, text: str, sensitivity: str = "medium", custom=None) -> list[str]:
    rule = get_rule(rule_id)
    assert rule is not None, rule_id
    findings = rule.check(Document(text), RuleContext(sensitivity=sensitivity, custom_phrases=custom or []))
    return [f.excerpt for f in findings]


def test_every_rule_is_well_formed():
    ids = [r.id for r in all_rules()]
    assert len(ids) == len(set(ids))
    for rule in all_rules():
        assert rule.name and rule.description and rule.category
        assert rule.check(Document(""), RuleContext()) == []  # empty text never crashes


@pytest.mark.parametrize(
    "text",
    [
        "It was not anger, but grief.",
        "Not because he was wrong, not because she didn't want him there, but because she did.",
        "He came not to fight, but to talk.",
        "It wasn't the cold, not the dark, but the silence.",
    ],
)
def test_not_x_but_y_positive(text):
    assert hits("not_x_but_y", text)


@pytest.mark.parametrize(
    "text",
    [
        "I didn't know, but I guessed.",
        "She did not want to go but had to.",
        "It wasn't much, but it was home.",
        "He couldn't sleep, but he tried anyway.",
    ],
)
def test_not_x_but_y_negative(text):
    assert hits("not_x_but_y", text) == []


def test_negation_reveal():
    assert hits("negation_reveal", "It wasn't anger. It was grief.")
    assert hits("negation_reveal", "I'm not angry. I'm disappointed.")
    assert hits("negation_reveal", "This isn't about money. It's about respect.")
    assert hits("negation_reveal", "It wasn't fear—it was relief.")
    assert hits("negation_reveal", "It wasn't much, but it was home.") == []
    assert hits("negation_reveal", "She wasn't hungry. Tom was.") == []


def test_not_fragment_chain():
    assert hits("not_fragment_chain", "Not forgiveness. Not yet. But something close to it.")
    assert hits("not_fragment_chain", "No anger. Just exhaustion.")
    assert hits("not_fragment_chain", "Not now, she thought, and went back to the dishes.") == []


def test_paradox_pairs_and_kind_of():
    assert hits("paradox_pairs", "It was both a warning and a promise.")
    assert hits("paradox_pairs", "a sound half laugh, half sob")
    assert hits("paradox_pairs", "It was less a question than an accusation.")
    text = "It was the kind of silence that hurt. He had the kind of face you forget."
    assert len(hits("kind_of_x_that", text)) == 2
    assert hits("kind_of_x_that", "It was the kind of silence that hurt.") == []  # once is fine at medium
    assert hits("kind_of_x_that", "It was the kind of silence that hurt.", "high")


def test_rhetorical_questions_and_reversal_tags():
    assert hits("rhetorical_questions", "What did it mean? Was she wrong? Could she ever forgive him?")
    assert hits("rhetorical_questions", '"Where?" he asked. "Why?" "When?"') == []  # dialogue
    assert hits("reversal_tags", "She thought it was over. Except it wasn't.")
    assert hits("reversal_tags", "Little did she know what waited.")


def test_repeated_openers_and_anaphora_note():
    text = "She stood. She thought about the letter. She thought about her mother. She waited."
    found = get_rule("repeated_openers").check(Document(text), RuleContext())
    assert found and "anaphora" in found[0].note
    assert hits("repeated_openers", "She stood. The kettle hissed. He came in. She smiled.") == []


def test_sentence_rhythm_monotony():
    monotone = " ".join(["The man walked slowly down the long and empty road."] * 7)
    assert hits("sentence_rhythm", monotone)
    varied = (
        "Rain. The man walked slowly down the long road that wound toward the river and the mill beyond it. "
        "He stopped. Somewhere behind him a door banged twice, and a dog started up, then thought better of it. "
        "Nothing else. He went on."
    )
    assert hits("sentence_rhythm", varied) == []


def test_word_echo_and_repeated_phrases():
    assert hits("word_echo", "The darkness pressed in. She stared into the darkness. The darkness seemed alive.")
    assert hits("word_echo", '"Single?" "Single, yes. A single man."') == []  # dialogue is skipped
    text = "She thought about her mother. She thought about the letter. She thought about everything."
    assert len(hits("repeated_phrases", text)) == 3


def test_syntax_echo():
    text = (
        "She looked at the door, her heart pounding. He turned to the window, his breath catching. "
        "She stared at the floor, her hands shaking."
    )
    assert len(hits("syntax_echo", text)) == 3


def test_em_dash_density_counts_but_spares_interruptions():
    heavy = "She ran—fast—toward the gate. He followed—slowly. The dog barked—once. " * 3
    assert hits("em_dashes", heavy)
    assert hits("em_dashes", '"I just—" she began. "No," he said.' * 10) == []
    assert hits("em_dashes", "She ran toward the gate—and stopped. " + "Plain words here. " * 60) == []


def test_ellipses_density():
    assert hits("ellipses", "Well... maybe... I don't know... " * 3)
    assert hits("ellipses", "Well... " + "Plain words follow here. " * 100) == []


def test_dramatic_fragments():
    text = "Silence. She waited by the door for an hour. Nothing. Then the phone rang. Gone. Rain."
    assert hits("dramatic_fragments", text)
    clean = "The radiator knocks. I call Reyes. He decides not to. The door opened."
    assert hits("dramatic_fragments", clean) == []


def test_purple_prose_rules():
    assert hits("abstract_imagery", "It settled over her like a promise.")
    assert hits("abstract_imagery", "a symphony of emotions")
    assert hits("abstract_imagery", "The world itself held its breath.")
    assert hits("melodrama", "Her heart shattered into a million pieces.")
    assert hits("abstraction", "The weight of her grief settled into the silence of her loneliness and despair.")
    assert hits("intensifiers", "an impossibly blue sky")
    assert hits("qualifier_stacking", "She smiled, almost sadly, somehow a little too quickly.")


def test_stock_phrases_cliches_and_redundancy():
    assert hits("ai_stock_phrases", "She let out a breath she didn't know she was holding.")
    assert hits("ai_stock_phrases", "Maybe, just maybe, it would work.")
    assert hits("cliches", "A chill ran down her spine.")
    found = get_rule("redundancy").check(Document("She nodded her head and whispered quietly."), RuleContext())
    assert [(f.excerpt, f.replacement) for f in found] == [("nodded her head", "nodded"), ("whispered quietly", "whispered")]
    found = get_rule("redundancy").check(Document("Nodded his head."), RuleContext())
    assert found[0].replacement == "Nodded"  # keeps capitalisation


def test_stock_body_language_only_when_piled_up():
    one = "Her jaw tightened."
    many = "Her jaw tightened. Her breath hitched. His eyes widened. She swallowed hard."
    assert hits("stock_body_language", one) == []
    assert len(hits("stock_body_language", many)) == 4


def test_ai_names_flags_first_use_only():
    assert hits("ai_names", "Elara ran. Elara stopped. Kael waited.") == ["Elara", "Kael"]


def test_dialogue_rules():
    assert hits("therapy_speak", '"Your feelings are valid," he said.')
    assert hits("therapy_speak", "Her feelings are valid, she decided.") == []  # narration
    agreeable = '"You\'re right." "That\'s fair." "I understand." "Fair enough."'
    assert len(hits("agreeable_dialogue", agreeable)) == 4
    assert hits("agreeable_dialogue", '"You\'re right," she said.') == []
    assert hits("speechifying", '"Maybe that\'s what love is," she said.')
    assert hits("as_you_know", '"As you know, the treaty expires tomorrow."')
    wit = '"Well, that went well." He smirked. "Note to self: run."'
    assert len(hits("forced_wit", wit)) == 3


def test_dialogue_tags():
    found = hits("dialogue_tags", '"Fine," he smirked. "Go," she said softly.')
    assert "smirked" in found and "softly" in found


def test_vocative_overuse():
    text = (
        '"Sarah, listen." Tom said.\n"I know, Tom." Sarah said.\n"Sarah, please."\n'
        '"No, Tom."\n"Sarah, wait."'
    )
    assert hits("vocative_overuse", text)


def test_polished_dialogue():
    found = get_rule("polished_dialogue").check(
        Document('"I am not certain; I do not believe it is wise," she said.'), RuleContext()
    )
    titles = {f.title for f in found}
    assert {"Semicolon in dialogue", "Uncontracted speech"} <= titles


def test_voice_similarity():
    lines = []
    for i in range(6):
        lines.append('"I think we should leave the house before the storm arrives tonight," Mara said.')
        lines.append('"I think we should check the cellar before the storm arrives tonight," Tom said.')
    found = get_rule("voice_similarity").check(Document("\n".join(lines)), RuleContext())
    assert found and "Mara" in found[0].title and "Tom" in found[0].title


def test_emotion_rules():
    assert hits("named_emotions", "She felt a surge of relief.")
    assert hits("named_emotions", "A wave of guilt washed over him.")
    found = get_rule("named_emotions").check(Document("Her hands shook. She felt terrified."), RuleContext())
    assert found[0].severity == "high" and "after it was shown" in found[0].title
    many = "She saw the door. She heard the stairs. She felt the cold. She noticed a smell. She watched the road."
    assert len(hits("filter_words", many)) == 5


def test_conflict_rules():
    text = '"How could you?" she shouted.\n\nHe said nothing.\n\nHer anger drained away.'
    found = get_rule("softened_conflict").check(Document(text), RuleContext())
    assert found and found[0].severity == "high"
    ending = ("Plain sentence here about the walk. " * 30) + "\n\nWhatever came next, they would face it together."
    assert hits("neat_resolution", ending)
    early = "Whatever came next, they would face it together.\n\n" + ("Plain sentence here about the walk. " * 30)
    assert hits("neat_resolution", early) == []


def test_custom_phrases_syntax():
    custom = [
        {"pattern": "orbs", "note": "", "enabled": True},
        {"pattern": "not * but *", "note": "", "enabled": True},
        {"pattern": "re:\\bsuddenly\\b", "note": "", "enabled": True},
        {"pattern": "heart pounding", "note": "", "enabled": False},
    ]
    text = "Her orbs shone. It was not anger but grief. Suddenly, a heart pounding."
    assert hits("custom_phrases", text, custom=custom) == ["orbs", "not anger but grief", "Suddenly"]


def test_custom_pattern_validation():
    from prose_clinic.rules.custom import pattern_error

    assert pattern_error("re:(unclosed") is not None
    assert pattern_error("re:.*") is not None  # matches empty text
    assert pattern_error("a * of relief") is None
