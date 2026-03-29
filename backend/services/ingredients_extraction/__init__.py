"""
Ingredients Extraction Module
Provides ingredient extraction using LLM, box classifier, and other methods.
"""

from backend.services.ingredients_extraction.llm_extraction import (
    LLMIngredientExtractor,
    extract_ingredients_with_llm,
)
from backend.services.ingredients_extraction.ingredient_box_classifier import (
    classify_boxes,
    extract_ingredients_from_boxes,
)
from backend.services.ingredients_extraction.ocr_corrector import (
    correct_ingredient_list,
)

__all__ = [
    'LLMIngredientExtractor',
    'extract_ingredients_with_llm',
    'classify_boxes',
    'extract_ingredients_from_boxes',
    'correct_ingredient_list',
]
