"""
Food Ingredients Data Module
Contains dictionaries for ingredient spell-checking and E-number lookup.
"""

from backend.services.ingredients_extraction.data.common_ingredients import (
    FOOD_INGREDIENTS,
    E_NUMBERS,
    VERY_COMMON_INGREDIENTS,
)

__all__ = [
    'FOOD_INGREDIENTS',
    'E_NUMBERS',
    'VERY_COMMON_INGREDIENTS',
]
