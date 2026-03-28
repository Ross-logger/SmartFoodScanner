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
    'gluten': [
        'gluten',
        'wheat', 'wheat flour', 'whole wheat', 'whole wheat flour', 'wheat flour (atta)',
        'atta', 'maida', 'semolina', 'durum', 'durum wheat', 'durum wheat semolina',
        'spelt', 'kamut', 'farro', 'einkorn', 'emmer', 'bulgur', 'couscous',
        'bran', 'wheat bran', 'wheat germ', 'malt', 'barley', 'barley flour',
        'barley malt', 'barley malt extract', 'malted barley', 'malt extract',
        'malt vinegar', 'rye', 'rye flour', 'oats', 'oat flakes', 'oat bran',
        'triticale', 'seitan', 'breadcrumbs', 'bread crumbs',
        'wheat starch', 'modified wheat starch'
    ],

    'dairy': [
        'milk', 'whole milk', 'skimmed milk', 'skimmilk', 'skim milk',
        'semi-skimmed milk', 'condensed milk', 'evaporated milk',
        'milk solids', 'milk powder', 'milk protein', 'milk proteins',
        'milk fat', 'milk permeate', 'milk derivative',
        'dried milk', 'dried whole milk', 'dried skimmed milk',
        'skimmed milk powder', 'whole milk powder',
        'cheese', 'cheddar', 'mozzarella', 'parmesan', 'gouda', 'gruyere',
        'butter', 'butterfat', 'butter oil', 'cream', 'double cream',
        'single cream', 'sour cream', 'whipping cream',
        'yogurt', 'yoghurt', 'greek yogurt', 'greek yoghurt',
        'greek style yogurt', 'greek style yoghurt',
        'kefir', 'curd', 'custard',
        'whey', 'whey powder', 'whey protein', 'whey protein concentrate',
        'whey solids', 'casein', 'caseinate', 'sodium caseinate',
        'calcium caseinate', 'lactose', 'buttermilk', 'ghee',
        'from milk', '(milk)'
    ],

    'nuts': [
        'nut', 'nuts',
        'peanut', 'peanuts', 'groundnut', 'groundnuts',
        'almond', 'almonds',
        'walnut', 'walnuts',
        'cashew', 'cashews', 'cashewnut', 'cashewnuts',
        'hazelnut', 'hazelnuts',
        'pecan', 'pecans',
        'pistachio', 'pistachios', 'pistachio nuts',
        'macadamia', 'macadamias', 'macadamia nuts',
        'brazil nut', 'brazil nuts',
        'pine nut', 'pine nuts',
        'chestnut', 'chestnuts',
        'mixed nuts', 'nut pieces', 'nut flour', 'nut paste',
        'almond flour', 'almond meal', 'almond paste',
        'hazelnut paste', 'cashew paste', 'peanut butter'
    ],

    'eggs': [
        'egg', 'eggs', 'egg white', 'egg whites', 'egg yolk', 'egg yolks',
        'albumin', 'ovalbumin', 'egg albumen', 'dried egg', 'powdered egg',
        'pasteurised egg', 'pasteurized egg', 'egg powder',
        'meringue'
    ],

    'soy': [
        'soy', 'soya', 'soybean', 'soybeans', 'soy bean',
        'soy flour', 'soya flour',
        'soy protein', 'soy protein isolate', 'soya protein',
        'soya protein isolate', 'isolated soya protein',
        'soy lecithin', 'soya lecithin', 'lecithin (soya)',
        'textured soy protein', 'textured vegetable protein', 'tvp',
        'soy milk', 'soya milk',
        'soy sauce', 'soya sauce',
        'tofu', 'tempeh', 'miso', 'edamame'
    ],

    'halal_restricted': [
        'pork', 'pork fat', 'pork gelatin', 'pork gelatine',
        'ham', 'bacon', 'lard', 'pepperoni', 'salami',
        'prosciutto', 'pancetta', 'chorizo', 'mortadella',
        'gelatin', 'gelatine',
        'blood', 'blood plasma',
        'rum', 'wine', 'beer', 'brandy', 'whisky', 'whiskey',
        'vodka', 'liqueur', 'alcohol', 'ethanol',
        'mirin', 'cooking wine'
    ],

    'vegetarian_restricted': [
        'meat', 'chicken', 'beef', 'pork', 'bacon', 'ham',
        'turkey', 'duck', 'lamb', 'mutton', 'veal',
        'fish', 'salmon', 'tuna', 'anchovy', 'anchovies',
        'sardine', 'sardines', 'cod', 'prawn', 'shrimp',
        'crab', 'lobster', 'gelatin', 'gelatine',
        'animal fat', 'beef fat', 'chicken fat', 'fish oil',
        'meat extract', 'chicken extract', 'beef extract',
        'stock', 'chicken stock', 'beef stock', 'fish stock',
        'broth', 'chicken broth', 'beef broth',
        'animal rennet', 'rennet', 'lard', 'suet',
        'shellfish', 'oyster', 'mussel', 'clam'
    ],

    'vegan_restricted': [
        'milk', 'whole milk', 'skimmed milk', 'skim milk',
        'milk solids', 'milk powder', 'milk protein', 'milk fat',
        'cheese', 'butter', 'butterfat', 'butter oil', 'cream',
        'yogurt', 'yoghurt', 'kefir', 'curd', 'custard',
        'whey', 'whey powder', 'whey protein', 'casein', 'caseinate',
        'lactose', 'buttermilk', 'ghee',
        'egg', 'eggs', 'egg white', 'egg yolk', 'albumin', 'ovalbumin',
        'honey', 'beeswax', 'royal jelly', 'propolis',
        'meat', 'chicken', 'beef', 'pork', 'fish', 'shellfish',
        'gelatin', 'gelatine', 'lard', 'suet',
        'animal fat', 'meat extract', 'chicken stock', 'beef stock',
        'fish oil', 'anchovy', 'anchovies', 'rennet', 'animal rennet'
    ]
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
    
    if dietary_profile.dairy_free:
        for item in ALLERGENS['dairy']:
            if any(item in ing for ing in ingredients_lower):
                warnings.append(f"Contains dairy: {item}")
                is_safe = False
    
    if dietary_profile.nut_free:
        for item in ALLERGENS['nuts']:
            if any(item in ing for ing in ingredients_lower):
                warnings.append(f"Contains nuts: {item}")
                is_safe = False
    
    if dietary_profile.halal:
        for item in ALLERGENS['halal_restricted']:
            if any(item in ing for ing in ingredients_lower):
                warnings.append(f"Not halal: Contains {item}")
                is_safe = False
    
    if dietary_profile.vegetarian:
        for item in ALLERGENS['vegetarian_restricted']:
            if any(item in ing for ing in ingredients_lower):
                warnings.append(f"Not vegetarian: Contains {item}")
                is_safe = False
    
    if dietary_profile.vegan:
        for item in ALLERGENS['vegan_restricted']:
            if any(item in ing for ing in ingredients_lower):
                warnings.append(f"Not vegan: Contains {item}")
                is_safe = False
    
    # Check custom allergens (one warning line, comma-separated names)
    if dietary_profile.allergens:
        matched_custom = [
            allergen
            for allergen in dietary_profile.allergens
            if any(allergen.lower() in ing for ing in ingredients_lower)
        ]
        if matched_custom:
            warnings.append(
                "Contains your allergens: " + ", ".join(matched_custom)
            )
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
