"""
Rule-based Dietary Analysis
Fallback method for analyzing ingredients when LLM is unavailable.
"""

from typing import List
import logging

from backend.models import DietaryProfile

logger = logging.getLogger(__name__)


# =============================================================================
# Allergen Definitions
# =============================================================================

ALLERGENS = {
    'gluten': ['wheat', 'barley', 'rye', 'oats', 'gluten'],
    'dairy': ['milk', 'cheese', 'butter', 'cream', 'yogurt', 'lactose', 'whey'],
    'nuts': ['peanut', 'almond', 'walnut', 'cashew', 'hazelnut', 'pecan', 'pistachio'],
    'eggs': ['egg', 'albumin', 'lecithin'],
    'soy': ['soy', 'soya', 'tofu'],
    'halal_restricted': ['pork', 'gelatin', 'lard', 'bacon'],
    'vegetarian_restricted': ['meat', 'chicken', 'beef', 'pork', 'fish', 'gelatin'],
    'vegan_restricted': ['milk', 'cheese', 'butter', 'honey', 'egg', 'meat', 'chicken', 'beef', 'pork', 'fish']
}


def analyze_with_rules(
    ingredients: List[str],
    dietary_profile: DietaryProfile
) -> dict:
    """
    Rule-based analysis (fallback method when LLM is unavailable).
    
    Args:
        ingredients: List of ingredient names
        dietary_profile: User's dietary profile with restrictions
        
    Returns:
        Analysis result dict with is_safe, warnings, and analysis_result
    """
    warnings = []
    is_safe = True  # Start with safe, mark unsafe if violations found
    
    ingredients_lower = [ing.lower() for ing in ingredients]
    
    # Check each restriction
    if dietary_profile.gluten_free:
        for item in ALLERGENS['gluten']:
            if any(item in ing for ing in ingredients_lower):
                warnings.append(f"Contains gluten: {item}")
                is_safe = False
                break
    
    if dietary_profile.dairy_free:
        for item in ALLERGENS['dairy']:
            if any(item in ing for ing in ingredients_lower):
                warnings.append(f"Contains dairy: {item}")
                is_safe = False
                break
    
    if dietary_profile.nut_free:
        for item in ALLERGENS['nuts']:
            if any(item in ing for ing in ingredients_lower):
                warnings.append(f"Contains nuts: {item}")
                is_safe = False
                break
    
    if dietary_profile.halal:
        for item in ALLERGENS['halal_restricted']:
            if any(item in ing for ing in ingredients_lower):
                warnings.append(f"Not halal: Contains {item}")
                is_safe = False
                break
    
    if dietary_profile.vegetarian:
        for item in ALLERGENS['vegetarian_restricted']:
            if any(item in ing for ing in ingredients_lower):
                warnings.append(f"Not vegetarian: Contains {item}")
                is_safe = False
                break
    
    if dietary_profile.vegan:
        for item in ALLERGENS['vegan_restricted']:
            if any(item in ing for ing in ingredients_lower):
                warnings.append(f"Not vegan: Contains {item}")
                is_safe = False
                break
    
    # Check custom allergens
    if dietary_profile.allergens:
        for allergen in dietary_profile.allergens:
            if any(allergen.lower() in ing for ing in ingredients_lower):
                warnings.append(f"Contains your allergen: {allergen}")
                is_safe = False
    
    # Generate analysis result
    if is_safe:
        analysis_result = "This product is safe for your dietary preferences."
    else:
        if warnings:
            analysis_result = "This product is not suitable for your dietary preferences.\n" + "\n".join(warnings)
        else:
            analysis_result = "This product is not suitable for your dietary preferences."
    
    return {
        "is_safe": is_safe,
        "warnings": warnings,
        "analysis_result": analysis_result
    }
