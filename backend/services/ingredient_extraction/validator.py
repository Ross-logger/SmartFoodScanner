"""
Ingredient Validator
Validates extracted ingredients using pattern matching.
"""

import re
from typing import List, Optional
from backend.services.ingredient_extraction.config import IngredientExtractionConfig


class IngredientValidator:
    """
    Validates ingredients using pattern matching.
    Note: OCR correction and misspelling handling is done by NLP extractor.
    """
    
    def __init__(self, config: Optional[IngredientExtractionConfig] = None):
        """
        Initialize validator.
        
        Args:
            config: Configuration object. Uses default if not provided.
        """
        self.config = config or IngredientExtractionConfig()
    
    def validate(self, ingredients: List[str]) -> List[str]:
        """
        Validate ingredients list.
        Filters out garbage and invalid entries.
        
        Args:
            ingredients: List of potential ingredients
            
        Returns:
            List of validated ingredients
        """
        if not ingredients:
            return []
        
        validated = []
        
        for ing in ingredients:
            if self._is_valid(ing):
                validated.append(ing)
        
        return validated
    
    def _is_valid(self, ingredient: str) -> bool:
        """
        Check if an ingredient is valid.
        
        Args:
            ingredient: Ingredient to validate
            
        Returns:
            True if valid, False otherwise
        """
        ing_lower = ingredient.lower()
        
        # Check validation garbage patterns
        if self._matches_any_pattern(ing_lower, self.config.VALIDATION_GARBAGE_PATTERNS):
            return False
        
        # Check if it matches ingredient patterns
        matches_pattern = self._matches_any_pattern(
            ing_lower,
            self.config.VALIDATION_PATTERNS
        )
        
        # Basic reasonableness check
        is_reasonable = (
            len(ingredient) >= self.config.MIN_INGREDIENT_LENGTH and
            re.search(r'[a-zA-Z]', ingredient) and
            len(ingredient.split()) <= self.config.MAX_INGREDIENT_WORDS
        )
        
        # If matches pattern or is reasonable, validate
        if matches_pattern or is_reasonable:
            return True
        
        return False
    
    def _matches_any_pattern(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any of the given patterns."""
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


