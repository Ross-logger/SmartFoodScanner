"""
Mock LLM Service for Testing

Provides mock implementations of LLM services to avoid
making real API calls during unit tests.
"""

from typing import List, Dict, Any, Optional
import json


class MockLLMProvider:
    """
    Mock LLM provider for testing.
    Returns predefined responses based on input patterns.
    """
    
    def __init__(self, responses: Optional[Dict[str, Any]] = None):
        """
        Initialize mock provider with optional custom responses.
        
        Args:
            responses: Dictionary mapping input patterns to responses
        """
        self.responses = responses or {}
        self.call_count = 0
        self.last_prompt = None
        self.last_system_prompt = None
        self._available = True
    
    @property
    def name(self) -> str:
        return "MockLLM"
    
    def is_available(self) -> bool:
        return self._available
    
    def set_available(self, available: bool):
        """Set whether the mock provider is available."""
        self._available = available
    
    def call(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        parse_json: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Mock LLM call that returns predefined responses.
        """
        self.call_count += 1
        self.last_prompt = prompt
        self.last_system_prompt = system_prompt
        
        if not self._available:
            return None
        
        # Check for custom responses
        for pattern, response in self.responses.items():
            if pattern.lower() in prompt.lower():
                if parse_json and isinstance(response, str):
                    return json.loads(response)
                return response
        
        # Default response based on prompt type
        if "extract" in prompt.lower() and "ingredient" in prompt.lower():
            return self._mock_extraction_response(prompt)
        elif "analyze" in prompt.lower() or "dietary" in prompt.lower():
            return self._mock_analysis_response(prompt)
        
        return {"response": "Mock response", "_provider": "MockLLM"}
    
    def _mock_extraction_response(self, prompt: str) -> Dict[str, Any]:
        """Generate mock extraction response."""
        # Extract ingredients from common patterns in the prompt
        ingredients = []
        
        # Look for common ingredient keywords
        common_ingredients = [
            "water", "sugar", "salt", "flour", "oil", "milk", "eggs",
            "wheat", "corn", "soy", "peanut", "butter", "cream"
        ]
        
        prompt_lower = prompt.lower()
        for ing in common_ingredients:
            if ing in prompt_lower:
                ingredients.append(ing.capitalize())
        
        if not ingredients:
            ingredients = ["Water", "Sugar", "Salt"]
        
        return {
            "ingredients": ingredients,
            "detected_language": "english",
            "confidence": "high",
            "_provider": "MockLLM"
        }
    
    def _mock_analysis_response(self, prompt: str) -> Dict[str, Any]:
        """Generate mock analysis response."""
        prompt_lower = prompt.lower()
        
        # Check for concerning ingredients
        warnings = []
        is_safe = True
        
        concerning_patterns = {
            "pork": "Contains pork - not halal/kosher",
            "gelatin": "Contains gelatin - may not be halal/vegetarian",
            "wheat": "Contains wheat/gluten",
            "milk": "Contains dairy",
            "eggs": "Contains eggs",
            "peanut": "Contains peanuts",
            "nut": "Contains nuts",
            "beef": "Contains beef - not vegetarian",
            "chicken": "Contains chicken - not vegetarian",
            "fish": "Contains fish",
            "honey": "Contains honey - not vegan",
        }
        
        for pattern, warning in concerning_patterns.items():
            if pattern in prompt_lower:
                if "halal" in prompt_lower and pattern in ["pork", "gelatin"]:
                    warnings.append(warning)
                    is_safe = False
                elif "vegan" in prompt_lower and pattern in ["milk", "eggs", "honey", "butter"]:
                    warnings.append(warning)
                    is_safe = False
                elif "vegetarian" in prompt_lower and pattern in ["beef", "chicken", "pork", "fish"]:
                    warnings.append(warning)
                    is_safe = False
                elif "gluten" in prompt_lower and pattern == "wheat":
                    warnings.append(warning)
                    is_safe = False
                elif "dairy" in prompt_lower and pattern in ["milk", "cream", "butter"]:
                    warnings.append(warning)
                    is_safe = False
                elif "nut" in prompt_lower and pattern in ["peanut", "nut"]:
                    warnings.append(warning)
                    is_safe = False
        
        analysis_result = "This product is safe for your dietary preferences." if is_safe else \
            f"Warning: This product may not be suitable. {'; '.join(warnings)}"
        
        return {
            "is_safe": is_safe,
            "warnings": warnings,
            "analysis_result": analysis_result,
            "_provider": "MockLLM"
        }


class MockLLMService:
    """
    Mock LLM service that wraps MockLLMProvider.
    Compatible with the real LLMService interface.
    """
    
    def __init__(self, providers: Optional[List[MockLLMProvider]] = None):
        """
        Initialize mock service.
        
        Args:
            providers: List of mock providers
        """
        self._providers = providers or [MockLLMProvider()]
    
    @classmethod
    def create_default(cls) -> "MockLLMService":
        """Create a default mock service with standard responses."""
        return cls([MockLLMProvider()])
    
    @classmethod
    def create_with_responses(cls, responses: Dict[str, Any]) -> "MockLLMService":
        """Create a mock service with custom responses."""
        return cls([MockLLMProvider(responses)])
    
    @classmethod
    def create_unavailable(cls) -> "MockLLMService":
        """Create a mock service that simulates unavailable LLM."""
        provider = MockLLMProvider()
        provider.set_available(False)
        return cls([provider])
    
    def call(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        parse_json: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Call the mock LLM service.
        """
        for provider in self._providers:
            if provider.is_available():
                result = provider.call(prompt, system_prompt, parse_json)
                if result is not None:
                    return result
        return None
    
    @property
    def is_available(self) -> bool:
        """Check if any mock provider is available."""
        return any(p.is_available() for p in self._providers)
    
    def get_call_count(self) -> int:
        """Get total call count across all providers."""
        return sum(p.call_count for p in self._providers)
    
    def reset(self):
        """Reset call counts and state."""
        for provider in self._providers:
            provider.call_count = 0
            provider.last_prompt = None
            provider.last_system_prompt = None


# Pre-configured mock responses for common test scenarios
MOCK_EXTRACTION_RESPONSES = {
    "simple_ingredients": {
        "ingredients": ["Water", "Sugar", "Salt"],
        "detected_language": "english",
        "confidence": "high"
    },
    "complex_ingredients": {
        "ingredients": [
            "Water", "Sugar", "Wheat Flour", "Palm Oil", "Salt",
            "Mono and Diglycerides", "Natural Flavors"
        ],
        "detected_language": "english",
        "confidence": "high"
    },
    "multilingual": {
        "ingredients": ["Water", "Sugar", "Wheat Flour"],
        "detected_language": "german",
        "confidence": "medium"
    },
}

MOCK_ANALYSIS_RESPONSES = {
    "safe": {
        "is_safe": True,
        "warnings": [],
        "analysis_result": "This product is safe for your dietary preferences."
    },
    "unsafe_halal": {
        "is_safe": False,
        "warnings": ["Contains pork-derived gelatin", "Not suitable for halal diet"],
        "analysis_result": "Warning: This product contains pork-derived ingredients."
    },
    "unsafe_vegan": {
        "is_safe": False,
        "warnings": ["Contains milk", "Contains eggs"],
        "analysis_result": "Warning: This product contains animal-derived ingredients."
    },
    "unsafe_gluten": {
        "is_safe": False,
        "warnings": ["Contains wheat gluten"],
        "analysis_result": "Warning: This product contains gluten."
    },
}
