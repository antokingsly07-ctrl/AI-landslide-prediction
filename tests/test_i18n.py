"""Tests for the multilingual alert template engine."""
from app.services.i18n import translate, supported_languages


def test_supported_languages():
    assert set(supported_languages()) == {"en", "hi", "as", "bn", "ta"}


def test_template_renders_with_values():
    msg = translate("risk_message", "en", level="HIGH", location="(26.1, 92.9)",
                    risk_score=78, action="Monitor")
    assert "HIGH" in msg
    assert "(26.1, 92.9)" in msg


def test_unknown_key_falls_back_empty():
    assert translate("does_not_exist", "en") == ""


def test_unknown_language_falls_back_to_english():
    assert translate("rainfall_title", "xx") == "Heavy Rainfall Alert"


def test_hi_translation_produces_non_english_text():
    title = translate("rainfall_title", "hi")
    assert title != "Heavy Rainfall Alert"
    assert title  # non-empty