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
    
    return f"""You are a dietary analysis expert. Analyze the ingredients ONLY against the restrictions listed below. Those restrictions are the complete rule set for this task.

User's Dietary Restrictions: {restrictions_text}

Ingredients List:
{json.dumps(ingredients, indent=2)}

Rules (follow strictly):
- Set is_safe to true if nothing in the ingredients conflicts with the restrictions above. Set is_safe to false only when a listed restriction is clearly violated (or plausibly violated for ambiguous names).
- Do NOT treat dairy, eggs, nuts, gluten, halal, vegan, etc. as restrictions unless they appear explicitly in "User's Dietary Restrictions" above (including profile-derived labels like dairy-free, nut-free, or allergens listed there).
- Warnings must only mention ingredients that actually conflict with those restrictions. Never warn about milk, eggs, or other allergens unless the user restricted them.
- When matching custom restriction words (e.g. oil, cinnamon), treat obvious matches: e.g. "palm oil", "vegetable oil" for "oil"; "cinnamon" or clear cinnamon derivatives for "cinnamon"; "agar" or agar-derived terms for "agar". If the text is OCR-noisy, use reasonable inference but still only for the stated restrictions.
- Optional nuance: if restrictions are empty or "no specific dietary restrictions", is_safe is true and warnings empty unless you find a clear self-contradiction in the prompt.

Provide:
1. is_safe: true/false relative ONLY to the user's restrictions
2. warnings: only violations of those restrictions
3. analysis_result: short, second-person explanation; do not enumerate every restriction the user does NOT have

In the response, write the analysis from your POV to the user.

DO NOT explain safety by listing every restricted ingredient the user avoids (e.g. "safe because no cinnamon, oil...").

Respond ONLY with valid JSON in this exact format:
{{
    "is_safe": true/false,
    "warnings": ["warning1", "warning2"],
    "analysis_result": "Brief explanation here"
}}

Example — safe for the stated restrictions only (adapt to the actual list):
{{
    "is_safe": true,
    "warnings": [],
    "analysis_result": "This product looks fine for your restrictions. Nothing on the label clearly conflicts with what you asked to avoid. If you have other medical needs beyond this list, double-check the packaging."
}}

Example — not safe (user is dairy-free in restrictions):
{{
    "is_safe": false,
    "warnings": ["Contains whey (milk derivative), which conflicts with dairy-free."],
    "analysis_result": "This product is not safe for your restrictions because it includes milk-derived ingredients. Consider an alternative that fits your diet."
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
