import json

import pytest

from prose_clinic import storage
from prose_clinic.findings import Finding


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    return tmp_path


def test_settings_roundtrip_and_defaults(data_dir):
    settings = storage.load_settings()
    assert settings["ai"]["provider"] == "none"
    settings["rules"]["cliches"] = {"enabled": False}
    settings["custom_phrases"].append({"pattern": "orbs", "note": "", "enabled": True})
    storage.save_settings(settings)
    again = storage.load_settings()
    assert again["rules"]["cliches"] == {"enabled": False}
    assert again["custom_phrases"][0]["pattern"] == "orbs"
    assert again["ai"]["max_findings"] == 15  # defaults merged in


def test_no_api_keys_in_settings_file(data_dir):
    storage.save_settings(storage.load_settings())
    raw = (data_dir / "settings.json").read_text()
    assert "api_key" not in raw.lower()


def test_corrupt_file_is_kept_and_defaults_used(data_dir):
    (data_dir / "settings.json").write_text("{not json")
    settings = storage.load_settings()
    assert settings["ai"]["provider"] == "none"
    assert list(data_dir.glob("settings.broken-*.json"))


def test_feedback(data_dir):
    feedback = storage.load_feedback()
    f = Finding("cliches", "cliche", "Clichés", "msg", "fix", 0, 10, excerpt="time stood still")
    storage.set_verdict(feedback, f, "false_positive")
    storage.save_feedback(feedback)
    feedback = storage.load_feedback()
    assert storage.verdict_for(feedback, f) == "false_positive"
    assert f.signature in storage.false_positive_signatures(feedback)
    assert storage.feedback_stats(feedback) == {"cliches": {"useful": 0, "false_positive": 1}}
    storage.set_verdict(feedback, f, None)
    assert storage.verdict_for(feedback, f) is None


def test_backup_roundtrip(data_dir):
    settings, library, feedback = storage.load_settings(), storage.load_library(), storage.load_feedback()
    library["samples"].append({"title": "A", "text": "Some prose.", "active": True})
    raw = storage.export_all(settings, library, feedback)
    s2, l2, f2 = storage.parse_backup(raw)
    assert l2["samples"][0]["title"] == "A"
    with pytest.raises(ValueError):
        storage.parse_backup(json.dumps({"hello": 1}))
    with pytest.raises(ValueError):
        storage.parse_backup("nope")


def test_archive_draft(data_dir):
    assert storage.archive_draft("same", "same") is None
    path = storage.archive_draft("The original text here.", "The revised text here.")
    assert path and path.exists() and "REVISED DRAFT" in path.read_text()
