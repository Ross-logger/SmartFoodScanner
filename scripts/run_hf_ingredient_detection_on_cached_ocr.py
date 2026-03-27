#!/usr/bin/env python3
"""
Run OpenFoodFacts ``openfoodfacts/ingredient-detection`` on sample OCR texts and
save structured results for inspection.

Default input: ``tests/data/cached_mistral_ocr_results.json``
Default output: ``tests/data/hf_ingredient_detection_cached_ocr_sample.json``

The model is token classification with labels only:
  O, B-ING, I-ING

There is **no** separate entity type for measurement units (g, %, ml) or
separators; those characters appear in OCR gaps between ING spans or inside
aggregated ING text.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_CACHE = PROJECT_ROOT / "tests" / "data" / "cached_mistral_ocr_results.json"
DEFAULT_OUT = PROJECT_ROOT / "tests" / "data" / "hf_ingredient_detection_cached_ocr_sample.json"

MODEL_ANALYSIS = {
    "model_id": "openfoodfacts/ingredient-detection",
    "task": "token-classification (BIO)",
    "labels": {
        "O": "Outside any ingredient mention",
        "B-ING": "Start of an ingredient span",
        "I-ING": "Continuation of the same ingredient span",
    },
    "ingredient_unit_meaning": (
        "Each contiguous ING span (after aggregation) is one 'ingredient unit' "
        "in the sense of one named chunk the model groups together. "
        "The model does **not** emit a distinct label for pack units (e.g. g, ml) "
        "or for list separators; percentages and units usually sit inside an ING "
        "span or in non-ING (O) gaps, depending on tokenization and training."
    ),
}


def _gap_between(
    ocr_text: str, prev_end: int | None, start: int, end: int
) -> Tuple[str | None, str]:
    """Return (gap_slice_or_none, span_slice) using OCR indices."""
    span = ocr_text[start:end]
    if prev_end is None:
        return None, span
    return ocr_text[prev_end:start], span


def _collect_ing_spans(ocr_text: str, results: List[dict]) -> List[Dict[str, Any]]:
    """ING-only spans sorted by start, with OCR gaps between consecutive spans."""
    raw: List[Tuple[int, int, str]] = []
    for r in results:
        if r.get("entity_group") != "ING":
            continue
        s, e = r.get("start"), r.get("end")
        if s is None or e is None:
            continue
        s, e = int(s), int(e)
        if e <= s or s < 0 or e > len(ocr_text):
            continue
        raw.append((s, e, str(r.get("word", ""))))

    raw.sort(key=lambda x: x[0])
    merged_ranges: List[List[int]] = []
    for s, e, _ in raw:
        if not merged_ranges or s > merged_ranges[-1][1]:
            merged_ranges.append([s, e])
        else:
            merged_ranges[-1][1] = max(merged_ranges[-1][1], e)

    out: List[Dict[str, Any]] = []
    prev_end: int | None = None
    for s, e in merged_ranges:
        gap, text_slice = _gap_between(ocr_text, prev_end, s, e)
        entry: Dict[str, Any] = {
            "start": s,
            "end": e,
            "text": text_slice,
            "gap_before": gap,
            "gap_before_repr": repr(gap) if gap is not None else None,
        }
        out.append(entry)
        prev_end = e
    return out


def run_sample(
    ner: Any,
    image_key: str,
    ocr_text: str,
) -> Dict[str, Any]:
    results: List[dict] = ner(ocr_text)
    entity_groups = sorted({r.get("entity_group") for r in results})

    ing_spans = _collect_ing_spans(ocr_text, results)

    # Full raw entities (can be long — cap list length in summary)
    raw_entities = []
    for r in results:
        sc = r.get("score")
        if sc is not None:
            sc = float(sc)
        raw_entities.append(
            {
                "entity_group": r.get("entity_group"),
                "word": r.get("word"),
                "start": r.get("start"),
                "end": r.get("end"),
                "score": sc,
            }
        )

    from backend.services.ingredients_extraction.hf_section_detection import (
        _merge_ing_spans_from_ocr,
        normalize_hf_ner_spacing,
    )

    merged = _merge_ing_spans_from_ocr(ocr_text, results)
    merged_norm = normalize_hf_ner_spacing(merged) if merged.strip() else merged

    return {
        "image_key": image_key,
        "ocr_char_len": len(ocr_text),
        "ocr_preview_200_chars": ocr_text[:200].replace("\n", "\\n"),
        "entity_groups_present": entity_groups,
        "ing_span_count": len(ing_spans),
        "ing_spans": ing_spans,
        "merged_ingredient_text": merged_norm,
        "raw_entity_count": len(raw_entities),
        "raw_entities": raw_entities,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_CACHE,
        help="JSON object: filename -> ocr_text",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUT,
        help="Where to write the report JSON",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of images to process (stable order: sorted keys)",
    )
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        cache: Dict[str, str] = json.load(f)

    # Preserve order of keys as stored in the JSON file (often in1, in2, … then IMG_*).
    all_keys = list(cache.keys())
    keys = all_keys[: max(0, args.limit)]

    from transformers import pipeline as hf_pipeline

    from backend import settings

    model_name = settings.HF_INGREDIENT_DETECTION_MODEL
    print(f"Loading {model_name} …")
    ner = hf_pipeline(
        "token-classification",
        model=model_name,
        aggregation_strategy="simple",
    )

    samples: List[Dict[str, Any]] = []
    for k in keys:
        text = cache[k] or ""
        print(f"  {k} ({len(text)} chars)")
        samples.append(run_sample(ner, k, text))

    payload = {
        "model_analysis": MODEL_ANALYSIS,
        "source_file": str(args.input.relative_to(PROJECT_ROOT)),
        "sample_count": len(samples),
        "image_keys": keys,
        "samples": samples,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Wrote {args.output.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
