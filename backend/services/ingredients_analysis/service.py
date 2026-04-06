"""
Ingredients Analysis Service
Main entry point for dietary analysis.
"""

from typing import List, Optional
import logging

from backend.models import DietaryProfile
from backend.services.ingredients_analysis.llm_analysis import analyze_with_llm
from backend.services.ingredients_analysis.rule_based import analyze_with_rules

logger = logging.getLogger(__name__)



def analyze_ingredients(
    ingredients: List[str],
    dietary_profile: Optional[DietaryProfile]
) -> dict:
    """
    Analyze ingredients against dietary restrictions.
    Uses LLM-based analysis if available, falls back to rule-based analysis.

    Args:
        ingredients: List of ingredient names (may contain comma-joined blobs)
        dietary_profile: User's dietary profile with restrictions

    Returns:
        Dictionary with:
        - is_safe: Boolean indicating if product is safe
        - warnings: List of warning messages
        - analysis_result: Human-readable analysis summary
    """
    if not dietary_profile:
        return {
            "is_safe": False,
            "warnings": ["No dietary profile set"],
            "analysis_result": "Please set your dietary profile to get the analysis."
        }

    # Try LLM analysis first
    llm_result = analyze_with_llm(ingredients, dietary_profile)
    if llm_result:
        return llm_result

    # Fall back to rule-based if LLM fails
    logger.info("LLM unavailable — falling back to rule-based analysis")
    return analyze_with_rules(ingredients, dietary_profile)
