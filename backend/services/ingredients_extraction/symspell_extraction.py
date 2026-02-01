"""
Lightweight Ingredient Spellcheck using SymSpell
Fast OCR error correction for food ingredient lists.

Uses symspellpy with a custom food ingredients dictionary for
domain-specific corrections. Prioritizes food terms over general English.
"""

import logging
import re
from typing import List, Optional

from symspellpy import SymSpell, Verbosity

from backend.services.ingredients_extraction.data import (
    FOOD_INGREDIENTS,
    E_NUMBERS,
    VERY_COMMON_INGREDIENTS,
)
from backend.services.ingredients_extraction.non_ingredient_filter import (
    extract_ingredients_section,
    filter_ingredients,
    is_valid_ingredient,
)

logger = logging.getLogger(__name__)

# =============================================================================
# SymSpell Spell Checker (Food-specific only)
# =============================================================================

_sym_spell: Optional[SymSpell] = None
_initialized: bool = False


def _get_spell_checker() -> SymSpell:
    """Get or initialize the SymSpell spell checker with ONLY food terms."""
    global _sym_spell, _initialized
    
    if not _initialized:
        logger.info("Initializing SymSpell with food ingredients dictionary...")
        _sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
        
        # Load food ingredients with frequency based on commonality
        for term in FOOD_INGREDIENTS:
            # Check if any word in the term is very common
            words = term.lower().split()
            if any(w in VERY_COMMON_INGREDIENTS for w in words) or term.lower() in VERY_COMMON_INGREDIENTS:
                freq = 10000000  # Very high for common terms
            else:
                freq = 1000000
            _sym_spell.create_dictionary_entry(term.lower(), freq)
        
        # Add E-numbers with their names
        for e_num, name in E_NUMBERS.items():
            _sym_spell.create_dictionary_entry(e_num, 1000000)
            _sym_spell.create_dictionary_entry(name, 1000000)
        
        _initialized = True
        logger.info(f"SymSpell initialized with {len(FOOD_INGREDIENTS)} food terms")
    
    return _sym_spell


def _correct_text(text: str, sym_spell: SymSpell) -> str:
    """
    Correct text using food-specific dictionary.
    Uses segmentation to handle compound words.
    """
    text_lower = text.lower().strip()
    
    if not text_lower or len(text_lower) < 2:
        return text_lower
    
    # Check if it's an E-number pattern (e.g., "E471", "e 322", "E150a")
    e_match = re.match(r'^e\s*(\d{3}[a-z]?)$', text_lower, re.IGNORECASE)
    if e_match:
        return f"e{e_match.group(1)}"
    
    # First, check if the whole phrase matches directly
    if text_lower in FOOD_INGREDIENTS:
        return text_lower
    
    # Try lookup for the whole phrase
    suggestions = sym_spell.lookup(
        text_lower,
        Verbosity.CLOSEST,
        max_edit_distance=2
    )
    
    if suggestions and suggestions[0].distance <= 2:
        return suggestions[0].term
    
    # Try word segmentation for compound terms
    segmented = sym_spell.word_segmentation(text_lower)
    if segmented and segmented.corrected_string:
        corrected = segmented.corrected_string
        input_len = len(text_lower.replace(" ", ""))
        
        # Only accept if error rate is <= 15% (1 edit per ~7 chars)
        # This prevents over-correction of short corrupted text
        error_rate = segmented.distance_sum / max(1, input_len)
        
        if error_rate <= 0.15:
            # Only use if it's a known food term or combination
            if corrected in FOOD_INGREDIENTS:
                return corrected
            # Check if each word is a food term
            words = corrected.split()
            if all(w in FOOD_INGREDIENTS or len(w) <= 2 for w in words):
                return corrected
    
    # Fall back to word-by-word correction
    words = text_lower.split()
    corrected_words = []
    for word in words:
        # Skip very short words
        if len(word) <= 2:
            corrected_words.append(word)
            continue
        
        # For short words (3-4 chars), only accept very close matches (distance 1)
        # For longer words, allow distance up to 2
        max_dist = 1 if len(word) <= 4 else 2
        
        word_suggestions = sym_spell.lookup(
            word,
            Verbosity.CLOSEST,
            max_edit_distance=max_dist
        )
        if word_suggestions and word_suggestions[0].distance <= max_dist:
            corrected_words.append(word_suggestions[0].term)
        else:
            # Keep original if no good match
            corrected_words.append(word)
    
    result = " ".join(corrected_words)
    
    # Final check: if result is a known compound, use it
    if result in FOOD_INGREDIENTS:
        return result
    
    return result


# =============================================================================
# Public API
# =============================================================================

def spellcheck_ingredients(ocr_text: str) -> str:
    """
    Correct OCR errors in ingredient list text.
    
    Args:
        ocr_text: Raw OCR text from food label
        
    Returns:
        Corrected ingredient list text
    """
    if not ocr_text or not ocr_text.strip():
        return ""
    
    sym_spell = _get_spell_checker()
    
    # Split by common delimiters
    ingredients = re.split(r'[,;]', ocr_text)
    
    corrected = []
    for ing in ingredients:
        ing = ing.strip()
        if ing:
            corrected_ing = _correct_text(ing, sym_spell)
            corrected.append(corrected_ing)
    
    return ", ".join(corrected)


def extract_ingredients(ocr_text: str) -> List[str]:
    """
    Extract and correct ingredients from OCR text.
    
    Filters out non-ingredient text (addresses, instructions, etc.) and
    extracts only the ingredients section when possible.
    
    Args:
        ocr_text: Raw OCR text from food label
        
    Returns:
        List of corrected ingredient names (non-ingredients filtered out)
    """
    if not ocr_text or not ocr_text.strip():
        return []
    
    # Step 1: Extract only the ingredients section (filter headers, footers, etc.)
    ingredients_text = extract_ingredients_section(ocr_text)
    
    sym_spell = _get_spell_checker()
    
    # Step 2: Split by common delimiters
    ingredients = re.split(r'[,;]', ingredients_text)
    
    # Step 3: Pre-filter and spell-correct each segment
    # Check validity BEFORE spell correction to avoid false positives
    # (e.g., "Made in USA" -> "mace in usa" would bypass filter)
    corrected_list = []
    for ing in ingredients:
        ing = ing.strip()
        if ing and len(ing) > 1:
            # Check if original text is valid BEFORE spell correction
            if not is_valid_ingredient(ing):
                continue
            
            corrected = _correct_text(ing, sym_spell)
            if corrected:
                corrected_list.append(corrected)
    
    # Step 4: Final filter on corrected ingredients
    filtered = filter_ingredients(corrected_list)
    
    return filtered


def get_e_number_name(e_number: str) -> Optional[str]:
    """
    Get the name of an E-number additive.
    
    Args:
        e_number: E-number code (e.g., "E471", "e322")
        
    Returns:
        Name of the additive, or None if not found
    """
    e_lower = e_number.lower().replace(" ", "")
    return E_NUMBERS.get(e_lower)
