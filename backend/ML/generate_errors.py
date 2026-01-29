"""
Generate Synthetic OCR Errors for Training
Simulates realistic OCR mistakes found in food packaging scans
"""

import random
import argparse
from pathlib import Path
from typing import List, Tuple
from tqdm import tqdm


class OCRErrorGenerator:
    """Generate realistic OCR errors for training"""
    
    def __init__(self, seed: int = 42):
        random.seed(seed)
        
        # Common OCR character confusions
        self.char_substitutions = {
            # Letters confused with numbers
            'o': ['0', 'O'],
            'O': ['0', 'o'],
            'l': ['1', 'I', '|'],
            'I': ['1', 'l', '|'],
            'i': ['1', '!', 'l'],
            's': ['5', 'S'],
            'S': ['5', 's'],
            'z': ['2', 'Z'],
            'Z': ['2', 'z'],
            'g': ['9', 'q'],
            'b': ['8', 'B'],
            'B': ['8', 'b'],
            'e': ['3', 'E'],
            'a': ['4', '@'],
            't': ['7', '+'],
            
            # Numbers confused with letters
            '0': ['o', 'O'],
            '1': ['l', 'I', '|'],
            '5': ['s', 'S'],
            '2': ['z', 'Z'],
            '8': ['b', 'B'],
            '3': ['e', 'E'],
            '7': ['t', 'T'],
            '9': ['g', 'q'],
            
            # Similar looking letters
            'c': ['e', 'o', 'C'],
            'n': ['m', 'h', 'N'],
            'm': ['n', 'rn', 'M'],
            'u': ['v', 'U'],
            'v': ['u', 'V'],
            'w': ['vv', 'W'],
            'r': ['n', 'R'],
            'h': ['n', 'li', 'H'],
            'k': ['K', 'lc'],
            'f': ['F', 't'],
            'p': ['q', 'P'],
            'q': ['p', 'g', 'Q'],
            'd': ['cl', 'D'],
            'y': ['v', 'Y'],
        }
        
        # Common character deletions (often missing in OCR)
        self.common_deletions = ['a', 'e', 'i', 'o', 'u', 'h', 'r', 'n', 'm']
        
        # Common character duplications
        self.common_duplications = ['l', 't', 'f', 's', 'n', 'm', 'p']
        
    def substitute_char(self, char: str) -> str:
        """Substitute a character with OCR confusion"""
        if char in self.char_substitutions:
            options = self.char_substitutions[char]
            return random.choice(options)
        return char
    
    def delete_char(self, text: str, position: int) -> str:
        """Delete a character at position"""
        if 0 <= position < len(text):
            return text[:position] + text[position+1:]
        return text
    
    def duplicate_char(self, text: str, position: int) -> str:
        """Duplicate a character at position"""
        if 0 <= position < len(text):
            return text[:position+1] + text[position] + text[position+1:]
        return text
    
    def insert_random_char(self, text: str, position: int) -> str:
        """Insert a random character at position"""
        random_chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
        char = random.choice(random_chars)
        return text[:position] + char + text[position:]
    
    def swap_adjacent_chars(self, text: str, position: int) -> str:
        """Swap two adjacent characters"""
        if 0 <= position < len(text) - 1:
            chars = list(text)
            chars[position], chars[position+1] = chars[position+1], chars[position]
            return ''.join(chars)
        return text
    
    def add_space_error(self, text: str) -> str:
        """Add or remove spaces incorrectly"""
        words = text.split()
        if len(words) > 1 and random.random() < 0.3:
            # Remove a space
            idx = random.randint(0, len(words) - 2)
            words[idx] = words[idx] + words[idx + 1]
            words.pop(idx + 1)
        elif random.random() < 0.2:
            # Add a space
            if words:
                idx = random.randint(0, len(words) - 1)
                word = words[idx]
                if len(word) > 3:
                    split_pos = random.randint(1, len(word) - 1)
                    words[idx] = word[:split_pos] + " " + word[split_pos:]
        return ' '.join(words)
    
    def generate_error(self, text: str, error_rate: float = 0.15) -> str:
        """
        Generate OCR errors in text
        
        Args:
            text: Clean text
            error_rate: Probability of error per character (0.0 to 1.0)
            
        Returns:
            Text with OCR errors
        """
        if not text or len(text) < 2:
            return text
        
        text = text.lower()
        result = list(text)
        
        # Apply character-level errors
        i = 0
        while i < len(result):
            if random.random() < error_rate:
                error_type = random.choice(['substitute', 'delete', 'duplicate', 'swap'])
                
                if error_type == 'substitute' and result[i].isalnum():
                    # Character substitution
                    result[i] = self.substitute_char(result[i])
                    
                elif error_type == 'delete' and i > 0 and i < len(result) - 1:
                    # Character deletion (not at edges)
                    if result[i] in self.common_deletions:
                        result.pop(i)
                        i -= 1
                        
                elif error_type == 'duplicate' and result[i] in self.common_duplications:
                    # Character duplication
                    result.insert(i, result[i])
                    i += 1
                    
                elif error_type == 'swap' and i < len(result) - 1:
                    # Character swap
                    result[i], result[i+1] = result[i+1], result[i]
                    i += 1
                    
            i += 1
        
        text = ''.join(result)
        
        # Apply word-level errors (spacing)
        if random.random() < 0.2:
            text = self.add_space_error(text)
        
        return text
    
    def generate_multiple_errors(self, text: str, num_variants: int = 3) -> List[str]:
        """Generate multiple error variants of the same text"""
        variants = set()
        attempts = 0
        max_attempts = num_variants * 10
        
        while len(variants) < num_variants and attempts < max_attempts:
            # Vary error rate slightly
            error_rate = random.uniform(0.05, 0.25)
            variant = self.generate_error(text, error_rate)
            
            # Only add if it's different from original and not too corrupted
            if variant != text and len(variant) >= len(text) * 0.5:
                variants.add(variant)
            
            attempts += 1
        
        return list(variants)


def create_training_pairs(
    ingredients_file: str = "data/ingredients.txt",
    output_train: str = "data/train_pairs.txt",
    output_test: str = "data/test_pairs.txt",
    train_size: int = 10000,
    test_size: int = 1000,
    variants_per_ingredient: int = 3
):
    """
    Create training and test pairs of (noisy, clean) text
    
    Args:
        ingredients_file: Path to clean ingredient list
        output_train: Output training pairs file
        output_test: Output test pairs file
        train_size: Number of training examples
        test_size: Number of test examples
        variants_per_ingredient: Error variants per ingredient
    """
    
    print("="*60)
    print("Generating OCR Error Training Data")
    print("="*60)
    
    # Load ingredients
    with open(ingredients_file, 'r', encoding='utf-8') as f:
        ingredients = [line.strip() for line in f if line.strip()]
    
    print(f"Loaded {len(ingredients)} ingredients")
    
    # Initialize error generator
    generator = OCRErrorGenerator()
    
    # Generate training pairs
    train_pairs = []
    test_pairs = []
    
    print("\nGenerating training pairs...")
    while len(train_pairs) < train_size:
        # Pick random ingredient
        ingredient = random.choice(ingredients)
        
        # Generate error variants
        variants = generator.generate_multiple_errors(ingredient, variants_per_ingredient)
        
        for variant in variants:
            if len(train_pairs) < train_size:
                train_pairs.append((variant, ingredient))
            elif len(test_pairs) < test_size:
                test_pairs.append((variant, ingredient))
            else:
                break
            
        print(f"Generated {len(train_pairs)} training pairs...")
    
    print("\nGenerating test pairs...")
    while len(test_pairs) < test_size:
        ingredient = random.choice(ingredients)
        variants = generator.generate_multiple_errors(ingredient, variants_per_ingredient)
        
        for variant in variants:
            if len(test_pairs) < test_size:
                test_pairs.append((variant, ingredient))
            else:
                break
    
    # Shuffle pairs
    random.shuffle(train_pairs)
    random.shuffle(test_pairs)
    
    # Save training pairs
    Path(output_train).parent.mkdir(exist_ok=True, parents=True)
    with open(output_train, 'w', encoding='utf-8') as f:
        for noisy, clean in train_pairs:
            f.write(f"{noisy}\t{clean}\n")
    
    print(f"\nSaved {len(train_pairs)} training pairs to {output_train}")
    
    # Save test pairs
    with open(output_test, 'w', encoding='utf-8') as f:
        for noisy, clean in test_pairs:
            f.write(f"{noisy}\t{clean}\n")
    
    print(f"Saved {len(test_pairs)} test pairs to {output_test}")
    
    # Show examples
    print("\n" + "="*60)
    print("Example Error Pairs:")
    print("="*60)
    for i in range(min(10, len(train_pairs))):
        noisy, clean = train_pairs[i]
        print(f"Noisy: {noisy:40s} → Clean: {clean}")
    
    print("\n" + "="*60)
    print("Data generation complete!")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(description="Generate OCR error training data")
    parser.add_argument("--input", default="data/ingredients.txt", help="Input ingredient file")
    parser.add_argument("--train-output", default="data/train_pairs.txt", help="Training pairs output")
    parser.add_argument("--test-output", default="data/test_pairs.txt", help="Test pairs output")
    parser.add_argument("--train-size", type=int, default=10000, help="Number of training examples")
    parser.add_argument("--test-size", type=int, default=1000, help="Number of test examples")
    parser.add_argument("--variants", type=int, default=3, help="Error variants per ingredient")
    
    args = parser.parse_args()
    
    create_training_pairs(
        ingredients_file=args.input,
        output_train=args.train_output,
        output_test=args.test_output,
        train_size=args.train_size,
        test_size=args.test_size,
        variants_per_ingredient=args.variants
    )


if __name__ == "__main__":
    main()

