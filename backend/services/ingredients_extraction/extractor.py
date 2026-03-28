from typing import List
from backend.services.ingredients_extraction.symspell_extraction import extract_ingredients


def extract(text: str) -> List[str]:
    """
    Extract ingredients from OCR text
    
    Args:
        text: Raw OCR text
        
    Returns:
        List of extracted ingredient names
    """
    if not text:
        return []
    
    return extract_ingredients(text)
