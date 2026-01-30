"""
Synthetic OCR Test Samples

Provides synthetic test data for OCR and ingredient extraction testing.
These samples simulate real-world ingredient label text.
"""

from typing import List, Dict, Any


# Synthetic OCR test cases with ground truth
SYNTHETIC_OCR_SAMPLES = [
    {
        "id": "syn_001",
        "name": "Simple Cookie Label",
        "ocr_text": "Ingredients: Wheat Flour, Sugar, Palm Oil, Salt, Baking Powder, Natural Vanilla Flavor",
        "ground_truth_text": "Ingredients: Wheat Flour, Sugar, Palm Oil, Salt, Baking Powder, Natural Vanilla Flavor",
        "ground_truth_ingredients": [
            "Wheat Flour", "Sugar", "Palm Oil", "Salt", 
            "Baking Powder", "Natural Vanilla Flavor"
        ],
        "dietary_flags": {
            "halal": True,
            "gluten_free": False,
            "vegetarian": True,
            "vegan": True,
            "nut_free": True,
            "dairy_free": True
        },
        "quality": "clear",
        "packaging_type": "box"
    },
    {
        "id": "syn_002",
        "name": "Chocolate Bar with Allergens",
        "ocr_text": "INGREDIENTS: Sugar, Cocoa Butter, Whole Milk Powder, Cocoa Mass, Soy Lecithin (E322), Vanilla Extract. May contain traces of nuts.",
        "ground_truth_text": "INGREDIENTS: Sugar, Cocoa Butter, Whole Milk Powder, Cocoa Mass, Soy Lecithin (E322), Vanilla Extract. May contain traces of nuts.",
        "ground_truth_ingredients": [
            "Sugar", "Cocoa Butter", "Whole Milk Powder", "Cocoa Mass",
            "Soy Lecithin", "Vanilla Extract"
        ],
        "dietary_flags": {
            "halal": True,
            "gluten_free": True,
            "vegetarian": True,
            "vegan": False,
            "nut_free": False,  # May contain traces
            "dairy_free": False
        },
        "quality": "clear",
        "packaging_type": "wrapper"
    },
    {
        "id": "syn_003",
        "name": "Instant Noodles with OCR Errors",
        "ocr_text": "lngredients: Wheat F1our, Pa1m 0il, Salt, Sugar, Monosodium G1utamate, Dried Vegetables (Carrot, Onion), Spices",
        "ground_truth_text": "Ingredients: Wheat Flour, Palm Oil, Salt, Sugar, Monosodium Glutamate, Dried Vegetables (Carrot, Onion), Spices",
        "ground_truth_ingredients": [
            "Wheat Flour", "Palm Oil", "Salt", "Sugar",
            "Monosodium Glutamate", "Dried Vegetables", "Carrot", "Onion", "Spices"
        ],
        "dietary_flags": {
            "halal": True,
            "gluten_free": False,
            "vegetarian": True,
            "vegan": True,
            "nut_free": True,
            "dairy_free": True
        },
        "quality": "moderate",
        "packaging_type": "packet"
    },
]


# Test cases for different dietary restrictions
DIETARY_TEST_CASES = [
    # Halal tests
    {
        "id": "diet_halal_001",
        "name": "Product with Gelatin (Not Halal)",
        "ingredients": ["Water", "Sugar", "Gelatin", "Citric Acid", "Natural Flavors"],
        "profile": {"halal": True},
        "expected_safe": False,
        "expected_warnings": ["gelatin"]
    },
    {
        "id": "diet_halal_002", 
        "name": "Product with Pork (Not Halal)",
        "ingredients": ["Pork", "Salt", "Spices", "Sugar"],
        "profile": {"halal": True},
        "expected_safe": False,
        "expected_warnings": ["pork"]
    },
    {
        "id": "diet_halal_003",
        "name": "Halal Safe Product",
        "ingredients": ["Water", "Sugar", "Rice Flour", "Sunflower Oil", "Salt"],
        "profile": {"halal": True},
        "expected_safe": True,
        "expected_warnings": []
    },
    
    # Gluten-free tests
    {
        "id": "diet_gluten_001",
        "name": "Product with Wheat (Contains Gluten)",
        "ingredients": ["Wheat Flour", "Sugar", "Salt", "Yeast", "Water"],
        "profile": {"gluten_free": True},
        "expected_safe": False,
        "expected_warnings": ["wheat"]
    },
    {
        "id": "diet_gluten_002",
        "name": "Product with Barley (Contains Gluten)",
        "ingredients": ["Barley Malt", "Sugar", "Water", "Natural Flavors"],
        "profile": {"gluten_free": True},
        "expected_safe": False,
        "expected_warnings": ["barley"]
    },
    {
        "id": "diet_gluten_003",
        "name": "Gluten-Free Product",
        "ingredients": ["Rice Flour", "Sugar", "Corn Starch", "Salt", "Baking Soda"],
        "profile": {"gluten_free": True},
        "expected_safe": True,
        "expected_warnings": []
    },
    
    # Vegan tests
    {
        "id": "diet_vegan_001",
        "name": "Product with Milk (Not Vegan)",
        "ingredients": ["Water", "Sugar", "Milk Powder", "Cocoa", "Salt"],
        "profile": {"vegan": True},
        "expected_safe": False,
        "expected_warnings": ["milk"]
    },
    {
        "id": "diet_vegan_002",
        "name": "Product with Eggs (Not Vegan)",
        "ingredients": ["Flour", "Sugar", "Egg Whites", "Butter", "Salt"],
        "profile": {"vegan": True},
        "expected_safe": False,
        "expected_warnings": ["egg", "butter"]
    },
    {
        "id": "diet_vegan_003",
        "name": "Vegan Product",
        "ingredients": ["Water", "Sugar", "Coconut Oil", "Rice Flour", "Salt"],
        "profile": {"vegan": True},
        "expected_safe": True,
        "expected_warnings": []
    },
    
    # Vegetarian tests
    {
        "id": "diet_veg_001",
        "name": "Product with Meat (Not Vegetarian)",
        "ingredients": ["Water", "Beef Extract", "Salt", "Spices", "Onion"],
        "profile": {"vegetarian": True},
        "expected_safe": False,
        "expected_warnings": ["beef"]
    },
    {
        "id": "diet_veg_002",
        "name": "Vegetarian Product",
        "ingredients": ["Water", "Sugar", "Milk", "Eggs", "Salt", "Vanilla"],
        "profile": {"vegetarian": True},
        "expected_safe": True,
        "expected_warnings": []
    },
    
    # Nut-free tests
    {
        "id": "diet_nut_001",
        "name": "Product with Peanuts",
        "ingredients": ["Sugar", "Peanut Butter", "Salt", "Cocoa"],
        "profile": {"nut_free": True},
        "expected_safe": False,
        "expected_warnings": ["peanut"]
    },
    {
        "id": "diet_nut_002",
        "name": "Product with Almonds",
        "ingredients": ["Sugar", "Almond Flour", "Butter", "Salt"],
        "profile": {"nut_free": True},
        "expected_safe": False,
        "expected_warnings": ["almond"]
    },
    
    # Dairy-free tests
    {
        "id": "diet_dairy_001",
        "name": "Product with Milk",
        "ingredients": ["Water", "Milk", "Sugar", "Salt"],
        "profile": {"dairy_free": True},
        "expected_safe": False,
        "expected_warnings": ["milk"]
    },
    {
        "id": "diet_dairy_002",
        "name": "Product with Cheese",
        "ingredients": ["Flour", "Cheese", "Butter", "Salt"],
        "profile": {"dairy_free": True},
        "expected_safe": False,
        "expected_warnings": ["cheese", "butter"]
    },
    
    # Multiple restrictions
    {
        "id": "diet_multi_001",
        "name": "Product Safe for Multiple Restrictions",
        "ingredients": ["Water", "Rice Flour", "Sugar", "Sunflower Oil", "Salt"],
        "profile": {"halal": True, "gluten_free": True, "vegan": True, "nut_free": True},
        "expected_safe": True,
        "expected_warnings": []
    },
    {
        "id": "diet_multi_002",
        "name": "Product Unsafe for Multiple Restrictions",
        "ingredients": ["Wheat Flour", "Butter", "Eggs", "Sugar", "Peanuts"],
        "profile": {"gluten_free": True, "vegan": True, "nut_free": True},
        "expected_safe": False,
        "expected_warnings": ["wheat", "butter", "egg", "peanut"]
    },
]


# Performance test samples (larger datasets)
PERFORMANCE_TEST_SAMPLES = [
    {
        "id": f"perf_{i:03d}",
        "ocr_text": f"Ingredients: Water, Sugar, Wheat Flour, Palm Oil, Salt, Yeast, Natural Flavor {i}",
        "ingredients": ["Water", "Sugar", "Wheat Flour", "Palm Oil", "Salt", "Yeast", f"Natural Flavor {i}"],
    }
    for i in range(1, 51)  # 50 samples for performance testing
]


def get_synthetic_ocr_samples() -> List[Dict[str, Any]]:
    """Get all synthetic OCR samples."""
    return SYNTHETIC_OCR_SAMPLES


def get_dietary_test_cases() -> List[Dict[str, Any]]:
    """Get all dietary restriction test cases."""
    return DIETARY_TEST_CASES


def get_performance_samples() -> List[Dict[str, Any]]:
    """Get samples for performance testing."""
    return PERFORMANCE_TEST_SAMPLES


def get_sample_by_id(sample_id: str) -> Dict[str, Any]:
    """Get a specific sample by ID."""
    all_samples = SYNTHETIC_OCR_SAMPLES + DIETARY_TEST_CASES + PERFORMANCE_TEST_SAMPLES
    for sample in all_samples:
        if sample["id"] == sample_id:
            return sample
    return {}
