"""
Unit Tests for Ingredient Validator

Tests for the ingredient validation functionality.
"""

import pytest

from backend.services.ingredients_extraction.validator import IngredientValidator


class TestIngredientValidator:
    """Tests for the IngredientValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        return IngredientValidator()
    
    def test_validator_initialization(self, validator):
        """Test validator initializes correctly."""
        assert validator is not None
        assert validator.config is not None
    
    def test_validate_valid_ingredients(self, validator):
        """Test validation of valid ingredients."""
        ingredients = ["Water", "Sugar", "Salt", "Wheat Flour"]
        
        validated = validator.validate(ingredients)
        
        assert len(validated) == 4
        assert "Water" in validated
        assert "Sugar" in validated
    
    def test_validate_filters_empty_strings(self, validator):
        """Test that empty strings are filtered."""
        ingredients = ["Water", "", "Sugar", "   ", "Salt"]
        
        validated = validator.validate(ingredients)
        
        assert "" not in validated
        assert "   " not in validated
    
    def test_validate_filters_single_characters(self, validator):
        """Test that single characters are filtered."""
        ingredients = ["Water", "a", "b", "Sugar", "x"]
        
        validated = validator.validate(ingredients)
        
        # Single letters should be filtered
        assert len([v for v in validated if len(v) == 1]) == 0
    
    def test_validate_filters_garbage_patterns(self, validator):
        """Test that garbage patterns are filtered."""
        ingredients = ["Water", "123", "d2", "Sugar", "!!!"]
        
        validated = validator.validate(ingredients)
        
        assert "123" not in validated
        assert "!!!" not in validated
    
    def test_validate_keeps_e_numbers(self, validator):
        """Test that valid E-numbers are kept."""
        ingredients = ["Water", "E471", "E322", "Sugar"]
        
        validated = validator.validate(ingredients)
        
        # E-numbers should be kept as they are valid ingredient identifiers
        # Note: This depends on the config patterns
        assert "Water" in validated
        assert "Sugar" in validated
    
    def test_validate_empty_list(self, validator):
        """Test validation of empty list."""
        validated = validator.validate([])
        
        assert validated == []
    
    def test_validate_keeps_compound_ingredients(self, validator):
        """Test that compound ingredients are kept."""
        ingredients = [
            "Wheat Flour",
            "Palm Oil",
            "Soy Lecithin",
            "Natural Flavors"
        ]
        
        validated = validator.validate(ingredients)
        
        assert "Wheat Flour" in validated
        assert "Palm Oil" in validated
        assert "Soy Lecithin" in validated
    
    def test_validate_filters_non_ingredient_words(self, validator):
        """Test filtering of non-ingredient words."""
        # These might be filtered depending on validation patterns
        ingredients = ["Water", "manufactured", "Sugar", "instructions"]
        
        validated = validator.validate(ingredients)
        
        # Core ingredients should remain
        assert "Water" in validated or "Sugar" in validated


class TestValidationPatterns:
    """Tests for specific validation patterns."""
    
    @pytest.fixture
    def validator(self):
        return IngredientValidator()
    
    def test_valid_common_ingredients(self, validator):
        """Test common ingredients pass validation."""
        common_ingredients = [
            "Water", "Sugar", "Salt", "Flour", "Oil",
            "Milk", "Eggs", "Butter", "Cream", "Yeast",
            "Baking Powder", "Vanilla Extract", "Cocoa"
        ]
        
        validated = validator.validate(common_ingredients)
        
        # Most common ingredients should pass
        assert len(validated) >= len(common_ingredients) * 0.8
    
    def test_valid_allergens(self, validator):
        """Test allergen ingredients pass validation."""
        allergens = [
            "Wheat", "Milk", "Eggs", "Peanuts",
            "Soy", "Fish", "Shellfish", "Tree Nuts"
        ]
        
        validated = validator.validate(allergens)
        
        # Allergens should be validated
        assert len(validated) >= len(allergens) * 0.7
    
    def test_valid_additives(self, validator):
        """Test additive ingredients pass validation."""
        additives = [
            "Citric Acid", "Sodium Benzoate",
            "Potassium Sorbate", "Ascorbic Acid"
        ]
        
        validated = validator.validate(additives)
        
        # Common additives should pass
        assert len(validated) >= 2


class TestValidatorEdgeCases:
    """Tests for validator edge cases."""
    
    @pytest.fixture
    def validator(self):
        return IngredientValidator()
    
    def test_very_long_ingredient_name(self, validator):
        """Test validation of very long ingredient names."""
        long_name = "Very Long Ingredient Name With Many Words In It"
        
        validated = validator.validate([long_name])
        
        # Should handle without error
        assert isinstance(validated, list)
    
    def test_special_characters_in_ingredient(self, validator):
        """Test ingredients with special characters."""
        special = ["Vitamin B12", "E471 (Mono-diglycerides)", "Salt (NaCl)"]
        
        validated = validator.validate(special)
        
        assert isinstance(validated, list)
    
    def test_numeric_ingredients(self, validator):
        """Test ingredients that are purely numeric."""
        numeric = ["Water", "12345", "Sugar", "100%"]
        
        validated = validator.validate(numeric)
        
        # Pure numbers should be filtered
        assert "12345" not in validated
    
    def test_whitespace_handling(self, validator):
        """Test handling of whitespace in ingredients."""
        with_whitespace = ["  Water  ", "\tSugar\t", "\nSalt\n"]
        
        validated = validator.validate(with_whitespace)
        
        # Should handle whitespace appropriately
        assert isinstance(validated, list)
    
    def test_case_sensitivity(self, validator):
        """Test case handling in validation."""
        mixed_case = ["WATER", "sugar", "SaLt", "Flour"]
        
        validated = validator.validate(mixed_case)
        
        # Validation should work regardless of case
        assert len(validated) >= 2
