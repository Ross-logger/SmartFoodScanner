"""
HuggingFace-based ingredient section detection.

Uses the openfoodfacts/ingredient-detection NER model (XLM-RoBERTa-large,
fine-tuned for token classification) to locate ingredient list spans inside
raw OCR text.  This replaces the regex-based extract_ingredients_section()
with a learned model that handles missing headers, corrupted text, and
multilingual labels.

The model is loaded lazily on first call and kept as a singleton.

NER aggregation returns entries like:
  {'entity_group': 'ING', 'word': '...', 'start': int, 'end': int, ...}

We splice text from the *original* OCR using character offsets so commas and
other separators between ING spans (often labeled non-ING) are preserved.
Joining only ``word`` fields would drop those delimiters.
"""

import logging
from typing import Any, List, Tuple, Optional

from backend.services.ingredients_extraction.utils import normalize_hf_ner_spacing

logger = logging.getLogger(__name__)

_ner_pipeline = None


def _get_pipeline():
    """Lazy-load the HF NER pipeline (singleton)."""
    global _ner_pipeline
    if _ner_pipeline is None:
        from transformers import pipeline as hf_pipeline

        from backend import settings

        model_name = settings.HF_INGREDIENT_DETECTION_MODEL
        logger.info("Loading HF ingredient-detection model: %s", model_name)
        _ner_pipeline = hf_pipeline(
            "token-classification",
            model=model_name,
            aggregation_strategy="simple",
        )
        logger.info("HF ingredient-detection model loaded.")
    return _ner_pipeline


def _merge_ing_spans_from_ocr(ocr_text: str, results: List[dict]) -> str:
    """
    Build ingredient-line text by taking slices from ocr_text for each ING
    entity and **concatenating the OCR gap** between consecutive spans.

    Those gaps are the only source of “separators”: e.g. ``, ``, ``\\n``,
    ``\\n\\n``, spaces, or ``;`` — whatever appears in the original text between
    the end of one ING span and the start of the next.
    """
    spans: List[Tuple[int, int]] = []
    for r in results:
        if r.get("entity_group") != "ING":
            continue
        s, e = r.get("start"), r.get("end")
        if s is None or e is None:
            continue
        s, e = int(s), int(e)
        if e <= s or s < 0 or e > len(ocr_text):
            continue
        spans.append((s, e))

    if not spans:
        return ""

    spans.sort(key=lambda x: x[0])
    merged: List[List[int]] = []
    for s, e in spans:
        if not merged or s > merged[-1][1]:
            merged.append([s, e])
        else:
            merged[-1][1] = max(merged[-1][1], e)

    parts: List[str] = []
    prev_end: Optional[int] = None
    for s, e in merged:
        if prev_end is not None:
            parts.append(ocr_text[prev_end:s])
        parts.append(ocr_text[s:e])
        prev_end = e
    return "".join(parts)


def _ingredients_from_word_fields(results: List[dict]) -> str:
    """Fallback when aggregated entities lack start/end (join ING words)."""
    parts: List[str] = []
    for result in results:
        if result.get("entity_group") != "ING":
            continue
        w = str(result.get("word", "")).strip()
        if w:
            parts.append(w)
    if not parts:
        return ""
    return normalize_hf_ner_spacing(" ".join(parts))


def extract_ingredients_list_hf(ocr_text: str) -> str:
    """
    Detect ingredient list span(s) in *ocr_text* using the HuggingFace
    NER model and return one string.

    Separators between ingredients are **not** predicted by the model: they are
    whatever characters appear in *ocr_text* between consecutive ING spans
    (commas, newlines, spaces, etc.). See ``_merge_ing_spans_from_ocr``.

    Falls back to *ocr_text* when the model finds no ING entities or on error
    (same rough contract as the regex section helper).
    """
    if not ocr_text or not ocr_text.strip():
        return ocr_text or ""

    try:
        ner = _get_pipeline()
        results: List[dict[str, Any]] = ner(ocr_text)
        merged = _merge_ing_spans_from_ocr(ocr_text, results)
        if merged.strip():
            return normalize_hf_ner_spacing(merged)
        fallback = _ingredients_from_word_fields(results)
        if fallback.strip():
            return normalize_hf_ner_spacing(fallback)
    except Exception:
        logger.exception("HF NER extraction failed; returning full OCR text")
        return ocr_text


    return ocr_text


# Back-compat for notebooks, docs, and `from module import *`
extract_ingredients_section_hf = extract_ingredients_list_hf
