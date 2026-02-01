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
    r'\bcontains?\s*[:]',
    r'\bingredients?\s*$',
    r'\binoredients?\s*[:]?',  # OCR error: "inoredients"
    r'\bingred\w*\s*[:]?',  # OCR errors: "ingred", "ingredents", etc.
]

# Patterns that indicate the END of ingredients section (stop extraction)
STOP_PATTERNS: List[str] = [
    r'\ballergen\s+warning',
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
]

# Patterns to remove from ingredients during validation
VALIDATION_GARBAGE_PATTERNS: List[str] = [
    r'^\d+$',
    r'^[a-z]\s*$',
    r'^[^\w\s]+$',
    r'\b(instructions?|warning|contains?|allergen|prepared|manufactured)\b',
    r'\b(address|contact|website|email|phone|store|keep|refrigerated)\b',
    r'\b(expir|best\s+before|net\s+weight|product\s+of|made\s+in)\b',
    r'\b(distributed\s+by|imported\s+from|country\s+of\s+origin)\b',
]



# =============================================================================
# COMPILED PATTERNS (for performance)
# =============================================================================

_compiled_start_patterns: Optional[List[re.Pattern]] = None
_compiled_stop_patterns: Optional[List[re.Pattern]] = None
_compiled_garbage_patterns: Optional[List[re.Pattern]] = None
_compiled_validation_patterns: Optional[List[re.Pattern]] = None


def _get_compiled_patterns(patterns: List[str], cache_attr: str) -> List[re.Pattern]:
    """Compile patterns lazily and cache them."""
    global _compiled_start_patterns, _compiled_stop_patterns
    global _compiled_garbage_patterns, _compiled_validation_patterns
    
    cache_map = {
        'start': '_compiled_start_patterns',
        'stop': '_compiled_stop_patterns', 
        'garbage': '_compiled_garbage_patterns',
        'validation': '_compiled_validation_patterns',
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
    
    Args:
        ingredients: List of potential ingredients
        
    Returns:
        Filtered list with only valid ingredients
    """
    filtered = []
    
    for ing in ingredients:
        ing = ing.strip()
        
        if is_valid_ingredient(ing):
            filtered.append(ing)
    
    return filtered
