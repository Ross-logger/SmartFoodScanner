"""
Ingredient Normalizer
Normalizes and standardizes ingredient names based on research findings.
Uses common patterns and integrates with ingredient-slicer library.
"""

import re
from typing import List, Dict, Optional
from app.services.ingredient_extraction.config import IngredientExtractionConfig
from app.services.ingredient_extraction.slicer_integration import get_slicer_integration


class IngredientNormalizer:
    """
    Normalizes ingredient names to standard forms.
    Based on research: ingredient-slicer, Open Food Facts patterns.
    """
    
    def __init__(self, config: Optional[IngredientExtractionConfig] = None):
        """
        Initialize normalizer.
        
        Args:
            config: Configuration object. Uses default if not provided.
        """
        self.config = config or IngredientExtractionConfig()
        self.slicer = get_slicer_integration()
        self._init_normalization_rules()
    
    def _init_normalization_rules(self):
        """Initialize normalization rules based on common patterns."""
        # Common ingredient name variations (from research)
        self.variations = {
            # Oils
            'palm oleic': 'palm oil',
            'hydrogenated palm oleic': 'hydrogenated palm oil',
            'partially hydrogenated palm oleic': 'partially hydrogenated palm oil',
            
            # Common OCR errors
            'inoredients': '',
            'ingred': '',
            'ingredents': '',
            
            # Standardizations
            'msg': 'monosodium glutamate',
            'e501': '',  # Remove E-numbers as they're not ingredient names
            'e500': '',
            'e300': '',
        }
        
        # Common prefixes/suffixes to remove
        self.prefixes_to_remove = [
            r'^\d+\.?\s*',  # Number prefixes
            r'^[-•\*\s]+',  # Bullet points
        ]
        
        self.suffixes_to_remove = [
            r'[-•\*\s]+$',  # Trailing bullets
            r'\([^)]*\)$',  # Trailing parentheses (often percentages)
        ]
    
    def normalize(self, ingredient: str, use_slicer: bool = True) -> str:
        """
        Normalize a single ingredient name.
        Uses ingredient-slicer if available for better parsing.
        
        Args:
            ingredient: Raw ingredient name
            use_slicer: Whether to use ingredient-slicer (default: True)
            
        Returns:
            Normalized ingredient name
        """
        if not ingredient:
            return ''
        
        # Try ingredient-slicer first if available
        if use_slicer and self.slicer.available:
            food_name = self.slicer.extract_food_name(ingredient)
            if food_name:
                # Use extracted food name as base, then apply our normalization
                normalized = food_name
            else:
                # Fallback to manual normalization
                normalized = ingredient.lower().strip()
        else:
            normalized = ingredient.lower().strip()
        
        # Apply variations (OCR corrections, common mistakes)
        for variant, replacement in self.variations.items():
            normalized = normalized.replace(variant, replacement)
        
        # Remove prefixes
        for pattern in self.prefixes_to_remove:
            normalized = re.sub(pattern, '', normalized)
        
        # Remove suffixes
        for pattern in self.suffixes_to_remove:
            normalized = re.sub(pattern, '', normalized)
        
        # Normalize whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Remove E-numbers and codes (they're identifiers, not ingredients)
        normalized = re.sub(r'\be\d+\b', '', normalized)
        normalized = re.sub(r'\bd\d+\b', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def normalize_list(self, ingredients: List[str]) -> List[str]:
        """
        Normalize a list of ingredients.
        
        Args:
            ingredients: List of raw ingredient names
            
        Returns:
            List of normalized ingredient names
        """
        normalized = [self.normalize(ing) for ing in ingredients]
        # Remove empty strings
        normalized = [ing for ing in normalized if ing]
        return normalized


def try_ingredient_slicer(ingredient_text: str) -> Optional[Dict]:
    """
    Try to use ingredient-slicer library if available.
    This is optional - falls back gracefully if not installed.
    
    Args:
        ingredient_text: Raw ingredient text
        
    Returns:
        Parsed ingredient dict or None if library not available
    """
    try:
        import ingredient_slicer
        parsed = ingredient_slicer.IngredientSlicer(ingredient_text)
        return parsed.to_dict()
    except ImportError:
        return None
    except Exception:
        return None

