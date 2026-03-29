from typing import List

from backend.services.ingredients_extraction.llm_extraction import (
    extract_ingredients_with_llm,
)


def extract(text: str) -> List[str]:
    """
    Extract ingredients from OCR text using LLM extraction.

    Args:
        text: Raw OCR text

    Returns:
        List of extracted ingredient names
    """
    if not text or not text.strip():
        return []

    result = extract_ingredients_with_llm(text)
    if result.get("success") and result.get("ingredients"):
        return result["ingredients"]
    return []
