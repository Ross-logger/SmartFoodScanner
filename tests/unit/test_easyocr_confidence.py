"""Tests for EasyOCR → SymSpell skip-key helpers."""

from backend.services.ocr.easyocr_confidence import (
    build_easyocr_skip_symspell_normalized_keys,
    normalize_for_symspell_skip_key,
    should_skip_symspell_for_segment,
)


def test_normalize_for_symspell_skip_key():
    assert normalize_for_symspell_skip_key("  Sugar  ") == "sugar"


def test_build_easyocr_skip_keys_full_line_and_splits():
    lines = [("Sugar, Salt", 0.95), ("Low line", 0.2)]
    keys = build_easyocr_skip_symspell_normalized_keys(lines, min_confidence=0.9)
    assert "sugar, salt" in keys
    assert "sugar" in keys
    assert "salt" in keys
    assert "low line" not in keys


def test_should_skip_symspell_for_segment():
    keys = frozenset({"sugar"})
    assert should_skip_symspell_for_segment("  Sugar ", keys) is True
    assert should_skip_symspell_for_segment("salt", keys) is False
    assert should_skip_symspell_for_segment("salt", None) is False
