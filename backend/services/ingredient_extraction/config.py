from pathlib import Path
from typing import List, Dict
import json


class IngredientExtractionConfig:
    """Configuration class for ingredient extraction patterns."""
    
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
        r'\bcontains?\s+.*\bwhey',
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
        r'\bchaleur',  # French: heat
        r'\blumiere',  # French: light
        r'\bemballe',  # French: packaged
        r'\bavertissement',  # French: warning
        r'\bconcernant',  # French: concerning
        r'\bfabrique',  # French: manufactured
    ]
    
    # Common ingredient keywords (used for fallback detection)
    INGREDIENT_KEYWORDS: List[str] = [
        'flour', 'sugar', 'salt', 'oil', 'powder', 'extract', 'flavor',
        'lecithin', 'starch', 'gum', 'acid', 'preservative', 'color'
    ]
    
    # Common multi-word ingredient patterns (keep together)
    COMPOUND_PATTERNS: List[str] = [
        r'\b(wheat|rice|corn|potato|tapioca|almond|coconut|oat)\s+flour\b',
        r'\b(baking)\s+powder\b',
        r'\b(whole|skim|nonfat)\s+milk\b',
        r'\b(palm|coconut|sunflower|canola|soybean|vegetable|olive|corn|peanut|sesame)\s+oil\b',
        r'\b(soy|sunflower)\s+lecithin\b',
        r'\b(cocoa|chocolate)\s+powder\b',
        r'\b(cardamom|cinnamon|nutmeg|ginger)\s+powder\b',
        r'\b(high\s+fructose)\s+corn\s+syrup\b',
        r'\b(monosodium|disodium)\s+glutamate\b',
        r'\b(hydrogenated|partially\s+hydrogenated)\s+\w+\s+oil\b',
    ]
    
    # Standalone ingredient words (typically single-word ingredients)
    STANDALONE_WORDS: List[str] = [
        'sugar', 'salt', 'walnut', 'almond', 'cashew', 'peanut'
    ]
    
    # Ingredient separators
    SEPARATORS: List[str] = [
        ',', ';', r'\s+and\s+', r'\s+&\s+', r'\.\s+(?=[A-Z])'
    ]
    
    # Patterns that indicate garbage/non-ingredient text
    GARBAGE_PATTERNS: List[str] = [
        r'^\d+$',  # Just numbers
        r'^[a-z]\s*$',  # Single letter
        r'\b(d2|d\d+|e\d+)\b',  # OCR artifacts like "d2", "e501"
        r'^\s*$',  # Whitespace only
        r'^[^\w\s]+$',  # Only special characters
    ]
    
    # Non-ingredient words (filter these out)
    NON_INGREDIENT_WORDS: List[str] = [
        'warning', 'contains', 'allergen', 'instructions', 'prepared',
        'manufactured', 'address', 'contact', 'website', 'email', 'phone',
        'store', 'keep', 'refrigerated', 'frozen', 'expir', 'best before',
        'net weight', 'product of', 'imported', 'distributed', 'made in',
        'country', 'origin', 'premises', 'sunlight', 'opened', 'container',
        'light', 'chaleur', 'lumiere', 'emballe', 'avertissement',
        'concernant', 'contient', 'produit', 'fabrique', 'meal', 'paste'
    ]
    
    # Ingredient validation patterns (to keep)
    VALIDATION_PATTERNS: List[str] = [
        r'\b(flour|sugar|salt|oil|powder|extract|flavor|lecithin|starch|gum|acid)\b',
        r'\b(milk|cream|butter|cheese|yogurt|whey|casein)\b',
        r'\b(egg|albumin|yolk|white)\b',
        r'\b(wheat|barley|rye|oats|corn|rice|soy|bean)\b',
        r'\b(nut|almond|walnut|peanut|cashew|hazelnut)\b',
        r'\b(vitamin|mineral|calcium|sodium|potassium)\b',
        r'\b(preservative|antioxidant|emulsifier|thickener|stabilizer)\b',
        r'\b(cocoa|chocolate|vanilla|cinnamon|spice)\b',
        r'\b(water|juice|syrup|honey|molasses)\b',
    ]
    
    # Validation garbage patterns (to remove)
    VALIDATION_GARBAGE_PATTERNS: List[str] = [
        r'^\d+$',
        r'^[a-z]\s*$',
        r'\b(d2|d\d+|e501)\b',
        r'^[^\w\s]+$',
        r'\b(red|blue|green|yellow|black|white)\s+(d2|d\d+|e\d+)\b',
        r'\b(instructions?|warning|contains?|allergen|prepared|manufactured)\b',
        r'\b(address|contact|website|email|phone|store|keep|refrigerated)\b',
        r'\b(expir|best\s+before|net\s+weight|product\s+of|made\s+in)\b',
    ]
    
    # Extraction settings
    MIN_INGREDIENT_LENGTH: int = 2
    MAX_INGREDIENT_WORDS: int = 5
    MAX_INGREDIENTS: int = 50
    MAX_INITIAL_SEARCH_LINES: int = 20
    MAX_FALLBACK_LINES: int = 10
    LONG_PART_THRESHOLD: int = 5  # Words
    
    # OCR artifact patterns to clean
    OCR_ARTIFACT_PATTERNS: Dict[str, str] = {
        r'\b(inoredients|ingred|ingredents)\b': '',
    }
    
    @classmethod
    def load_from_json(cls, config_path: Path) -> 'IngredientExtractionConfig':
        """Load configuration from JSON file (for future extensibility)."""
        if config_path.exists():
            with open(config_path, 'r') as f:
                config_data = json.load(f)
                # Create new instance and update attributes
                instance = cls()
                for key, value in config_data.items():
                    if hasattr(instance, key.upper()):
                        setattr(instance, key.upper(), value)
                return instance
        return cls()
    
    @classmethod
    def save_to_json(cls, config_path: Path):
        """Save current configuration to JSON file."""
        config_data = {
            'start_patterns': cls.START_PATTERNS,
            'stop_patterns': cls.STOP_PATTERNS,
            'ingredient_keywords': cls.INGREDIENT_KEYWORDS,
            'compound_patterns': cls.COMPOUND_PATTERNS,
            'standalone_words': cls.STANDALONE_WORDS,
            'separators': cls.SEPARATORS,
            'garbage_patterns': cls.GARBAGE_PATTERNS,
            'non_ingredient_words': cls.NON_INGREDIENT_WORDS,
            'validation_patterns': cls.VALIDATION_PATTERNS,
            'validation_garbage_patterns': cls.VALIDATION_GARBAGE_PATTERNS,
            'min_ingredient_length': cls.MIN_INGREDIENT_LENGTH,
            'max_ingredient_words': cls.MAX_INGREDIENT_WORDS,
            'max_ingredients': cls.MAX_INGREDIENTS,
        }
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)


