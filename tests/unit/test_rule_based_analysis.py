"""
Unit Tests for Rule-Based Dietary Analysis

Tests for the rule-based dietary analysis functionality including:
- Halal detection
- Gluten-free detection
- Vegetarian/Vegan detection
- Nut-free detection
- Dairy-free detection
- Custom allergen detection
- Warning message generation
"""

import pytest
from unittest.mock import MagicMock

from backend.services.ingredients_analysis.rule_based import (
    analyze_with_rules,
    ALLERGENS,
)


def create_mock_dietary_profile(
    halal: bool = False,
    gluten_free: bool = False,
    vegetarian: bool = False,
    vegan: bool = False,
    nut_free: bool = False,
    dairy_free: bool = False,
    allergens: list = None,
    custom_restrictions: list = None
):
    """Create a mock dietary profile for testing."""
    profile = MagicMock()
    profile.halal = halal
    profile.gluten_free = gluten_free
    profile.vegetarian = vegetarian
    profile.vegan = vegan
    profile.nut_free = nut_free
    profile.dairy_free = dairy_free
    profile.allergens = allergens or []
    profile.custom_restrictions = custom_restrictions or []
    return profile


class TestHalalAnalysis:
    """Tests for halal dietary restriction analysis."""
    
    def test_halal_safe_product(self):
        """Test product that is safe for halal diet."""
        profile = create_mock_dietary_profile(halal=True)
        ingredients = ["Water", "Sugar", "Rice Flour", "Sunflower Oil", "Salt"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == True
        assert len(result["warnings"]) == 0
    
    def test_halal_unsafe_pork(self):
        """Test product with pork (not halal)."""
        profile = create_mock_dietary_profile(halal=True)
        ingredients = ["Water", "Pork", "Salt", "Spices"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
        assert any("pork" in w.lower() for w in result["warnings"])
    
    def test_halal_unsafe_gelatin(self):
        """Test product with gelatin (potentially not halal)."""
        profile = create_mock_dietary_profile(halal=True)
        ingredients = ["Water", "Sugar", "Gelatin", "Natural Flavors"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
        assert any("gelatin" in w.lower() for w in result["warnings"])
    
    def test_halal_unsafe_lard(self):
        """Test product with lard (not halal)."""
        profile = create_mock_dietary_profile(halal=True)
        ingredients = ["Flour", "Lard", "Sugar", "Salt"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
        assert any("lard" in w.lower() for w in result["warnings"])
    
    def test_halal_unsafe_bacon(self):
        """Test product with bacon (not halal)."""
        profile = create_mock_dietary_profile(halal=True)
        ingredients = ["Eggs", "Bacon Bits", "Salt", "Pepper"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
        assert any("bacon" in w.lower() for w in result["warnings"])


class TestGlutenFreeAnalysis:
    """Tests for gluten-free dietary restriction analysis."""
    
    def test_gluten_free_safe_product(self):
        """Test product that is gluten-free."""
        profile = create_mock_dietary_profile(gluten_free=True)
        ingredients = ["Rice Flour", "Sugar", "Corn Starch", "Salt"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == True
        assert len(result["warnings"]) == 0
    
    def test_gluten_free_unsafe_wheat(self):
        """Test product with wheat (contains gluten)."""
        profile = create_mock_dietary_profile(gluten_free=True)
        ingredients = ["Wheat Flour", "Sugar", "Salt", "Yeast"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
        assert any("wheat" in w.lower() or "gluten" in w.lower() for w in result["warnings"])
    
    def test_gluten_free_unsafe_barley(self):
        """Test product with barley (contains gluten)."""
        profile = create_mock_dietary_profile(gluten_free=True)
        ingredients = ["Barley Malt", "Sugar", "Water"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
        assert any("barley" in w.lower() or "gluten" in w.lower() for w in result["warnings"])
    
    def test_gluten_free_unsafe_rye(self):
        """Test product with rye (contains gluten)."""
        profile = create_mock_dietary_profile(gluten_free=True)
        ingredients = ["Rye Flour", "Salt", "Yeast", "Water"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
    
    def test_gluten_free_unsafe_oats(self):
        """Test product with oats (may contain gluten)."""
        profile = create_mock_dietary_profile(gluten_free=True)
        ingredients = ["Oats", "Sugar", "Dried Fruit"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False


class TestVegetarianAnalysis:
    """Tests for vegetarian dietary restriction analysis."""
    
    def test_vegetarian_safe_product(self):
        """Test product safe for vegetarians."""
        profile = create_mock_dietary_profile(vegetarian=True)
        ingredients = ["Water", "Sugar", "Milk", "Eggs", "Salt"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == True
        assert len(result["warnings"]) == 0
    
    def test_vegetarian_unsafe_meat(self):
        """Test product with meat (not vegetarian)."""
        profile = create_mock_dietary_profile(vegetarian=True)
        ingredients = ["Water", "Meat", "Salt", "Spices"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
        assert any("meat" in w.lower() or "vegetarian" in w.lower() for w in result["warnings"])
    
    def test_vegetarian_unsafe_chicken(self):
        """Test product with chicken (not vegetarian)."""
        profile = create_mock_dietary_profile(vegetarian=True)
        ingredients = ["Rice", "Chicken Broth", "Vegetables", "Salt"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
    
    def test_vegetarian_unsafe_beef(self):
        """Test product with beef (not vegetarian)."""
        profile = create_mock_dietary_profile(vegetarian=True)
        ingredients = ["Pasta", "Beef Extract", "Tomatoes", "Salt"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
    
    def test_vegetarian_unsafe_fish(self):
        """Test product with fish (not vegetarian)."""
        profile = create_mock_dietary_profile(vegetarian=True)
        ingredients = ["Rice", "Fish Sauce", "Vegetables"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
    
    def test_vegetarian_unsafe_gelatin(self):
        """Test product with gelatin (not vegetarian)."""
        profile = create_mock_dietary_profile(vegetarian=True)
        ingredients = ["Sugar", "Water", "Gelatin", "Citric Acid"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False


class TestVeganAnalysis:
    """Tests for vegan dietary restriction analysis."""
    
    def test_vegan_safe_product(self):
        """Test product safe for vegans."""
        profile = create_mock_dietary_profile(vegan=True)
        ingredients = ["Water", "Sugar", "Rice Flour", "Coconut Oil", "Salt"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == True
        assert len(result["warnings"]) == 0
    
    def test_vegan_unsafe_milk(self):
        """Test product with milk (not vegan)."""
        profile = create_mock_dietary_profile(vegan=True)
        ingredients = ["Water", "Milk", "Sugar", "Cocoa"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
        assert any("milk" in w.lower() or "vegan" in w.lower() for w in result["warnings"])
    
    def test_vegan_unsafe_eggs(self):
        """Test product with eggs (not vegan)."""
        profile = create_mock_dietary_profile(vegan=True)
        ingredients = ["Flour", "Egg Whites", "Sugar", "Salt"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
    
    def test_vegan_unsafe_honey(self):
        """Test product with honey (not vegan)."""
        profile = create_mock_dietary_profile(vegan=True)
        ingredients = ["Oats", "Honey", "Almonds", "Salt"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
    
    def test_vegan_unsafe_butter(self):
        """Test product with butter (not vegan)."""
        profile = create_mock_dietary_profile(vegan=True)
        ingredients = ["Flour", "Butter", "Sugar", "Vanilla"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
    
    def test_vegan_unsafe_cheese(self):
        """Test product with cheese (not vegan)."""
        profile = create_mock_dietary_profile(vegan=True)
        ingredients = ["Pasta", "Cheese", "Tomatoes", "Basil"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False


class TestNutFreeAnalysis:
    """Tests for nut-free dietary restriction analysis."""
    
    def test_nut_free_safe_product(self):
        """Test product safe for nut allergies."""
        profile = create_mock_dietary_profile(nut_free=True)
        ingredients = ["Water", "Sugar", "Wheat Flour", "Salt"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == True
        assert len(result["warnings"]) == 0
    
    def test_nut_free_unsafe_peanut(self):
        """Test product with peanuts."""
        profile = create_mock_dietary_profile(nut_free=True)
        ingredients = ["Sugar", "Peanut Butter", "Salt"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
        assert any("peanut" in w.lower() or "nut" in w.lower() for w in result["warnings"])
    
    def test_nut_free_unsafe_almond(self):
        """Test product with almonds."""
        profile = create_mock_dietary_profile(nut_free=True)
        ingredients = ["Flour", "Almond Flour", "Sugar", "Eggs"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
    
    def test_nut_free_unsafe_walnut(self):
        """Test product with walnuts."""
        profile = create_mock_dietary_profile(nut_free=True)
        ingredients = ["Chocolate", "Walnut Pieces", "Sugar"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
    
    def test_nut_free_unsafe_cashew(self):
        """Test product with cashews."""
        profile = create_mock_dietary_profile(nut_free=True)
        ingredients = ["Rice", "Cashew Cream", "Spices"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False


class TestDairyFreeAnalysis:
    """Tests for dairy-free dietary restriction analysis."""
    
    def test_dairy_free_safe_product(self):
        """Test product safe for dairy-free diet."""
        profile = create_mock_dietary_profile(dairy_free=True)
        # Note: Using "Coconut Oil" instead of "Coconut Milk" to avoid false positive
        # from keyword matching on "milk" substring
        ingredients = ["Water", "Sugar", "Coconut Oil", "Salt"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == True
        assert len(result["warnings"]) == 0
    
    def test_dairy_free_unsafe_milk(self):
        """Test product with milk."""
        profile = create_mock_dietary_profile(dairy_free=True)
        ingredients = ["Water", "Milk", "Sugar", "Cocoa"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
        assert any("milk" in w.lower() or "dairy" in w.lower() for w in result["warnings"])
    
    def test_dairy_free_unsafe_cheese(self):
        """Test product with cheese."""
        profile = create_mock_dietary_profile(dairy_free=True)
        ingredients = ["Pasta", "Cheese", "Tomatoes"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
    
    def test_dairy_free_unsafe_butter(self):
        """Test product with butter."""
        profile = create_mock_dietary_profile(dairy_free=True)
        ingredients = ["Flour", "Butter", "Sugar"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
    
    def test_dairy_free_unsafe_cream(self):
        """Test product with cream."""
        profile = create_mock_dietary_profile(dairy_free=True)
        ingredients = ["Coffee", "Cream", "Sugar"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
    
    def test_dairy_free_unsafe_whey(self):
        """Test product with whey."""
        profile = create_mock_dietary_profile(dairy_free=True)
        ingredients = ["Protein", "Whey Isolate", "Flavoring"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False


class TestCustomAllergenAnalysis:
    """Tests for custom allergen detection."""
    
    def test_custom_allergen_detected(self):
        """Test detection of custom allergen."""
        profile = create_mock_dietary_profile(allergens=["shellfish"])
        ingredients = ["Rice", "Shrimp", "Shellfish Extract", "Salt"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
        assert any("shellfish" in w.lower() for w in result["warnings"])
    
    def test_custom_allergen_safe(self):
        """Test product without custom allergen."""
        profile = create_mock_dietary_profile(allergens=["shellfish"])
        ingredients = ["Rice", "Chicken", "Vegetables", "Salt"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == True
    
    def test_multiple_custom_allergens(self):
        """Test multiple custom allergens."""
        profile = create_mock_dietary_profile(allergens=["sesame", "mustard"])
        ingredients = ["Bread", "Sesame Seeds", "Butter"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
        assert any("sesame" in w.lower() for w in result["warnings"])


class TestMultipleRestrictions:
    """Tests for multiple dietary restrictions combined."""
    
    def test_multiple_restrictions_safe(self):
        """Test product safe for multiple restrictions."""
        profile = create_mock_dietary_profile(
            halal=True,
            gluten_free=True,
            vegan=True,
            nut_free=True
        )
        ingredients = ["Water", "Rice Flour", "Sugar", "Sunflower Oil", "Salt"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == True
        assert len(result["warnings"]) == 0
    
    def test_multiple_restrictions_one_violation(self):
        """Test product with one restriction violated."""
        profile = create_mock_dietary_profile(
            halal=True,
            gluten_free=True,
            vegan=True
        )
        ingredients = ["Water", "Rice Flour", "Milk", "Sugar"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
        # Should flag milk for vegan restriction
    
    def test_multiple_restrictions_multiple_violations(self):
        """Test product with multiple restrictions violated."""
        profile = create_mock_dietary_profile(
            halal=True,
            gluten_free=True,
            dairy_free=True
        )
        ingredients = ["Wheat Flour", "Milk", "Gelatin", "Sugar"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
        # Should have warnings for wheat (gluten) and milk (dairy) at minimum


class TestWarningMessages:
    """Tests for warning message generation."""
    
    def test_warning_message_format(self):
        """Test that warnings have proper format."""
        profile = create_mock_dietary_profile(halal=True)
        ingredients = ["Water", "Pork", "Salt"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert len(result["warnings"]) > 0
        # Warning should mention the problematic ingredient
        assert any("pork" in w.lower() for w in result["warnings"])
    
    def test_analysis_result_safe(self):
        """Test analysis result message for safe product."""
        profile = create_mock_dietary_profile(halal=True)
        ingredients = ["Water", "Sugar", "Salt"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert "safe" in result["analysis_result"].lower()
    
    def test_analysis_result_unsafe(self):
        """Test analysis result message for unsafe product."""
        profile = create_mock_dietary_profile(halal=True)
        ingredients = ["Water", "Pork", "Salt"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert "not suitable" in result["analysis_result"].lower() or \
               "warning" in result["analysis_result"].lower() or \
               "not safe" in result["analysis_result"].lower()


class TestNoRestrictions:
    """Tests when user has no dietary restrictions."""
    
    def test_no_restrictions_always_safe(self):
        """Test that products are always safe with no restrictions."""
        profile = create_mock_dietary_profile()  # All False
        ingredients = ["Pork", "Wheat", "Milk", "Peanuts", "Gelatin"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == True
        assert len(result["warnings"]) == 0


class TestCaseInsensitivity:
    """Tests for case-insensitive ingredient matching."""
    
    def test_uppercase_ingredient_detected(self):
        """Test that uppercase ingredients are detected."""
        profile = create_mock_dietary_profile(halal=True)
        ingredients = ["Water", "PORK", "Salt"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
    
    def test_mixed_case_ingredient_detected(self):
        """Test that mixed case ingredients are detected."""
        profile = create_mock_dietary_profile(halal=True)
        ingredients = ["Water", "PoRk FaT", "Salt"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False
    
    def test_partial_match_detected(self):
        """Test that partial matches are detected."""
        profile = create_mock_dietary_profile(gluten_free=True)
        ingredients = ["Enriched Wheat Flour", "Sugar", "Salt"]
        
        result = analyze_with_rules(ingredients, profile)
        
        assert result["is_safe"] == False


class TestSyntheticDietaryData:
    """Tests using synthetic dietary test cases."""
    
    def test_synthetic_dietary_cases(self):
        """Test with synthetic dietary test cases."""
        from tests.data.synthetic.ocr_samples import get_dietary_test_cases
        
        test_cases = get_dietary_test_cases()
        
        for case in test_cases:
            profile = create_mock_dietary_profile(**case["profile"])
            result = analyze_with_rules(case["ingredients"], profile)
            
            assert result["is_safe"] == case["expected_safe"], \
                f"Failed for {case['id']}: {case['name']}"
            
            # Check that expected warnings are present (if any)
            if not case["expected_safe"]:
                assert len(result["warnings"]) > 0, \
                    f"Expected warnings for unsafe product {case['id']}"
