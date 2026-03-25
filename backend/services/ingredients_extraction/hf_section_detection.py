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
We concatenate the *word* fragments for ING spans (tokenizer-normalized spacing).
"""

import logging
from typing import List

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


def extract_ingredients_list_hf(ocr_text: str) -> str:
    """
    Detect ingredient list span(s) in *ocr_text* using the HuggingFace
    NER model and return one string (joined ING *word* fields).

    Falls back to *ocr_text* when the model finds no ING entities or on error
    (same rough contract as the regex section helper).
    """
    if not ocr_text or not ocr_text.strip():
        return ocr_text or ""

    try:
        ner = _get_pipeline()
        results = ner(ocr_text)
        parts: List[str] = []
        for result in results:
            if result.get("entity_group") != "ING":
                continue
            w = str(result.get("word", "")).strip()
            if w:
                parts.append(w)
    except Exception:
        logger.exception("HF NER extraction failed; returning full OCR text")
        return ocr_text

    if not parts:
        return ocr_text
    return normalize_hf_ner_spacing(" ".join(parts))


# Back-compat for notebooks, docs, and `from module import *`
extract_ingredients_section_hf = extract_ingredients_list_hf
