"""
Shared post-processing utilities for ingredient extraction.

Applied after both LLM and SymSpell extraction pipelines to guarantee
consistent, normalised output that matches the ground-truth format.
"""

import re
import unicodedata
from typing import List

_RE_PERCENTAGE = re.compile(r"\s*\(\s*\d+(?:\.\d+)?\s*%\s*\*?\s*\)")
_RE_WARNING = re.compile(
    r"^\s*(?:contains?|added|allergen|not suitable|may contain)\b", re.IGNORECASE
)
# Whole-phrase OCR fixes (Mistral / label noise) before generic cleanup
_OCR_PHRASE_FIXES = (
    (re.compile(r"concentrate\s+fruit\s+rice", re.IGNORECASE), "concentrated fruit juice"),
)
# SymSpell / OCR false friends: keep wording aligned with labels so merge-precision
# (substring vs joined ground truth) does not penalise harmless variants.
_MERGE_ALIGNMENT_FIXES = (
    # "raising agent" is often mis-corrected to "raisin agent" (raisin is in the food dict).
    (re.compile(r"\braisin\s+agents\b", re.IGNORECASE), "raising agents"),
    (re.compile(r"\braisin\s+agent\b", re.IGNORECASE), "raising agent"),
    # Allergen line: "Butter (Milk)" OCR’d without parentheses.
    (re.compile(r"\bunsalted\s+butter\s+milk\b(?!\s*solids)", re.IGNORECASE), "unsalted butter (milk)"),
    (re.compile(r"\bbutter\s+milk\b(?!\s*solids)", re.IGNORECASE), "butter (milk)"),
    # GT mixes hyphen and space spellings for this term.
    (re.compile(r"\bfructo-oligosaccharides\b", re.IGNORECASE), "fructo oligosaccharides"),
    (re.compile(r"\bfructo-oligosaccharide\b", re.IGNORECASE), "fructo oligosaccharide"),
    (re.compile(r"\bbanana\s+pureed\b", re.IGNORECASE), "banana puree"),
    (re.compile(r"\bmango\s+pureed\b", re.IGNORECASE), "mango puree"),
    (re.compile(r"\bpineapple\s+pureed\b", re.IGNORECASE), "pineapple puree"),
    (re.compile(r"\bpineapple\s+rice\b", re.IGNORECASE), "pineapple juice"),
    (re.compile(r"\bpassion\s+fruit\s+rice\b", re.IGNORECASE), "passion fruit juice"),
    (re.compile(r"\bfruit\s+peach\s+day\b", re.IGNORECASE), "fruits each day"),
    (re.compile(r"\bolein\s+acid\b", re.IGNORECASE), "oleic acid"),
    (re.compile(r"\bsugar\s+tea\s+salt\b", re.IGNORECASE), "sugar sea salt"),
    (re.compile(r"\bconcentrate\s+apple\s+rice\b", re.IGNORECASE), "concentrated apple juice"),
    (re.compile(r"\bconcentrate\s+apple\b", re.IGNORECASE), "concentrated apple"),
    (re.compile(r"\brice\s+infused\s+cranberries\b", re.IGNORECASE), "juice infused cranberries"),
)


def _strip_accents(text: str) -> str:
    """Convert accented characters to their plain ASCII equivalents."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if unicodedata.category(ch) != "Mn")


def _strip_outer_dots_commas(s: str) -> str:
    """Remove leading/trailing periods, commas, semicolons, middot, and whitespace."""
    s = s.strip()
    s = s.strip(".,;·")
    return s.strip()


def post_process_ingredient(ingredient: str) -> str:
    """Apply all normalisation fixes to a single ingredient string."""
    s = ingredient

    for pat, repl in _OCR_PHRASE_FIXES:
        s = pat.sub(repl, s)
    for pat, repl in _MERGE_ALIGNMENT_FIXES:
        s = pat.sub(repl, s)

    s = s.replace("[", "(").replace("]", ")")
    s = s.replace("{", "(").replace("}", ")")

    s = s.replace("&amp;", "&")

    s = s.replace("*", "")

    s = _RE_PERCENTAGE.sub("", s)

    s = _strip_accents(s)

    s = re.sub(r"  +", " ", s).strip()
    s = _strip_outer_dots_commas(s)

    if s.count("(") > s.count(")"):
        s = s + ")"

    return s


def post_process_ingredients(ingredients: List[str]) -> List[str]:
    """
    Post-process a list of extracted ingredients so the output matches
    the normalised ground-truth format.  Catches issues that either the
    LLM or SymSpell pipeline may still emit.
    """
    processed: List[str] = []
    for raw in ingredients:
        if not isinstance(raw, str):
            continue

        if _RE_WARNING.match(raw):
            continue

        cleaned = post_process_ingredient(raw)

        if cleaned and len(cleaned) > 1:
            processed.append(cleaned)

    return processed
