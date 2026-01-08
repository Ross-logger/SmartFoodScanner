"""
Ingredient Extraction Service
Uses NLP-based extraction for reliable ingredient identification and correction.
"""

from app.services.ingredient_extraction.extractor import IngredientExtractor
from app.services.ingredient_extraction.nlp_extractor import NLPIngredientExtractor

__all__ = ['IngredientExtractor', 'NLPIngredientExtractor']
