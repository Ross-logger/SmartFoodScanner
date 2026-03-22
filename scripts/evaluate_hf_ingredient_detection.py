#!/usr/bin/env python3
"""
Evaluate the OpenFoodFacts ingredient-detection HuggingFace model
against our current regex-based extract_ingredients_section().

For each sample in true_ingredients.json (which already has ocr_text),
we run:
  A) Our regex pipeline:  extract_ingredients_section → split → spellcheck
  B) HF NER model:        token classification → extract ING spans → split → spellcheck

Then compare both against ground truth using exact/fuzzy/merge metrics.
No OCR is re-run — we use the stored ocr_text from true_ingredients.json.

Usage:
  python scripts/evaluate_hf_ingredient_detection.py
  python scripts/evaluate_hf_ingredient_detection.py --limit 30
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.ingredients_extraction.non_ingredient_filter import (
    extract_ingredients_section,
)
from backend.services.ingredients_extraction.symspell_extraction import (
    extract_ingredients,
)

GROUND_TRUTH_PATH = PROJECT_ROOT / "tests" / "data" / "true_ingredients.json"
OUTPUT_PATH = PROJECT_ROOT / "tests" / "data" / "hf_model_evaluation.json"

_PCT_RE = re.compile(r"\s*\(\d+(?:\.\d+)?%\)|\s*\(\d+(?:\.\d+)?%|\s*\d+(?:\.\d+)?%\)?")


def normalize(ingredients: List[str]) -> List[str]:
    out = []
    for s in ingredients:
        s = _PCT_RE.sub("", s.lower().strip()).strip().rstrip(",")
        if s:
            out.append(s)
    return out


# ─── Metrics ────────────────────────────────────────────────────────────────

def exact_precision(extracted: List[str], truth: List[str]) -> float:
    if not extracted:
        return 1.0 if not truth else 0.0
    matched = sum(1 for e in extracted if e in truth)
    return matched / len(extracted)


def exact_recall(extracted: List[str], truth: List[str]) -> float:
    if not truth:
        return 1.0
    matched = sum(1 for t in truth if t in extracted)
    return matched / len(truth)


def f1(p: float, r: float) -> float:
    return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


def fuzzy_score(a: str, b: str) -> float:
    """Simple character-level similarity (Jaccard on bigrams)."""
    if a == b:
        return 1.0
    if len(a) < 2 or len(b) < 2:
        return 1.0 if a == b else 0.0
    bg_a = set(a[i:i+2] for i in range(len(a)-1))
    bg_b = set(b[i:i+2] for i in range(len(b)-1))
    inter = bg_a & bg_b
    union = bg_a | bg_b
    return len(inter) / len(union) if union else 0.0


def fuzzy_precision(extracted: List[str], truth: List[str], threshold: float = 0.8) -> float:
    if not extracted:
        return 1.0 if not truth else 0.0
    matched = 0
    for e in extracted:
        if any(fuzzy_score(e, t) >= threshold for t in truth):
            matched += 1
    return matched / len(extracted)


def fuzzy_recall(extracted: List[str], truth: List[str], threshold: float = 0.8) -> float:
    if not truth:
        return 1.0
    matched = 0
    for t in truth:
        if any(fuzzy_score(t, e) >= threshold for e in extracted):
            matched += 1
    return matched / len(truth)


def merge_text(items: List[str]) -> str:
    return " ".join(items).lower()


def merge_recall(extracted: List[str], truth: List[str]) -> float:
    if not truth:
        return 1.0
    merged = merge_text(extracted)
    found = sum(1 for t in truth if t in merged)
    return found / len(truth)


def merge_precision(extracted: List[str], truth: List[str]) -> float:
    if not extracted:
        return 1.0 if not truth else 0.0
    merged = merge_text(truth)
    found = sum(1 for e in extracted if e in merged)
    return found / len(extracted)


# ─── HuggingFace Model ─────────────────────────────────────────────────────

def load_hf_model():
    """Load the openfoodfacts/ingredient-detection NER pipeline."""
    from transformers import pipeline as hf_pipeline
    print("Loading openfoodfacts/ingredient-detection model...")
    t0 = time.time()
    ner = hf_pipeline(
        "token-classification",
        model="openfoodfacts/ingredient-detection",
        aggregation_strategy="simple",
    )
    print(f"  Model loaded in {time.time() - t0:.1f}s")
    return ner


def extract_section_with_hf(ner_pipeline, ocr_text: str) -> str:
    """
    Run the HF NER model on OCR text and return the detected
    ingredient section(s) as a single string.
    """
    if not ocr_text or not ocr_text.strip():
        return ""

    results = ner_pipeline(ocr_text)

    ing_spans = [r for r in results if r["entity_group"] == "ING"]
    if not ing_spans:
        return ""

    texts = []
    for span in ing_spans:
        text = ocr_text[span["start"]:span["end"]].strip()
        if text:
            texts.append(text)

    return " ".join(texts)


def split_and_correct(section_text: str) -> List[str]:
    """
    Run the SymSpell splitting + correction pipeline on a section of text.
    Reuses the same logic as extract_ingredients but starts from a
    pre-detected section instead of running our regex section detection.
    """
    if not section_text or not section_text.strip():
        return []
    return extract_ingredients(section_text)


# ─── Main evaluation ───────────────────────────────────────────────────────

def evaluate(limit: Optional[int] = None) -> Dict[str, Any]:
    with open(GROUND_TRUTH_PATH, encoding="utf-8") as f:
        samples = json.load(f)

    if limit:
        samples = samples[:limit]

    ner = load_hf_model()

    results = []
    totals = {
        "regex": {"ep": 0, "er": 0, "ef": 0, "fp": 0, "fr": 0, "ff": 0, "mp": 0, "mr": 0, "mf": 0},
        "hf":    {"ep": 0, "er": 0, "ef": 0, "fp": 0, "fr": 0, "ff": 0, "mp": 0, "mr": 0, "mf": 0},
    }
    n = len(samples)

    for i, sample in enumerate(samples):
        image = sample["image"]
        ocr_text = sample.get("ocr_text", "")
        truth = normalize(sample.get("true_ingredients", []))

        # --- Method A: Our regex pipeline ---
        regex_section = extract_ingredients_section(ocr_text)
        regex_ingredients = normalize(extract_ingredients(ocr_text))

        # --- Method B: HF NER model ---
        hf_section = extract_section_with_hf(ner, ocr_text)
        hf_ingredients = normalize(split_and_correct(hf_section))

        # --- Compute metrics for both ---
        def metrics_for(extracted):
            ep = exact_precision(extracted, truth)
            er = exact_recall(extracted, truth)
            ef = f1(ep, er)
            fp = fuzzy_precision(extracted, truth)
            fr_ = fuzzy_recall(extracted, truth)
            ff = f1(fp, fr_)
            mp = merge_precision(extracted, truth)
            mr = merge_recall(extracted, truth)
            mf = f1(mp, mr)
            return {
                "exact":  {"precision": round(ep, 4), "recall": round(er, 4), "f1": round(ef, 4)},
                "fuzzy":  {"precision": round(fp, 4), "recall": round(fr_, 4), "f1": round(ff, 4)},
                "merge":  {"precision": round(mp, 4), "recall": round(mr, 4), "f1": round(mf, 4)},
            }

        r_metrics = metrics_for(regex_ingredients)
        h_metrics = metrics_for(hf_ingredients)

        for key in ("ep", "er", "ef", "fp", "fr", "ff", "mp", "mr", "mf"):
            full_key = {"ep": ("exact","precision"), "er": ("exact","recall"), "ef": ("exact","f1"),
                        "fp": ("fuzzy","precision"), "fr": ("fuzzy","recall"), "ff": ("fuzzy","f1"),
                        "mp": ("merge","precision"), "mr": ("merge","recall"), "mf": ("merge","f1")}[key]
            totals["regex"][key] += r_metrics[full_key[0]][full_key[1]]
            totals["hf"][key]    += h_metrics[full_key[0]][full_key[1]]

        entry = {
            "image": image,
            "ocr_text": ocr_text,
            "true_ingredients": truth,
            "regex": {
                "section_text": regex_section,
                "extracted_ingredients": regex_ingredients,
                "count": len(regex_ingredients),
                **r_metrics,
            },
            "hf_model": {
                "section_text": hf_section,
                "extracted_ingredients": hf_ingredients,
                "count": len(hf_ingredients),
                **h_metrics,
            },
            "ground_truth_count": len(truth),
        }
        results.append(entry)

        tag = ""
        if h_metrics["exact"]["f1"] > r_metrics["exact"]["f1"] + 0.05:
            tag = " << HF WINS"
        elif r_metrics["exact"]["f1"] > h_metrics["exact"]["f1"] + 0.05:
            tag = " << REGEX WINS"

        print(
            f"  [{i+1}/{n}] {image:<12}  "
            f"Regex F1={r_metrics['exact']['f1']:.2f}  "
            f"HF F1={h_metrics['exact']['f1']:.2f}"
            f"{tag}"
        )

    # --- Summary ---
    def avg(method, key):
        return round(totals[method][key] / n, 4) if n else 0

    summary = {
        "total_samples": n,
        "regex_pipeline": {
            "exact":  {"precision": avg("regex","ep"), "recall": avg("regex","er"), "f1": avg("regex","ef")},
            "fuzzy":  {"precision": avg("regex","fp"), "recall": avg("regex","fr"), "f1": avg("regex","ff")},
            "merge":  {"precision": avg("regex","mp"), "recall": avg("regex","mr"), "f1": avg("regex","mf")},
        },
        "hf_model": {
            "exact":  {"precision": avg("hf","ep"), "recall": avg("hf","er"), "f1": avg("hf","ef")},
            "fuzzy":  {"precision": avg("hf","fp"), "recall": avg("hf","fr"), "f1": avg("hf","ff")},
            "merge":  {"precision": avg("hf","mp"), "recall": avg("hf","mr"), "f1": avg("hf","mf")},
        },
    }

    # Count wins
    regex_wins = sum(1 for r in results if r["regex"]["exact"]["f1"] > r["hf_model"]["exact"]["f1"])
    hf_wins    = sum(1 for r in results if r["hf_model"]["exact"]["f1"] > r["regex"]["exact"]["f1"])
    ties       = n - regex_wins - hf_wins
    summary["wins"] = {"regex": regex_wins, "hf_model": hf_wins, "ties": ties}

    return {"summary": summary, "details": results}


def print_summary(data: Dict[str, Any]):
    s = data["summary"]
    n = s["total_samples"]

    print("\n" + "=" * 90)
    print("  REGEX PIPELINE  vs  HF openfoodfacts/ingredient-detection")
    print(f"  Samples: {n}")
    print("=" * 90)

    for metric_type in ("exact", "fuzzy", "merge"):
        r = s["regex_pipeline"][metric_type]
        h = s["hf_model"][metric_type]
        label = metric_type.upper()
        print(f"\n  {label}:")
        print(f"    {'':>12} {'Regex':>10} {'HF Model':>10} {'Delta':>10}")
        print(f"    {'-'*42}")
        for k in ("precision", "recall", "f1"):
            delta = h[k] - r[k]
            sign = "+" if delta >= 0 else ""
            print(f"    {k:<12} {r[k]:>9.2%} {h[k]:>9.2%} {sign}{delta:>8.2%}")

    w = s["wins"]
    print(f"\n  Head-to-head (exact F1): Regex wins {w['regex']}, HF wins {w['hf_model']}, Ties {w['ties']}")
    print("=" * 90)


def main():
    parser = argparse.ArgumentParser(description="Evaluate HF ingredient-detection model vs regex pipeline")
    parser.add_argument("--limit", type=int, default=50, help="Number of samples to evaluate (default: 50)")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="Output JSON path")
    args = parser.parse_args()

    data = evaluate(limit=args.limit)
    print_summary(data)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n  Full results saved to {args.output}")


if __name__ == "__main__":
    main()
