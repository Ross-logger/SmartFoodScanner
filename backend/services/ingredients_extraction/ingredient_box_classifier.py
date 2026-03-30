"""
Ingredient box classification and merging pipeline.

Combines two stages:
  1. Box classification – loads a trained logistic regression model bundle
     (joblib) and classifies each EasyOCR detection box as ingredient (1)
     or non-ingredient (0).
  2. Box merging – takes the classified DataFrame and reconstructs a single
     coherent ingredient-text block by clustering, scoring, and joining the
     boxes the model considers part of the ingredients list.

"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from scipy.sparse import hstack

from backend import settings

logger = logging.getLogger(__name__)


def _df_select_rows(df: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    """
    Boolean row slice without index ``take`` (coverage + joblib can reload NumPy
    and break pandas boolean/integer ``take`` on RangeIndex in the same process).
    """
    parts: List[pd.DataFrame] = []
    for i in range(len(df)):
        if bool(mask.iloc[i]):
            parts.append(pd.DataFrame([df.iloc[i].to_dict()]))
    if not parts:
        return pd.DataFrame(columns=list(df.columns))
    out = pd.concat(parts, ignore_index=True)
    return out


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
            "Set BOX_CLASSIFIER_MODEL_PATH in your environment to point to the model file."
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
# EasyOCR results → DataFrame
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


# ---------------------------------------------------------------------------
# Stage 1 – Box classification (public API)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Stage 2 – Merge boxes: constants
# ---------------------------------------------------------------------------

HEADER_PATTERNS = [
    r"^\s*ingredients?\s*:?\s*$",
    r"^\s*(list|table)\s+of\s+ingredients?\s*:?\s*$",
    r"^\s*ingredients?\s+list\s*:?\s*$",
]

_NON_INGREDIENT_HINTS: Tuple[str, ...] = (
    "nutrition facts", "nutrition information", "nutritional information",
    "nutritional values", "supplement facts", "energy value",
    "reference intake", "daily value", "amount per serving",
    "per 100g", "per 100ml", "serving size",
    "of which saturates", "of which sugars", "carbohydrate",
    "total fat", "nutrition", "nutritional", "energy", "protein",
    "calories", "serving",
    "for allergens", "allergen advice", "allergen information",
    "allergen statement", "allergenic ingredients", "contains allergens",
    "may also contain", "traces of",
    "allergens", "allergen", "allergy", "allergies",
    "storage conditions", "storage instruction", "storage instructions",
    "storage", "store in a cool", "store in a dry", "store below",
    "store at", "store in", "keep refrigerated", "keep frozen",
    "once opened", "use within", "refrigerate after opening",
    "best before end", "best before", "for best before",
    "use by", "use before", "expiry date", "expiration date", "sell by",
    "batch code", "lot number", "lot no", "batch no",
    "manufactured by", "manufactured for", "manufactured",
    "produced by", "packed by", "packed for",
    "distributed by", "distributed in", "distributed",
    "imported by", "imported from", "made in", "product of",
    "country of origin", "registered office",
    "suitable for", "not suitable for", "recycling", "recycle",
    "https://", "http://", "www.", ".com", ".net", ".org",
    "e-mail", "email", "contact us", "customer service",
    "consumer care", "consumer information", "p.o. box", "po box",
    "@", "telephone", "tel.", "fax", "fax:",
)

GENERIC_BAD_HINTS = _NON_INGREDIENT_HINTS
TAIL_CUT_HINTS = _NON_INGREDIENT_HINTS


# ---------------------------------------------------------------------------
# Stage 2 – Text helpers
# ---------------------------------------------------------------------------

def normalize_text(s: str) -> str:
    return str(s).strip().lower()


def is_header(text: str) -> bool:
    t = normalize_text(text)
    return any(re.fullmatch(p, t) for p in HEADER_PATTERNS)


def has_bad_hint(text: str) -> bool:
    t = normalize_text(text)
    return any(w in t for w in GENERIC_BAD_HINTS)


def alpha_ratio(text: str) -> float:
    t = str(text)
    if not t:
        return 0.0
    alpha = sum(ch.isalpha() for ch in t)
    alnum = sum(ch.isalnum() for ch in t)
    return alpha / max(alnum, 1)


def digit_ratio(text: str) -> float:
    t = str(text)
    if not t:
        return 0.0
    digits = sum(ch.isdigit() for ch in t)
    alnum = sum(ch.isalnum() for ch in t)
    return digits / max(alnum, 1)


def symbol_ratio(text: str) -> float:
    t = str(text)
    if not t:
        return 0.0
    sym = sum(not ch.isalnum() and not ch.isspace() for ch in t)
    return sym / max(len(t), 1)


def looks_like_junk_fragment(text: str) -> bool:
    t = str(text).strip()
    if not t:
        return True
    if len(t) <= 2:
        return True
    if digit_ratio(t) > 0.75:
        return True
    if alpha_ratio(t) < 0.25 and len(t) <= 6:
        return True
    if len(t) <= 8 and symbol_ratio(t) > 0.4:
        return True
    if len(t) <= 8 and re.fullmatch(r"[A-Za-z0-9\-_/.]+", t) and alpha_ratio(t) < 0.5:
        return True
    return False


def looks_like_continuation(text: str) -> bool:
    t = str(text).strip()
    tl = t.lower()
    if not t:
        return False
    if t.startswith(("(", "[", "%", ",", ";", ":", "&")):
        return True
    if re.fullmatch(r"\(?\d+([.,]\d+)?%\)?", t):
        return True
    if tl.startswith(("and ", "with ", "from ", "of ", "or ")):
        return True
    if t and t[0].islower() and len(t) <= 20:
        return True
    return False


# ---------------------------------------------------------------------------
# Stage 2 – Box pipeline functions
# ---------------------------------------------------------------------------

def prepare_boxes(df_image: pd.DataFrame) -> pd.DataFrame:
    df = df_image.copy()

    required = ["x1", "y1", "x2", "y2", "pred_prob", "text"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    for col in ["x1", "y1", "x2", "y2", "pred_prob"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    if "confidence" not in df.columns:
        df["confidence"] = 1.0
    else:
        df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce").fillna(0.0)

    df["text"] = df["text"].fillna("").astype(str)
    df["width"] = df["x2"] - df["x1"]
    df["height"] = df["y2"] - df["y1"]
    df["x_center"] = (df["x1"] + df["x2"]) / 2.0
    df["y_center"] = (df["y1"] + df["y2"]) / 2.0
    return df


def find_header_box(df: pd.DataFrame) -> Optional[pd.Series]:
    headers = _df_select_rows(df, df["text"].apply(is_header))
    if len(headers) == 0:
        return None
    headers = headers.sort_values("y_center")
    return headers.iloc[0]


def filter_positive_boxes(
    df: pd.DataFrame,
    threshold: float = 0.4,
    strong_keep_threshold: float = 0.8,
) -> pd.DataFrame:
    pos = _df_select_rows(df, df["pred_prob"] >= threshold)
    if len(pos) == 0:
        return pos.reset_index(drop=True)

    pos = _df_select_rows(pos, ~pos["text"].apply(is_header))
    pos = _df_select_rows(
        pos,
        ~(pos["text"].apply(looks_like_junk_fragment)
          & (pos["pred_prob"] < strong_keep_threshold)),
    )
    pos = _df_select_rows(
        pos,
        ~(pos["text"].apply(has_bad_hint) & (pos["pred_prob"] < 0.92)),
    )
    return pos.reset_index(drop=True)


def apply_header_constraint(
    pos: pd.DataFrame,
    header_row: Optional[pd.Series],
    tolerance_above: float = 25.0,
) -> pd.DataFrame:
    if header_row is None or len(pos) == 0:
        return pos
    cutoff = float(header_row["y_center"]) - tolerance_above
    return _df_select_rows(
        pos, pos["y_center"] >= cutoff
    ).reset_index(drop=True)


def remove_isolated_boxes(
    pos: pd.DataFrame,
    y_radius: float = 120.0,
    x_radius: float = 900.0,
) -> pd.DataFrame:
    if len(pos) <= 1:
        return pos.copy()

    pos = pos.reset_index(drop=True)
    keep = []
    for i, row in pos.iterrows():
        dy = np.abs(pos["y_center"] - row["y_center"])
        dx = np.abs(pos["x_center"] - row["x_center"])
        neighbors = ((dy <= y_radius) & (dx <= x_radius)).sum() - 1
        if row["pred_prob"] >= 0.75 or neighbors >= 1 or looks_like_continuation(row["text"]):
            keep.append(True)
        else:
            keep.append(False)
    parts: List[pd.DataFrame] = []
    for i in range(len(pos)):
        if keep[i]:
            parts.append(pd.DataFrame([pos.iloc[i].to_dict()]))
    if not parts:
        return pd.DataFrame(columns=list(pos.columns))
    return pd.concat(parts, ignore_index=True).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Stage 2 – Clustering
# ---------------------------------------------------------------------------

def cluster_boxes_by_rows(
    pos: pd.DataFrame, row_gap: float = 90.0
) -> List[pd.DataFrame]:
    if len(pos) == 0:
        return []
    pos = pos.sort_values(["y_center", "x1"]).copy().reset_index(drop=True)
    clusters: List[pd.DataFrame] = []
    current = [pos.iloc[0]]

    for i in range(1, len(pos)):
        prev = current[-1]
        cur = pos.iloc[i]
        if abs(cur["y_center"] - prev["y_center"]) <= row_gap:
            current.append(cur)
        else:
            clusters.append(pd.DataFrame(current))
            current = [cur]

    clusters.append(pd.DataFrame(current))
    return clusters


def merge_close_clusters(
    clusters: List[pd.DataFrame], cluster_gap: float = 120.0
) -> List[pd.DataFrame]:
    if not clusters:
        return []
    merged = [clusters[0].copy()]
    for c in clusters[1:]:
        prev = merged[-1]
        prev_bottom = prev["y2"].max()
        cur_top = c["y1"].min()
        if cur_top - prev_bottom <= cluster_gap:
            merged[-1] = pd.concat([prev, c], ignore_index=True)
        else:
            merged.append(c.copy())
    return merged


def score_cluster(
    cluster: pd.DataFrame, header_row: Optional[pd.Series] = None
) -> float:
    score = float(cluster["pred_prob"].sum())
    score += 0.18 * len(cluster)

    bad_count = cluster["text"].apply(has_bad_hint).sum()
    score -= 0.8 * bad_count

    avg_text_len = cluster["text"].astype(str).str.len().mean()
    score += min(avg_text_len / 50.0, 0.6)

    if header_row is not None:
        cluster_top = float(np.min(cluster["y1"].to_numpy(dtype=np.float64)))
        dist = max(0.0, cluster_top - float(header_row["y2"]))
        score -= 0.002 * dist
    return float(score)


def choose_best_cluster(
    clusters: List[pd.DataFrame], header_row: Optional[pd.Series] = None
) -> Optional[pd.DataFrame]:
    if not clusters:
        return None
    scored = []
    for c in clusters:
        if len(c) == 0:
            continue
        scored.append((score_cluster(c, header_row=header_row), c))
    if not scored:
        return None
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1].copy().reset_index(drop=True)


# ---------------------------------------------------------------------------
# Stage 2 – Text reconstruction
# ---------------------------------------------------------------------------

def assign_rows(cluster: pd.DataFrame, row_gap: float = 45.0) -> pd.DataFrame:
    if len(cluster) == 0:
        return cluster.copy()
    cluster = cluster.sort_values(["y_center", "x1"]).copy().reset_index(drop=True)
    median_h = max(1.0, float(cluster["height"].median()))
    adaptive_gap = max(row_gap, median_h * 0.7)

    row_ids = []
    current_row = 0
    prev_y: Optional[float] = None

    for _, r in cluster.iterrows():
        if prev_y is None:
            row_ids.append(current_row)
            prev_y = r["y_center"]
            continue
        if abs(r["y_center"] - prev_y) <= adaptive_gap:
            row_ids.append(current_row)
        else:
            current_row += 1
            row_ids.append(current_row)
            prev_y = r["y_center"]

    cluster["row_id"] = row_ids
    return cluster


def cleanup_row_boxes(row_df: pd.DataFrame) -> pd.DataFrame:
    row_df = row_df.sort_values("x1").copy().reset_index(drop=True)
    keep = []
    for _, r in row_df.iterrows():
        txt = str(r["text"]).strip()
        if looks_like_junk_fragment(txt) and not looks_like_continuation(txt):
            keep.append(False)
            continue
        keep.append(True)
    parts: List[pd.DataFrame] = []
    for i in range(len(row_df)):
        if keep[i]:
            parts.append(pd.DataFrame([row_df.iloc[i].to_dict()]))
    if not parts:
        return pd.DataFrame(columns=list(row_df.columns))
    return pd.concat(parts, ignore_index=True).reset_index(drop=True)


def smart_join_row_texts(texts: List[str]) -> str:
    out: List[str] = []
    for t in texts:
        t = str(t).strip()
        if not t:
            continue
        if not out:
            out.append(t)
            continue
        prev = out[-1]
        if looks_like_continuation(t):
            out[-1] = prev.rstrip() + " " + t
            continue
        if prev.endswith(("(", "[", "/", "-", "&", ":")):
            out[-1] = prev + " " + t
            continue
        out.append(t)

    line = " ".join(out)
    line = re.sub(r"\s+", " ", line).strip()
    return line


def reconstruct_text_from_cluster(cluster: Optional[pd.DataFrame]) -> str:
    if cluster is None or len(cluster) == 0:
        return ""
    cluster = assign_rows(cluster)
    lines: List[str] = []
    for _, row_df in cluster.groupby("row_id", sort=True):
        row_df = cleanup_row_boxes(row_df)
        if len(row_df) == 0:
            continue
        line = smart_join_row_texts(row_df["text"].astype(str).tolist())
        if line:
            lines.append(line)
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Stage 2 – Post-processing
# ---------------------------------------------------------------------------

def trim_tail_by_hints(text: str) -> str:
    if not text:
        return ""
    lower = text.lower()
    cut_positions = []
    for hint in TAIL_CUT_HINTS:
        idx = lower.find(hint)
        if idx > 0:
            cut_positions.append(idx)
    if cut_positions:
        text = text[: min(cut_positions)].strip()
    return text


def remove_trailing_junk_lines(text: str) -> str:
    if not text:
        return ""
    cleaned_lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if has_bad_hint(line):
            continue
        if looks_like_junk_fragment(line):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def normalize_ingredient_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace(" ,", ",")
    text = text.replace(" .", ".")
    text = text.replace(" ;", ";")
    text = text.replace(" :", ":")
    text = text.replace(" )", ")")
    text = text.replace("( ", "(")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[\s,;:]+$", "", text).strip()
    return text


def postprocess_ingredient_text(text: str) -> str:
    text = trim_tail_by_hints(text)
    text = remove_trailing_junk_lines(text)
    text = normalize_ingredient_text(text)
    return text


# ---------------------------------------------------------------------------
# Stage 2 – High-level merge API
# ---------------------------------------------------------------------------

def extract_ingredient_region(
    df_boxes: pd.DataFrame,
    threshold: float = 0.4,
    row_gap: float = 90.0,
    cluster_gap: float = 120.0,
) -> Dict[str, Any]:
    """
    Run the full merge pipeline on a single image's boxes.

    Args:
        df_boxes: DataFrame with columns
            ``text, confidence, x1, y1, x2, y2, pred_prob``.
        threshold: Minimum ``pred_prob`` to keep a box.
        row_gap: Max vertical distance to group boxes into the same row cluster.
        cluster_gap: Max gap to merge adjacent clusters.

    Returns:
        Dict with ``raw_text`` and ``final_text`` keys (plus internals).
    """
    df = prepare_boxes(df_boxes)
    header_row = find_header_box(df)
    pos = filter_positive_boxes(df, threshold=threshold)
    pos = apply_header_constraint(pos, header_row)
    pos = remove_isolated_boxes(pos)

    clusters = cluster_boxes_by_rows(pos, row_gap=row_gap)
    clusters = merge_close_clusters(clusters, cluster_gap=cluster_gap)

    best_cluster = choose_best_cluster(clusters, header_row=header_row)
    raw_text = reconstruct_text_from_cluster(best_cluster)
    final_text = postprocess_ingredient_text(raw_text)

    return {
        "header_row": header_row,
        "positive_boxes": pos,
        "clusters": clusters,
        "best_cluster": best_cluster,
        "raw_text": raw_text,
        "final_text": final_text,
    }


def extract_ingredients_from_boxes(
    df_boxes: pd.DataFrame,
    threshold: float = 0.4,
    row_gap: float = 90.0,
    cluster_gap: float = 120.0,
) -> str:
    """
    Convenience wrapper: classify boxes then merge and return the final
    ingredient text string.

    Args:
        df_boxes: DataFrame with ``pred_prob`` column (from ``classify_boxes``).

    Returns:
        Merged + post-processed ingredient text string.
    """
    result = extract_ingredient_region(
        df_boxes,
        threshold=threshold,
        row_gap=row_gap,
        cluster_gap=cluster_gap,
    )
    final = result["final_text"]
    logger.info(
        "Merge boxes: %d chars of ingredient text extracted",
        len(final),
    )
    return final
