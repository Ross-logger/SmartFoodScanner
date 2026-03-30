"""Unit tests for ingredient box classifier and merge pipeline."""

import joblib
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from scipy.sparse import csr_matrix

import backend.services.ingredients_extraction.ingredient_box_classifier as ibc


class _PicklableTfidf:
    def transform(self, texts):
        n = len(texts)
        return csr_matrix(np.zeros((n, 4), dtype=np.float64))


class _PicklableDictVec:
    def transform(self, rows):
        n = len(rows)
        return csr_matrix(np.zeros((n, 8), dtype=np.float64))


class _PicklableClf:
    def predict_proba(self, X):
        n = X.shape[0]
        p1 = np.linspace(0.35, 0.88, n)
        return np.column_stack([1.0 - p1, p1])


def _picklable_classifier_bundle(threshold: float = 0.45):
    return {
        "classifier": _PicklableClf(),
        "tfidf": _PicklableTfidf(),
        "dict_vectorizer": _PicklableDictVec(),
        "decision_threshold": threshold,
    }


def _write_bundle(tmp_path, bundle, name="m.joblib"):
    path = tmp_path / name
    joblib.dump(bundle, path)
    return path


@pytest.fixture
def sample_raw_easyocr():
    return [
        ([[0, 0], [120, 0], [120, 18], [0, 18]], "nutrition facts", 0.9),
        ([[0, 22], [90, 22], [90, 38], [0, 38]], "Ingredients:", 0.95),
        ([[0, 42], [160, 42], [160, 58], [0, 58]], "sugar, water, salt", 0.92),
    ]


def test_normalize_text():
    assert ibc.normalize_text("  FOO  ") == "foo"


def test_is_header_variants():
    assert ibc.is_header("Ingredients") is True
    assert ibc.is_header("INGREDIENTS:") is True
    assert ibc.is_header("list of ingredients") is True
    assert ibc.is_header("sugar") is False


def test_has_bad_hint():
    assert ibc.has_bad_hint("Nutrition Facts") is True
    assert ibc.has_bad_hint("sugar") is False


def test_alpha_digit_symbol_ratios():
    assert ibc.alpha_ratio("") == 0.0
    assert ibc.digit_ratio("") == 0.0
    assert ibc.symbol_ratio("") == 0.0
    assert ibc.alpha_ratio("abc123") > 0.4
    assert ibc.digit_ratio("123abc") > 0.4
    assert ibc.symbol_ratio("a!@#b") > 0.3


def test_looks_like_junk_fragment_branches():
    assert ibc.looks_like_junk_fragment("") is True
    assert ibc.looks_like_junk_fragment("ab") is True
    assert ibc.looks_like_junk_fragment("99999") is True
    assert ibc.looks_like_junk_fragment("12a") is True
    assert ibc.looks_like_junk_fragment("sugar") is False
    assert ibc.looks_like_junk_fragment("!!@@") is True


def test_looks_like_continuation():
    assert ibc.looks_like_continuation("") is False
    assert ibc.looks_like_continuation("(wheat)") is True
    assert ibc.looks_like_continuation("12.5%") is True
    assert ibc.looks_like_continuation("(12.5%)") is True
    assert ibc.looks_like_continuation("and salt") is True
    assert ibc.looks_like_continuation("lowercase start") is True


def test_prepare_boxes_missing_columns():
    df = pd.DataFrame({"text": ["a"], "x1": [0]})
    with pytest.raises(ValueError, match="Missing required columns"):
        ibc.prepare_boxes(df)


def test_prepare_boxes_fills_defaults():
    df = pd.DataFrame({
        "text": [" hi "],
        "x1": [0.0], "y1": [0.0], "x2": [10.0], "y2": [5.0],
        "pred_prob": [0.9],
    })
    out = ibc.prepare_boxes(df)
    assert out["width"].iloc[0] == 10.0
    assert "confidence" in out.columns


def test_find_header_box_found_and_none():
    df = pd.DataFrame({
        "text": ["Ingredients:", "sugar"],
        "x1": [0.0, 0.0], "y1": [0.0, 20.0], "x2": [50.0, 40.0], "y2": [10.0, 30.0],
        "pred_prob": [0.9, 0.9], "confidence": [0.9, 0.9],
    }).astype({"x1": float, "y1": float, "x2": float, "y2": float, "pred_prob": float, "confidence": float})
    prep = ibc.prepare_boxes(df)
    row = ibc.find_header_box(prep)
    assert row is not None
    assert "ingredients" in str(row["text"]).lower()

    df2 = pd.DataFrame({
        "text": ["sugar"],
        "x1": [0], "y1": [0], "x2": [1], "y2": [1],
        "pred_prob": [0.9], "confidence": [0.9],
    })
    assert ibc.find_header_box(ibc.prepare_boxes(df2)) is None


def test_filter_positive_boxes_filters():
    df = pd.DataFrame({
        "text": ["Ingredients:", "junk", "sugar, water"],
        "x1": [0.0, 0.0, 0.0],
        "y1": [0.0, 10.0, 20.0],
        "x2": [40.0, 40.0, 100.0],
        "y2": [8.0, 18.0, 28.0],
        "pred_prob": [0.95, 0.5, 0.85],
        "confidence": [0.9, 0.9, 0.9],
    }).astype({"x1": float, "y1": float, "x2": float, "y2": float, "pred_prob": float, "confidence": float})
    prep = ibc.prepare_boxes(df)
    pos = ibc.filter_positive_boxes(prep, threshold=0.4, strong_keep_threshold=0.8)
    assert "Ingredients" not in " ".join(pos["text"].tolist())


def test_apply_header_constraint_filters_above():
    header = pd.Series({"y_center": 50.0, "y1": 40.0, "y2": 60.0})
    pos = pd.DataFrame({
        "text": ["a", "b"],
        "y_center": [30.0, 80.0],
        "pred_prob": [0.9, 0.9],
        "x_center": [0.0, 0.0],
    })
    out = ibc.apply_header_constraint(pos, header, tolerance_above=5.0)
    assert len(out) == 1
    assert float(out["y_center"].iloc[0]) == 80.0


def test_remove_isolated_multi_box():
    pos = pd.DataFrame({
        "text": ["sugar", "orphan"],
        "pred_prob": [0.5, 0.5],
        "x_center": [10.0, 5000.0],
        "y_center": [10.0, 10.0],
    })
    out = ibc.remove_isolated_boxes(pos, y_radius=50.0, x_radius=100.0)
    assert len(out) >= 1


def test_cluster_merge_choose_assign_reconstruct():
    pos = pd.DataFrame({
        "text": ["sugar", "water"],
        "pred_prob": [0.9, 0.85],
        "x1": [0.0, 50.0], "y1": [0.0, 0.0], "x2": [40.0, 90.0], "y2": [10.0, 10.0],
        "confidence": [0.9, 0.9],
    })
    pos = ibc.prepare_boxes(pos)
    clusters = ibc.cluster_boxes_by_rows(pos, row_gap=100.0)
    assert len(clusters) >= 1
    merged = ibc.merge_close_clusters(clusters, cluster_gap=200.0)
    best = ibc.choose_best_cluster(merged, header_row=None)
    assert best is not None
    text = ibc.reconstruct_text_from_cluster(best)
    assert "sugar" in text.lower()


def test_assign_rows_multiple_rows():
    cluster = pd.DataFrame({
        "text": ["a", "b"],
        "y_center": [0.0, 100.0],
        "x1": [0.0, 0.0],
        "height": [10.0, 10.0],
    })
    out = ibc.assign_rows(cluster, row_gap=10.0)
    assert out["row_id"].nunique() >= 2


def test_cleanup_row_boxes_and_smart_join_punct():
    df = pd.DataFrame({"text": ["xx", "and salt"], "x1": [0.0, 10.0]})
    cleaned = ibc.cleanup_row_boxes(df)
    assert "and salt" in cleaned["text"].tolist()
    line = ibc.smart_join_row_texts(["Oil", "/", "Palm"])
    assert "/" in line or "Palm" in line


def test_cluster_boxes_by_rows_empty():
    assert ibc.cluster_boxes_by_rows(pd.DataFrame()) == []


def test_merge_close_clusters_empty():
    assert ibc.merge_close_clusters([]) == []


def test_choose_best_cluster_empty():
    assert ibc.choose_best_cluster([]) is None
    assert ibc.choose_best_cluster([pd.DataFrame()]) is None


def test_assign_rows_empty():
    out = ibc.assign_rows(pd.DataFrame())
    assert len(out) == 0


def test_smart_join_row_texts_continuation_and_punct():
    joined = ibc.smart_join_row_texts(["Sugar", "(wheat)"])
    assert "Sugar" in joined and "(wheat)" in joined
    line = ibc.smart_join_row_texts(["Oil", "(Palm)"])
    assert "(" in line


def test_reconstruct_text_from_cluster_none():
    assert ibc.reconstruct_text_from_cluster(None) == ""


def test_trim_tail_by_hints():
    t = ibc.trim_tail_by_hints("sugar, water nutrition facts here")
    assert "nutrition" not in t.lower()
    assert ibc.trim_tail_by_hints("") == ""


def test_remove_trailing_junk_lines():
    t = ibc.remove_trailing_junk_lines("sugar\nbest before 2026")
    assert "sugar" in t
    assert ibc.remove_trailing_junk_lines("") == ""


def test_normalize_ingredient_text():
    out = ibc.normalize_ingredient_text("a  ,  b")
    assert "a" in out and "b" in out and out.count(",") == 1
    assert ibc.normalize_ingredient_text("") == ""


def test_postprocess_ingredient_text():
    s = ibc.postprocess_ingredient_text("sugar  \n  water")
    assert "sugar" in s


def test_easyocr_results_to_dataframe_skips_bad_rows():
    raw = [
        ([[0, 0]], "x", 0.9),
        ([[0, 0], [1, 0], [1, 1], [0, 1]], "", 0.9),
        ([[0, 0], [1, 0], [1, 1], [0, 1]], "ok", 0.9),
    ]
    df = ibc._easyocr_results_to_dataframe(raw)
    assert len(df) == 1
    assert df["text"].iloc[0] == "ok"


def test_load_model_success(tmp_path, monkeypatch, sample_raw_easyocr):
    bundle = _picklable_classifier_bundle(threshold=0.41)
    path = _write_bundle(tmp_path, bundle)
    monkeypatch.setattr(ibc.settings, "BOX_CLASSIFIER_MODEL_PATH", str(path))
    ibc._model_bundle = None
    out = ibc._load_model()
    assert out["decision_threshold"] == 0.41
    ibc._model_bundle = None


def test_load_model_file_not_found(monkeypatch):
    ibc._model_bundle = None
    monkeypatch.setattr(ibc.settings, "BOX_CLASSIFIER_MODEL_PATH", "/nonexistent/box_model.joblib")
    with pytest.raises(FileNotFoundError):
        ibc._load_model()
    ibc._model_bundle = None


def test_load_model_missing_keys(tmp_path, monkeypatch):
    joblib.dump({"classifier": None}, tmp_path / "bad.joblib")
    ibc._model_bundle = None
    monkeypatch.setattr(ibc.settings, "BOX_CLASSIFIER_MODEL_PATH", str(tmp_path / "bad.joblib"))
    with pytest.raises(ValueError, match="missing keys"):
        ibc._load_model()
    ibc._model_bundle = None


def test_load_model_cached(monkeypatch, tmp_path, sample_raw_easyocr):
    bundle = _picklable_classifier_bundle()
    path = _write_bundle(tmp_path, bundle)
    monkeypatch.setattr(ibc.settings, "BOX_CLASSIFIER_MODEL_PATH", str(path))
    ibc._model_bundle = None
    real_load = joblib.load
    calls = []

    def counting_load(*args, **kwargs):
        calls.append(True)
        return real_load(*args, **kwargs)

    with patch(
        "backend.services.ingredients_extraction.ingredient_box_classifier.joblib.load",
        side_effect=counting_load,
    ):
        ibc._load_model()
        ibc._load_model()
    assert len(calls) == 1
    ibc._model_bundle = None


def test_load_model_early_return_cache():
    ibc._model_bundle = _picklable_classifier_bundle(threshold=0.1)
    assert ibc._load_model() is ibc._model_bundle
    ibc._model_bundle = None


def test_classify_boxes_empty(monkeypatch, tmp_path, sample_raw_easyocr):
    bundle = _picklable_classifier_bundle()
    path = _write_bundle(tmp_path, bundle)
    monkeypatch.setattr(ibc.settings, "BOX_CLASSIFIER_MODEL_PATH", str(path))
    ibc._model_bundle = None
    df = ibc.classify_boxes([], image_id="z")
    assert df.empty
    assert "pred_prob" in df.columns
    ibc._model_bundle = None


def test_classify_boxes_with_data(monkeypatch, tmp_path, sample_raw_easyocr):
    bundle = _picklable_classifier_bundle()
    path = _write_bundle(tmp_path, bundle)
    monkeypatch.setattr(ibc.settings, "BOX_CLASSIFIER_MODEL_PATH", str(path))
    ibc._model_bundle = None
    df = ibc.classify_boxes(sample_raw_easyocr, image_id="img")
    assert len(df) == 3
    assert "pred_label" in df.columns
    ibc._model_bundle = None


def test_score_cluster_with_header():
    hdr = pd.Series({
        "y1": np.float64(0.0),
        "y2": np.float64(20.0),
        "text": "Ingredients:",
    })
    cl = pd.DataFrame({
        "text": ["sugar"],
        "pred_prob": [np.float64(0.9)],
        "y1": [np.float64(25.0)],
    })
    s0 = ibc.score_cluster(cl, header_row=None)
    s1 = ibc.score_cluster(cl, header_row=hdr)
    assert isinstance(s0, float) and isinstance(s1, float)


def test_extract_ingredient_region_pipeline(monkeypatch, tmp_path, sample_raw_easyocr):
    bundle = _picklable_classifier_bundle()
    path = _write_bundle(tmp_path, bundle)
    monkeypatch.setattr(ibc.settings, "BOX_CLASSIFIER_MODEL_PATH", str(path))
    ibc._model_bundle = None
    df = ibc.classify_boxes(sample_raw_easyocr, "p1")
    res = ibc.extract_ingredient_region(df, threshold=0.4)
    assert "final_text" in res
    assert "raw_text" in res
    ibc._model_bundle = None


def test_extract_ingredients_from_boxes_logs(monkeypatch, tmp_path, sample_raw_easyocr):
    bundle = _picklable_classifier_bundle()
    path = _write_bundle(tmp_path, bundle)
    monkeypatch.setattr(ibc.settings, "BOX_CLASSIFIER_MODEL_PATH", str(path))
    ibc._model_bundle = None
    df = ibc.classify_boxes(sample_raw_easyocr, "p1")
    with patch.object(ibc.logger, "info"):
        txt = ibc.extract_ingredients_from_boxes(df)
    assert isinstance(txt, str)
    ibc._model_bundle = None


def test_has_any_and_context_columns():
    raw = [
        ([[0, 0], [40, 0], [40, 12], [0, 12]], "a", 0.9),
        ([[0, 14], [40, 14], [40, 26], [0, 26]], "b", 0.9),
    ]
    df = ibc._easyocr_results_to_dataframe(raw, "g")
    out = ibc._add_context_columns(df)
    assert out["prev_text"].iloc[1] == "a"
    assert ibc._has_any("sugar and salt", ibc.INGREDIENT_HINTS) == 1


def test_make_manual_features_row():
    raw = [
        ([[0, 0], [30, 0], [30, 10], [0, 10]], "SUGAR", 0.99),
    ]
    df = ibc._easyocr_results_to_dataframe(raw, "z")
    df = ibc._add_context_columns(df)
    feats = ibc._make_manual_features(df)
    assert feats[0]["is_all_caps"] == 1
    assert feats[0]["char_len"] > 0


def test_apply_header_constraint_empty_or_no_header():
    pos = pd.DataFrame({"text": ["x"], "y_center": [1.0]})
    assert len(ibc.apply_header_constraint(pos, None)) == 1
    hdr = pd.Series({"y_center": 0.0})
    assert len(ibc.apply_header_constraint(pd.DataFrame(), hdr)) == 0


def test_remove_isolated_single_row():
    df = pd.DataFrame({
        "text": ["sugar"],
        "pred_prob": [0.9],
        "x_center": [10.0], "y_center": [10.0],
    })
    assert len(ibc.remove_isolated_boxes(df)) == 1


def test_filter_positive_boxes_strong_keep_junk():
    df = pd.DataFrame({
        "text": ["xx"],
        "x1": [0.0], "y1": [0.0], "x2": [10.0], "y2": [10.0],
        "pred_prob": [0.95],
        "confidence": [0.9],
    })
    prep = ibc.prepare_boxes(df)
    out = ibc.filter_positive_boxes(prep, strong_keep_threshold=0.9)
    assert len(out) == 1


def test_filter_positive_bad_hint_dropped_below_092():
    df = pd.DataFrame({
        "text": ["nutrition facts panel"],
        "x1": [0.0], "y1": [0.0], "x2": [10.0], "y2": [10.0],
        "pred_prob": [0.91],
        "confidence": [0.9],
    })
    prep = ibc.prepare_boxes(df)
    out = ibc.filter_positive_boxes(prep)
    assert len(out) == 0


def test_trim_tail_hint_at_start_untrimmed():
    t = ibc.trim_tail_by_hints("nutrition facts first")
    assert "nutrition" in t.lower()


def test_easyocr_empty_dataframe():
    df = ibc._easyocr_results_to_dataframe([], "x")
    assert df.empty

