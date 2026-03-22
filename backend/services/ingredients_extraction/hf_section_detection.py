"""
HuggingFace-based ingredient section detection.

Uses the openfoodfacts/ingredient-detection NER model (XLM-RoBERTa-large,
fine-tuned for token classification) to locate ingredient list spans inside
raw OCR text.  This replaces the regex-based extract_ingredients_section()
with a learned model that handles missing headers, corrupted text, and
multilingual labels.

The model is loaded lazily on first call and kept as a singleton.
"""

import logging
from typing import List, Optional

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


def extract_ingredients_section_hf(ocr_text: str) -> str:
    """
    Detect ingredient list span(s) in *ocr_text* using the HuggingFace
    NER model and return the concatenated text.

    Falls back to returning the full *ocr_text* when the model finds no
    ING entities (same contract as the regex version).
    """
    if not ocr_text or not ocr_text.strip():
        return ocr_text or ""

    ner = _get_pipeline()
    results = ner(ocr_text)

    ing_spans: List[dict] = [r for r in results if r["entity_group"] == "ING"]
    if not ing_spans:
        logger.debug("HF model found no ING spans — returning full text")
        return ocr_text

    texts: List[str] = []
    for span in ing_spans:
        fragment = ocr_text[span["start"]:span["end"]].strip()
        if fragment:
            texts.append(fragment)

    section = " ".join(texts)
    logger.debug("HF model extracted section (%d chars from %d spans)", len(section), len(ing_spans))
    return section
