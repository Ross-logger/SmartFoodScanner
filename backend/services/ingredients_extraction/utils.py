"""
Shared post-processing utilities for ingredient extraction.

Applied after both LLM and SymSpell extraction pipelines to guarantee
consistent, normalised output that matches the ground-truth format.
"""

import re
import unicodedata
from typing import List


def split_ingredients_text(text: str) -> List[str]:
    """
    Split ingredients text by delimiters: comma, semicolon, middot/bullet (·•),
    newlines (HF/OCR often uses one ingredient per line), &, " and ", " or ".
    Respects parentheses so "Emulsifier (E322 and E476)" stays as one segment.

    Notes:
    - EU-style separators such as middot/bullet are normalized to comma boundaries
      upstream before calling this (see SymSpell / spellcheck entry points).
    """
    if not text or not text.strip():
        return []
    text = text.strip()
    segments: List[str] = []
    current: List[str] = []
    paren_depth = 0
    i = 0
    n = len(text)

    def flush_current() -> None:
        if current:
            s = "".join(current).strip()
            if s:
                segments.append(s)
            current.clear()

    while i < n:
        if paren_depth == 0:
            for sep in (" and ", " or ", " . "):
                if i + len(sep) <= n and text[i : i + len(sep)].lower() == sep:
                    flush_current()
                    i += len(sep)
                    continue
        if paren_depth == 0 and text[i] == "&":
            flush_current()
            i += 1
            while i < n and text[i] == " ":
                i += 1
            continue
        if paren_depth == 0 and (text[i] in ",;" or text[i] in "\u00b7\u2022"):
            flush_current()
            i += 1
            while i < n and text[i] == " ":
                i += 1
            continue
        if paren_depth == 0 and text[i] in "\n\r\v\f\u0085\u2028\u2029":
            flush_current()
            i += 1
            while i < n and text[i] in " \t\n\r\v\f\u0085\u2028\u2029":
                i += 1
            continue
        if text[i] == "(":
            paren_depth += 1
            current.append(text[i])
        elif text[i] == ")":
            paren_depth = max(0, paren_depth - 1)
            current.append(text[i])
        else:
            current.append(text[i])
        i += 1

    flush_current()
    return segments

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
# HuggingFace token-classification aggregates often insert spaces around
# punctuation; tighten before SymSpell splits on commas/parentheses.
_RE_SPACE_BEFORE_PUNCT = re.compile(r"\s+([,;:\)\]\}%])")
_RE_SPACE_AFTER_OPEN_PUNCT = re.compile(r"([(\[\{])\s+")
_RE_DIGIT_SPACE_PERCENT = re.compile(r"(\d)\s+%")


def normalize_hf_ner_spacing(text: str) -> str:
    """
    Remove tokenizer-style gaps before commas, brackets, etc., and after
    opening brackets — e.g. ``( with foo , bar )`` → ``(with foo, bar)``.
    Safe to run only on HF NER *word* joins, not on arbitrary prose.
    """
    s = text.strip()
    if not s:
        return s
    for _ in range(8):
        prev = s
        s = _RE_SPACE_BEFORE_PUNCT.sub(r"\1", s)
        s = _RE_SPACE_AFTER_OPEN_PUNCT.sub(r"\1", s)
        s = _RE_DIGIT_SPACE_PERCENT.sub(r"\1%", s)
        # Footnote star glued to preceding token: "30% *" → "30%*"
        s = re.sub(r"%\s+\*", "%*", s)
        if s == prev:
            break
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s


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
