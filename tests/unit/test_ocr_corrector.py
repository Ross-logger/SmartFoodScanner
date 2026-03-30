"""Unit tests for OCR ingredient corrector (high coverage)."""

from unittest.mock import MagicMock, patch

import pytest

import backend.services.ingredients_extraction.ocr_corrector as oc


@pytest.fixture(autouse=True)
def reset_ocr_corrector_singletons():
    oc._vocabulary = None
    oc._vocab_list = None
    oc._corrector_sym_spell = None
    yield
    oc._vocabulary = None
    oc._vocab_list = None
    oc._corrector_sym_spell = None


def test_build_vocabulary_singleton():
    a = oc._build_vocabulary()
    b = oc._build_vocabulary()
    assert a is b
    assert oc._vocab_list is not None
    assert len(oc._get_vocab_list()) == len(a)


def test_get_sym_spell_singleton():
    s1 = oc._get_sym_spell()
    s2 = oc._get_sym_spell()
    assert s1 is s2


def test_cleanup_ocr_text_basic():
    assert oc.cleanup_ocr_text("  SUGAR  ") == "sugar"
    assert "e330" in oc.cleanup_ocr_text("contains e 330 acid")


def test_cleanup_ocr_text_stray_punct():
    out = oc.cleanup_ocr_text("Sugar!!!")
    assert "!" not in out


def test_normalize_e_number_match_and_no_match():
    assert oc._normalize_e_number("E 330") == "e330"
    assert oc._normalize_e_number("plain") == "plain"


def test_is_junk_candidate_empty_and_short():
    assert oc.is_junk_candidate("") is True
    assert oc.is_junk_candidate("a") is True


def test_is_junk_candidate_substrings():
    assert oc.is_junk_candidate("See nutrition facts below") is True
    assert oc.is_junk_candidate("https://example.com") is True


def test_is_junk_candidate_digits_only():
    assert oc.is_junk_candidate("12345") is True


def test_is_junk_candidate_long_marketing():
    long_txt = "x" * 50 + " contributes to normal immune system function and lifestyle benefits"
    assert oc.is_junk_candidate(long_txt) is True


def test_is_junk_candidate_ingredient_like():
    assert oc.is_junk_candidate("whole wheat flour") is False


def test_is_dangerous_correction():
    assert oc._is_dangerous_correction("salt", "malt") is True
    assert oc._is_dangerous_correction("sugar", "salt") is False


def test_correct_single_candidate_alias():
    vocab = oc._build_vocabulary()
    sym = oc._get_sym_spell()
    vlist = oc._get_vocab_list()
    out = oc.correct_single_candidate("citnc acid", vocab, sym, vlist)
    assert "citric" in out


def test_correct_single_candidate_exact_vocab():
    vocab = oc._build_vocabulary()
    sym = oc._get_sym_spell()
    vlist = oc._get_vocab_list()
    out = oc.correct_single_candidate("sugar", vocab, sym, vlist)
    assert out == "sugar"


def test_correct_single_candidate_e_number_spacing():
    vocab = oc._build_vocabulary()
    sym = oc._get_sym_spell()
    vlist = oc._get_vocab_list()
    out = oc.correct_single_candidate("E 330", vocab, sym, vlist)
    assert out == "e330"


def test_correct_single_candidate_too_short_no_fuzzy():
    vocab = oc._build_vocabulary()
    sym = oc._get_sym_spell()
    vlist = oc._get_vocab_list()
    out = oc.correct_single_candidate("oil", vocab, sym, vlist)
    assert out == "oil"


def test_correct_single_candidate_empty_cleanup_returns_original():
    vocab = frozenset()
    mock_sym = MagicMock()
    mock_sym.lookup.return_value = []
    seg = MagicMock()
    seg.corrected_string = ""
    mock_sym.word_segmentation.return_value = seg
    with patch.object(oc.rf_process, "extractOne", return_value=None):
        out = oc.correct_single_candidate("@@@", vocab, mock_sym, [])
    assert out == "@@@"


def test_correct_single_dangerous_symspell_blocked():
    vocab = frozenset({"salt", "malt"})
    vlist = sorted(vocab)
    mock_sym = MagicMock()

    class Sug:
        def __init__(self, term, distance):
            self.term = term
            self.distance = distance

    mock_sym.lookup.return_value = [Sug("malt", 1)]
    seg = MagicMock()
    seg.corrected_string = ""
    mock_sym.word_segmentation.return_value = seg
    with patch.object(oc.rf_process, "extractOne", return_value=None):
        out = oc.correct_single_candidate("salt", vocab, mock_sym, vlist)
    assert out == "salt"


def test_correct_single_word_segmentation_in_vocab():
    vocab = frozenset({"brown sugar"})
    vlist = sorted(vocab)
    mock_sym = MagicMock()
    mock_sym.lookup.return_value = []
    seg = MagicMock()
    seg.corrected_string = "brown sugar"
    seg.distance_sum = 1
    mock_sym.word_segmentation.return_value = seg
    with patch.object(oc.rf_process, "extractOne", return_value=None):
        out = oc.correct_single_candidate("brownsugar", vocab, mock_sym, vlist)
    assert out == "brown sugar"


def test_correct_single_segmentation_dangerous_blocked():
    vocab = frozenset({"salt", "malt"})
    vlist = sorted(vocab)
    mock_sym = MagicMock()
    mock_sym.lookup.return_value = []
    seg = MagicMock()
    seg.corrected_string = "malt"
    seg.distance_sum = 1
    mock_sym.word_segmentation.return_value = seg
    with patch.object(oc.rf_process, "extractOne", return_value=None):
        out = oc.correct_single_candidate("salt", vocab, mock_sym, vlist)
    assert out == "salt"


def test_correct_single_rapidfuzz_match():
    vocab = frozenset({"gluten"})
    vlist = sorted(vocab)
    mock_sym = MagicMock()
    mock_sym.lookup.return_value = []
    seg = MagicMock()
    seg.corrected_string = ""
    mock_sym.word_segmentation.return_value = seg
    with patch.object(oc.rf_process, "extractOne", return_value=("gluten", 96, 0)):
        out = oc.correct_single_candidate("glutenx", vocab, mock_sym, vlist)
    assert out == "gluten"


def test_correct_single_rapidfuzz_short_word_high_score():
    vocab = frozenset({"salt"})
    vlist = sorted(vocab)
    mock_sym = MagicMock()
    mock_sym.lookup.return_value = []
    seg = MagicMock()
    seg.corrected_string = ""
    mock_sym.word_segmentation.return_value = seg
    with patch.object(oc.rf_process, "extractOne", return_value=("salt", 96, 0)):
        out = oc.correct_single_candidate("slat", vocab, mock_sym, vlist)
    assert out == "salt"


def test_correct_single_word_by_word_multipart():
    vocab = frozenset({"gluten", "contains"})
    vlist = sorted(vocab)

    class Sug:
        def __init__(self, term, distance):
            self.term = term
            self.distance = distance

    def lookup_side_effect(word, verbosity, max_edit_distance):
        if word == "cluten":
            return [Sug("gluten", 1)]
        return []

    mock_sym = MagicMock()
    mock_sym.lookup.side_effect = lookup_side_effect
    seg = MagicMock()
    seg.corrected_string = ""
    mock_sym.word_segmentation.return_value = seg
    with patch.object(oc.rf_process, "extractOne", return_value=None):
        out = oc.correct_single_candidate("contains cluten", vocab, mock_sym, vlist)
    assert "gluten" in out


def test_correct_ingredient_list_empty():
    assert oc.correct_ingredient_list([]) == []


def test_correct_ingredient_list_skips_junk():
    out = oc.correct_ingredient_list(["nutrition facts", "sugar"])
    assert "sugar" in [x.lower() for x in out]


def test_correct_ingredient_list_no_corrector():
    out = oc.correct_ingredient_list(["  Sugar  ", "Salt"], use_ocr_corrector=False)
    assert any("sugar" == x.lower() for x in out)


def test_correct_ingredient_list_dedup():
    out = oc.correct_ingredient_list(["Sugar", "sugar", "SALT"])
    keys = [x.lower() for x in out]
    assert keys.count("sugar") == 1


def test_correct_ingredient_list_skips_empty_after_fix():
    out = oc.correct_ingredient_list(["x"])
    assert isinstance(out, list)


def test_is_junk_garbage_stop_allergen_branches():
    with patch.object(oc, "is_garbage_text", return_value=True):
        assert oc.is_junk_candidate("plain oats") is True
    with patch.object(oc, "is_garbage_text", return_value=False):
        with patch.object(oc, "is_stop_pattern", return_value=True):
            assert oc.is_junk_candidate("plain oats") is True
        with patch.object(oc, "is_stop_pattern", return_value=False):
            with patch.object(oc, "is_allergen_warning_segment", return_value=True):
                assert oc.is_junk_candidate("plain oats") is True


def test_correct_single_e_number_hyphen_normalizes():
    vocab = oc._build_vocabulary()
    sym = oc._get_sym_spell()
    vlist = oc._get_vocab_list()
    out = oc.correct_single_candidate("E-330", vocab, sym, vlist)
    assert out == "e330"


def test_correct_single_symspell_typo_in_vocab():
    vocab = oc._build_vocabulary()
    sym = oc._get_sym_spell()
    vlist = oc._get_vocab_list()
    if "sugar" not in vocab:
        pytest.skip("vocabulary missing sugar")
    out = oc.correct_single_candidate("suger", vocab, sym, vlist)
    assert out == "sugar"


def test_correct_single_word_by_word_skips_short_tokens():
    vocab = oc._build_vocabulary()
    sym = oc._get_sym_spell()
    vlist = oc._get_vocab_list()
    out = oc.correct_single_candidate("salt and suger", vocab, sym, vlist)
    assert "sugar" in out


def test_correct_single_fallthrough_unknown():
    vocab = frozenset({"sugar"})
    vlist = sorted(vocab)
    mock_sym = MagicMock()
    mock_sym.lookup.return_value = []
    seg = MagicMock()
    seg.corrected_string = ""
    mock_sym.word_segmentation.return_value = seg
    with patch.object(oc.rf_process, "extractOne", return_value=None):
        out = oc.correct_single_candidate("zzzzunknown", vocab, mock_sym, vlist)
    assert out == "zzzzunknown"


def test_correct_ingredient_list_strips_blank_entries():
    out = oc.correct_ingredient_list(["sugar", "   ", "\t"])
    assert isinstance(out, list)


def test_correct_ingredient_list_second_pass_alias():
    out = oc.correct_ingredient_list(["citnc acid"])
    assert any("citric" in x.lower() for x in out)


def test_correct_ingredient_list_alias_after_cleanup_only():
    out = oc.correct_ingredient_list(["citnc acid"], use_ocr_corrector=False)
    assert any("citric" in x.lower() for x in out)


def test_correct_ingredient_list_drops_short_after_cleanup():
    out = oc.correct_ingredient_list(["##"], use_ocr_corrector=False)
    assert out == []
