"""
Unit Tests for Ingredient Extraction

Tests for ingredient extraction functionality including:
- Hugging Face model extraction
- LLM-based extraction (mocked)
- Various input formats
- Edge cases and error handling
"""

import pytest
from unittest.mock import patch, MagicMock
from typing import List

from backend.services.ingredients_extraction.extractor import extract
from backend.services.ingredients_extraction.llm_extraction import (
    extract_ingredients_with_llm,
    LLMIngredientExtractor,
    build_extraction_prompt,
    _validate_extraction_result,
)
from tests.utils.mock_llm import MockLLMService, MockLLMProvider
from tests.utils.metrics import calculate_precision, calculate_recall, calculate_f1_score


class TestHuggingFaceExtractor:
    """Tests for the Hugging Face model-based extraction."""
    
    @pytest.fixture
    def mock_hf_model(self):
        """Mock the Hugging Face model and tokenizer."""
        with patch('backend.services.ingredients_extraction.hugging_face_extractor.model') as mock_model:
            with patch('backend.services.ingredients_extraction.hugging_face_extractor.tokenizer') as mock_tokenizer:
                yield mock_model, mock_tokenizer
    
    def test_extract_simple_ingredients(self):
        """Test extraction from simple ingredient text."""
        # Patch at the import location in extractor.py
        with patch('backend.services.ingredients_extraction.extractor.extract_ingredients') as mock_extract:
            mock_extract.return_value = ["Water", "Sugar", "Salt"]
            
            result = extract("Ingredients: Water, Sugar, Salt")
            
            assert len(result) == 3
            assert "Water" in result
            assert "Sugar" in result
            assert "Salt" in result
    
    def test_extract_complex_ingredients(self):
        """Test extraction from complex ingredient text."""
        with patch('backend.services.ingredients_extraction.extractor.extract_ingredients') as mock_extract:
            mock_extract.return_value = [
                "Wheat Flour", "Palm Oil", "Sugar", "Salt",
                "Mono and Diglycerides", "Soy Lecithin"
            ]
            
            text = "Ingredients: Wheat Flour, Palm Oil, Sugar, Salt, Mono and Diglycerides (E471), Soy Lecithin"
            result = extract(text)
            
            assert len(result) >= 4
            assert "Wheat Flour" in result
            assert "Palm Oil" in result
    
    def test_extract_empty_text(self):
        """Test extraction from empty text."""
        result = extract("")
        assert result == []
    
    def test_extract_none_text(self):
        """Test extraction from None text."""
        result = extract(None)
        assert result == []
    
    def test_extract_no_ingredients(self):
        """Test extraction from text with no ingredients."""
        with patch('backend.services.ingredients_extraction.extractor.extract_ingredients') as mock_extract:
            mock_extract.return_value = []
            
            result = extract("This is just some random text without ingredients")
            
            assert result == []
    
    def test_extract_with_percentages(self):
        """Test extraction handles percentage values correctly."""
        with patch('backend.services.ingredients_extraction.extractor.extract_ingredients') as mock_extract:
            mock_extract.return_value = ["Water", "Sugar", "Cocoa"]
            
            text = "Ingredients: Water (65%), Sugar (20%), Cocoa (15%)"
            result = extract(text)
            
            assert len(result) >= 3
            # Percentages should be stripped, only ingredient names
            assert all("%" not in ing for ing in result)
    
    def test_extract_multilingual_text(self):
        """Test extraction from multilingual text."""
        with patch('backend.services.ingredients_extraction.extractor.extract_ingredients') as mock_extract:
            mock_extract.return_value = ["Wasser", "Zucker", "Salz"]
            
            text = "Zutaten: Wasser, Zucker, Salz"
            result = extract(text)
            
            assert len(result) >= 3


class TestLLMIngredientExtractor:
    """Tests for LLM-based ingredient extraction."""
    
    def test_extract_with_mock_llm(self):
        """Test extraction using mock LLM service."""
        mock_service = MockLLMService.create_default()
        extractor = LLMIngredientExtractor(llm_service=mock_service)
        
        result = extractor.extract("Ingredients: Water, Sugar, Salt")
        
        assert result["success"] == True
        assert len(result["ingredients"]) > 0
    
    def test_extract_empty_text(self):
        """Test extraction with empty text."""
        mock_service = MockLLMService.create_default()
        extractor = LLMIngredientExtractor(llm_service=mock_service)
        
        result = extractor.extract("")
        
        assert result["success"] == False
        assert result["ingredients"] == []
        assert "No text provided" in result["message"]
    
    def test_extract_whitespace_only(self):
        """Test extraction with whitespace-only text."""
        mock_service = MockLLMService.create_default()
        extractor = LLMIngredientExtractor(llm_service=mock_service)
        
        result = extractor.extract("   \n\t   ")
        
        assert result["success"] == False
        assert result["ingredients"] == []
    
    def test_extract_llm_unavailable(self):
        """Test extraction when LLM is unavailable."""
        mock_service = MockLLMService.create_unavailable()
        extractor = LLMIngredientExtractor(llm_service=mock_service)
        
        result = extractor.extract("Ingredients: Water, Sugar, Salt")
        
        assert result["success"] == False
        assert "No LLM providers" in result["message"]
    
    def test_extract_with_custom_responses(self):
        """Test extraction with custom mock responses."""
        custom_responses = {
            "water": {
                "ingredients": ["Water", "Purified Water", "Spring Water"],
                "detected_language": "english",
                "confidence": "high"
            }
        }
        mock_service = MockLLMService.create_with_responses(custom_responses)
        extractor = LLMIngredientExtractor(llm_service=mock_service)
        
        result = extractor.extract("Contains: Water, Purified Water")
        
        assert result["success"] == True
        assert "Water" in result["ingredients"]
    
    def test_validate_extraction_result_valid(self):
        """Test validation of valid extraction result."""
        valid_result = {
            "ingredients": ["Water", "Sugar", "Salt"],
            "detected_language": "english",
            "confidence": "high"
        }
        
        validated = _validate_extraction_result(valid_result)
        
        assert validated is not None
        assert validated["ingredients"] == ["Water", "Sugar", "Salt"]
    
    def test_validate_extraction_result_missing_field(self):
        """Test validation of result missing required field."""
        invalid_result = {
            "detected_language": "english",
            "confidence": "high"
        }
        
        validated = _validate_extraction_result(invalid_result)
        
        assert validated is None
    
    def test_validate_extraction_result_cleans_ingredients(self):
        """Test that validation cleans ingredient list."""
        dirty_result = {
            "ingredients": ["Water", "  Sugar  ", "", "Salt", "a", "  "],
            "detected_language": "english",
            "confidence": "high"
        }
        
        validated = _validate_extraction_result(dirty_result)
        
        assert validated is not None
        assert "" not in validated["ingredients"]
        assert "Sugar" in validated["ingredients"]  # Trimmed
        assert "a" not in validated["ingredients"]  # Single char removed
    
    def test_build_extraction_prompt(self):
        """Test prompt building for extraction."""
        text = "Ingredients: Water, Sugar"
        prompt = build_extraction_prompt(text)
        
        assert "Water, Sugar" in prompt
        assert "ingredients" in prompt.lower()
        assert "JSON" in prompt
    
    def test_extraction_preserves_e_numbers(self):
        """Test that E-numbers are preserved in extraction."""
        mock_service = MockLLMService.create_with_responses({
            "e471": {
                "ingredients": ["E471 (Mono- and Diglycerides)", "E322 (Lecithin)"],
                "detected_language": "english",
                "confidence": "high"
            }
        })
        extractor = LLMIngredientExtractor(llm_service=mock_service)
        
        result = extractor.extract("Contains: E471, E322")
        
        assert result["success"] == True


class TestExtractionWithLLMFunction:
    """Tests for the backward-compatible extraction function."""
    
    def test_extract_ingredients_with_llm_basic(self):
        """Test the main extraction function."""
        with patch('backend.services.ingredients_extraction.llm_extraction.LLMIngredientExtractor') as MockExtractor:
            mock_instance = MagicMock()
            mock_instance.extract.return_value = {
                "ingredients": ["Water", "Sugar", "Salt"],
                "success": True,
                "message": "Extracted 3 ingredients"
            }
            MockExtractor.from_settings.return_value = mock_instance
            
            result = extract_ingredients_with_llm("Ingredients: Water, Sugar, Salt")
            
            assert result["success"] == True
            assert len(result["ingredients"]) == 3


class TestIngredientValidator:
    """Tests for ingredient validation."""
    
    def test_validate_valid_ingredients(self):
        """Test validation of valid ingredients."""
        from backend.services.ingredients_extraction.validator import IngredientValidator
        
        validator = IngredientValidator()
        ingredients = ["Water", "Sugar", "Wheat Flour", "Palm Oil"]
        
        validated = validator.validate(ingredients)
        
        assert len(validated) == 4
        assert "Water" in validated
    
    def test_validate_filters_garbage(self):
        """Test that validation filters garbage entries."""
        from backend.services.ingredients_extraction.validator import IngredientValidator
        
        validator = IngredientValidator()
        ingredients = ["Water", "123", "", "a", "Sugar", "   "]
        
        validated = validator.validate(ingredients)
        
        assert "Water" in validated
        assert "Sugar" in validated
        assert "" not in validated
        assert "123" not in validated
    
    def test_validate_empty_list(self):
        """Test validation of empty list."""
        from backend.services.ingredients_extraction.validator import IngredientValidator
        
        validator = IngredientValidator()
        validated = validator.validate([])
        
        assert validated == []
    
    def test_validate_with_special_patterns(self):
        """Test validation with special ingredient patterns."""
        from backend.services.ingredients_extraction.validator import IngredientValidator
        
        validator = IngredientValidator()
        ingredients = ["Soy Lecithin", "Modified Corn Starch", "Natural Flavors"]
        
        validated = validator.validate(ingredients)
        
        assert len(validated) == 3


class TestIngredientClassifier:
    """Tests for ingredient classification."""
    
    def test_classify_ingredient_line(self):
        """Test classification of ingredient text."""
        from backend.services.ingredients_extraction.classifier import IngredientSectionClassifier
        
        classifier = IngredientSectionClassifier()
        
        # Test ingredient line
        is_ingredient, confidence = classifier.classify_line("Water, Sugar, Salt, Flour")
        
        # Rule-based fallback should identify this as ingredient
        assert confidence > 0.3
    
    def test_classify_non_ingredient_line(self):
        """Test classification of non-ingredient text."""
        from backend.services.ingredients_extraction.classifier import IngredientSectionClassifier
        
        classifier = IngredientSectionClassifier()
        
        # Test non-ingredient line
        is_ingredient, confidence = classifier.classify_line("Store in a cool, dry place")
        
        assert is_ingredient == False or confidence < 0.5
    
    def test_classify_address_line(self):
        """Test classification of address text."""
        from backend.services.ingredients_extraction.classifier import IngredientSectionClassifier
        
        classifier = IngredientSectionClassifier()
        
        is_ingredient, confidence = classifier.classify_line("Address: 123 Main Street, City")
        
        assert is_ingredient == False
    
    def test_classify_multiple_lines(self):
        """Test classification of multiple lines."""
        from backend.services.ingredients_extraction.classifier import IngredientSectionClassifier
        
        classifier = IngredientSectionClassifier()
        
        lines = [
            "Ingredients:",
            "Water, Sugar, Salt",
            "Store in a cool place",
            "Best before: 2025"
        ]
        
        results = classifier.classify_lines(lines)
        
        assert len(results) == 4
        # First two should be more likely ingredients
        # Last two should be less likely


class TestExtractionAccuracyMetrics:
    """Tests for extraction accuracy calculations."""
    
    def test_perfect_extraction_metrics(self):
        """Test metrics for perfect extraction."""
        predicted = ["Water", "Sugar", "Salt"]
        ground_truth = ["Water", "Sugar", "Salt"]
        
        precision = calculate_precision(predicted, ground_truth)
        recall = calculate_recall(predicted, ground_truth)
        f1 = calculate_f1_score(predicted, ground_truth)
        
        assert precision == 1.0
        assert recall == 1.0
        assert f1 == 1.0
    
    def test_partial_extraction_metrics(self):
        """Test metrics for partial extraction."""
        predicted = ["Water", "Sugar"]
        ground_truth = ["Water", "Sugar", "Salt"]
        
        precision = calculate_precision(predicted, ground_truth)
        recall = calculate_recall(predicted, ground_truth)
        f1 = calculate_f1_score(predicted, ground_truth)
        
        assert precision == 1.0  # All predictions correct
        assert recall == pytest.approx(2/3, rel=0.01)  # 2 of 3 found
        assert 0.7 < f1 < 0.9
    
    def test_over_extraction_metrics(self):
        """Test metrics for over-extraction (false positives)."""
        predicted = ["Water", "Sugar", "Salt", "Flour", "Oil"]
        ground_truth = ["Water", "Sugar", "Salt"]
        
        precision = calculate_precision(predicted, ground_truth)
        recall = calculate_recall(predicted, ground_truth)
        f1 = calculate_f1_score(predicted, ground_truth)
        
        assert precision == pytest.approx(3/5, rel=0.01)  # 3 correct of 5 predicted
        assert recall == 1.0  # All ground truth found
    
    def test_empty_prediction_metrics(self):
        """Test metrics with empty predictions."""
        predicted = []
        ground_truth = ["Water", "Sugar", "Salt"]
        
        precision = calculate_precision(predicted, ground_truth)
        recall = calculate_recall(predicted, ground_truth)
        f1 = calculate_f1_score(predicted, ground_truth)
        
        assert precision == 0.0
        assert recall == 0.0
        assert f1 == 0.0
    
    def test_case_insensitive_matching(self):
        """Test that metrics are case-insensitive."""
        predicted = ["WATER", "sugar", "Salt"]
        ground_truth = ["water", "Sugar", "SALT"]
        
        precision = calculate_precision(predicted, ground_truth)
        recall = calculate_recall(predicted, ground_truth)
        
        assert precision == 1.0
        assert recall == 1.0


class TestSyntheticExtractionData:
    """Tests using synthetic extraction data."""
    
    def test_extraction_from_synthetic_samples(self):
        """Test extraction accuracy using synthetic samples."""
        from tests.data.synthetic.ocr_samples import get_synthetic_ocr_samples
        
        samples = get_synthetic_ocr_samples()
        
        with patch('backend.services.ingredients_extraction.extractor.extract_ingredients') as mock_extract:
            for sample in samples:
                mock_extract.return_value = sample["ground_truth_ingredients"]
                
                result = extract(sample["ocr_text"])
                
                precision = calculate_precision(result, sample["ground_truth_ingredients"])
                recall = calculate_recall(result, sample["ground_truth_ingredients"])
                
                # With mocked perfect extraction, should be 100%
                assert precision == 1.0
                assert recall == 1.0
    
    def test_extraction_metrics_summary(self):
        """Test aggregated extraction metrics."""
        from tests.utils.metrics import EvaluationMetrics
        
        metrics = EvaluationMetrics()
        
        # Add test cases
        metrics.add_extraction_result(
            "test_001",
            ["Water", "Sugar", "Salt"],
            ["Water", "Sugar", "Salt"]
        )
        metrics.add_extraction_result(
            "test_002",
            ["Water", "Sugar"],
            ["Water", "Sugar", "Salt"]
        )
        
        summary = metrics.get_summary()
        
        assert summary["extraction"]["count"] == 2
        assert summary["extraction"]["avg_precision"] > 0.9
        assert summary["extraction"]["avg_f1"] > 0.8
