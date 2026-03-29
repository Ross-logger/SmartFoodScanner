"""
LLM-based Ingredient Extractor
Uses LLM to accurately extract ingredients from food product labels.

Benchmark (offline artefact ``tests/data/comparison_result_with_llm_extraction.json``):
100 label images with ground truth in ``tests/data/true_ingredients_for_llm.json`` (``IMG_0045.png``
excluded: unusable Mistral OCR in cache). Per-image macro averages:

- **Exact (set overlap):** precision 95.09%, recall 95.05%, F1 95.06%
- **Fuzzy (threshold 0.8):** precision 95.78%, recall 95.74%, F1 95.75%
- **Merge (substring containment):** precision 95.18%, recall 95.19%, F1 95.17%
- **Split vs merge gap (mean):** recall +0.14%pt, precision +0.09%pt (merge − exact)
"""

from typing import Dict, Any, Optional
import logging

from backend.services.llm import LLMService
from backend.services.ingredients_extraction.utils import post_process_ingredients

logger = logging.getLogger(__name__)


# =============================================================================
# Extraction Prompts
# =============================================================================

EXTRACTION_SYSTEM_PROMPT = (
    "You are an expert food ingredient extractor. "
    "Extract ingredients accurately given the instructions."
    "Always respond with valid JSON only."
)


def build_extraction_prompt(text: str) -> str:
    """Build the prompt for ingredient extraction."""
    return f"""You are an expert food ingredient extractor. Your task is to extract ALL ingredients from the given text, which may be from a food product label.

CRITICAL INSTRUCTIONS:
1. Extract ONLY the actual food ingredients - not packaging info, brand names, nutritional values, marketing text, or standalone allergen advisory lines (e.g. "Contains: Milk", "May contain traces of nuts"). Do NOT treat the words "contains" or "with" inside a single compound ingredient as an allergen line to skip.
2. Preserve scientific names in parentheses when present (e.g., "Vitamin C (Ascorbic Acid)")
3. Keep compound/nested ingredients together as a single entry, preserving the sub-ingredient list in round parentheses ONLY (never square brackets or curly braces):
   - "Choco Cream (36%) [Sugar, Vegetable Fat, Cocoa Solids, Emulsifiers (E322)]" -> one entry: "Choco Cream (Sugar, Vegetable Fat, Cocoa Solids, Emulsifiers (E322))"
   - "Breadcrumbs {{Wheat Flour, Yeast, Salt}}" -> one entry: "Breadcrumbs (Wheat Flour, Yeast, Salt)"
   - Only split at the TOP-LEVEL comma separators between ingredients, not within parentheses
3b. UK/EU flour and similar compound declarations: copy the label wording for that one ingredient; do NOT shorten or rephrase.
   - If the text says "Wheatflour contains Gluten (with Wheatflour, Calcium Carbonate, Iron, Niacin, Thiamin)" or "Wheatflour (contains Gluten) (with ...)", output it that way — keep the phrase "contains Gluten" and the "(with ...)" fortification list exactly as written (aside from removing percentages and normalising "&amp;" to "&").
   - Wrong: "Wheatflour (Gluten, Calcium Carbonate, Iron, Niacin, Thiamin)" or dropping "contains Gluten" / "(with ...)".
4. For food additive codes (E-numbers / INS numbers), preserve the EXACT prefix format from the original text:
   - If the text uses "E" prefix (E322, E-450, E 471), output with "E" prefix (e.g., "E322", "E450", "E471")
   - If the text uses "INS" prefix (INS 330, INS322), output with "INS" prefix (e.g., "INS 330", "INS 322")
   - Preserve sub-part notation like (i), (ii) when present (e.g., "E500(ii)", "INS 451(i)")
   - Do NOT expand additive codes with their chemical names - output ONLY the code (e.g., "E471" not "E471 (Mono- and Diglycerides)")
5. Remove percentages and "contains X%" annotations, but keep sub-ingredient lists intact
6. Do NOT use accented characters - use plain ASCII (e.g., "Puree" not "Puree", "Creme" not "Creme")
7. Do NOT include "&amp;" in output - use "&" instead
8. Do NOT include asterisks (*) in ingredient names
9. If no ingredients are found or the text doesn't contain ingredient information, return an empty array

INPUT TEXT:
{text}

Respond ONLY with valid JSON in this exact format:
{{
    "ingredients": ["ingredient1", "ingredient2", "ingredient3"]
}}

EXAMPLE:
- Input: "Ingredients: Choco Cream (36%) [Sugar, Vegetable Fat, Cocoa Solids, Emulsifiers (E322 from Soya)], Refined Wheat Flour (Maida), Sugar, Edible Vegetable Oil (Palm), Raising Agents [E503(ii), E500(ii)], Iodised Salt"
  Output: {{"ingredients": ["Choco Cream (Sugar, Vegetable Fat, Cocoa Solids, Emulsifiers (E322 from Soya))", "Refined Wheat Flour (Maida)", "Sugar", "Edible Vegetable Oil (Palm)", "Raising Agents (E503(ii), E500(ii))", "Iodised Salt"]}}
- Input: "INGREDIENTS Wheatflour contains Gluten (with Wheatflour, Calcium Carbonate, Iron, Niacin, Thiamin), Butter (Milk), Sugar"
  Output: {{"ingredients": ["Wheatflour contains Gluten (with Wheatflour, Calcium Carbonate, Iron, Niacin, Thiamin)", "Butter (Milk)", "Sugar"]}}"""


def _validate_extraction_result(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Validate, clean and post-process extraction result."""
    if "ingredients" not in result:
        logger.warning("LLM response missing 'ingredients' field")
        return None

    if not isinstance(result["ingredients"], list):
        result["ingredients"] = []

    result["ingredients"] = post_process_ingredients(result["ingredients"])
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
            - ingredients: List of extracted ingredient names
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
            "provider": provider_name
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
