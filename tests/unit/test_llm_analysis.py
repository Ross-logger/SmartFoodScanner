"""
Unit Tests for LLM-Based Dietary Analysis

Tests for the LLM-based dietary analysis functionality including:
- Analysis with mocked LLM responses
- Fallback to rule-based analysis
- Prompt building
- Response validation
"""

import pytest
from unittest.mock import patch, MagicMock

from backend.services.ingredients_analysis.llm_analysis import (
    analyze_with_llm,
    build_dietary_prompt,
    _validate_analysis_result,
)
from backend.services.ingredients_analysis.service import analyze_ingredients
from tests.utils.mock_llm import MockLLMService, MockLLMProvider


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


class TestBuildDietaryPrompt:
    """Tests for dietary analysis prompt building."""
    
    def test_build_prompt_with_halal(self):
        """Test prompt building with halal restriction."""
        profile = create_mock_dietary_profile(halal=True)
        ingredients = ["Water", "Sugar", "Salt"]
        
        prompt = build_dietary_prompt(ingredients, profile)
        
        assert "halal" in prompt.lower()
        assert "Water" in prompt
        assert "Sugar" in prompt
    
    def test_build_prompt_with_multiple_restrictions(self):
        """Test prompt building with multiple restrictions."""
        profile = create_mock_dietary_profile(
            halal=True,
            gluten_free=True,
            vegan=True
        )
        ingredients = ["Water", "Sugar", "Salt"]
        
        prompt = build_dietary_prompt(ingredients, profile)
        
        assert "halal" in prompt.lower()
        assert "gluten-free" in prompt.lower()
        assert "vegan" in prompt.lower()
    
    def test_build_prompt_with_allergens(self):
        """Test prompt building with custom allergens."""
        profile = create_mock_dietary_profile(allergens=["shellfish", "sesame"])
        ingredients = ["Water", "Sugar", "Salt"]
        
        prompt = build_dietary_prompt(ingredients, profile)
        
        assert "shellfish" in prompt.lower()
        assert "sesame" in prompt.lower()
    
    def test_build_prompt_with_custom_restrictions(self):
        """Test prompt building with custom restrictions."""
        profile = create_mock_dietary_profile(
            custom_restrictions=["no artificial colors"]
        )
        ingredients = ["Water", "Sugar", "Salt"]
        
        prompt = build_dietary_prompt(ingredients, profile)
        
        assert "no artificial colors" in prompt.lower()
    
    def test_build_prompt_no_restrictions(self):
        """Test prompt building with no restrictions."""
        profile = create_mock_dietary_profile()
        ingredients = ["Water", "Sugar", "Salt"]
        
        prompt = build_dietary_prompt(ingredients, profile)
        
        assert "no specific dietary restrictions" in prompt.lower()
    
    def test_build_prompt_json_format(self):
        """Test that prompt requests JSON format."""
        profile = create_mock_dietary_profile(halal=True)
        ingredients = ["Water", "Sugar", "Salt"]
        
        prompt = build_dietary_prompt(ingredients, profile)
        
        assert "json" in prompt.lower()
        assert "is_safe" in prompt
        assert "warnings" in prompt


class TestValidateAnalysisResult:
    """Tests for analysis result validation."""
    
    def test_validate_valid_result(self):
        """Test validation of valid result."""
        result = {
            "is_safe": True,
            "warnings": [],
            "analysis_result": "This product is safe."
        }
        
        validated = _validate_analysis_result(result)
        
        assert validated is not None
        assert validated["is_safe"] == True
        assert validated["warnings"] == []
    
    def test_validate_missing_is_safe(self):
        """Test validation with missing is_safe field."""
        result = {
            "warnings": [],
            "analysis_result": "This product is safe."
        }
        
        validated = _validate_analysis_result(result)
        
        assert validated is None
    
    def test_validate_missing_warnings(self):
        """Test validation with missing warnings field."""
        result = {
            "is_safe": True,
            "analysis_result": "This product is safe."
        }
        
        validated = _validate_analysis_result(result)
        
        assert validated is None
    
    def test_validate_missing_analysis_result(self):
        """Test validation with missing analysis_result field."""
        result = {
            "is_safe": True,
            "warnings": []
        }
        
        validated = _validate_analysis_result(result)
        
        assert validated is None
    
    def test_validate_converts_is_safe_to_bool(self):
        """Test that is_safe is converted to boolean."""
        result = {
            "is_safe": 1,  # Truthy value
            "warnings": [],
            "analysis_result": "Safe"
        }
        
        validated = _validate_analysis_result(result)
        
        assert validated is not None
        assert validated["is_safe"] == True
        assert isinstance(validated["is_safe"], bool)
    
    def test_validate_converts_warnings_to_list(self):
        """Test that non-list warnings are converted to empty list."""
        result = {
            "is_safe": True,
            "warnings": "not a list",
            "analysis_result": "Safe"
        }
        
        validated = _validate_analysis_result(result)
        
        assert validated is not None
        assert validated["warnings"] == []


class TestAnalyzeWithLLM:
    """Tests for LLM analysis function."""
    
    def test_analyze_with_mock_llm_safe(self):
        """Test analysis with mock LLM returning safe result."""
        profile = create_mock_dietary_profile(halal=True)
        ingredients = ["Water", "Sugar", "Salt"]
        
        with patch('backend.services.ingredients_analysis.llm_analysis.LLMService') as MockService:
            mock_instance = MagicMock()
            mock_instance.is_available = True
            mock_instance.call.return_value = {
                "is_safe": True,
                "warnings": [],
                "analysis_result": "This product is safe for halal diet.",
                "_provider": "MockLLM"
            }
            MockService.from_settings.return_value = mock_instance
            
            result = analyze_with_llm(ingredients, profile)
            
            assert result is not None
            assert result["is_safe"] == True
    
    def test_analyze_with_mock_llm_unsafe(self):
        """Test analysis with mock LLM returning unsafe result."""
        profile = create_mock_dietary_profile(halal=True)
        ingredients = ["Water", "Gelatin", "Sugar"]
        
        with patch('backend.services.ingredients_analysis.llm_analysis.LLMService') as MockService:
            mock_instance = MagicMock()
            mock_instance.is_available = True
            mock_instance.call.return_value = {
                "is_safe": False,
                "warnings": ["Contains gelatin which may not be halal"],
                "analysis_result": "This product may not be suitable for halal diet.",
                "_provider": "MockLLM"
            }
            MockService.from_settings.return_value = mock_instance
            
            result = analyze_with_llm(ingredients, profile)
            
            assert result is not None
            assert result["is_safe"] == False
            assert len(result["warnings"]) > 0
    
    def test_analyze_llm_unavailable(self):
        """Test analysis when LLM is unavailable."""
        profile = create_mock_dietary_profile(halal=True)
        ingredients = ["Water", "Sugar", "Salt"]
        
        with patch('backend.services.ingredients_analysis.llm_analysis.LLMService') as MockService:
            mock_instance = MagicMock()
            mock_instance.is_available = False
            MockService.from_settings.return_value = mock_instance
            
            result = analyze_with_llm(ingredients, profile)
            
            assert result is None
    
    def test_analyze_llm_returns_none(self):
        """Test analysis when LLM returns None."""
        profile = create_mock_dietary_profile(halal=True)
        ingredients = ["Water", "Sugar", "Salt"]
        
        with patch('backend.services.ingredients_analysis.llm_analysis.LLMService') as MockService:
            mock_instance = MagicMock()
            mock_instance.is_available = True
            mock_instance.call.return_value = None
            MockService.from_settings.return_value = mock_instance
            
            result = analyze_with_llm(ingredients, profile)
            
            assert result is None
    
    def test_analyze_llm_invalid_response(self):
        """Test analysis when LLM returns invalid response."""
        profile = create_mock_dietary_profile(halal=True)
        ingredients = ["Water", "Sugar", "Salt"]
        
        with patch('backend.services.ingredients_analysis.llm_analysis.LLMService') as MockService:
            mock_instance = MagicMock()
            mock_instance.is_available = True
            mock_instance.call.return_value = {
                "invalid": "response",
                "_provider": "MockLLM"
            }
            MockService.from_settings.return_value = mock_instance
            
            result = analyze_with_llm(ingredients, profile)
            
            assert result is None


class TestAnalyzeIngredientsService:
    """Tests for the main analyze_ingredients service function."""
    
    def test_analyze_no_profile(self):
        """Test analysis with no dietary profile."""
        ingredients = ["Water", "Sugar", "Salt"]
        
        result = analyze_ingredients(ingredients, None)
        
        assert result["is_safe"] == False
        assert "No dietary profile" in result["warnings"][0]
    
    def test_analyze_fallback_to_rules(self):
        """Test fallback to rule-based analysis when LLM fails."""
        profile = create_mock_dietary_profile(halal=True)
        ingredients = ["Water", "Pork", "Salt"]
        
        with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock_llm:
            mock_llm.return_value = None  # LLM fails
            
            result = analyze_ingredients(ingredients, profile)
            
            # Should fallback to rule-based and detect pork
            assert result["is_safe"] == False
    
    def test_analyze_uses_llm_when_available(self):
        """Test that LLM analysis is used when available."""
        profile = create_mock_dietary_profile(halal=True)
        ingredients = ["Water", "Sugar", "Salt"]
        
        with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock_llm:
            mock_llm.return_value = {
                "is_safe": True,
                "warnings": [],
                "analysis_result": "Safe for halal diet."
            }
            
            result = analyze_ingredients(ingredients, profile)
            
            assert result["is_safe"] == True
            mock_llm.assert_called_once()


class TestMockLLMProviderAnalysis:
    """Tests using the MockLLMProvider for analysis."""
    
    def test_mock_provider_halal_analysis(self):
        """Test mock provider with halal analysis."""
        provider = MockLLMProvider()
        
        prompt = "Analyze for halal diet: Pork, Water, Salt"
        result = provider.call(prompt, parse_json=True)
        
        # Mock should detect pork as halal concern
        assert result is not None
    
    def test_mock_provider_vegan_analysis(self):
        """Test mock provider with vegan analysis."""
        provider = MockLLMProvider()
        
        prompt = "Analyze for vegan diet: Milk, Eggs, Honey"
        result = provider.call(prompt, parse_json=True)
        
        assert result is not None
        # Mock should detect animal products
    
    def test_mock_provider_gluten_analysis(self):
        """Test mock provider with gluten analysis."""
        provider = MockLLMProvider()
        
        prompt = "Analyze for gluten-free diet: Wheat Flour, Sugar"
        result = provider.call(prompt, parse_json=True)
        
        assert result is not None


class TestAnalysisAccuracyMetrics:
    """Tests for analysis accuracy calculations."""
    
    def test_compliance_accuracy_calculation(self):
        """Test dietary compliance accuracy calculation."""
        from tests.utils.metrics import EvaluationMetrics
        
        metrics = EvaluationMetrics()
        
        # Add test cases
        metrics.add_compliance_result(
            "test_001",
            predicted_safe=False,
            actual_safe=False,
            predicted_warnings=["Contains pork"],
            expected_warnings=["Contains pork"]
        )
        metrics.add_compliance_result(
            "test_002",
            predicted_safe=True,
            actual_safe=True,
            predicted_warnings=[],
            expected_warnings=[]
        )
        
        summary = metrics.get_summary()
        
        assert summary["compliance"]["count"] == 2
        assert summary["compliance"]["accuracy"] == 1.0
    
    def test_compliance_accuracy_with_errors(self):
        """Test compliance accuracy with prediction errors."""
        from tests.utils.metrics import EvaluationMetrics
        
        metrics = EvaluationMetrics()
        
        # Add correct prediction
        metrics.add_compliance_result(
            "test_001",
            predicted_safe=True,
            actual_safe=True,
            predicted_warnings=[],
            expected_warnings=[]
        )
        # Add incorrect prediction
        metrics.add_compliance_result(
            "test_002",
            predicted_safe=True,  # Wrong!
            actual_safe=False,
            predicted_warnings=[],
            expected_warnings=["Contains gluten"]
        )
        
        summary = metrics.get_summary()
        
        assert summary["compliance"]["accuracy"] == 0.5
        assert summary["compliance"]["correct"] == 1
        assert summary["compliance"]["incorrect"] == 1


class TestEdgeCases:
    """Tests for edge cases in analysis."""
    
    def test_empty_ingredients_list(self):
        """Test analysis with empty ingredients list."""
        profile = create_mock_dietary_profile(halal=True)
        ingredients = []
        
        with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock_llm:
            mock_llm.return_value = None
            
            result = analyze_ingredients(ingredients, profile)
            
            # Empty ingredients should be safe
            assert result["is_safe"] == True
    
    def test_very_long_ingredients_list(self):
        """Test analysis with very long ingredients list."""
        profile = create_mock_dietary_profile(halal=True)
        ingredients = [f"Ingredient{i}" for i in range(100)]
        
        with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock_llm:
            mock_llm.return_value = None
            
            result = analyze_ingredients(ingredients, profile)
            
            # Should handle gracefully
            assert result is not None
    
    def test_special_characters_in_ingredients(self):
        """Test analysis with special characters."""
        profile = create_mock_dietary_profile(halal=True)
        ingredients = ["E471 (Mono-diglycerides)", "Vitamin B12", "Salt (NaCl)"]
        
        with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock_llm:
            mock_llm.return_value = None
            
            result = analyze_ingredients(ingredients, profile)
            
            assert result is not None
