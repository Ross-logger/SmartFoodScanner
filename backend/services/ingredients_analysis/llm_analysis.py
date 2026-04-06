"""
LLM-based Dietary Analysis
Uses LLM to analyze ingredients against user's dietary restrictions.
"""

from typing import List, Optional
import logging

from backend.models import DietaryProfile
from backend import settings
from backend.services.llm import LLMService

logger = logging.getLogger(__name__)


ANALYSIS_SYSTEM_PROMPT = (
    "You are a food safety checker. "
    "Always respond with valid JSON only, no additional text."
)

# Flat banned-term lists per restriction — short and scannable for small models.
_BANNED: dict[str, list[str]] = {
    "vegan": [
        "meat", "chicken", "beef", "pork", "lamb", "turkey", "duck", "venison",
        "fish", "salmon", "tuna", "cod", "anchovy", "anchovies", "sardine", "herring",
        "shrimp", "prawn", "crab", "lobster", "shellfish", "squid",
        "egg", "eggs", "albumin", "ovalbumin",
        "milk", "cream", "butter", "cheese", "yoghurt", "yogurt", "whey", "casein",
        "lactose", "ghee", "buttermilk",
        "honey", "beeswax", "royal jelly",
        "gelatin", "gelatine", "lard", "suet", "animal fat", "tallow",
        "chicken stock", "beef stock", "fish stock", "bone broth", "rennet",
        "carmine", "cochineal", "isinglass",
    ],
    "vegetarian": [
        "meat", "chicken", "beef", "pork", "lamb", "turkey", "duck", "venison",
        "fish", "salmon", "tuna", "cod", "anchovy", "anchovies", "sardine", "herring",
        "shrimp", "prawn", "crab", "lobster", "shellfish", "squid",
        "gelatin", "gelatine", "lard", "suet", "animal fat", "tallow",
        "chicken stock", "beef stock", "fish stock", "bone broth",
        "chicken extract", "beef extract", "meat extract", "rennet",
    ],
    "halal": [
        "pork", "pig", "ham", "bacon", "lard", "pepperoni", "salami", "chorizo",
        "prosciutto", "pancetta", "mortadella",
        "gelatin", "gelatine", "blood",
        "alcohol", "wine", "beer", "rum", "vodka", "whisky", "whiskey",
        "brandy", "liqueur", "ethanol", "mirin", "cooking wine",
    ],
    "gluten-free": [
        "wheat", "wheat flour", "barley", "rye", "oats", "oat flakes", "spelt",
        "semolina", "durum", "bulgur", "couscous", "malt", "malt extract",
        "gluten", "seitan", "breadcrumbs",
    ],
    "dairy-free": [
        "milk", "whole milk", "skimmed milk", "cream", "butter", "cheese",
        "yoghurt", "yogurt", "whey", "casein", "caseinate", "lactose",
        "ghee", "buttermilk", "custard", "kefir",
    ],
    "nut-free": [
        "almond", "almonds", "walnut", "walnuts", "cashew", "cashews",
        "hazelnut", "hazelnuts", "pecan", "pecans", "pistachio", "pistachios",
        "peanut", "peanuts", "groundnut", "groundnuts", "macadamia",
        "brazil nut", "pine nut", "chestnut", "nut", "nuts",
    ],
}


def build_dietary_prompt(ingredients: List[str], dietary_profile: DietaryProfile) -> str:
    """Build a short, small-model-friendly prompt for dietary analysis."""
    restriction_labels: list[str] = []
    banned_terms: list[str] = []

    if dietary_profile.vegan:
        restriction_labels.append("vegan")
        banned_terms.extend(_BANNED["vegan"])
    if dietary_profile.vegetarian:
        restriction_labels.append("vegetarian")
        banned_terms.extend(_BANNED["vegetarian"])
    if dietary_profile.halal:
        restriction_labels.append("halal")
        banned_terms.extend(_BANNED["halal"])
    if dietary_profile.gluten_free:
        restriction_labels.append("gluten-free")
        banned_terms.extend(_BANNED["gluten-free"])
    if dietary_profile.dairy_free:
        restriction_labels.append("dairy-free")
        banned_terms.extend(_BANNED["dairy-free"])
    if dietary_profile.nut_free:
        restriction_labels.append("nut-free")
        banned_terms.extend(_BANNED["nut-free"])
    if dietary_profile.allergens:
        restriction_labels.append(f"allergic to {', '.join(dietary_profile.allergens)}")
        banned_terms.extend(dietary_profile.allergens)
    if dietary_profile.custom_restrictions:
        restriction_labels.append(f"custom: {', '.join(dietary_profile.custom_restrictions)}")
        banned_terms.extend(dietary_profile.custom_restrictions)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_banned: list[str] = []
    for t in banned_terms:
        if t.lower() not in seen:
            seen.add(t.lower())
            unique_banned.append(t)

    if not restriction_labels:
        return (
            f'Ingredients: {", ".join(ingredients)}\n'
            f'Reply with JSON: {{"is_safe": true, "warnings": [], "analysis_result": "No dietary restrictions set."}}'
        )

    diet = ", ".join(restriction_labels)
    banned_str = ", ".join(unique_banned)
    ingredients_str = ", ".join(ingredients)

    return (
        f"Is this food safe for someone who is {diet}?\n"
        f"NOT ALLOWED: {banned_str}\n"
        f"Ingredients: {ingredients_str}\n"
        f'Reply with JSON only: {{"is_safe": true/false, "warnings": ["item: reason"], "analysis_result": "one sentence"}}'
    )


def _validate_analysis_result(result: dict) -> Optional[dict]:
    """Validate and normalise LLM analysis response."""
    if not all(key in result for key in ["is_safe", "warnings", "analysis_result"]):
        logger.warning("LLM response missing required fields")
        return None

    if not isinstance(result["warnings"], list):
        result["warnings"] = []

    result["is_safe"] = bool(result["is_safe"])

    # Hard consistency fix: warnings present → must be unsafe.
    if result["warnings"] and result["is_safe"]:
        logger.warning(
            "LLM contradiction: warnings present but is_safe=True — forcing is_safe=False."
        )
        result["is_safe"] = False

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
    model_override = settings.LLM_ANALYZE_MODEL if settings.LLM_ANALYZE_MODEL else None
    llm_service = LLMService.from_settings(settings, model_override)

    if not llm_service.is_available:
        logger.warning("No LLM provider available for analysis")
        return None

    prompt = build_dietary_prompt(ingredients, dietary_profile)
    logger.info(f"LLM analysis request — ingredients ({len(ingredients)}): {ingredients}")
    logger.info(f"LLM prompt:\n{prompt}")
    result = llm_service.call(
        prompt=prompt,
        system_prompt=ANALYSIS_SYSTEM_PROMPT,
        parse_json=True
    )

    if result is None:
        return None

    provider_name = result.pop("_provider", "unknown")

    validated = _validate_analysis_result(result)
    if validated:
        logger.info(
            f"LLM analysis completed with {provider_name}: "
            f"is_safe={validated['is_safe']}, warnings={len(validated['warnings'])}"
        )

    return validated
