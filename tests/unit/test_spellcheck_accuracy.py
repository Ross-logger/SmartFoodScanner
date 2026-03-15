"""
Spellcheck Accuracy Tests for OCR Correction

Tests the SymSpell-based spell correction against 300 ground truth ingredients
with 4 categories of systematic misspellings simulating OCR errors:
  1. one_letter_changed   – 1 random letter replaced by adjacent keyboard key
  2. one_letter_removed   – 1 random letter deleted
  3. two_letters_changed  – 2 random letters replaced
  4. two_letters_removed  – 2 random letters deleted

Ground truth source:
  OpenFoodFacts (world.openfoodfacts.org/ingredients) – top 300 ingredients
  by frequency across 4M+ packaged food products.

Usage:
  pytest tests/unit/test_spellcheck_accuracy.py -v
  pytest tests/unit/test_spellcheck_accuracy.py -v -s   # with print output
"""

import csv
import random
import string
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

# ── Add project root to path ─────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tests.data.spellcheck_ground_truth import TOP_300_INGREDIENTS
from backend.services.ingredients_extraction.symspell_extraction import (
    _correct_text,
    _get_spell_checker,
)

# ── Constants ─────────────────────────────────────────────────────────────────

# Fixed seed for reproducible misspellings
RANDOM_SEED = 42

# Keyboard adjacency map for realistic OCR-like substitutions
# Each letter maps to its neighbours on a QWERTY keyboard
KEYBOARD_ADJACENT: Dict[str, str] = {
    "a": "sqwz",
    "b": "vngh",
    "c": "xdfv",
    "d": "sfcxer",
    "e": "wrsdf",
    "f": "dgcvrt",
    "g": "fhvbty",
    "h": "gjbnyu",
    "i": "ujkol",
    "j": "hknmui",
    "k": "jlmio",
    "l": "kop",
    "m": "njk",
    "n": "bmhj",
    "o": "iklp",
    "p": "ol",
    "q": "wa",
    "r": "edft",
    "s": "awdxze",
    "t": "rfgy",
    "u": "yhji",
    "v": "cfgb",
    "w": "qase",
    "x": "zsdc",
    "y": "tghu",
    "z": "asx",
}

# Characters that are visually similar (common OCR confusions)
OCR_CONFUSIONS: Dict[str, str] = {
    "o": "0",
    "l": "1i",
    "i": "1l",
    "s": "5",
    "b": "6",
    "g": "9q",
    "z": "2",
    "e": "c",
    "c": "e",
    "n": "m",
    "m": "n",
    "u": "v",
    "v": "u",
    "r": "n",
    "a": "o",
    "d": "b",
    "h": "n",
    "t": "f",
    "f": "t",
    "w": "vv",
    "p": "q",
    "q": "p",
}


# ── Misspelling Generators ───────────────────────────────────────────────────

def _get_letter_positions(word: str) -> List[int]:
    """Get indices of alphabetic characters in a word."""
    return [i for i, ch in enumerate(word) if ch.isalpha()]


def _substitute_char(char: str, rng: random.Random) -> str:
    """Replace a character with an adjacent key or OCR confusion."""
    char_lower = char.lower()
    # 50% chance: keyboard adjacent, 50% chance: OCR confusion
    if rng.random() < 0.5 and char_lower in KEYBOARD_ADJACENT:
        replacement = rng.choice(KEYBOARD_ADJACENT[char_lower])
    elif char_lower in OCR_CONFUSIONS:
        candidates = OCR_CONFUSIONS[char_lower]
        replacement = rng.choice(list(candidates))
    elif char_lower in KEYBOARD_ADJACENT:
        replacement = rng.choice(KEYBOARD_ADJACENT[char_lower])
    else:
        # Fallback: random letter
        replacement = rng.choice(string.ascii_lowercase)
    return replacement


def change_one_letter(word: str, rng: random.Random) -> str:
    """Replace 1 random letter with an adjacent/similar character."""
    positions = _get_letter_positions(word)
    if len(positions) < 2:
        return word  # too short to misspell safely
    # Avoid first character (spell checkers are more sensitive to it)
    pos = rng.choice(positions[1:]) if len(positions) > 2 else positions[-1]
    chars = list(word)
    original = chars[pos]
    replacement = _substitute_char(original, rng)
    # Make sure it's actually different
    attempts = 0
    while replacement == original.lower() and attempts < 10:
        replacement = _substitute_char(original, rng)
        attempts += 1
    chars[pos] = replacement
    return "".join(chars)


def remove_one_letter(word: str, rng: random.Random) -> str:
    """Remove 1 random letter from the word."""
    positions = _get_letter_positions(word)
    if len(positions) < 3:
        return word  # too short to remove from safely
    # Avoid first and last character
    interior = positions[1:-1] if len(positions) > 2 else positions
    pos = rng.choice(interior)
    return word[:pos] + word[pos + 1:]


def change_two_letters(word: str, rng: random.Random) -> str:
    """Replace 2 random letters with adjacent/similar characters."""
    positions = _get_letter_positions(word)
    if len(positions) < 4:
        return change_one_letter(word, rng)  # fall back to 1 change
    # Pick 2 distinct positions, avoiding the first character
    candidate_positions = positions[1:] if len(positions) > 3 else positions
    chosen = rng.sample(candidate_positions, min(2, len(candidate_positions)))
    chars = list(word)
    for pos in chosen:
        original = chars[pos]
        replacement = _substitute_char(original, rng)
        attempts = 0
        while replacement == original.lower() and attempts < 10:
            replacement = _substitute_char(original, rng)
            attempts += 1
        chars[pos] = replacement
    return "".join(chars)


def remove_two_letters(word: str, rng: random.Random) -> str:
    """Remove 2 random letters from the word."""
    positions = _get_letter_positions(word)
    if len(positions) < 5:
        return remove_one_letter(word, rng)  # fall back to 1 removal
    # Pick 2 distinct interior positions
    interior = positions[1:-1] if len(positions) > 3 else positions
    chosen = sorted(rng.sample(interior, min(2, len(interior))), reverse=True)
    result = word
    for pos in chosen:
        result = result[:pos] + result[pos + 1:]
    return result


# ── Misspelling Categories ───────────────────────────────────────────────────

MISSPELLING_CATEGORIES = {
    "one_letter_changed": change_one_letter,
    "one_letter_removed": remove_one_letter,
    "two_letters_changed": change_two_letters,
    "two_letters_removed": remove_two_letters,
}


def generate_misspellings(
    ingredients: List[str], seed: int = RANDOM_SEED
) -> Dict[str, List[Tuple[str, str, str]]]:
    """
    Generate misspellings for all ingredients across all categories.

    Returns:
        Dict mapping category_name -> list of (ground_truth, misspelled, category)
    """
    rng = random.Random(seed)
    results: Dict[str, List[Tuple[str, str, str]]] = {}

    for category_name, misspell_fn in MISSPELLING_CATEGORIES.items():
        category_results = []
        for ingredient in ingredients:
            misspelled = misspell_fn(ingredient, rng)
            category_results.append((ingredient, misspelled, category_name))
        results[category_name] = category_results

    return results


# ── Test Execution ───────────────────────────────────────────────────────────

def run_spellcheck_test(
    ingredients: List[str], seed: int = RANDOM_SEED
) -> Dict[str, Dict]:
    """
    Run the full spellcheck accuracy test.

    Returns dict with per-category results:
      {category_name: {
          "total": int,
          "correct": int,
          "accuracy": float,
          "details": [(ground_truth, misspelled, corrected, is_correct), ...]
      }}
    """
    sym_spell = _get_spell_checker()
    all_misspellings = generate_misspellings(ingredients, seed)
    results = {}

    for category_name, test_cases in all_misspellings.items():
        correct_count = 0
        details = []

        for ground_truth, misspelled, _ in test_cases:
            corrected = _correct_text(misspelled, sym_spell)
            is_correct = corrected.strip().lower() == ground_truth.strip().lower()
            if is_correct:
                correct_count += 1
            details.append((ground_truth, misspelled, corrected, is_correct))

        total = len(test_cases)
        results[category_name] = {
            "total": total,
            "correct": correct_count,
            "accuracy": (correct_count / total * 100) if total > 0 else 0.0,
            "details": details,
        }

    return results


def save_results_csv(results: Dict[str, Dict], output_path: Path) -> None:
    """Save detailed results to CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "ground_truth",
            "misspelling_category",
            "misspelled",
            "corrected",
            "is_correct",
        ])
        for category_name, data in results.items():
            for ground_truth, misspelled, corrected, is_correct in data["details"]:
                writer.writerow([
                    ground_truth,
                    category_name,
                    misspelled,
                    corrected,
                    is_correct,
                ])


def print_summary_table(results: Dict[str, Dict]) -> None:
    """Print a formatted summary table."""
    print("\n" + "=" * 75)
    print("  SPELLCHECK ACCURACY TEST RESULTS")
    print("  Ground truth: Top 300 Ingredients (OpenFoodFacts)")
    print("=" * 75)
    print(f"  {'Category':<25} {'Correct':>8} {'Total':>8} {'Accuracy':>10}")
    print("-" * 75)

    total_correct = 0
    total_items = 0

    for category_name, data in results.items():
        label = category_name.replace("_", " ").title()
        print(
            f"  {label:<25} {data['correct']:>8} "
            f"{data['total']:>8} {data['accuracy']:>9.1f}%"
        )
        total_correct += data["correct"]
        total_items += data["total"]

    overall_accuracy = (total_correct / total_items * 100) if total_items else 0
    print("-" * 75)
    print(
        f"  {'OVERALL':<25} {total_correct:>8} "
        f"{total_items:>8} {overall_accuracy:>9.1f}%"
    )
    print("=" * 75)


def print_failure_details(results: Dict[str, Dict], max_per_category: int = 20) -> None:
    """Print details of failed corrections."""
    print("\n" + "=" * 75)
    print("  FAILED CORRECTIONS (sample)")
    print("=" * 75)

    for category_name, data in results.items():
        failures = [
            (gt, ms, corr)
            for gt, ms, corr, ok in data["details"]
            if not ok
        ]
        if not failures:
            continue

        label = category_name.replace("_", " ").title()
        print(f"\n  --- {label} ({len(failures)} failures) ---")
        print(f"  {'Ground Truth':<25} {'Misspelled':<25} {'Corrected':<25}")
        print("  " + "-" * 73)
        for gt, ms, corr in failures[:max_per_category]:
            print(f"  {gt:<25} {ms:<25} {corr:<25}")
        if len(failures) > max_per_category:
            print(f"  ... and {len(failures) - max_per_category} more")


# ── Pytest Fixtures & Tests ──────────────────────────────────────────────────

@pytest.fixture(scope="module")
def spellcheck_results():
    """Run all spellcheck tests once per module."""
    return run_spellcheck_test(TOP_300_INGREDIENTS)


class TestSpellcheckAccuracy:
    """Test OCR spell correction accuracy across misspelling categories."""

    def test_one_letter_changed_accuracy(self, spellcheck_results):
        """Correcting 1 substituted letter should have high accuracy."""
        result = spellcheck_results["one_letter_changed"]
        print(
            f"\n  1 Letter Changed: {result['correct']}/{result['total']} "
            f"({result['accuracy']:.1f}%)"
        )
        # We expect high accuracy for single-character substitution
        assert result["accuracy"] >= 50.0, (
            f"1-letter-changed accuracy too low: {result['accuracy']:.1f}% "
            f"(expected >= 50%)"
        )

    def test_one_letter_removed_accuracy(self, spellcheck_results):
        """Correcting 1 deleted letter should have high accuracy."""
        result = spellcheck_results["one_letter_removed"]
        print(
            f"\n  1 Letter Removed: {result['correct']}/{result['total']} "
            f"({result['accuracy']:.1f}%)"
        )
        assert result["accuracy"] >= 50.0, (
            f"1-letter-removed accuracy too low: {result['accuracy']:.1f}% "
            f"(expected >= 50%)"
        )

    def test_two_letters_changed_accuracy(self, spellcheck_results):
        """Correcting 2 substituted letters – harder, lower threshold."""
        result = spellcheck_results["two_letters_changed"]
        print(
            f"\n  2 Letters Changed: {result['correct']}/{result['total']} "
            f"({result['accuracy']:.1f}%)"
        )
        # 2-letter changes are much harder; accept lower accuracy
        assert result["accuracy"] >= 30.0, (
            f"2-letters-changed accuracy too low: {result['accuracy']:.1f}% "
            f"(expected >= 30%)"
        )

    def test_two_letters_removed_accuracy(self, spellcheck_results):
        """Correcting 2 deleted letters – harder, lower threshold."""
        result = spellcheck_results["two_letters_removed"]
        print(
            f"\n  2 Letters Removed: {result['correct']}/{result['total']} "
            f"({result['accuracy']:.1f}%)"
        )
        assert result["accuracy"] >= 30.0, (
            f"2-letters-removed accuracy too low: {result['accuracy']:.1f}% "
            f"(expected >= 30%)"
        )

    def test_overall_accuracy(self, spellcheck_results):
        """Overall accuracy across all categories."""
        total_correct = sum(d["correct"] for d in spellcheck_results.values())
        total_items = sum(d["total"] for d in spellcheck_results.values())
        overall = (total_correct / total_items * 100) if total_items else 0

        print(f"\n  Overall: {total_correct}/{total_items} ({overall:.1f}%)")
        assert overall >= 40.0, (
            f"Overall accuracy too low: {overall:.1f}% (expected >= 40%)"
        )

    def test_print_summary(self, spellcheck_results):
        """Print the full summary table (always passes)."""
        print_summary_table(spellcheck_results)
        print_failure_details(spellcheck_results, max_per_category=15)

        # Save CSV to test output
        csv_path = PROJECT_ROOT / "tests" / "data" / "spellcheck_results.csv"
        save_results_csv(spellcheck_results, csv_path)
        print(f"\n  Detailed results saved to: {csv_path}")


# ── Standalone Execution ─────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Running spellcheck accuracy test...")
    print(f"Testing {len(TOP_300_INGREDIENTS)} ingredients × 4 categories "
          f"= {len(TOP_300_INGREDIENTS) * 4} test cases\n")

    results = run_spellcheck_test(TOP_300_INGREDIENTS)
    print_summary_table(results)
    print_failure_details(results, max_per_category=20)

    # Save CSV
    csv_path = PROJECT_ROOT / "tests" / "data" / "spellcheck_results.csv"
    save_results_csv(results, csv_path)
    print(f"\nDetailed results saved to: {csv_path}")
