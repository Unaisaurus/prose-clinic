"""End-to-end checks of the Streamlit pages using Streamlit's own test harness."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from prose_clinic.sample_text import SAMPLE_PASSAGE

TIMEOUT = 60
APP = Path(__file__).resolve().parent.parent / "app.py"


def make_at(page: str) -> AppTest:
    source = f'''
from prose_clinic.ui import state, {page}
state.init()
{page}.render()
'''
    return AppTest.from_string(source, default_timeout=TIMEOUT)


def test_main_app_runs_and_analyzes_example():
    at = AppTest.from_file(str(APP), default_timeout=TIMEOUT).run()
    assert not at.exception
    next(b for b in at.button if b.label == "Load example").click().run()
    assert not at.exception
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Words"] == "324" and int(metrics["Findings"]) > 30


def test_select_findings_and_mark_false_positive():
    at = AppTest.from_file(str(APP), default_timeout=TIMEOUT).run()
    next(b for b in at.button if b.label == "Load example").click().run()
    boxes = [c for c in at.checkbox if c.label == "Add to revision list"]
    boxes[0].check().run()
    assert len(at.session_state["selected"]) == 1
    before = int({m.label: m.value for m in at.metric}["Findings"])
    feedback = at.button_group[2]  # first finding card's feedback buttons (after two filter widgets)
    feedback.set_value("false_positive").run()
    assert not at.exception
    after = int({m.label: m.value for m in at.metric}["Findings"])
    assert after == before - 1


def test_revise_page_with_selection_and_quick_fix():
    at = make_at("revise_page")
    at.session_state["analyzed_text"] = SAMPLE_PASSAGE
    at.session_state["draft_text"] = SAMPLE_PASSAGE
    at.run()
    # Select the redundancy finding via the analysis itself.
    from prose_clinic.analyzer import analyze

    finding = next(f for f in analyze(SAMPLE_PASSAGE, {}).findings if f.excerpt == "nodded her head")
    at.session_state["selected"] = {finding.uid: finding.to_dict()}
    at.run()
    assert not at.exception
    next(b for b in at.button if b.label == "Apply quick fix").click().run()
    assert not at.exception
    assert "She nodded slowly." in at.session_state["draft_text"]
    assert at.session_state["analyzed_text"] == SAMPLE_PASSAGE  # original untouched


def test_revise_page_without_analysis():
    at = make_at("revise_page").run()
    assert not at.exception
    assert any("Analyze a passage first" in i.value for i in at.info)


def test_settings_page_renders_and_toggles_rule():
    at = make_at("settings_page").run()
    assert not at.exception
    toggle = next(t for t in at.toggle if t.label == "Clichés")
    toggle.set_value(False).run()
    assert at.session_state["settings"]["rules"]["cliches"]["enabled"] is False


def test_settings_custom_phrase_form():
    at = make_at("settings_page")
    at.session_state["settings_tab"] = "🚫 Custom phrases"
    at.run()
    at.text_input[0].input("orbs")
    at.text_input[1].input("Nobody says orbs.")
    next(b for b in at.button if b.label == "Add to my list").click().run()
    assert not at.exception
    assert at.session_state["settings"]["custom_phrases"][-1]["pattern"] == "orbs"


def test_settings_ai_tab_switches_provider():
    at = make_at("settings_page")
    at.session_state["settings_tab"] = "🤖 AI connection"
    at.run()
    at.radio(key="ai_provider").set_value("openai_compatible").run()
    assert not at.exception
    assert at.session_state["settings"]["ai"]["provider"] == "openai_compatible"
    at.radio(key="ai_provider").set_value("none").run()


def test_library_and_help_pages_render():
    for page in ("library_page", "help_page"):
        at = make_at(page).run()
        assert not at.exception, page


def test_every_settings_and_analyze_tab_renders():
    for label in ["🧪 Detection rules", "🚫 Custom phrases", "👍 Feedback", "🤖 AI connection", "💾 Backup"]:
        at = make_at("settings_page")
        at.session_state["settings_tab"] = label
        assert not at.run().exception, label
    for label in ["📋 Rule-based findings", "🤖 AI critique (optional)", "📊 Statistics"]:
        at = make_at("analyze_page")
        at.session_state["analyzed_text"] = SAMPLE_PASSAGE
        at.session_state["analyze_tab"] = label
        assert not at.run().exception, label
    for label in ["📝 Full-passage revision", "📄 Revision draft"]:
        at = make_at("revise_page")
        at.session_state["analyzed_text"] = SAMPLE_PASSAGE
        at.session_state["draft_text"] = SAMPLE_PASSAGE.replace("slowly", "")
        at.session_state["revise_tab"] = label
        assert not at.run().exception, label
