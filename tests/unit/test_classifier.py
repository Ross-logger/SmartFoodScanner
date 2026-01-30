"""
Unit Tests for Ingredient Section Classifier

Tests for the ML-based classifier that identifies ingredient text lines.
"""

import pytest
from unittest.mock import patch, MagicMock
import numpy as np

from backend.services.ingredients_extraction.classifier import IngredientSectionClassifier


class TestIngredientSectionClassifier:
    """Tests for the IngredientSectionClassifier."""
    
    @pytest.fixture
    def classifier(self):
        """Create a classifier instance."""
        return IngredientSectionClassifier()
    
    def test_classifier_initialization(self, classifier):
        """Test classifier initializes correctly."""
        assert classifier is not None
        assert classifier.config is not None
    
    def test_extract_features_basic(self, classifier):
        """Test basic feature extraction."""
        text = "Water, Sugar, Salt"
        features = classifier.extract_features(text)
        
        assert isinstance(features, np.ndarray)
        assert len(features) > 0
    
    def test_extract_features_with_context(self, classifier):
        """Test feature extraction with context."""
        text = "Ingredients: Water, Sugar, Salt"
        context = {"line_index": 0, "total_lines": 5}
        
        features = classifier.extract_features(text, context)
        
        assert isinstance(features, np.ndarray)
    
    def test_rule_based_classify_ingredient_line(self, classifier):
        """Test rule-based classification of ingredient line."""
        ingredient_lines = [
            "Water, Sugar, Salt, Flour",
            "E471, Soy Lecithin, Natural Flavors",
            "Wheat Flour, Milk Powder, Butter",
        ]
        
        for line in ingredient_lines:
            is_ingredient, confidence = classifier._rule_based_classify(line)
            # Ingredient lines should have higher confidence
            assert confidence > 0.3, f"Expected ingredient line: {line}"
    
    def test_rule_based_classify_non_ingredient_line(self, classifier):
        """Test rule-based classification of non-ingredient line."""
        non_ingredient_lines = [
            "Store in a cool, dry place",
            "Manufactured by: ABC Company",
            "Address: 123 Main Street",
            "Best before: 2025-12-31",
            "Website: www.example.com",
        ]
        
        for line in non_ingredient_lines:
            is_ingredient, confidence = classifier._rule_based_classify(line)
            assert is_ingredient == False, f"Should not be ingredient: {line}"
    
    def test_classify_line_empty(self, classifier):
        """Test classification of empty line."""
        is_ingredient, confidence = classifier.classify_line("")
        assert is_ingredient == False
        assert confidence == 0.0
    
    def test_classify_line_whitespace(self, classifier):
        """Test classification of whitespace-only line."""
        is_ingredient, confidence = classifier.classify_line("   \t\n  ")
        assert is_ingredient == False
        assert confidence == 0.0
    
    def test_classify_lines_multiple(self, classifier):
        """Test classification of multiple lines."""
        lines = [
            "Ingredients:",
            "Water, Sugar, Salt",
            "Store in a cool place",
            "Best before 2025",
        ]
        
        results = classifier.classify_lines(lines)
        
        assert len(results) == 4
        # Each result should be (text, is_ingredient, confidence) tuple
        for text, is_ingredient, confidence in results:
            assert isinstance(text, str)
            assert isinstance(is_ingredient, bool)
            assert isinstance(confidence, float)
            assert 0.0 <= confidence <= 1.0
    
    def test_feature_extraction_comma_count(self, classifier):
        """Test that comma count is captured in features."""
        text_with_commas = "Water, Sugar, Salt, Flour, Oil"
        text_without_commas = "Water Sugar Salt"
        
        features_with = classifier.extract_features(text_with_commas)
        features_without = classifier.extract_features(text_without_commas)
        
        # Features should be different
        assert not np.array_equal(features_with, features_without)
    
    def test_feature_extraction_ingredient_keywords(self, classifier):
        """Test detection of ingredient keywords."""
        text_with_keywords = "Flour, Sugar, Oil, Salt"
        text_without_keywords = "Random text here"
        
        features_with = classifier.extract_features(text_with_keywords)
        features_without = classifier.extract_features(text_without_keywords)
        
        # Features should differ in keyword-related dimensions
        assert not np.array_equal(features_with, features_without)
    
    def test_feature_extraction_e_numbers(self, classifier):
        """Test detection of E-numbers."""
        text_with_e_numbers = "E471, E322, E500"
        text_without = "Water, Sugar, Salt"
        
        features_with = classifier.extract_features(text_with_e_numbers)
        features_without = classifier.extract_features(text_without)
        
        assert not np.array_equal(features_with, features_without)


class TestClassifierThresholds:
    """Tests for classifier threshold behavior."""
    
    @pytest.fixture
    def classifier(self):
        return IngredientSectionClassifier()
    
    def test_high_threshold_strict(self, classifier):
        """Test with high threshold (strict classification)."""
        text = "Water, Sugar"
        
        # With high threshold, should be more conservative
        is_ingredient, confidence = classifier.classify_line(text, threshold=0.9)
        
        # Verify threshold behavior with floating point tolerance
        # Due to floating point precision, use approx comparison for the edge case
        import math
        expected_result = confidence >= 0.9 or math.isclose(confidence, 0.9, rel_tol=1e-9)
        assert is_ingredient == expected_result, \
            f"Threshold behavior inconsistent: confidence={confidence}, is_ingredient={is_ingredient}"
    
    def test_low_threshold_permissive(self, classifier):
        """Test with low threshold (permissive classification)."""
        text = "Water, Sugar, Salt"
        
        is_ingredient, confidence = classifier.classify_line(text, threshold=0.2)
        
        # With low threshold, more lines should pass
        if confidence >= 0.2:
            assert is_ingredient == True


class TestClassifierEdgeCases:
    """Tests for classifier edge cases."""
    
    @pytest.fixture
    def classifier(self):
        return IngredientSectionClassifier()
    
    def test_very_long_line(self, classifier):
        """Test with very long ingredient line."""
        long_line = ", ".join([f"Ingredient{i}" for i in range(100)])
        
        is_ingredient, confidence = classifier.classify_line(long_line)
        
        # Should handle without error
        assert isinstance(confidence, float)
    
    def test_special_characters(self, classifier):
        """Test with special characters."""
        special_text = "E471 (Mono-diglycerides), Vitamin C: 100%, Salt (NaCl)"
        
        is_ingredient, confidence = classifier.classify_line(special_text)
        
        assert isinstance(confidence, float)
    
    def test_unicode_characters(self, classifier):
        """Test with unicode characters."""
        unicode_text = "Café, Crème, Pâté"
        
        is_ingredient, confidence = classifier.classify_line(unicode_text)
        
        assert isinstance(confidence, float)
    
    def test_numeric_only(self, classifier):
        """Test with numeric-only line."""
        numeric_text = "12345 67890"
        
        is_ingredient, confidence = classifier.classify_line(numeric_text)
        
        # Numbers alone are probably not ingredients
        assert confidence < 0.8
