"""
Synthetic OCR lines and dietary scenarios for unit/integration tests.

Dietary ``expected_safe`` values match ``analyze_with_rules`` when the LLM is bypassed.
"""

from __future__ import annotations

from typing import Any, Dict, List


def get_synthetic_ocr_samples() -> List[Dict[str, Any]]:
    return [
        {
            "id": "syn_001",
            "ocr_text": "Water, Sugar, Salt",
            "ground_truth_text": "Water, Sugar, Salt",
            "ground_truth_ingredients": ["Water", "Sugar", "Salt"],
        },
        {
            "id": "syn_002",
            "ocr_text": "Wheat Flour, Palm Oil, Salt",
            "ground_truth_text": "Wheat Flour, Palm Oil, Salt",
            "ground_truth_ingredients": ["Wheat Flour", "Palm Oil", "Salt"],
        },
        {
            "id": "syn_003",
            "ocr_text": "Watr Suger Salt",
            "ground_truth_text": "Water Sugar Salt",
            "ground_truth_ingredients": ["Water", "Sugar", "Salt"],
        },
    ]


def get_dietary_test_cases() -> List[Dict[str, Any]]:
    return [
        {"id": "halal_safe", "name": "Halal safe", "profile": {"halal": True}, "ingredients": ["Water", "Rice", "Salt"], "expected_safe": True},
        {"id": "halal_pork", "name": "Halal pork", "profile": {"halal": True}, "ingredients": ["Water", "Pork"], "expected_safe": False},
        {"id": "halal_gel", "name": "Halal gelatin", "profile": {"halal": True}, "ingredients": ["Gelatin", "Sugar"], "expected_safe": False},
        {"id": "halal_lard", "name": "Halal lard", "profile": {"halal": True}, "ingredients": ["Lard"], "expected_safe": False},
        {"id": "halal_alc", "name": "Halal ethanol", "profile": {"halal": True}, "ingredients": ["Ethanol"], "expected_safe": False},
        {"id": "halal_wine", "name": "Halal wine", "profile": {"halal": True}, "ingredients": ["Wine"], "expected_safe": False},
        {"id": "halal_beer", "name": "Halal beer", "profile": {"halal": True}, "ingredients": ["Beer"], "expected_safe": False},
        {"id": "halal_safe2", "name": "Halal beef ok", "profile": {"halal": True}, "ingredients": ["Beef", "Salt"], "expected_safe": True},
        {"id": "halal_gluten", "name": "Halal + GF safe", "profile": {"halal": True, "gluten_free": True}, "ingredients": ["Rice", "Oil"], "expected_safe": True},
        {"id": "halal_gluten_bad", "name": "Halal + GF pork", "profile": {"halal": True, "gluten_free": True}, "ingredients": ["Pork", "Rice"], "expected_safe": False},
        {"id": "gf_safe", "name": "GF rice", "profile": {"gluten_free": True}, "ingredients": ["Rice", "Corn"], "expected_safe": True},
        {"id": "gf_wheat", "name": "GF wheat", "profile": {"gluten_free": True}, "ingredients": ["Wheat Flour"], "expected_safe": False},
        {"id": "gf_malt", "name": "GF malt", "profile": {"gluten_free": True}, "ingredients": ["Malt Extract"], "expected_safe": False},
        {"id": "gf_oats", "name": "GF oats", "profile": {"gluten_free": True}, "ingredients": ["Oats"], "expected_safe": False},
        {"id": "gf_barley", "name": "GF barley", "profile": {"gluten_free": True}, "ingredients": ["Barley Malt"], "expected_safe": False},
        {"id": "gf_safe2", "name": "GF pseudo grains", "profile": {"gluten_free": True}, "ingredients": ["Quinoa", "Amaranth"], "expected_safe": True},
        {"id": "veg_safe", "name": "Vegetarian dairy ok", "profile": {"vegetarian": True}, "ingredients": ["Milk", "Eggs", "Cheese"], "expected_safe": True},
        {"id": "veg_chicken", "name": "Vegetarian chicken", "profile": {"vegetarian": True}, "ingredients": ["Chicken"], "expected_safe": False},
        {"id": "veg_fish", "name": "Vegetarian fish", "profile": {"vegetarian": True}, "ingredients": ["Salmon"], "expected_safe": False},
        {"id": "veg_gel", "name": "Vegetarian gelatin", "profile": {"vegetarian": True}, "ingredients": ["Gelatin"], "expected_safe": False},
        {"id": "vegan_safe", "name": "Vegan soy", "profile": {"vegan": True}, "ingredients": ["Water", "Sugar", "Soy Protein"], "expected_safe": True},
        {"id": "vegan_milk", "name": "Vegan milk", "profile": {"vegan": True}, "ingredients": ["Milk"], "expected_safe": False},
        {"id": "vegan_honey", "name": "Vegan honey", "profile": {"vegan": True}, "ingredients": ["Honey"], "expected_safe": False},
        {"id": "vegan_egg", "name": "Vegan egg", "profile": {"vegan": True}, "ingredients": ["Egg Yolk"], "expected_safe": False},
        {"id": "vegan_veg_combo", "name": "Vegan + veg flags", "profile": {"vegan": True, "vegetarian": True}, "ingredients": ["Tofu", "Rice"], "expected_safe": True},
        {"id": "vegan_veg_bad", "name": "Vegan + veg chicken", "profile": {"vegan": True, "vegetarian": True}, "ingredients": ["Chicken"], "expected_safe": False},
        {"id": "nut_safe", "name": "Nut-free seeds", "profile": {"nut_free": True}, "ingredients": ["Water", "Sunflower Seeds"], "expected_safe": True},
        {"id": "nut_peanut", "name": "Nut-free peanuts", "profile": {"nut_free": True}, "ingredients": ["Peanuts"], "expected_safe": False},
        {"id": "nut_almond", "name": "Nut-free almond flour", "profile": {"nut_free": True}, "ingredients": ["Almond Flour"], "expected_safe": False},
        {"id": "dairy_safe", "name": "Dairy-free oil", "profile": {"dairy_free": True}, "ingredients": ["Water", "Oil"], "expected_safe": True},
        {"id": "dairy_butter", "name": "Dairy-free butter", "profile": {"dairy_free": True}, "ingredients": ["Butter"], "expected_safe": False},
        {"id": "dairy_whey", "name": "Dairy-free whey", "profile": {"dairy_free": True}, "ingredients": ["Whey Protein"], "expected_safe": False},
        {"id": "multi_gf_veg", "name": "GF + veg safe", "profile": {"gluten_free": True, "vegetarian": True}, "ingredients": ["Rice", "Vegetables"], "expected_safe": True},
        {"id": "multi_gf_veg_bad", "name": "GF + veg wheat", "profile": {"gluten_free": True, "vegetarian": True}, "ingredients": ["Wheat", "Lettuce"], "expected_safe": False},
        {"id": "custom_sesame", "name": "Custom sesame tahini", "profile": {"allergens": ["sesame"]}, "ingredients": ["Tahini"], "expected_safe": True},
        {"id": "custom_safe", "name": "Custom sesame absent", "profile": {"allergens": ["sesame"]}, "ingredients": ["Water"], "expected_safe": True},
        {"id": "custom_mustard", "name": "Custom mustard hit", "profile": {"allergens": ["mustard"]}, "ingredients": ["Mustard Seeds"], "expected_safe": False},
        {"id": "none_safe", "name": "No restrictions", "profile": {}, "ingredients": ["Anything"], "expected_safe": True},
    ]
