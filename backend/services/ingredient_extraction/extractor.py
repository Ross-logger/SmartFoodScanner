"""
Ingredient Extractor
Uses Hugging Face model for ingredient extraction.
"""

from typing import List
from backend.services.ingredient_extraction.hugging_face_extractor import extract_ingredients


def extract(text: str) -> List[str]:
    """
    Extract ingredients from OCR text using Hugging Face model.
    
    Args:
        text: Raw OCR text
        
    Returns:
        List of extracted ingredient names
    """
    if not text:
        return []
    
    return extract_ingredients(text)
