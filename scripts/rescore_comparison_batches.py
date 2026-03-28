#!/usr/bin/env python3
"""
Recompute fuzzy/merge metrics for existing comparison JSON batches using a
different ground-truth file (no OCR / LLM re-run).

Predictions are taken from each input file's ``extracted_ingredients``;
``true_ingredients`` are replaced from the chosen GT JSON.

Normalization rules must match ``compare_ingredients_accuracy.py``.

Usage:
  python scripts/rescore_comparison_batches.py \\
    --ground_truth tests/data/true_ingredients_symspell.json \\
    --inputs tests/data/comparison_mistral_llm_batch0*.json \\
    --output_suffix _symspell
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tests.utils.metrics import (
    EvaluationMetrics,
    _merge_containment_text,
    calculate_fuzzy_match_accuracy,
    calculate_merge_f1,
    calculate_merge_precision,
    calculate_merge_recall,
)

# Keep in sync with scripts/compare_ingredients_accuracy.py
FUZZY_THRESHOLD = 0.8
_PCT_RE = re.compile(r"\s*\(\d+(?:\.\d+)?%\)|\s*\(\d+(?:\.\d+)?%|\s*\d+(?:\.\d+)?%\)?")
_COLON_SPACE = re.compile(r"\s*:\s*")


def _normalize_for_comparison(ingredients: list[str]) -> list[str]:
    """Strip percentages and normalize for symmetric fuzzy/merge comparison."""
    out = []
    for s in ingredients:
        s = _PCT_RE.sub("", s.lower().strip()).strip().rstrip(",")
        if not s:
            continue
        s = s.replace("[", "(").replace("]", ")")
        s = s.replace("{", "(").replace("}", ")")
        s = _COLON_SPACE.sub(" ", s)
        s = re.sub(r"\s+", " ", s).strip()
        s = s.rstrip(".")
        s = re.sub(r"\bwheat\s+flour\b", "wheatflour", s)
        s = re.sub(r"\bsun\s+flower\b", "sunflower", s)
        s = re.sub(r"\bpectin\b", "pectins", s)
        for us, uk in (
            ("flavorings", "flavourings"),
            ("flavoring", "flavouring"),
            ("flavors", "flavours"),
            ("flavor", "flavour"),
        ):
            s = re.sub(rf"\b{us}\b", uk, s)
        s = re.sub(r"\boat\s+flour\b", "oats flour", s)
        s = re.sub(r"\bsoy\b", "soya", s)
        s = re.sub(r"\bsunflowerseed\b", "sunflower seed", s)
        s = re.sub(r"\bsalt\s+caramelised\b", "salted caramelised", s)
        s = re.sub(r"\bsultana\b", "sultanas", s)
        s = re.sub(r"\brice\s+infused\s+cranberries\b", "juice infused cranberries", s)
        if s:
            out.append(s)
    return out


def _load_ground_truth_map(path: Path) -> Dict[str, List[str]]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {e["image"]: e.get("true_ingredients", []) for e in data}


def rescore_details(
    details: List[Dict[str, Any]],
    gt_map: Dict[str, List[str]],
    fuzzy_threshold: float,
) -> Dict[str, Any]:
    """Return summary + fuzzy + merge + new details (same shape as comparison JSON)."""
    metrics = EvaluationMetrics()
    new_details: List[Dict[str, Any]] = []
    merge_micro_hits_p = 0
    merge_micro_total_p = 0
    merge_micro_hits_r = 0
    merge_micro_total_r = 0

    for detail in details:
        image = detail.get("image", "unknown")
        extracted = detail.get("extracted_ingredients") or []
        if image not in gt_map:
            raise KeyError(f"No ground truth for image {image!r} in GT file")
        ground_truth_ingredients = gt_map[image]

        extracted_norm = _normalize_for_comparison(list(extracted))
        truth_norm = _normalize_for_comparison(list(ground_truth_ingredients))

        metrics.add_extraction_result(
            image,
            extracted_norm,
            truth_norm,
            metadata={},
        )

        raw_fuzzy = calculate_fuzzy_match_accuracy(
            extracted_norm, truth_norm, threshold=fuzzy_threshold
        )
        fuzzy = {k: round(v, 2) for k, v in raw_fuzzy.items()}

        merge_precision = round(calculate_merge_precision(extracted_norm, truth_norm), 2)
        merge_recall = round(calculate_merge_recall(extracted_norm, truth_norm), 2)
        merge_f1 = round(calculate_merge_f1(extracted_norm, truth_norm), 2)

        merged_gt = _merge_containment_text(" ".join(truth_norm))
        merged_pred = _merge_containment_text(" ".join(extracted_norm))
        for p in extracted_norm:
            merge_micro_total_p += 1
            if _merge_containment_text(p) in merged_gt:
                merge_micro_hits_p += 1
        for g in truth_norm:
            merge_micro_total_r += 1
            if _merge_containment_text(g) in merged_pred:
                merge_micro_hits_r += 1

        new_details.append({
            "image": image,
            "extracted_count": len(extracted),
            "ground_truth_count": len(ground_truth_ingredients),
            "fuzzy": fuzzy,
            "merge": {"precision": merge_precision, "recall": merge_recall, "f1": merge_f1},
            "split_gap_recall": round(merge_recall - fuzzy["recall"], 2),
            "split_gap_precision": round(merge_precision - fuzzy["precision"], 2),
            "extracted_ingredients": extracted,
            "true_ingredients": ground_truth_ingredients,
        })

    extraction_cases = [c for c in metrics.test_cases if c["type"] == "extraction"]

    def _avg_fuzzy(cases: List[Dict]) -> Dict[str, float]:
        if not cases:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
        fuzzy = [c.get("fuzzy_metrics", {}) for c in cases]
        return {
            "precision": round(sum(f.get("precision", 0) for f in fuzzy) / len(fuzzy), 2),
            "recall": round(sum(f.get("recall", 0) for f in fuzzy) / len(fuzzy), 2),
            "f1": round(sum(f.get("f1", 0) for f in fuzzy) / len(fuzzy), 2),
        }

    fuzzy_avg = _avg_fuzzy(extraction_cases)

    merge_pooled_precision = round(
        merge_micro_hits_p / merge_micro_total_p if merge_micro_total_p else 0.0, 2
    )
    merge_pooled_recall = round(
        merge_micro_hits_r / merge_micro_total_r if merge_micro_total_r else 0.0, 2
    )
    merge_pooled_f1 = round(
        2
        * merge_pooled_precision
        * merge_pooled_recall
        / (merge_pooled_precision + merge_pooled_recall)
        if (merge_pooled_precision + merge_pooled_recall) > 0
        else 0.0,
        2,
    )
    merge_summary = {
        "precision": merge_pooled_precision,
        "recall": merge_pooled_recall,
        "f1": merge_pooled_f1,
        "total_predictions": merge_micro_total_p,
        "total_ground_truth": merge_micro_total_r,
    }
    avg_split_gap_recall = (
        round(sum(d.get("split_gap_recall", 0) for d in new_details) / len(new_details), 2)
        if new_details
        else 0
    )
    avg_split_gap_precision = (
        round(sum(d.get("split_gap_precision", 0) for d in new_details) / len(new_details), 2)
        if new_details
        else 0
    )
    return {
        "fuzzy": fuzzy_avg,
        "merge": merge_summary,
        "summary": {
            "total_images": len(new_details),
            "avg_fuzzy_precision": fuzzy_avg.get("precision", 0),
            "avg_fuzzy_recall": fuzzy_avg.get("recall", 0),
            "avg_fuzzy_f1": fuzzy_avg.get("f1", 0),
            "avg_merge_precision": merge_pooled_precision,
            "avg_merge_recall": merge_pooled_recall,
            "avg_merge_f1": merge_pooled_f1,
            "avg_split_gap_recall": avg_split_gap_recall,
            "avg_split_gap_precision": avg_split_gap_precision,
        },
        "details": new_details,
    }


def _path_for_meta(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(p.resolve())


def _save_batch(payload: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Rescore comparison JSON batches against alternate GT.")
    parser.add_argument(
        "--ground_truth",
        type=Path,
        required=True,
        help="Ground truth JSON (e.g. tests/data/true_ingredients_symspell.json)",
    )
    parser.add_argument(
        "--inputs",
        type=Path,
        nargs="+",
        required=True,
        help="Existing comparison batch JSON files (predictions preserved).",
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=None,
        help="Directory for output files. Default: same as first input's parent.",
    )
    parser.add_argument(
        "--output_suffix",
        type=str,
        default="_symspell",
        help="Insert before .json (e.g. batch01.json -> batch01_symspell.json).",
    )
    parser.add_argument(
        "--fuzzy_threshold",
        type=float,
        default=FUZZY_THRESHOLD,
        help=f"Fuzzy threshold (default {FUZZY_THRESHOLD}).",
    )
    args = parser.parse_args()
    gt_path = args.ground_truth.resolve()
    if not gt_path.is_file():
        print(f"Error: ground truth not found: {gt_path}", file=sys.stderr)
        return 1
    gt_map = _load_ground_truth_map(gt_path)
    out_dir = args.output_dir.resolve() if args.output_dir else None

    all_details_for_total: List[Dict[str, Any]] = []

    for inp in args.inputs:
        inp = inp.resolve()
        if not inp.is_file():
            print(f"Error: input not found: {inp}", file=sys.stderr)
            return 1
        with open(inp, encoding="utf-8") as f:
            raw = json.load(f)
        details = raw.get("details") or []
        scored = rescore_details(details, gt_map, args.fuzzy_threshold)
        stem = inp.stem
        if stem.endswith(args.output_suffix):
            stem = stem[: -len(args.output_suffix)]
        out_name = f"{stem}{args.output_suffix}.json"
        dest = (out_dir or inp.parent) / out_name
        payload = {
            "meta": {
                "predictions_source": _path_for_meta(inp),
                "ground_truth_file": _path_for_meta(gt_path),
                "fuzzy_threshold": args.fuzzy_threshold,
            },
            "summary": scored["summary"],
            "fuzzy": scored["fuzzy"],
            "merge": scored["merge"],
            "details": scored["details"],
        }
        _save_batch(payload, dest)
        print(f"Wrote {dest} ({len(scored['details'])} images)")
        all_details_for_total.extend(scored["details"])

    total = rescore_details(all_details_for_total, gt_map, args.fuzzy_threshold)
    print("\n=== Combined (all inputs) ===")
    print(f"Images: {total['summary']['total_images']}")
    print(f"Fuzzy avg  P/R/F1: {total['fuzzy']['precision']:.2f} / {total['fuzzy']['recall']:.2f} / {total['fuzzy']['f1']:.2f}")
    m = total["merge"]
    print(
        f"Merge pool P/R/F1: {m['precision']:.2f} / {m['recall']:.2f} / {m['f1']:.2f} "
        f"({m['total_predictions']} pred, {m['total_ground_truth']} gt tokens)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
