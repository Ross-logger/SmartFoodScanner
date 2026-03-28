"""
Ingredients Extraction Module
Provides ingredient extraction using LLM, SymSpell, box classifier, and other methods.
"""

from backend.services.ingredients_extraction.llm_extraction import (
    LLMIngredientExtractor,
    extract_ingredients_with_llm,
)
from backend.services.ingredients_extraction.extractor import extract
from backend.services.ingredients_extraction.symspell_extraction import (
    extract_ingredients,
    spellcheck_ingredients,
    get_e_number_name,
)
from backend.services.ingredients_extraction.box_classifier import classify_boxes
from backend.services.ingredients_extraction.merge_boxes import (
    extract_ingredients_from_boxes,
)
from backend.services.ingredients_extraction.ocr_corrector import (
    correct_ingredient_list,
)

__all__ = [
    'LLMIngredientExtractor',
    'extract_ingredients_with_llm',
    'extract',
    'extract_ingredients',
    'spellcheck_ingredients',
    'get_e_number_name',
    'classify_boxes',
    'extract_ingredients_from_boxes',
    'correct_ingredient_list',
]
