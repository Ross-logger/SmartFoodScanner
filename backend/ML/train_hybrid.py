"""
Hybrid OCR Correction Model Training
Combines SymSpell dictionary-based correction with character-level pattern learning
RECOMMENDED: Fast, accurate, no GPU required
"""

import os
import json
import pickle
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np
from collections import Counter
from tqdm import tqdm

try:
    from symspellpy import SymSpell, Verbosity
except ImportError:
    print("Installing symspellpy...")
    os.system("pip install symspellpy")
    from symspellpy import SymSpell, Verbosity


class HybridOCRCorrector:
    """
    Hybrid approach combining:
    1. SymSpell for fast dictionary matching
    2. Character-level error patterns
    3. Confidence scoring
    """
    
    def __init__(self, max_edit_distance: int = 2):
        self.symspell = SymSpell(max_dictionary_edit_distance=max_edit_distance)
        self.max_edit_distance = max_edit_distance
        self.char_error_patterns = {}  # Common character error mappings
        self.word_cache = {}  # Cache for frequent corrections
        
    def build_dictionary(self, ingredients: List[str]):
        """Build SymSpell dictionary from ingredient list"""
        print("Building dictionary...")
        
        # Add each ingredient and its words
        for ingredient in tqdm(ingredients):
            # Add full ingredient
            self.symspell.create_dictionary_entry(ingredient.lower(), 1)
            
            # Also add individual words (for multi-word ingredients)
            words = ingredient.lower().split()
            for word in words:
                if len(word) > 1:
                    self.symspell.create_dictionary_entry(word, 1)
        
        print(f"Dictionary built with {self.symspell.word_count} entries")
    
    def learn_error_patterns(self, training_pairs: List[Tuple[str, str]]):
        """Learn common character-level error patterns from training data"""
        print("\nLearning error patterns...")
        
        char_mappings = Counter()
        
        for noisy, clean in tqdm(training_pairs):
            # Simple character alignment (for similar length strings)
            if abs(len(noisy) - len(clean)) <= 2:
                # Align characters
                for i, (n_char, c_char) in enumerate(zip(noisy, clean)):
                    if n_char != c_char:
                        # Record this error pattern
                        char_mappings[(n_char, c_char)] += 1
        
        # Keep most common patterns
        self.char_error_patterns = dict(char_mappings.most_common(100))
        
        print(f"Learned {len(self.char_error_patterns)} character error patterns")
        
        # Print top patterns
        print("\nTop 10 error patterns:")
        for (noisy_char, clean_char), count in list(self.char_error_patterns.items())[:10]:
            print(f"  '{noisy_char}' → '{clean_char}': {count} times")
    
    def correct_with_patterns(self, text: str) -> str:
        """Apply learned character patterns"""
        result = list(text)
        
        for i, char in enumerate(result):
            # Check if this character appears in error patterns
            for (noisy_char, clean_char), _ in self.char_error_patterns.items():
                if char == noisy_char:
                    # Apply correction with some probability
                    result[i] = clean_char
                    break
        
        return ''.join(result)
    
    def correct_word(self, word: str) -> Tuple[str, float]:
        """
        Correct a single word
        
        Returns:
            (corrected_word, confidence_score)
        """
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
            confidence = 1.0 / (1.0 + best.distance)  # Higher confidence for smaller distance
            result = (best.term, confidence)
        else:
            # No suggestion found, return original
            result = (word, 0.0)
        
        # Cache result
        self.word_cache[word] = result
        return result
    
    def correct(self, text: str) -> str:
        """Correct OCR errors in text"""
        if not text:
            return text
        
        # Split into words
        words = text.lower().split()
        corrected_words = []
        
        for word in words:
            # Remove special characters for matching
            clean_word = ''.join(c for c in word if c.isalnum())
            
            if clean_word:
                corrected, confidence = self.correct_word(clean_word)
                corrected_words.append(corrected)
            else:
                corrected_words.append(word)
        
        return ' '.join(corrected_words)
    
    def save(self, model_dir: str):
        """Save model to disk"""
        model_path = Path(model_dir)
        model_path.mkdir(exist_ok=True, parents=True)
        
        # Save SymSpell dictionary
        dict_path = model_path / "symspell_dict.pkl"
        with open(dict_path, 'wb') as f:
            pickle.dump({
                'word_count': self.symspell.word_count,
                'words': list(self.symspell.words.items())
            }, f)
        
        # Save error patterns
        patterns_path = model_path / "error_patterns.json"
        with open(patterns_path, 'w') as f:
            # Convert tuple keys to strings for JSON
            patterns_dict = {f"{k[0]}_{k[1]}": v for k, v in self.char_error_patterns.items()}
            json.dump(patterns_dict, f)
        
        # Save config
        config_path = model_path / "config.json"
        with open(config_path, 'w') as f:
            json.dump({
                'max_edit_distance': self.max_edit_distance,
                'model_type': 'hybrid'
            }, f)
        
        print(f"\nModel saved to {model_dir}")
    
    @classmethod
    def load(cls, model_dir: str):
        """Load model from disk"""
        model_path = Path(model_dir)
        
        # Load config
        config_path = model_path / "config.json"
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Create model
        model = cls(max_edit_distance=config['max_edit_distance'])
        
        # Load SymSpell dictionary
        dict_path = model_path / "symspell_dict.pkl"
        with open(dict_path, 'rb') as f:
            dict_data = pickle.load(f)
            for word, count in dict_data['words']:
                model.symspell.create_dictionary_entry(word, count)
        
        # Load error patterns
        patterns_path = model_path / "error_patterns.json"
        with open(patterns_path, 'r') as f:
            patterns_dict = json.load(f)
            # Convert string keys back to tuples
            model.char_error_patterns = {
                tuple(k.split('_')): v for k, v in patterns_dict.items()
            }
        
        print(f"Model loaded from {model_dir}")
        return model


def evaluate_model(model: HybridOCRCorrector, test_pairs: List[Tuple[str, str]]):
    """Evaluate model accuracy"""
    print("\n" + "="*60)
    print("Evaluating model...")
    print("="*60)
    
    correct = 0
    total = len(test_pairs)
    
    examples = []
    
    for noisy, clean in tqdm(test_pairs):
        predicted = model.correct(noisy)
        
        if predicted == clean.lower():
            correct += 1
        
        # Save some examples
        if len(examples) < 20:
            examples.append((noisy, clean, predicted, predicted == clean.lower()))
    
    accuracy = correct / total * 100
    
    print(f"\nAccuracy: {accuracy:.2f}% ({correct}/{total})")
    
    print("\n" + "="*60)
    print("Example Predictions:")
    print("="*60)
    for noisy, clean, predicted, is_correct in examples[:10]:
        status = "✓" if is_correct else "✗"
        print(f"{status} Noisy: {noisy:30s} → Predicted: {predicted:30s} (Truth: {clean})")
    
    return accuracy


def train_hybrid_model(
    ingredients_file: str = "data/ingredients.txt",
    train_file: str = "data/train_pairs.txt",
    test_file: str = "data/test_pairs.txt",
    output_dir: str = "models/hybrid",
    max_edit_distance: int = 2
):
    """
    Train hybrid OCR correction model
    
    Args:
        ingredients_file: Path to ingredient vocabulary
        train_file: Path to training pairs
        test_file: Path to test pairs
        output_dir: Output directory for model
        max_edit_distance: Maximum edit distance for SymSpell
    """
    
    print("="*60)
    print("Training Hybrid OCR Correction Model")
    print("="*60)
    
    # Load ingredients
    print("\nLoading ingredients...")
    with open(ingredients_file, 'r', encoding='utf-8') as f:
        ingredients = [line.strip() for line in f if line.strip()]
    print(f"Loaded {len(ingredients)} ingredients")
    
    # Load training pairs
    print("\nLoading training data...")
    train_pairs = []
    with open(train_file, 'r', encoding='utf-8') as f:
        for line in f:
            if '\t' in line:
                noisy, clean = line.strip().split('\t')
                train_pairs.append((noisy, clean))
    print(f"Loaded {len(train_pairs)} training pairs")
    
    # Load test pairs
    print("\nLoading test data...")
    test_pairs = []
    with open(test_file, 'r', encoding='utf-8') as f:
        for line in f:
            if '\t' in line:
                noisy, clean = line.strip().split('\t')
                test_pairs.append((noisy, clean))
    print(f"Loaded {len(test_pairs)} test pairs")
    
    # Create and train model
    print("\n" + "="*60)
    print("Building model...")
    print("="*60)
    
    model = HybridOCRCorrector(max_edit_distance=max_edit_distance)
    
    # Build dictionary
    model.build_dictionary(ingredients)
    
    # Learn error patterns
    model.learn_error_patterns(train_pairs)
    
    # Evaluate
    accuracy = evaluate_model(model, test_pairs)
    
    # Save model
    model.save(output_dir)
    
    print("\n" + "="*60)
    print("Training Complete!")
    print("="*60)
    print(f"Model saved to: {output_dir}")
    print(f"Final accuracy: {accuracy:.2f}%")
    print("\nNext step: Use inference_hybrid.py to test the model")
    
    return model


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Train hybrid OCR correction model")
    parser.add_argument("--ingredients", default="data/ingredients.txt", help="Ingredient vocabulary file")
    parser.add_argument("--train", default="data/train_pairs.txt", help="Training pairs file")
    parser.add_argument("--test", default="data/test_pairs.txt", help="Test pairs file")
    parser.add_argument("--output", default="models/hybrid", help="Output directory")
    parser.add_argument("--max-edit-distance", type=int, default=2, help="Max edit distance for SymSpell")
    
    args = parser.parse_args()
    
    train_hybrid_model(
        ingredients_file=args.ingredients,
        train_file=args.train,
        test_file=args.test,
        output_dir=args.output,
        max_edit_distance=args.max_edit_distance
    )


if __name__ == "__main__":
    main()

