"""
LLM-based Dietary Analysis
Uses LLM to analyze ingredients against user's dietary restrictions.
"""

from typing import List, Optional
import json
import logging

from backend.models import DietaryProfile
from backend import settings
from backend.services.llm import LLMService

logger = logging.getLogger(__name__)


ANALYSIS_SYSTEM_PROMPT = (
    "You are a dietary analysis expert. "
    "Always respond with valid JSON only, no additional text."
)


def build_dietary_prompt(ingredients: List[str], dietary_profile: DietaryProfile) -> str:
    """Build the prompt for dietary analysis."""
    restrictions = []
    if dietary_profile.gluten_free:
        restrictions.append("gluten-free")
    if dietary_profile.dairy_free:
        restrictions.append("dairy-free")
    if dietary_profile.nut_free:
        restrictions.append("nut-free")
    if dietary_profile.halal:
        restrictions.append("halal")
    if dietary_profile.vegetarian:
        restrictions.append("vegetarian")
    if dietary_profile.vegan:
        restrictions.append("vegan")
    if dietary_profile.allergens:
        restrictions.append(f"allergic to: {', '.join(dietary_profile.allergens)}")
    if dietary_profile.custom_restrictions:
        restrictions.append(f"custom restrictions: {', '.join(dietary_profile.custom_restrictions)}")
    
    restrictions_text = ", ".join(restrictions) if restrictions else "no specific dietary restrictions"
    
    return f"""You are a dietary analysis expert. Analyze the following ingredients list against the user's dietary restrictions and provide a detailed assessment.

User's Dietary Restrictions: {restrictions_text}

Ingredients List:
{json.dumps(ingredients, indent=2)}

Analyze these ingredients and provide:
1. Whether the product is SAFE (is_safe: true/false) for the user's dietary restrictions
2. Any specific warnings (warnings: array of warning messages) about ingredients that violate restrictions
3. A clear, user-friendly analysis result (analysis_result: string) explaining the safety assessment

Consider:
- Hidden ingredients and derivatives (e.g., whey contains dairy, lecithin may contain eggs)
- Cross-contamination risks
- Ambiguous ingredient names
- Common allergens and their variations

In the response, write the analysis from your POV to the user. e.g. "... The product is safe for your dietary restrictions ..."
DO NOT write and explain the safety of a product by writing "The product is safe because it does not contain cinnamon, oil, sugar, etc.", no need to list the restricted ingredients of a user.

Respond ONLY with valid JSON in this exact format:
{{
    "is_safe": true/false,
    "warnings": ["warning1", "warning2"],
    "analysis_result": "Brief explanation here"
}}

Example — product is safe (tone and specificity; adapt to the actual list above):
{{
    "is_safe": true,
    "warnings": [],
    "analysis_result": "This product looks fine for your restrictions. Ingredients that would clearly conflict are not present."; if your needs are strict (e.g. severe allergy), still confirm on the package and with the manufacturer when unsure."
}}

Example — product is not safe:
{{
    "is_safe": false,
    "warnings": ["Contains whey (milk derivative), which is not compatible with dairy-free."],
    "analysis_result": "This product is not safe for your restrictions. The label includes dairy-derived components. Consider choosing a product without milk or whey, or one explicitly marked for your diet."
}}"""


def _validate_analysis_result(result: dict) -> Optional[dict]:
    """Validate and normalize LLM analysis response."""
    # Validate response structure
    if not all(key in result for key in ["is_safe", "warnings", "analysis_result"]):
        logger.warning("LLM response missing required fields")
        return None
    
    # Ensure warnings is a list
    if not isinstance(result["warnings"], list):
        result["warnings"] = []
    
    # Ensure is_safe is boolean
    result["is_safe"] = bool(result["is_safe"])
    
    return result


def analyze_with_llm(
    ingredients: List[str],
    dietary_profile: DietaryProfile
) -> Optional[dict]:
    """
    Analyze ingredients using LLM via the unified service.
    
    Args:
        ingredients: List of ingredient names
        dietary_profile: User's dietary profile with restrictions
        
    Returns:
        Analysis result dict or None if LLM is not available or fails.
    """
    # Use LLM_ANALYZE_MODEL if set, otherwise use provider's default
    model_override = settings.LLM_ANALYZE_MODEL if settings.LLM_ANALYZE_MODEL else None
    llm_service = LLMService.from_settings(settings, model_override)
    
    if not llm_service.is_available:
        logger.warning("No LLM provider available for analysis")
        return None
    
    prompt = build_dietary_prompt(ingredients, dietary_profile)
    result = llm_service.call(
        prompt=prompt,
        system_prompt=ANALYSIS_SYSTEM_PROMPT,
        parse_json=True
    )
    
    if result is None:
        return None
    
    # Get provider name and remove internal key
    provider_name = result.pop("_provider", "unknown")
    
    # Validate the result
    validated = _validate_analysis_result(result)
    if validated:
        logger.info(f"LLM analysis completed with {provider_name}: is_safe={validated['is_safe']}, warnings={len(validated['warnings'])}")
    
    return validated
