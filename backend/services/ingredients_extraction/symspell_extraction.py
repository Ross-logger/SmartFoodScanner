"""
Lightweight Ingredient Spellcheck using SymSpell
Fast OCR error correction for food ingredient lists.

Uses symspellpy with a custom food ingredients dictionary for
domain-specific corrections. Prioritizes food terms over general English.
"""

import difflib
import logging
import re
from typing import AbstractSet, List, Optional

from symspellpy import SymSpell, Verbosity

from backend.services.ocr.easyocr_confidence import should_skip_symspell_for_segment
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
from backend.services.ingredients_extraction.utils import (
    post_process_ingredients,
    split_ingredients_text,
)


def _strip_leading_ingredients_label(text: str) -> str:
    """Remove a leading ``Ingredients`` heading (optional colon); case-insensitive."""
    if not text or not text.strip():
        return (text or "").strip()
    s = text.strip()
    s = re.sub(
        r"^\s*ingredients\b\s*[:：]?\s*",
        "",
        s,
        count=1,
        flags=re.IGNORECASE,
    )
    return s.strip()


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
        for term in VERY_COMMON_INGREDIENTS:
            _sym_spell.create_dictionary_entry(term.lower(), 10000000)
        for term in FOOD_INGREDIENTS:
            _sym_spell.create_dictionary_entry(term.lower(), 1000000)
        
        # Add E-numbers with their names
        for e_num, name in E_NUMBERS.items():
            _sym_spell.create_dictionary_entry(e_num, 1000000)
            _sym_spell.create_dictionary_entry(name, 1000000)
        
        _initialized = True
        logger.info(f"SymSpell initialized with {len(FOOD_INGREDIENTS)} food terms")
    
    return _sym_spell


def _is_false_yam_correction(original: str, candidate: str) -> bool:
    return candidate == "yam" and "yam" not in original.replace(" ", "")


def _is_false_tea_for_sea(original: str, candidate: str) -> bool:
    """SymSpell often maps ``sea`` → ``tea`` (e.g. ``sea salt`` → ``tea salt``)."""
    ol, cl = original.lower(), candidate.lower()
    if not re.search(r"\bsea\b", ol):
        return False
    if not re.search(r"\btea\b", cl):
        return False
    return not re.search(r"\bsea\b", cl)


def _reject_word_spell_suggestion(word: str, suggestion: str, segment_lower: str) -> bool:
    """
    Reject SymSpell word correction when it is a known false friend on labels.

    segment_lower is the full ingredient segment (lowercase) for context.
    """
    wl, sl = word.lower(), suggestion.lower()
    if sl in ("raisin", "raisins") and "agent" in segment_lower and wl not in ("raisin", "raisins"):
        if difflib.SequenceMatcher(None, wl, "raising").ratio() >= 0.72:
            return True
    if sl == "mace" and wl in ("made", "mada", "mad"):
        return True
    if sl == "tea" and wl == "sea":
        return True
    return False


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
        t = suggestions[0].term
        if t == "yam" and "yam" not in text_lower.replace(" ", ""):
            pass
        elif _is_false_tea_for_sea(text_lower, t):
            pass
        else:
            t = re.sub(r"\braisin\s+agents\b", "raising agents", t, flags=re.IGNORECASE)
            t = re.sub(r"\braisin\s+agent\b", "raising agent", t, flags=re.IGNORECASE)
            return t
    
    # Try word segmentation for compound terms
    segmented = sym_spell.word_segmentation(text_lower)
    if segmented and segmented.corrected_string:
        corrected = segmented.corrected_string
        corrected = re.sub(r"\braisin\s+agents\b", "raising agents", corrected, flags=re.IGNORECASE)
        corrected = re.sub(r"\braisin\s+agent\b", "raising agent", corrected, flags=re.IGNORECASE)
        input_len = len(text_lower.replace(" ", ""))
        
        # Only accept if error rate is <= 15% (1 edit per ~7 chars)
        # This prevents over-correction of short corrupted text
        error_rate = segmented.distance_sum / max(1, input_len)
        
        if error_rate <= 0.15:
            # Only use if it's a known food term or combination
            if corrected in FOOD_INGREDIENTS:
                if not (corrected == "yam" and "yam" not in text_lower.replace(" ", "")):
                    if not _is_false_tea_for_sea(text_lower, corrected):
                        return corrected
            # Check if each word is a food term
            words = corrected.split()
            if all(w in FOOD_INGREDIENTS or len(w) <= 2 for w in words):
                if not (corrected == "yam" and "yam" not in text_lower.replace(" ", "")):
                    if not _is_false_tea_for_sea(text_lower, corrected):
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
            sug = word_suggestions[0].term
            if _reject_word_spell_suggestion(word, sug, text_lower):
                corrected_words.append(word)
            else:
                corrected_words.append(sug)
        else:
            # Keep original if no good match
            corrected_words.append(word)
    
    result = " ".join(corrected_words)
    result = re.sub(r"\braisin\s+agents\b", "raising agents", result, flags=re.IGNORECASE)
    result = re.sub(r"\braisin\s+agent\b", "raising agent", result, flags=re.IGNORECASE)

    # Final check: if result is a known compound, use it
    if result in FOOD_INGREDIENTS:
        return result

    return result


# =============================================================================
# Public API
# =============================================================================

def spellcheck_ingredients(
    ocr_text: str,
    *,
    easyocr_skip_symspell_normalized: Optional[AbstractSet[str]] = None,
) -> str:
    """
    Correct OCR errors in ingredient list text.

    Args:
        ocr_text: Raw OCR text from food label
        easyocr_skip_symspell_normalized: Optional set of normalized segment
            strings (see ``build_easyocr_skip_symspell_normalized_keys``) for
            which SymSpell is skipped (EasyOCR confidence was high).

    Returns:
        Corrected ingredients as one comma-separated string (no leading
        ``Ingredients`` label).
    """
    if not ocr_text or not ocr_text.strip():
        return ""

    # Normalize EU-style separators to comma before splitting.
    ocr_text = ocr_text.replace("\u00b7", ",").replace("\u2022", ",")
    ocr_text = _strip_leading_ingredients_label(ocr_text)

    sym_spell = _get_spell_checker()

    # Split by delimiters: comma, semicolon, &, " and ", " or "
    ingredients = split_ingredients_text(ocr_text)

    corrected = []
    for ing in ingredients:
        ing = ing.strip()
        if ing:
            if should_skip_symspell_for_segment(ing, easyocr_skip_symspell_normalized):
                corrected_ing = ing.lower().strip()
            else:
                corrected_ing = _correct_text(ing, sym_spell)
            corrected.append(corrected_ing)

    joined = ", ".join(corrected).strip()
    return _strip_leading_ingredients_label(joined)


def extract_ingredient_segments(
    ocr_text: str,
    *,
    easyocr_skip_symspell_normalized: Optional[AbstractSet[str]] = None,
) -> List[str]:
    """
    Extract and correct each ingredient as its own string (splitting, SymSpell,
    filters). Use this for metrics, tests, or analysis that need per-item lists.

    For API responses that should be one comma-separated block without an
    ``Ingredients`` prefix, use ``extract_ingredients`` instead.

    Args:
        easyocr_skip_symspell_normalized: When set, segments whose normalized
            form appears here are not spell-corrected (high EasyOCR confidence).
    """
    if not ocr_text or not ocr_text.strip():
        return []

    # Normalize EU-style separators to comma before section extraction/splitting.
    ocr_text = ocr_text.replace("\u00b7", ",").replace("\u2022", ",")

    # Step 1: Extract only the ingredients section (regex-based section detection).
    ingredients_text = extract_ingredients_section(ocr_text)

    ingredients_text = _strip_leading_ingredients_label(ingredients_text)

    sym_spell = _get_spell_checker()

    # Step 2: Split by delimiters (comma, semicolon, &, " and ", " or ")
    ingredients = split_ingredients_text(ingredients_text)

    # Step 3: Pre-filter and spell-correct each segment
    # Check validity BEFORE spell correction to avoid false positives
    # (e.g., "Made in USA" -> "mace in usa" would bypass filter)
    corrected_list = []
    for ingredient in ingredients:
        ingredient = ingredient.strip()
        if ingredient and len(ingredient) > 1:
            # Check if original text is valid BEFORE spell correction
            if not is_valid_ingredient(ingredient):
                continue

            if should_skip_symspell_for_segment(
                ingredient, easyocr_skip_symspell_normalized
            ):
                corrected = ingredient.lower().strip()
            else:
                corrected = _correct_text(ingredient, sym_spell)
            if corrected:
                corrected_list.append(corrected)

    # Step 4: Final filter on corrected ingredients
    filtered = filter_ingredients(corrected_list)

    # Step 5: Shared post-processing (percentages, brackets, accents, etc.)
    filtered = post_process_ingredients(filtered)
    return filtered


def extract_ingredients(
    ocr_text: str,
    *,
    easyocr_skip_symspell_normalized: Optional[AbstractSet[str]] = None,
) -> List[str]:
    """
    Extract and correct the ingredients section from OCR text.

    Returns a list of **one** element: all ingredients joined with comma + space,
    with no leading ``Ingredients`` label. Uses regex section detection followed
    by SymSpell per-segment correction.

    Args:
        ocr_text: Raw OCR text from food label
        easyocr_skip_symspell_normalized: Optional normalized segment keys to
            skip SymSpell for (from EasyOCR line confidence ≥ threshold).

    Returns:
        ``[comma_separated_ingredients]`` or ``[]`` if nothing valid remains
    """
    segments = extract_ingredient_segments(
        ocr_text,
        easyocr_skip_symspell_normalized=easyocr_skip_symspell_normalized,
    )
    if not segments:
        return []
    joined = ", ".join(segments).strip()
    joined = _strip_leading_ingredients_label(joined)
    return [joined] if joined else []



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
