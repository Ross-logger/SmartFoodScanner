"""
Ingredients Extraction Module
Provides ingredient extraction using LLM, Hugging Face, and other methods.
"""

from backend.services.ingredients_extraction.llm_extraction import (
    LLMIngredientExtractor,
    extract_ingredients_with_llm,
)
from backend.services.ingredients_extraction.extractor import extract
from backend.services.ingredients_extraction.hugging_face_extractor import extract_ingredients

__all__ = [
    'LLMIngredientExtractor',
    'extract_ingredients_with_llm',
    'extract',
    'extract_ingredients',
]
