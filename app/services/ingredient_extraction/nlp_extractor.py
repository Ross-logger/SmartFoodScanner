"""
NLP-Based Ingredient Extractor
Uses NLP techniques to identify and correct ingredients from OCR text.
Handles OCR errors, typos, and variations using dictionary lookup and fuzzy matching.
"""

import re
from typing import List, Set, Optional, Dict, Tuple
from pathlib import Path
from difflib import get_close_matches, SequenceMatcher


class NLPIngredientExtractor:
    """
    Extracts and corrects ingredients using NLP techniques:
    - Dictionary lookup for validation
    - Fuzzy matching for OCR error correction
    - Text normalization and cleaning
    - Pattern-based extraction
    """
    
    def __init__(self, ingredients_file: Optional[str] = None):
        """
        Initialize NLP extractor.
        
        Args:
            ingredients_file: Path to ingredients.txt file.
                             Defaults to app/ML/data/ingredients.txt
        """
        if ingredients_file is None:
            base_path = Path(__file__).parent.parent.parent.parent
            ingredients_file = str(base_path / "app" / "ML" / "data" / "ingredients.txt")
        
        self.ingredients_file = ingredients_file
        self.ingredient_set: Set[str] = set()
        self.ingredient_words: Set[str] = set()  # Individual words for matching
        self._load_ingredients()
        self._init_nlp_patterns()
    
    def _load_ingredients(self):
        """Load ingredients dictionary for validation and correction."""
        try:
            with open(self.ingredients_file, 'r', encoding='utf-8') as f:
                for line in f:
                    ingredient = line.strip().lower()
                    if ingredient:
                        self.ingredient_set.add(ingredient)
                        # Also store individual words
                        words = ingredient.split()
                        self.ingredient_words.update(words)
            print(f"✅ Loaded {len(self.ingredient_set)} ingredients for NLP extraction")
        except FileNotFoundError:
            print(f"⚠️  Ingredients file not found: {self.ingredients_file}")
            self.ingredient_set = set()
        except Exception as e:
            print(f"⚠️  Failed to load ingredients: {e}")
            self.ingredient_set = set()
    
    def _init_nlp_patterns(self):
        """Initialize NLP patterns for ingredient extraction."""
        # E-number pattern (case-insensitive)
        self.e_number_pattern = re.compile(r'\be\d+\b', re.IGNORECASE)
        
        # Common separators
        self.separator_pattern = re.compile(r'[,;]|\s+and\s+|\s+&\s+')
        
        # Common OCR error patterns
        self.ocr_error_patterns = {
            r'##(\d+)': r'e\1',  # ##42 -> e42
            r'(\w)##(\w)': r'\1\2',  # car##min -> carmin
            r'(\w)\s*##(\w)': r'\1\2',  # car ##min -> carmin
        }
        
        # Common ingredient word patterns
        self.ingredient_word_patterns = [
            r'\b(flour|sugar|salt|oil|powder|extract|flavor|lecithin|starch|gum|acid)\b',
            r'\b(milk|cream|butter|cheese|yogurt|whey|casein)\b',
            r'\b(egg|albumin|yolk|white)\b',
            r'\b(wheat|barley|rye|oats|corn|rice|soy|bean)\b',
            r'\b(nut|almond|walnut|peanut|cashew|hazelnut)\b',
        ]
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for matching.
        Handles OCR errors, spaces, punctuation.
        """
        if not text:
            return ""
        
        # Convert to lowercase
        normalized = text.lower().strip()
        
        # Fix common OCR errors first
        for pattern, replacement in self.ocr_error_patterns.items():
            normalized = re.sub(pattern, replacement, normalized)
        
        # Normalize E-numbers: "E420" -> "e420", "e 420" -> "e420", "eE420" -> "e420"
        normalized = re.sub(r'\be+\s*(\d+)', r'e\1', normalized)
        normalized = re.sub(r'\be+e+(\d+)', r'e\1', normalized)  # Fix double e's
        
        # Remove extra spaces
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove trailing punctuation (except E-numbers)
        normalized = re.sub(r'[.,;]+$', '', normalized)
        
        return normalized.strip()
    
    def _extract_e_numbers(self, text: str) -> List[str]:
        """Extract E-numbers from text."""
        matches = self.e_number_pattern.findall(text)
        return [f"e{m}" for m in matches]
    
    def _fuzzy_match(self, text: str, threshold: float = 0.7) -> Optional[Tuple[str, float]]:
        """
        Find fuzzy match in ingredient dictionary.
        Returns (matched_ingredient, similarity_score).
        """
        if not self.ingredient_set or not text:
            return None
        
        normalized = self._normalize_text(text)
        
        # Try exact match first
        if normalized in self.ingredient_set:
            return (normalized, 1.0)
        
        # Try fuzzy match
        matches = get_close_matches(
            normalized,
            self.ingredient_set,
            n=1,
            cutoff=threshold
        )
        
        if matches:
            similarity = SequenceMatcher(None, normalized, matches[0]).ratio()
            return (matches[0], similarity)
        
        return None
    
    def _correct_ocr_errors(self, text: str) -> str:
        """
        Correct common OCR errors in ingredient text.
        """
        corrected = text
        
        # Fix ## patterns (common OCR artifact)
        corrected = re.sub(r'##(\d+)', r'e\1', corrected)
        corrected = re.sub(r'(\w)##(\w)', r'\1\2', corrected)
        corrected = re.sub(r'(\w)\s*##(\w)', r'\1\2', corrected)
        
        # Fix common word splits (e.g., "car min" -> "carmin")
        # Check if combining adjacent words creates a valid ingredient
        words = corrected.split()
        if len(words) >= 2:
            for i in range(len(words) - 1):
                combined = words[i] + words[i + 1]
                if combined in self.ingredient_set:
                    words[i] = combined
                    words[i + 1] = ""
            corrected = " ".join(w for w in words if w)
        
        return corrected
    
    def _extract_ingredient_phrases(self, text: str) -> List[str]:
        """
        Extract potential ingredient phrases from text.
        Uses NLP techniques to identify multi-word ingredients.
        """
        # Split by separators
        parts = self.separator_pattern.split(text)
        
        ingredients = []
        
        for part in parts:
            part = part.strip()
            if not part or len(part) < 2:
                continue
            
            # Correct OCR errors
            corrected = self._correct_ocr_errors(part)
            
            # Normalize
            normalized = self._normalize_text(corrected)
            
            if normalized:
                ingredients.append(normalized)
        
        return ingredients
    
    def _match_multi_word(self, text: str) -> Optional[str]:
        """
        Try to match multi-word phrases against ingredient dictionary.
        Handles cases where words might be split incorrectly.
        """
        words = text.split()
        
        # Try all possible combinations (up to 4 words)
        for length in range(min(4, len(words)), 0, -1):
            for i in range(len(words) - length + 1):
                phrase = ' '.join(words[i:i + length])
                if phrase in self.ingredient_set:
                    return phrase
        
        return None
    
    def extract(self, text: str) -> List[str]:
        """
        Extract and correct ingredients from OCR text.
        
        Args:
            text: OCR text containing ingredients
            
        Returns:
            List of extracted and corrected ingredient names
        """
        if not text:
            return []
        
        # Extract potential ingredient phrases
        phrases = self._extract_ingredient_phrases(text)
        
        ingredients = []
        seen = set()
        
        # Process each phrase
        for phrase in phrases:
            if not phrase:
                continue
            
            # Normalize phrase (handles OCR errors)
            normalized = self._normalize_text(phrase)
            
            if not normalized or normalized in seen:
                continue
            
            # Check if it's an E-number
            if self.e_number_pattern.match(normalized):
                # Normalize E-number format
                e_match = re.search(r'e(\d+)', normalized)
                if e_match:
                    e_normalized = f"e{e_match.group(1)}"
                    if e_normalized not in seen:
                        ingredients.append(e_normalized)
                        seen.add(e_normalized)
                continue
            
            # Try exact match
            if normalized in self.ingredient_set:
                if normalized not in seen:
                    ingredients.append(normalized)
                    seen.add(normalized)
                continue
            
            # Try multi-word matching
            multi_match = self._match_multi_word(normalized)
            if multi_match and multi_match not in seen:
                ingredients.append(multi_match)
                seen.add(multi_match)
                continue
            
            # Try fuzzy matching
            fuzzy_match = self._fuzzy_match(normalized, threshold=0.7)
            if fuzzy_match:
                matched, similarity = fuzzy_match
                if matched not in seen and similarity >= 0.7:
                    ingredients.append(matched)
                    seen.add(matched)
                    continue
        
        return ingredients
    
    def extract_with_corrections(self, text: str) -> List[Dict[str, any]]:
        """
        Extract ingredients with correction information.
        
        Args:
            text: OCR text containing ingredients
            
        Returns:
            List of dicts with 'original', 'corrected', 'confidence' keys
        """
        if not text:
            return []
        
        # Extract E-numbers
        e_numbers = self._extract_e_numbers(text)
        
        # Extract phrases
        phrases = self._extract_ingredient_phrases(text)
        
        results = []
        seen = set()
        
        for phrase in phrases:
            if not phrase or phrase in seen:
                continue
            
            original = phrase
            
            # E-number handling
            if self.e_number_pattern.match(phrase):
                normalized = phrase.lower()
                if normalized not in seen:
                    results.append({
                        'original': original,
                        'corrected': normalized,
                        'confidence': 1.0,
                        'method': 'e_number'
                    })
                    seen.add(normalized)
                continue
            
            # Exact match
            if phrase in self.ingredient_set:
                if phrase not in seen:
                    results.append({
                        'original': original,
                        'corrected': phrase,
                        'confidence': 1.0,
                        'method': 'exact'
                    })
                    seen.add(phrase)
                continue
            
            # Multi-word match
            multi_match = self._match_multi_word(phrase)
            if multi_match and multi_match not in seen:
                results.append({
                    'original': original,
                    'corrected': multi_match,
                    'confidence': 0.9,
                    'method': 'multi_word'
                })
                seen.add(multi_match)
                continue
            
            # Fuzzy match
            fuzzy_match = self._fuzzy_match(phrase, threshold=0.6)
            if fuzzy_match:
                matched, similarity = fuzzy_match
                if matched not in seen and similarity >= 0.6:
                    results.append({
                        'original': original,
                        'corrected': matched,
                        'confidence': similarity,
                        'method': 'fuzzy'
                    })
                    seen.add(matched)
                    continue
        
        # Add E-numbers
        for e_num in e_numbers:
            if e_num not in seen:
                results.append({
                    'original': e_num,
                    'corrected': e_num,
                    'confidence': 1.0,
                    'method': 'e_number'
                })
                seen.add(e_num)
        
        return results

