"""
Conservative OCR ingredient corrector.

Dictionary-constrained, safe, deterministic.  Designed to fix common OCR
errors in food ingredient text *without* hallucinating new ingredients.

Pipeline position: runs **after** merge (box reconstruction) and splitting,
**before** final normalization / output.

Correction strategy (in order of priority):
    1. Exact alias lookup
    2. Exact vocabulary membership
    3. Conservative SymSpell correction (edit distance <= 2)
    4. RapidFuzz best match (score >= 90, very strict)
    5. Fall through: keep original candidate unchanged
"""

import logging
import re
from typing import FrozenSet, List, Optional, Set

from rapidfuzz import fuzz, process as rf_process
from symspellpy import SymSpell, Verbosity

from backend.services.ingredients_extraction.data import (
    E_NUMBERS,
    FOOD_INGREDIENTS,
    INGREDIENT_ALIASES,
    VERY_COMMON_INGREDIENTS,
)
from backend.services.ingredients_extraction.non_ingredient_filter import (
    is_allergen_warning_segment,
    is_garbage_text,
    is_stop_pattern,
)
from backend.services.ingredients_extraction.utils import (
    post_process_ingredients,
    split_ingredients_text,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Vocabulary singleton
# ---------------------------------------------------------------------------
_vocabulary: Optional[FrozenSet[str]] = None
_vocab_list: Optional[List[str]] = None


def _build_vocabulary() -> FrozenSet[str]:
    """Build the canonical ingredient vocabulary (lowercase) from all sources."""
    global _vocabulary, _vocab_list
    if _vocabulary is not None:
        return _vocabulary

    vocab: Set[str] = set()

    for term in FOOD_INGREDIENTS:
        vocab.add(term.lower().strip())

    for term in VERY_COMMON_INGREDIENTS:
        vocab.add(term.lower().strip())

    for code, name in E_NUMBERS.items():
        vocab.add(code.lower().strip())
        vocab.add(name.lower().strip())

    for canonical in INGREDIENT_ALIASES.values():
        vocab.add(canonical.lower().strip())

    vocab.discard("")
    _vocabulary = frozenset(vocab)
    _vocab_list = sorted(vocab)
    logger.info("OCR corrector vocabulary: %d terms", len(_vocabulary))
    return _vocabulary


def _get_vocab_list() -> List[str]:
    """Sorted list form of vocabulary (for RapidFuzz choices)."""
    _build_vocabulary()
    assert _vocab_list is not None
    return _vocab_list


# ---------------------------------------------------------------------------
# SymSpell singleton (food-specific, reuses same dictionary as main pipeline)
# ---------------------------------------------------------------------------
_corrector_sym_spell: Optional[SymSpell] = None


def _get_sym_spell() -> SymSpell:
    global _corrector_sym_spell
    if _corrector_sym_spell is not None:
        return _corrector_sym_spell

    sym = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)

    for term in VERY_COMMON_INGREDIENTS:
        sym.create_dictionary_entry(term.lower(), 10_000_000)
    for term in FOOD_INGREDIENTS:
        sym.create_dictionary_entry(term.lower(), 1_000_000)
    for code, name in E_NUMBERS.items():
        sym.create_dictionary_entry(code.lower(), 1_000_000)
        sym.create_dictionary_entry(name.lower(), 1_000_000)

    _corrector_sym_spell = sym
    return sym


# ---------------------------------------------------------------------------
# E-number regex
# ---------------------------------------------------------------------------
_RE_E_NUMBER = re.compile(
    r"^e[\s\-]*(\d{3,4}[a-z]?)$", re.IGNORECASE
)

_RE_E_NUMBER_INLINE = re.compile(
    r"\be[\s\-]+(\d{3,4}[a-z]?)\b", re.IGNORECASE
)


def _normalize_e_number(text: str) -> str:
    """Normalize an E-number string: 'E 330', 'e-330', 'E330' -> 'e330'."""
    m = _RE_E_NUMBER.match(text.strip())
    if m:
        return f"e{m.group(1).lower()}"
    return text


# ---------------------------------------------------------------------------
# OCR text cleanup
# ---------------------------------------------------------------------------
_RE_MULTI_SPACE = re.compile(r"\s+")
_RE_STRAY_PUNCT = re.compile(r"[^\w\s(),.:;/&%\-'+]")


def cleanup_ocr_text(text: str) -> str:
    """
    Pre-process a single candidate ingredient string for correction.

    - Lowercase
    - Normalize whitespace
    - Remove stray punctuation that isn't meaningful in ingredient context
    - Fix E-number spacing (``e 330`` -> ``e330``)
    """
    s = text.strip().lower()

    s = _RE_E_NUMBER_INLINE.sub(lambda m: f"e{m.group(1)}", s)

    s = _RE_STRAY_PUNCT.sub("", s)

    s = _RE_MULTI_SPACE.sub(" ", s).strip()
    return s


# ---------------------------------------------------------------------------
# Junk detection
# ---------------------------------------------------------------------------

_JUNK_SUBSTRINGS = (
    "nutrition facts", "nutrition information", "nutritional information",
    "supplement facts", "daily value", "amount per serving",
    "serving size", "per 100g", "per 100ml",
    "manufactured by", "manufactured for", "distributed by",
    "produced by", "packed by", "imported by",
    "made in", "product of", "country of origin",
    "store in a cool", "store in a dry", "keep refrigerated",
    "keep frozen", "once opened", "refrigerate after opening",
    "best before", "use by", "use before", "expiry date",
    "batch code", "lot number",
    "suitable for", "not suitable for",
    "may contain", "may also contain", "traces of",
    "for allergens", "allergen advice", "allergen information",
    "https://", "http://", "www.", ".com", ".org", ".net",
    "contact us", "customer service", "consumer care",
    "p.o. box", "po box", "telephone", "tel.", "fax:",
)


def is_junk_candidate(text: str) -> bool:
    """
    Check whether a candidate string is obviously not an ingredient.

    Conservative: only removes clear non-ingredient text.
    """
    s = text.strip()
    if not s or len(s) < 2:
        return True

    s_lower = s.lower()

    if any(j in s_lower for j in _JUNK_SUBSTRINGS):
        return True

    if is_garbage_text(s):
        return True

    if is_stop_pattern(s):
        return True

    if is_allergen_warning_segment(s):
        return True

    digits = sum(c.isdigit() for c in s)
    alpha = sum(c.isalpha() for c in s)
    if alpha == 0 and digits > 0:
        return True

    if len(s) > 80:
        tl = s_lower
        if any(w in tl for w in (
            "lifestyle", "immune system", "contributes to normal",
            "deliciously", "healthy variety", "differently coloured",
        )):
            return True

    return False


# ---------------------------------------------------------------------------
# Single-candidate correction
# ---------------------------------------------------------------------------

# Known false-friend pairs: never correct FROM -> TO
_DANGEROUS_CORRECTIONS = {
    ("cumin", "curcumin"),
    ("caseinate", "cashews"),
    ("casein", "cashews"),
    ("acid", "citric acid"),
    ("starch", "cornstarch"),
    ("oil", "olive oil"),
    ("salt", "malt"),
    ("malt", "salt"),
    ("tea", "sea"),
    ("sea", "tea"),
    ("yam", "yeast"),
    ("raisin", "raising"),
    ("finger", "ginger"),
    ("vitamins", "vitamin c"),
    ("chloride", "chlorine"),
}


def _is_dangerous_correction(original: str, corrected: str) -> bool:
    return (original.lower(), corrected.lower()) in _DANGEROUS_CORRECTIONS


def correct_single_candidate(
    candidate: str,
    vocabulary: FrozenSet[str],
    sym_spell: SymSpell,
    vocab_list: List[str],
    *,
    fuzzy_threshold: int = 90,
) -> str:
    """
    Attempt to correct a single ingredient candidate.

    Returns the corrected string, or the original if confidence is low.
    """
    cleaned = cleanup_ocr_text(candidate)
    if not cleaned or len(cleaned) < 2:
        return cleaned or candidate

    # 1. Exact alias lookup
    alias_hit = INGREDIENT_ALIASES.get(cleaned)
    if alias_hit:
        return alias_hit

    # 2. Exact vocabulary match -- already correct
    if cleaned in vocabulary:
        return cleaned

    # 3. E-number: handle via regex, not fuzzy
    e_norm = _normalize_e_number(cleaned)
    if e_norm != cleaned and e_norm in vocabulary:
        return e_norm

    # 4. Very short tokens: don't auto-correct (too risky)
    if len(cleaned) <= 3:
        return cleaned

    # 5. SymSpell lookup (conservative: distance <= 2)
    suggestions = sym_spell.lookup(
        cleaned, Verbosity.CLOSEST, max_edit_distance=2
    )
    if suggestions:
        best = suggestions[0]
        max_dist = 1 if len(cleaned) <= 5 else 2
        if best.distance <= max_dist and best.term in vocabulary:
            if not _is_dangerous_correction(cleaned, best.term):
                return best.term

    # 6. SymSpell word segmentation for compound terms
    seg = sym_spell.word_segmentation(cleaned)
    if seg and seg.corrected_string:
        seg_text = seg.corrected_string
        input_len = len(cleaned.replace(" ", ""))
        error_rate = seg.distance_sum / max(1, input_len)
        if error_rate <= 0.12 and seg_text in vocabulary:
            if not _is_dangerous_correction(cleaned, seg_text):
                return seg_text

    # 7. RapidFuzz against vocabulary (very strict threshold)
    match = rf_process.extractOne(
        cleaned,
        vocab_list,
        scorer=fuzz.ratio,
        score_cutoff=fuzzy_threshold,
    )
    if match is not None:
        matched_term, score, _idx = match
        if not _is_dangerous_correction(cleaned, matched_term):
            if len(cleaned) > 4 or score >= 95:
                return matched_term

    # 8. Word-by-word correction fallback
    #    When the candidate is a multi-word phrase that didn't match as a
    #    whole, correct each word individually against the vocabulary.
    #    This handles cases like "contains cluten" -> "contains gluten"
    #    where the merged OCR text lacks delimiters.
    words = cleaned.split()
    if len(words) > 1:
        corrected_words: List[str] = []
        changed = False
        for word in words:
            if len(word) <= 3:
                corrected_words.append(word)
                continue
            max_dist = 1 if len(word) <= 5 else 2
            w_suggestions = sym_spell.lookup(
                word, Verbosity.CLOSEST, max_edit_distance=max_dist
            )
            if w_suggestions and w_suggestions[0].distance <= max_dist:
                sug = w_suggestions[0].term
                if not _is_dangerous_correction(word, sug):
                    if sug != word:
                        changed = True
                    corrected_words.append(sug)
                    continue
            corrected_words.append(word)
        if changed:
            return " ".join(corrected_words)

    # 9. Fall through: keep original
    return cleaned


# ---------------------------------------------------------------------------
# Candidate list correction (public API)
# ---------------------------------------------------------------------------

def correct_ingredient_list(
    candidates: List[str],
    *,
    use_ocr_corrector: bool = True,
) -> List[str]:
    """
    Process a list of parsed ingredient candidates through the full
    correction pipeline.

    Steps:
        1. Remove obvious junk
        2. OCR cleanup per candidate
        3. Correct each candidate (if ``use_ocr_corrector`` is True)
        4. Normalize via alias mapping
        5. Deduplicate (order-preserving)
        6. Post-process (shared pipeline)

    Args:
        candidates: Raw split ingredient strings.
        use_ocr_corrector: When False, skip SymSpell/RapidFuzz correction
            but still apply cleanup, junk removal, and deduplication.

    Returns:
        Cleaned, corrected, deduplicated ingredient list.
    """
    if not candidates:
        return []

    vocabulary = _build_vocabulary()
    vocab_list = _get_vocab_list()
    sym_spell = _get_sym_spell()

    corrected: List[str] = []

    for raw in candidates:
        raw = raw.strip()
        if not raw:
            continue

        # Step 1: junk filter
        if is_junk_candidate(raw):
            continue

        # Step 2+3: cleanup and correct
        if use_ocr_corrector:
            fixed = correct_single_candidate(
                raw, vocabulary, sym_spell, vocab_list
            )
        else:
            fixed = cleanup_ocr_text(raw)

        if not fixed or len(fixed) < 2:
            continue

        # Step 4: alias normalization (catch any remaining aliases)
        alias_hit = INGREDIENT_ALIASES.get(fixed)
        if alias_hit:
            fixed = alias_hit

        corrected.append(fixed)

    # Step 5: deduplicate (preserve first occurrence order)
    seen: Set[str] = set()
    deduped: List[str] = []
    for item in corrected:
        key = item.lower().strip()
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    # Step 6: shared post-processing (percentages, brackets, accents, etc.)
    result = post_process_ingredients(deduped)
    return result
