"""
EasyOCR confidence helpers for downstream pipelines.

EasyOCR returns one confidence score per detection box (often a full text line).
When that score is high, SymSpell correction can be skipped for segments that
originate from that box (see ``build_easyocr_skip_symspell_normalized_keys``).
"""

from __future__ import annotations

import re
from typing import AbstractSet, FrozenSet, List, Tuple

# Same delimiter idea as ingredient splitting (comma, semicolon, EU middot/bullet).
_SPLIT_LINE_FOR_SKIP_KEYS = re.compile(r"[,;\u00b7\u2022]+")


def normalize_for_symspell_skip_key(s: str) -> str:
    """Lowercase, strip, collapse internal whitespace — stable key for set lookup."""
    t = (s or "").strip().lower()
    return re.sub(r"\s+", " ", t)


def build_easyocr_skip_symspell_normalized_keys(
    lines: List[Tuple[str, float]],
    *,
    min_confidence: float = 0.9,
) -> FrozenSet[str]:
    """
    Build normalized segment keys that should not be passed through SymSpell.

    For each EasyOCR line with ``confidence >= min_confidence``:
    - the full line (normalized), and
    - each piece after splitting on comma / semicolon / middot / bullet

    Split pieces shorter than 2 characters are omitted (avoids noisy matches).
    """
    out: set[str] = set()
    for text, conf in lines:
        if conf < min_confidence:
            continue
        full = normalize_for_symspell_skip_key(text)
        if full:
            out.add(full)
        for part in _SPLIT_LINE_FOR_SKIP_KEYS.split(text):
            p = normalize_for_symspell_skip_key(part)
            if len(p) > 1:
                out.add(p)
    return frozenset(out)


def should_skip_symspell_for_segment(
    segment: str, skip_keys: AbstractSet[str] | None
) -> bool:
    """True if this ingredient segment was read with high EasyOCR confidence."""
    if not skip_keys:
        return False
    key = normalize_for_symspell_skip_key(segment)
    return bool(key) and key in skip_keys
