"""
Box-level ingredient classifier using the trained logistic regression model.

Loads the joblib model bundle (classifier, tfidf, dict_vectorizer,
decision_threshold) and classifies each EasyOCR detection box as
ingredient (1) or non-ingredient (0).

Feature engineering mirrors training/training_code.py exactly so that
the saved vectorisers produce compatible feature matrices at inference.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
from scipy.sparse import hstack

from backend import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy singleton for the model bundle
# ---------------------------------------------------------------------------
_model_bundle: Optional[Dict[str, Any]] = None


def _load_model() -> Dict[str, Any]:
    """Load the joblib model bundle once and cache it."""
    global _model_bundle
    if _model_bundle is not None:
        return _model_bundle

    model_path = Path(settings.BOX_CLASSIFIER_MODEL_PATH)
    if not model_path.exists():
        raise FileNotFoundError(
            f"Box classifier model not found at {model_path}. "
            "Set BOX_CLASSIFIER_MODEL_PATH or disable USE_BOX_CLASSIFIER."
        )

    logger.info("Loading box classifier model from %s", model_path)
    bundle = joblib.load(model_path)

    required_keys = {"classifier", "tfidf", "dict_vectorizer", "decision_threshold"}
    missing = required_keys - set(bundle.keys())
    if missing:
        raise ValueError(f"Model bundle missing keys: {missing}")

    _model_bundle = bundle
    logger.info(
        "Box classifier loaded (threshold=%.3f)", bundle["decision_threshold"]
    )
    return _model_bundle


# ---------------------------------------------------------------------------
# Feature hints (must match training/training_code.py exactly)
# ---------------------------------------------------------------------------
INGREDIENT_HINTS = [
    "sugar", "salt", "oil", "flour", "milk", "wheat", "water",
    "glucose", "butter", "maize", "corn", "lecithin", "pectin",
    "citric", "flavour", "flavouring", "emulsifier", "strawberry",
    "cocoa", "egg", "yeast", "barley", "oat", "almond", "peanut",
]

NON_INGREDIENT_HINTS = [
    "storage", "store", "nutrition", "energy", "protein",
    "allergy", "allergens", "manufactured", "distributed",
    "keep refrigerated", "serving", "calories", "made in",
    "po box", "united kingdom", "ireland", "suitable for",
    "for best before", "best before", "recycle", "www.", ".com",
]

HEADER_HINTS = ["ingredients", "ingredients:", "ingredient", "ingredient:"]


def _has_any(text: str, words: List[str]) -> int:
    t = str(text).lower()
    return int(any(w in t for w in words))


# ---------------------------------------------------------------------------
# Context columns (prev_text / next_text / context_text)
# ---------------------------------------------------------------------------
def _add_context_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Sort boxes in reading order per image and build context strings."""
    df = df.sort_values(["image_id", "y_center", "x1"]).reset_index(drop=True)

    prev_texts: List[str] = []
    next_texts: List[str] = []

    for _image_id, grp in df.groupby("image_id", sort=False):
        grp = grp.sort_values(["y_center", "x1"])
        texts = grp["text"].tolist()
        prev_texts.extend([""] + texts[:-1])
        next_texts.extend(texts[1:] + [""])

    df["prev_text"] = prev_texts
    df["next_text"] = next_texts
    df["context_text"] = (
        df["prev_text"].fillna("").astype(str)
        + " [SEP] "
        + df["text"].fillna("").astype(str)
        + " [SEP] "
        + df["next_text"].fillna("").astype(str)
    )
    return df


# ---------------------------------------------------------------------------
# Manual features (must match training exactly)
# ---------------------------------------------------------------------------
def _make_manual_features(df: pd.DataFrame) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for _, r in df.iterrows():
        t = str(r["text"]).lower()
        prev_t = str(r["prev_text"]).lower()
        next_t = str(r["next_text"]).lower()

        rows.append({
            "ocr_confidence": float(r["confidence"]),
            "char_len": len(t),
            "word_count": len(t.split()),
            "digit_count": sum(c.isdigit() for c in t),
            "comma_count": t.count(","),
            "percent_count": t.count("%"),
            "paren_count": t.count("(") + t.count(")"),
            "colon_count": t.count(":"),
            "is_all_caps": int(str(r["text"]).isupper()),

            "has_ingredient_hint": _has_any(t, INGREDIENT_HINTS),
            "has_noningredient_hint": _has_any(t, NON_INGREDIENT_HINTS),
            "has_header_hint": _has_any(t, HEADER_HINTS),

            "prev_has_ingredient_hint": _has_any(prev_t, INGREDIENT_HINTS),
            "prev_has_noningredient_hint": _has_any(prev_t, NON_INGREDIENT_HINTS),
            "prev_has_header_hint": _has_any(prev_t, HEADER_HINTS),

            "next_has_ingredient_hint": _has_any(next_t, INGREDIENT_HINTS),
            "next_has_noningredient_hint": _has_any(next_t, NON_INGREDIENT_HINTS),
            "next_has_header_hint": _has_any(next_t, HEADER_HINTS),

            "width": float(r["width"]),
            "height": float(r["height"]),
            "x_center": float(r["x_center"]),
            "y_center": float(r["y_center"]),
        })
    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def _easyocr_results_to_dataframe(
    raw_results: List,
    image_id: str = "scan",
) -> pd.DataFrame:
    """Convert raw EasyOCR ``[(bbox, text, confidence), ...]`` to a DataFrame."""
    rows: List[Dict[str, Any]] = []
    for i, result in enumerate(raw_results):
        if len(result) < 3:
            continue
        bbox, text, confidence = result[0], str(result[1]).strip(), float(result[2])
        if not text:
            continue
        flat = np.array(bbox).flatten()
        if len(flat) < 4:
            continue
        xs, ys = flat[0::2], flat[1::2]
        rows.append({
            "image_id": image_id,
            "box_id": i,
            "text": text,
            "confidence": confidence,
            "x1": float(np.min(xs)),
            "y1": float(np.min(ys)),
            "x2": float(np.max(xs)),
            "y2": float(np.max(ys)),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["width"] = df["x2"] - df["x1"]
    df["height"] = df["y2"] - df["y1"]
    df["x_center"] = (df["x1"] + df["x2"]) / 2.0
    df["y_center"] = (df["y1"] + df["y2"]) / 2.0
    return df


def classify_boxes(raw_easyocr_results: List, image_id: str = "scan") -> pd.DataFrame:
    """
    Classify each EasyOCR detection box as ingredient or non-ingredient.

    Args:
        raw_easyocr_results: Raw output from ``reader.readtext()`` —
            list of ``(bbox, text, confidence)`` tuples.
        image_id: Identifier for the image (used for grouping context).

    Returns:
        DataFrame with all original columns plus ``pred_prob`` and
        ``pred_label`` (using the saved decision threshold).
    """
    bundle = _load_model()
    classifier = bundle["classifier"]
    tfidf = bundle["tfidf"]
    dict_vec = bundle["dict_vectorizer"]
    threshold = bundle["decision_threshold"]

    df = _easyocr_results_to_dataframe(raw_easyocr_results, image_id=image_id)
    if df.empty:
        df["pred_prob"] = pd.Series(dtype=float)
        df["pred_label"] = pd.Series(dtype=int)
        return df

    df = _add_context_columns(df)

    X_text = tfidf.transform(df["context_text"])
    X_manual = dict_vec.transform(_make_manual_features(df))
    X = hstack([X_text, X_manual])

    probs = classifier.predict_proba(X)[:, 1]
    df["pred_prob"] = probs
    df["pred_label"] = (probs >= threshold).astype(int)

    logger.info(
        "Box classifier: %d boxes, %d predicted as ingredient (threshold=%.3f)",
        len(df),
        int(df["pred_label"].sum()),
        threshold,
    )
    return df
