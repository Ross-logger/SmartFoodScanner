"""
Inference for Hybrid OCR Correction Model
Fast, lightweight, perfect for production
"""

import json
import pickle
from pathlib import Path
from typing import List, Dict, Tuple, Optional

try:
    from symspellpy import SymSpell, Verbosity
except ImportError:
    print("Installing symspellpy...")
    import os
    os.system("pip install symspellpy")
    from symspellpy import SymSpell, Verbosity


class OcrCorrector:
    """
    Fast OCR correction using hybrid approach
    
    Usage:
        corrector = OcrCorrector()
        corrected = corrector.correct("s0y lec1th1n")
        # Returns: "soy lecithin"
    """
    
    def __init__(self, model_dir: str = "models/hybrid", max_edit_distance: int = 2):
        """
        Initialize OCR corrector
        
        Args:
            model_dir: Path to trained model directory
            max_edit_distance: Maximum edit distance for corrections
        """
        self.model_dir = Path(model_dir)
        self.max_edit_distance = max_edit_distance
        self.symspell = SymSpell(max_dictionary_edit_distance=max_edit_distance)
        self.char_error_patterns = {}
        self.word_cache = {}
        
        # Load model if exists
        if self.model_dir.exists():
            self._load_model()
        else:
            print(f"Warning: Model directory {model_dir} not found.")
            print("Run train_hybrid.py first to train the model.")
    
    def _load_model(self):
        """Load trained model from disk"""
        
        # Load config
        config_path = self.model_dir / "config.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.max_edit_distance = config.get('max_edit_distance', self.max_edit_distance)
        
        # Load SymSpell dictionary
        dict_path = self.model_dir / "symspell_dict.pkl"
        if dict_path.exists():
            with open(dict_path, 'rb') as f:
                dict_data = pickle.load(f)
                for word, count in dict_data['words']:
                    self.symspell.create_dictionary_entry(word, count)
        
        # Load error patterns
        patterns_path = self.model_dir / "error_patterns.json"
        if patterns_path.exists():
            with open(patterns_path, 'r') as f:
                patterns_dict = json.load(f)
                # Convert string keys back to tuples
                self.char_error_patterns = {
                    tuple(k.split('_')): v for k, v in patterns_dict.items()
                }
    
    def correct_word(self, word: str) -> Tuple[str, float]:
        """
        Correct a single word
        
        Args:
            word: Noisy word to correct
            
        Returns:
            (corrected_word, confidence_score)
        """
        if not word:
            return word, 0.0
        
        # Check cache
        if word in self.word_cache:
            return self.word_cache[word]
        
        # Try SymSpell lookup
        suggestions = self.symspell.lookup(
            word.lower(),
            Verbosity.CLOSEST,
            max_edit_distance=self.max_edit_distance
        )
        
        if suggestions:
            best = suggestions[0]
            confidence = 1.0 / (1.0 + best.distance)
            result = (best.term, confidence)
        else:
            # No suggestion found, return original
            result = (word, 0.0)
        
        # Cache result
        self.word_cache[word] = result
        return result
    
    def correct(self, text: str, return_confidence: bool = False) -> str:
        """
        Correct OCR errors in text
        
        Args:
            text: Noisy text to correct
            return_confidence: If True, return (corrected_text, avg_confidence)
            
        Returns:
            Corrected text or (corrected_text, confidence) tuple
        """
        if not text:
            return text if not return_confidence else (text, 0.0)
        
        # Split into words
        words = text.lower().split()
        corrected_words = []
        confidences = []
        
        for word in words:
            # Remove special characters for matching
            clean_word = ''.join(c for c in word if c.isalnum())
            
            if clean_word:
                corrected, confidence = self.correct_word(clean_word)
                corrected_words.append(corrected)
                confidences.append(confidence)
            else:
                corrected_words.append(word)
                confidences.append(0.0)
        
        result = ' '.join(corrected_words)
        
        if return_confidence:
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            return result, avg_confidence
        
        return result
    
    def correct_batch(self, texts: List[str]) -> List[str]:
        """
        Correct multiple texts
        
        Args:
            texts: List of noisy texts
            
        Returns:
            List of corrected texts
        """
        return [self.correct(text) for text in texts]
    
    def correct_with_details(self, text: str) -> Dict:
        """
        Correct text and return detailed information
        
        Args:
            text: Noisy text
            
        Returns:
            Dict with corrected text, confidence, and word-level corrections
        """
        if not text:
            return {
                'original': text,
                'corrected': text,
                'confidence': 0.0,
                'corrections': []
            }
        
        words = text.lower().split()
        corrected_words = []
        corrections = []
        confidences = []
        
        for word in words:
            clean_word = ''.join(c for c in word if c.isalnum())
            
            if clean_word:
                corrected, confidence = self.correct_word(clean_word)
                corrected_words.append(corrected)
                confidences.append(confidence)
                
                if corrected != clean_word:
                    corrections.append({
                        'original': clean_word,
                        'corrected': corrected,
                        'confidence': confidence
                    })
            else:
                corrected_words.append(word)
        
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return {
            'original': text,
            'corrected': ' '.join(corrected_words),
            'confidence': avg_confidence,
            'corrections': corrections
        }


def demo():
    """Demo of the OCR corrector"""
    print("="*60)
    print("Hybrid OCR Corrector - Demo")
    print("="*60)
    
    corrector = OcrCorrector()
    
    # Test examples
    test_cases = [
        "s0y lec1th1n",
        "whey pr0te1n",
        "m0n0s0d1um glUtamate",
        "natral flvors",
        "c0rn syrup",
        "v1tam1n c",
        "sod1um benzoate",
        "art1f1c1al fl4vors",
        "palm o1l",
        "h1gh fruct0se c0rn syrup"
    ]
    
    print("\nTest Cases:")
    print("-"*60)
    
    for noisy in test_cases:
        result = corrector.correct_with_details(noisy)
        
        print(f"\nOriginal:   {result['original']}")
        print(f"Corrected:  {result['corrected']}")
        print(f"Confidence: {result['confidence']:.2f}")
        
        if result['corrections']:
            print("Changes:")
            for corr in result['corrections']:
                print(f"  - {corr['original']} → {corr['corrected']} (confidence: {corr['confidence']:.2f})")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    demo()

