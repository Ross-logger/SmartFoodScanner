"""
Non-Ingredient Text Filter

This module provides rules and functions to filter out non-ingredient text
from OCR-scanned food labels. It handles:
- Detecting ingredient section boundaries (start/stop patterns)
- Removing garbage text (single characters, numbers only, etc.)
- Filtering out non-ingredient words (addresses, instructions, etc.)

Used by symspell_extraction.py to clean OCR text before ingredient extraction.
"""

import re
from typing import List, Tuple, Optional


# =============================================================================
# SECTION BOUNDARY PATTERNS
# =============================================================================

# Patterns that indicate the START of ingredients section
START_PATTERNS: List[str] = [
    r'\bingredients?\s*[:]',
    r'\bingredients?\s*$',
    r'\binoredients?\s*[:]?',  # OCR: "inoredients" (i→o)
    r'\bingred\w*\s*[:]?',  # OCR: "ingred", "ingredents", "ingredlents", etc.
    r'\bingredicnt\s*[:]?',  # OCR: "Ingredicnt"
    r'\bingnedienes?\s*[:]?',  # OCR: "Ingnedienes"
    r'\bingrodlonts?\s*[:]?',  # OCR: "Ingrodlonts"
    r'\bingrcdients?\s*[:]?',  # OCR: "Ingrcdients" (e→c)
    r'\bincredients?\s*[:]?',  # OCR: "INCREDIENTS" (extra C)
    r'\bingreoients?\s*[:]?',  # OCR: "ingreoients" (e/o swapped)
    r'\bingridients?\s*[:]?',  # OCR: "ingridients" (e→i)
    r'\bingr[03]dients?\s*[:]?',  # OCR: "ingr0dients", "ingr3dients" (digit for e)
    r'\bingrédients?\s*[:]?',  # French: "Ingrédients"
    r'\bingr[eo]d[il]ents?\s*[:]?',  # OCR: "ingredlents", "ingrodients"
]

# Patterns that indicate the END of ingredients section (stop extraction)
STOP_PATTERNS: List[str] = [
    r'\ballergen\s+warning',
    r'\ballergen\s+(?:information|info)',
    r'\bcontains?\s*[:].*\b(?:wheat|gluten|milk|egg|nut|soy|tree)\b',  # Allergen list
    r'\bcontains?\s+.*\ballergen',
    r'\binstructions?\s*[:]',
    r'\bprepared\s+in',
    r'\bmanufactured\s+in',
    r'\bpackaged\s+in',
    r'\baddress\s*[:]',
    r'\bcontact\s*[:]',
    r'\bwebsite\s*[:]',
    r'\bwww\.',
    r'\bhttp[s]?://',
    r'\bemail\s*[:]',
    r'\bphone\s*[:]',
    r'\bnet\s+weight',
    r'\bexpir',
    r'\bbest\s+before',
    r'\bstore\s+in',
    r'\bkeep\s+refrigerated',
    r'\bkeep\s+frozen',
    r'\bproduct\s+of',
    r'\bimported\s+from',
    r'\bdistributed\s+by',
    r'\bmade\s+in',
    r'\bcountry\s+of\s+origin',
    r'\bpremises',
    r'\bsunlight',
    r'\bopened',
    r'\bcontainer',
    r'\bcontains?\s+naturally\s+occurring',  # "Contains naturally occurring sugars"
]


# =============================================================================
# GARBAGE/INVALID TEXT PATTERNS
# =============================================================================

# Patterns that indicate garbage/non-ingredient text
GARBAGE_PATTERNS: List[str] = [
    r'^\d+$',  # Just numbers
    r'^[a-z]\s*$',  # Single letter
    r'^\s*$',  # Whitespace only
    r'^[^\w\s]+$',  # Only special characters
    r'^\d+\s*[gGmMlL]$',  # Weight/volume (e.g., "100g", "250ml")
    r'^\d+\s*%$',  # Percentage only
    r'^1[oO0]{2}\s*%\s*natural$',  # "1oo% natural", "100% natural"
    # Section headers as standalone segments (nothing meaningful after strip)
    r'^ingredicnt\s*[:.]?\s*$',
    r'^ingrcdients?\s*[:.]?\s*$',
    r'^ingreoients?\s*[:.]?\s*$',
    r'^ingrodlonts?\s*[:.]?\s*$',
    r'^ingnedienes?\s*[:.]?\s*$',
    r'^incredients?\s*[:.]?\s*$',
    r'^ingridients?\s*[:.]?\s*$',
    r'^inoredients?\s*[:.]?\s*$',
    r'^ingred\w*\s*[:.]?\s*$',  # ingredlents, ingredienes, etc. alone
    r'^ingr[03]dients?\s*[:.]?\s*$',
    r'^ngredients?\s*[:.]?\s*$',
    # Other garbage
    r'^1[oO0]{2}\s*%\s*$',  # "1oo%", "100%" alone
    r'^natural\s*$',  # "natural" alone (from "100% natural")
]

# Section headers to strip from start of segments (ingrodlonts:, ingnedienes, etc.)
SECTION_HEADER_PATTERNS: List[str] = [
    r'^ingredients?\s*[:.]?\s*',
    r'^ingred\w*\s*[:.]?\s*',  # Catches ingredlents, ingredienes, ingrediants, etc.
    r'^ingrodlonts?\s*[:.]?\s*',
    r'^ingnedienes?\s*[:.]?\s*',
    r'^ingnedienes\s+',  # "Ingnedienes " at start (no colon)
    r'^inoredients?\s*[:.]?\s*',
    r'^ingredicnt\s*[:.]?\s*',
    r'^ingrcdients?\s*[:.]?\s*',
    r'^incredients?\s*[:.]?\s*',
    r'^ingreoients?\s*[:.]?\s*',
    r'^ingridients?\s*[:.]?\s*',
    r'^ingr[03]dients?\s*[:.]?\s*',
    r'^ingrédients?\s*[:.]?\s*',
    r'^ingreoients\s*[:.]?\s*',  # "ingreoients:" (typo)
    r'^ochttps?://[^\s]+\s*',  # OCR garbage: "ochttps://..." merged with text
]

# Patterns to remove from ingredients during validation
VALIDATION_GARBAGE_PATTERNS: List[str] = [
    r'^\d+$',
    r'^[a-z]\s*$',
    r'^[^\w\s]+$',
    r'\b(instructions?|warning|prepared|manufactured)\b',
    r'\b(address|contact|website|email|phone|store|keep|refrigerated)\b',
    r'\b(expir|best\s+before|net\s+weight|product\s+of|made\s+in)\b',
    r'\b(distributed\s+by|imported\s+from|country\s+of\s+origin)\b',
]

# Patterns for allergen/warning segments to exclude from ingredients list.
# These are typically "Contains:", "May contain traces", "Produced on equipment", etc.
ALLERGEN_WARNING_PATTERNS: List[str] = [
    r'^contains?\s*[:.]?\s*$',  # "Contains:" or "Contains." alone
    r'\bthe\s+product\s+is\s+(being\s+)?produced\s+on\b',
    r'\bprocessed\s+(and\s+packaged\s+)?in\s+a\s+(facility|plant)\b',
    r'\bmade\s+on\s+equipment\s+that\b',
    r'\bproduced\s+on\s+(the\s+same\s+)?(equipment|premises)\b',
    r'\bpremises\s+where\b',
    r'\bmay\s+contain\s+traces?\s+of\b',
    r'\bfor\s+identification\s+of\s+manufacturing\b',
    r'\bfor\s+reference\s+only\b',
    r'\bsole\s+distributor\b',
    r'\bproduct\s+of\s+\.\s*$',  # "Product of." or similar
    r'\bstore\s+in\s+a\s+cool\b',
    r'\bkeep\s+away\s+from\s+heat\b',
    r'\bonce\s+(pack\s+)?is\s+opened\b',
    r'\bair\s+tight\s+container\b',
    r'\bbeans?\s+produced\b',  # OCR error for "being produced"
]



# =============================================================================
# COMPILED PATTERNS (for performance)
# =============================================================================

_compiled_start_patterns: Optional[List[re.Pattern]] = None
_compiled_stop_patterns: Optional[List[re.Pattern]] = None
_compiled_garbage_patterns: Optional[List[re.Pattern]] = None
_compiled_validation_patterns: Optional[List[re.Pattern]] = None
_compiled_allergen_patterns: Optional[List[re.Pattern]] = None


def _get_compiled_patterns(patterns: List[str], cache_attr: str) -> List[re.Pattern]:
    """Compile patterns lazily and cache them."""
    global _compiled_start_patterns, _compiled_stop_patterns
    global _compiled_garbage_patterns, _compiled_validation_patterns
    
    cache_map = {
        'start': '_compiled_start_patterns',
        'stop': '_compiled_stop_patterns',
        'garbage': '_compiled_garbage_patterns',
        'validation': '_compiled_validation_patterns',
        'allergen': '_compiled_allergen_patterns',
    }
    
    cache_var = cache_map.get(cache_attr)
    cached = globals().get(cache_var)
    
    if cached is None:
        compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
        globals()[cache_var] = compiled
        return compiled
    
    return cached


# =============================================================================
# FILTERING FUNCTIONS
# =============================================================================

def is_start_of_ingredients(text: str) -> bool:
    """
    Check if text indicates the start of an ingredients section.
    
    Args:
        text: Text to check
        
    Returns:
        True if text matches a start pattern
    """
    patterns = _get_compiled_patterns(START_PATTERNS, 'start')
    text_lower = text.lower().strip()
    
    return any(p.search(text_lower) for p in patterns)


def is_stop_pattern(text: str) -> bool:
    """
    Check if text indicates we should stop extracting ingredients.
    
    Args:
        text: Text to check
        
    Returns:
        True if text matches a stop pattern (non-ingredient section)
    """
    patterns = _get_compiled_patterns(STOP_PATTERNS, 'stop')
    text_lower = text.lower().strip()
    
    return any(p.search(text_lower) for p in patterns)


def strip_section_header(text: str) -> str:
    """Strip section header prefixes like 'ingrodlonts:', 'ingnedienes' from segment."""
    result = text.strip()
    for pattern in SECTION_HEADER_PATTERNS:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE).strip()
    return result


def is_garbage_text(text: str) -> bool:
    """
    Check if text is garbage (numbers only, single chars, etc.).
    
    Args:
        text: Text to check
        
    Returns:
        True if text matches a garbage pattern
    """
    patterns = _get_compiled_patterns(GARBAGE_PATTERNS, 'garbage')
    text_stripped = text.strip()
    
    return any(p.match(text_stripped) for p in patterns)



def is_allergen_warning_segment(text: str) -> bool:
    """
    Check if text is an allergen warning or non-ingredient message.
    These should be excluded from the main ingredients list.
    
    Args:
        text: Text to check (e.g., "the product is being produced on the same premises")
        
    Returns:
        True if text matches allergen/warning patterns
    """
    patterns = _get_compiled_patterns(ALLERGEN_WARNING_PATTERNS, 'allergen')
    text_lower = text.lower().strip()
    return any(p.search(text_lower) for p in patterns)


def is_valid_ingredient(text: str) -> bool:
    """
    Check if text is likely a valid ingredient.
    
    Args:
        text: Text to check
        
    Returns:
        True if text passes all validation checks
    """
    text = text.strip()
    
    # Must have minimum length
    if len(text) < 2:
        return False
    
    # Check against garbage patterns
    if is_garbage_text(text):
        return False
    
    # Check for stop patterns (addresses, instructions, etc.)
    if is_stop_pattern(text):
        return False
    
    # Exclude allergen warning segments
    if is_allergen_warning_segment(text):
        return False
    
    return True


def extract_ingredients_section(text: str) -> str:
    """
    Extract only the ingredients section from OCR text.
    
    Finds text between START_PATTERNS and STOP_PATTERNS.
    
    Args:
        text: Full OCR text from food label
        
    Returns:
        Text containing only the ingredients section
    """
    lines = text.split('\n')
    
    in_ingredients_section = False
    ingredients_lines = []
    
    for line in lines:
        line_stripped = line.strip()
        
        if not line_stripped:
            continue
        
        # Check for start of ingredients
        if is_start_of_ingredients(line_stripped):
            in_ingredients_section = True
            # Remove the "Ingredients:" prefix if present
            for pattern in START_PATTERNS:
                cleaned = re.sub(pattern, '', line_stripped, flags=re.IGNORECASE).strip()
                if cleaned != line_stripped:
                    line_stripped = cleaned
                    break
            if line_stripped:
                ingredients_lines.append(line_stripped)
            continue
        
        # Check for end of ingredients
        if in_ingredients_section and is_stop_pattern(line_stripped):
            break
        
        # Add line if we're in ingredients section
        if in_ingredients_section:
            ingredients_lines.append(line_stripped)
    
    # If no explicit section found, return original (might be just ingredients)
    if not ingredients_lines:
        return text
    
    return ' '.join(ingredients_lines)


def filter_ingredients(ingredients: List[str]) -> List[str]:
    """
    Filter a list of extracted ingredients to remove non-ingredients.
    Strips section headers and invalid segments.
    
    Args:
        ingredients: List of potential ingredients
        
    Returns:
        Filtered list with only valid ingredients
    """
    filtered = []
    
    for ing in ingredients:
        ing = ing.strip()
        # Strip section headers (ingrodlonts:, ingnedienes, etc.)
        ing = strip_section_header(ing)
        if not ing:
            continue
        
        if is_valid_ingredient(ing):
            filtered.append(ing)
    
    return filtered
