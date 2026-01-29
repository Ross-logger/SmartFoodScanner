"""
LLM-based Ingredient Extractor
Uses LLM to accurately extract and translate ingredients to English.
"""

from typing import Dict, Any, Optional
import logging

from backend.services.llm import LLMService

logger = logging.getLogger(__name__)


# =============================================================================
# Extraction Prompts
# =============================================================================

EXTRACTION_SYSTEM_PROMPT = (
    "You are an expert food ingredient extractor. "
    "Extract ingredients accurately and translate them to English. "
    "Always respond with valid JSON only."
)


def build_extraction_prompt(text: str) -> str:
    """Build the prompt for ingredient extraction."""
    return f"""You are an expert food ingredient extractor. Your task is to extract ALL ingredients from the given text, which may be from a food product label.

CRITICAL INSTRUCTIONS:
1. Extract ONLY the actual food ingredients - not packaging info, brand names, nutritional values, or marketing text
2. Translate ALL ingredients to English if they are in another language
3. Preserve scientific names in parentheses when present (e.g., "Vitamin C (Ascorbic Acid)")
4. Split compound ingredients appropriately (e.g., "vegetable oils (palm, sunflower)" becomes separate entries)
5. Include E-numbers with their names when identifiable (e.g., "E471" becomes "E471 (Mono- and Diglycerides)")
6. Normalize ingredient names to their common English form
7. Remove percentages, quantities, and "contains X%" type annotations - just extract the ingredient name
8. If no ingredients are found or the text doesn't contain ingredient information, return an empty array

INPUT TEXT:
{text}

Respond ONLY with valid JSON in this exact format:
{{
    "ingredients": ["ingredient1", "ingredient2", "ingredient3"],
    "detected_language": "detected source language or 'english' if already in English",
    "confidence": "high/medium/low"
}}

EXAMPLES:
- Input: "Zutaten: Wasser, Zucker, Weizenmehl"
  Output: {{"ingredients": ["Water", "Sugar", "Wheat Flour"], "detected_language": "german", "confidence": "high"}}

- Input: "مكونات: ماء، سكر، دقيق القمح"
  Output: {{"ingredients": ["Water", "Sugar", "Wheat Flour"], "detected_language": "arabic", "confidence": "high"}}

- Input: "Ingredients: Water, Sugar (15%), Wheat Flour, Emulsifier (E471), Natural Flavoring"
  Output: {{"ingredients": ["Water", "Sugar", "Wheat Flour", "E471 (Mono- and Diglycerides)", "Natural Flavoring"], "detected_language": "english", "confidence": "high"}}"""


def _validate_extraction_result(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Validate and clean extraction result."""
    if "ingredients" not in result:
        logger.warning("LLM response missing 'ingredients' field")
        return None
    
    # Ensure ingredients is a list
    if not isinstance(result["ingredients"], list):
        result["ingredients"] = []
    
    # Clean and validate ingredients
    cleaned_ingredients = []
    for ing in result["ingredients"]:
        if isinstance(ing, str):
            cleaned = ing.strip()
            if cleaned and len(cleaned) > 1:  # Filter out single characters
                cleaned_ingredients.append(cleaned)
    
    result["ingredients"] = cleaned_ingredients
    return result


# =============================================================================
# Main Extraction Interface
# =============================================================================

class LLMIngredientExtractor:
    """
    High-level interface for extracting ingredients using LLM.
    Uses the unified LLM service for provider management.
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        Initialize the extractor.
        
        Args:
            llm_service: LLM service instance. If None, will be created from settings.
        """
        self._llm_service = llm_service
    
    @classmethod
    def from_settings(cls, settings) -> "LLMIngredientExtractor":
        """Create extractor with provider configured from settings."""
        # Use LLM_EXTRACTOR_MODEL if set, otherwise use provider's default
        model_override = settings.LLM_EXTRACTOR_MODEL if settings.LLM_EXTRACTOR_MODEL else None
        llm_service = LLMService.from_settings(settings, model_override)
        return cls(llm_service=llm_service)
    
    def extract(self, text: str) -> Dict[str, Any]:
        """
        Extract ingredients from text using LLM.
        
        Args:
            text: Raw text (possibly from OCR) containing ingredient information
            
        Returns:
            Dictionary with:
            - ingredients: List of extracted ingredient names in English
            - success: Boolean indicating if extraction was successful
            - message: Optional message about the extraction
            - provider: Name of the provider that succeeded (if any)
        """
        if not text or not text.strip():
            return {
                "ingredients": [],
                "success": False,
                "message": "No text provided for extraction"
            }
        
        if not self._llm_service or not self._llm_service.is_available:
            return {
                "ingredients": [],
                "success": False,
                "message": "No LLM providers configured"
            }
        
        logger.info(f"Extracting ingredients from text: {text[:100]}...")
        
        prompt = build_extraction_prompt(text)
        result = self._llm_service.call(
            prompt=prompt,
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            parse_json=True
        )
        
        if result is None:
            return {
                "ingredients": [],
                "success": False,
                "message": "Failed to extract ingredients from LLM"
            }
        
        # Get provider name and remove internal key
        provider_name = result.pop("_provider", "unknown")
        
        # Validate the result
        validated = _validate_extraction_result(result)
        if validated is None:
            return {
                "ingredients": [],
                "success": False,
                "message": "Invalid response format from LLM"
            }
        
        logger.info(f"Successfully extracted {len(validated['ingredients'])} ingredients with {provider_name}")
        
        return {
            "ingredients": validated.get("ingredients", []),
            "success": True,
            "message": f"Extracted {len(validated['ingredients'])} ingredients using {provider_name}",
            "provider": provider_name,
            "detected_language": validated.get("detected_language", "unknown"),
            "confidence": validated.get("confidence", "unknown")
        }


# =============================================================================
# Backward-Compatible Function Interface
# =============================================================================

def extract_ingredients_with_llm(text: str) -> Dict[str, Any]:
    """
    Extract ingredients from text using LLM.
    
    This is the main entry point for ingredient extraction.
    """
    from backend import settings
    
    logger.info(f"Using LLM provider: {settings.LLM_PROVIDER}")
    extractor = LLMIngredientExtractor.from_settings(settings)
    return extractor.extract(text)
