from typing import List, Optional
from app.models import DietaryProfile


def analyze_ingredients(
    ingredients: List[str],
    dietary_profile: Optional[DietaryProfile]
) -> dict:
    """
    Analyze ingredients against dietary restrictions.
    This is a simple rule-based analysis. In production, you'd use an LLM.
    """
    if not dietary_profile:
        return {
            "is_safe": False,
            "warnings": ["No dietary profile set"],
            "analysis_result": "Please set your dietary profile to get the analysis."
        }
    
    warnings = []
    is_safe = False
    analysis_result = "Please set your dietary profile to get the analysis."
    
    # Common allergens and restricted ingredients
    allergens = {
        'gluten': ['wheat', 'barley', 'rye', 'oats', 'gluten'],
        'dairy': ['milk', 'cheese', 'butter', 'cream', 'yogurt', 'lactose', 'whey'],
        'nuts': ['peanut', 'almond', 'walnut', 'cashew', 'hazelnut', 'pecan', 'pistachio'],
        'eggs': ['egg', 'albumin', 'lecithin'],
        'soy': ['soy', 'soya', 'tofu'],
        'halal_restricted': ['pork', 'gelatin', 'lard', 'bacon'],
        'vegetarian_restricted': ['meat', 'chicken', 'beef', 'pork', 'fish', 'gelatin'],
        'vegan_restricted': ['milk', 'cheese', 'butter', 'honey', 'egg', 'meat', 'chicken', 'beef', 'pork', 'fish']
    }
    
    ingredients_lower = [ing.lower() for ing in ingredients]
    
    # Check each restriction
    if dietary_profile.gluten_free:
        for item in allergens['gluten']:
            if any(item in ing for ing in ingredients_lower):
                warnings.append(f"Contains gluten: {item}")
                is_safe = False
                break
    
    if dietary_profile.dairy_free:
        for item in allergens['dairy']:
            if any(item in ing for ing in ingredients_lower):
                warnings.append(f"Contains dairy: {item}")
                is_safe = False
                break
    
    if dietary_profile.nut_free:
        for item in allergens['nuts']:
            if any(item in ing for ing in ingredients_lower):
                warnings.append(f"Contains nuts: {item}")
                is_safe = False
                break
    
    if dietary_profile.halal:
        for item in allergens['halal_restricted']:
            if any(item in ing for ing in ingredients_lower):
                warnings.append(f"Not halal: Contains {item}")
                is_safe = False
                break
    
    if dietary_profile.vegetarian:
        for item in allergens['vegetarian_restricted']:
            if any(item in ing for ing in ingredients_lower):
                warnings.append(f"Not vegetarian: Contains {item}")
                is_safe = False
                break
    
    if dietary_profile.vegan:
        for item in allergens['vegan_restricted']:
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

