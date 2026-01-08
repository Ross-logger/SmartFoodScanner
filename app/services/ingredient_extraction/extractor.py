"""
Ingredient Extractor
Uses NLP-based extraction for reliable ingredient identification and correction.
"""

from typing import List, Optional
from app.services.ingredient_extraction.config import IngredientExtractionConfig
from app.services.ingredient_extraction.nlp_extractor import NLPIngredientExtractor

class IngredientExtractor:
    """
    Extracts ingredients from OCR text using NLP techniques.
    Handles OCR errors, typos, and variations using dictionary lookup and fuzzy matching.
    """
    
    def __init__(self, config: Optional[IngredientExtractionConfig] = None, 
                 use_nlp: bool = True):
        """
        Initialize ingredient extractor.
        
        Args:
            config: Configuration object. Uses default if not provided.
            use_nlp: Whether to use NLP-based extraction (default: True)
        """
        self.config = config or IngredientExtractionConfig()
        self.use_nlp = use_nlp
        
        # Initialize NLP extractor (the only extraction method)
        if self.use_nlp:
            try:
                self.nlp_extractor = NLPIngredientExtractor()
            except Exception as e:
                print(f"⚠️  Failed to initialize NLP extractor: {e}. Using fallback.")
                self.nlp_extractor = None
                self.use_nlp = False
        else:
            self.nlp_extractor = None
    
    def extract(self, text: str) -> List[str]:
        """
        Extract ingredients from OCR text using NLP extraction.
        Falls back to pattern-based extraction if NLP fails.
        
        Args:
            text: Raw OCR text
            
        Returns:
            List of extracted ingredient names (normalized to lowercase)
        """
        if not text:
            return []
        
        # Use NLP extraction (reliable method)
        if self.use_nlp and self.nlp_extractor:
            ingredients = self.nlp_extractor.extract(text)
            if ingredients:
                return ingredients
        
        # Fallback to pattern-based extraction
        return self._extract_with_patterns(text)
    
    def extract_with_corrections(self, text: str) -> List[dict]:
        """
        Extract ingredients with correction information.
        
        Args:
            text: Raw OCR text
            
        Returns:
            List of dicts with 'original', 'corrected', 'confidence', 'method' keys
        """
        if not text:
            return []
        
        # Use NLP extractor if available
        if self.use_nlp and self.nlp_extractor:
            return self.nlp_extractor.extract_with_corrections(text)
        
        # Fallback: extract normally and format as corrections
        ingredients = self.extract(text)
        return [
            {
                'original': ing,
                'corrected': ing,
                'confidence': 1.0,
                'method': 'pattern'
            }
            for ing in ingredients
        ]
    
    def _extract_with_patterns(self, text: str) -> List[str]:
        """
        Fallback pattern-based extraction.
        
        Args:
            text: Raw OCR text
            
        Returns:
            List of extracted ingredients
        """
        import re
        
        # Find ingredients section
        lines = text.split('\n')
        ingredients_lines = []
        found_start = False
        
        for line in lines:
            line_lower = line.lower().strip()
            
            if not found_start:
                if any(re.search(p, line_lower) for p in self.config.START_PATTERNS):
                    found_start = True
                    extracted = self._extract_after_header(line)
                    if extracted:
                        ingredients_lines.append(extracted)
                    continue
            
            if found_start:
                if any(re.search(p, line_lower) for p in self.config.STOP_PATTERNS):
                    break
                if line.strip():
                    ingredients_lines.append(line.strip())
        
        if not ingredients_lines:
            return []
        
        # Split by separators
        text_section = ' '.join(ingredients_lines)
        separator_pattern = r'[,;]|\s+and\s+|\s+&\s+'
        parts = re.split(separator_pattern, text_section)
        
        ingredients = []
        for part in parts:
            part = part.strip()
            part = re.sub(r'\.$', '', part).strip()
            if part and len(part) > 2:
                ingredients.append(part.lower())
        
        # Remove duplicates
        seen = set()
        unique_ingredients = []
        for ing in ingredients:
            if ing not in seen:
                seen.add(ing)
                unique_ingredients.append(ing)
        
        return unique_ingredients[:self.config.MAX_INGREDIENTS]
    
    def _extract_after_header(self, line: str) -> str:
        """Extract text after ingredients header."""
        import re
        match = re.search(r'[:]\s*(.+)$', line, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        cleaned = re.sub(
            r'^(inoredients?|ingredients?|ingred\w*|contains?)\s*[:]?\s*',
            '',
            line,
            flags=re.IGNORECASE
        ).strip()
        
        return cleaned if cleaned and len(cleaned) > self.config.MIN_INGREDIENT_LENGTH else ''
