#!/usr/bin/env python3
"""
Build tests/data/true_ingredients_symspell.json from true_ingredients.json.

Compound label lines like
  Breadcrumbs (Wheat Flour, Yeast, Salt, Preservative (INS 282))
are expanded to atomic ingredient phrases: Wheat Flour, Yeast, Salt, etc.
The outer composite name (Breadcrumbs) is dropped when the parentheses hold a
multi-part list, matching how SymSpell-style extractors surface sub-ingredients.

Single-parenthetical qualifiers (e.g. Permitted Stabilizer (E 460(i)),
Bengal Gram Flour (Besan)) stay as one string.

If a colon appears in the text before the first ``(``, the whole line is kept
(e.g. ``Natural Colour: Anthocyanins (from Grape, ...)``) so category labels are
not stripped incorrectly.

EU-style functional headings followed by a colon (e.g. ``Emulsifier: E471``,
``Raising Agent: E450, E501``) drop the heading; comma-separated tails become
separate entries. Headings not in the allow-list (e.g. ``Natural Colour:``) are
left unchanged.

Usage:
  python scripts/build_true_ingredients_symspell.py
  python scripts/build_true_ingredients_symspell.py -o path/to/out.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SRC = PROJECT_ROOT / "tests" / "data" / "true_ingredients.json"
DEFAULT_DST = PROJECT_ROOT / "tests" / "data" / "true_ingredients_symspell.json"

# Normalised (lowercase, single spaces) label before ":" on pack copy.
_FUNCTIONAL_HEADS = frozenset(
    {
        "acid",
        "acids",
        "acidity regulator",
        "acidity regulators",
        "antioxidant",
        "antioxidants",
        "cultures",
        "emulsifier",
        "emulsifiers",
        "gelling agent",
        "gelling agents",
        "glazing agent",
        "glazing agents",
        "humectant",
        "humectants",
        "preservative",
        "preservatives",
        "raising agent",
        "raising agents",
        "stabiliser",
        "stabilisers",
        "stabilizer",
        "stabilizers",
    }
)


def _split_top_level_commas(s: str) -> List[str]:
    parts: List[str] = []
    depth = 0
    start = 0
    for i, c in enumerate(s):
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif c == "," and depth == 0:
            chunk = s[start:i].strip()
            if chunk:
                parts.append(chunk)
            start = i + 1
    tail = s[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def _matching_close(s: str, open_idx: int) -> int | None:
    depth = 0
    for i in range(open_idx, len(s)):
        c = s[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i
    return None


def strip_functional_label_split(s: str) -> List[str]:
    """
    Remove whitelisted functional headings before ':' and split the remainder on
    top-level commas (e.g. 'Raising Agent: E450, E501' -> E450, E501).
    """
    s = s.strip()
    if not s:
        return []
    if ":" not in s:
        return [s]
    idx = s.index(":")
    head = " ".join(s[:idx].strip().lower().split())
    tail = s[idx + 1 :].strip()
    if head not in _FUNCTIONAL_HEADS:
        return [s]
    if not tail:
        return []
    parts = _split_top_level_commas(tail)
    return [p.strip() for p in parts if p.strip()]


def expand_compound_phrase(label: str) -> List[str]:
    """
    Split composite ingredient lines into atomic phrases for symspell evaluation.

    If the first '(...)' group contains multiple top-level comma segments,
    return the recursively expanded segments (outer name dropped). Otherwise
    return the original phrase as a single item.
    """
    label = label.strip()
    if not label:
        return []

    open_idx = label.find("(")
    if open_idx == -1:
        return strip_functional_label_split(label)

    # Lines like "Natural Colour: X (from A, B, C)" use parens for sources, not a
    # composite product to unwrap; keep the full phrase.
    if ":" in label[:open_idx]:
        return strip_functional_label_split(label)

    close_idx = _matching_close(label, open_idx)
    if close_idx is None:
        return strip_functional_label_split(label)

    inner = label[open_idx + 1 : close_idx].strip()
    inner_parts = _split_top_level_commas(inner)

    if len(inner_parts) > 1:
        out: List[str] = []
        for p in inner_parts:
            out.extend(expand_compound_phrase(p))
        return out

    return strip_functional_label_split(label)


def dedupe_preserve_order(items: List[str]) -> List[str]:
    seen_set: set[str] = set()
    out: List[str] = []
    for x in items:
        t = x.strip()
        if not t:
            continue
        k = t.lower()
        if k not in seen_set:
            seen_set.add(k)
            out.append(t)
    return out


def build_entries(src: Path) -> list:
    data = json.loads(src.read_text(encoding="utf-8"))
    result = []
    for entry in data:
        image = entry["image"]
        raw = entry.get("true_ingredients") or []
        expanded: List[str] = []
        for phrase in raw:
            expanded.extend(expand_compound_phrase(phrase))
        result.append(
            {
                "image": image,
                "true_ingredients": dedupe_preserve_order(expanded),
            }
        )
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "-i",
        "--input",
        type=Path,
        default=DEFAULT_SRC,
        help=f"Source true_ingredients JSON. Default: {DEFAULT_SRC}",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_DST,
        help=f"Output path. Default: {DEFAULT_DST}",
    )
    args = p.parse_args()

    if not args.input.is_file():
        print(f"Error: input not found: {args.input}", file=sys.stderr)
        return 1

    built = build_entries(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(built, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(built)} entries to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
