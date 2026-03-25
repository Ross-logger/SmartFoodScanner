#!/usr/bin/env python3
"""
Compare extracted ingredients with ground truth.

Runs the full pipeline (OCR + ingredient extraction) on each image in
tests/data/images, loads ground truth from tests/data/true_ingredients.json,
and reports precision, recall, and F1 (exact and fuzzy matching).

Usage:
  python scripts/compare_ingredients_accuracy.py
  python scripts/compare_ingredients_accuracy.py --use_mistral_ocr
  python scripts/compare_ingredients_accuracy.py --use_llm
  python scripts/compare_ingredients_accuracy.py --limit 5
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.ocr import extract_text_from_image
from backend.services.ingredients_extraction.symspell_extraction import extract_ingredients
from backend.services.ingredients_extraction import extract_ingredients_with_llm
from tests.utils.metrics import (
    calculate_precision,
    calculate_recall,
    calculate_f1_score,
    calculate_fuzzy_match_accuracy,
    calculate_merge_precision,
    calculate_merge_recall,
    calculate_merge_f1,
    EvaluationMetrics,
    _merge_containment_text,
)

IMAGES_DIR = PROJECT_ROOT / "tests" / "data" / "images"
GROUND_TRUTH_PATH = PROJECT_ROOT / "tests" / "data" / "true_ingredients.json"
COMPARISON_RESULT_PATH = PROJECT_ROOT / "tests" / "data" / "comparison_result.json"
OCR_CACHE_PATH = PROJECT_ROOT / "tests" / "data" / "cached_mistral_ocr_results.json"
FUZZY_THRESHOLD = 0.8

# Strip percentages before comparison (we don't evaluate percentages)
_PCT_RE = re.compile(r"\s*\(\d+(?:\.\d+)?%\)|\s*\(\d+(?:\.\d+)?%|\s*\d+(?:\.\d+)?%\)?")
_COLON_SPACE = re.compile(r"\s*:\s*")


def _normalize_for_comparison(ingredients: list[str]) -> list[str]:
    """Strip percentages and normalize for symmetric exact/fuzzy comparison."""
    out = []
    for s in ingredients:
        s = _PCT_RE.sub("", s.lower().strip()).strip().rstrip(",")
        if not s:
            continue
        # Align bracket style so merge (substring) metrics are not penalised for
        # GT using [503(ii)] vs prediction using (503(ii)).
        s = s.replace("[", "(").replace("]", ")")
        s = s.replace("{", "(").replace("}", ")")
        s = _COLON_SPACE.sub(" ", s)
        s = re.sub(r"\s+", " ", s).strip()
        s = s.rstrip(".")
        # Label / OCR variants that should count as the same token in exact match
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


def _natural_sort_key(path: Path):
    """Sort by natural numeric order (in0, in1, in2, in10, not in0, in1, in10, in2)."""
    parts = re.split(r"(\d+)", path.name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def _load_ground_truth(path: Optional[Path] = None) -> Dict[str, List[str]]:
    """Load ground truth: image -> true_ingredients."""
    path = path or GROUND_TRUTH_PATH
    if not path.exists():
        raise FileNotFoundError(f"Ground truth not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {e["image"]: e.get("true_ingredients", []) for e in data}


def _load_ocr_cache(path: Optional[Path] = None) -> Dict[str, str]:
    """Load cached OCR results: image -> ocr_text."""
    path = path or OCR_CACHE_PATH
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_ocr_cache(cache: Dict[str, str], path: Optional[Path] = None) -> None:
    """Persist the OCR cache back to disk (includes any newly-added entries)."""
    path = path or OCR_CACHE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def _run_pipeline(
    images_dir: Path,
    ground_truth: Dict[str, List[str]],
    use_mistral_ocr: bool = False,
    use_llm: bool = False,
    use_hf_section: bool = False,
    limit: Optional[int] = None,
    ocr_cache: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """
    Run OCR + extraction on each image that has ground truth.
    Returns list of {image, ocr_text, extracted_ingredients, true_ingredients}.

    When *ocr_cache* is provided, cached OCR text is used instead of calling
    the OCR service.  Any newly-produced OCR results are added to the cache
    dict in-place so the caller can persist them.
    """
    image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
    image_files = sorted(
        (f for f in images_dir.iterdir() if f.is_file() and f.suffix.lower() in image_extensions),
        key=_natural_sort_key,
    )

    # Only process images that have ground truth
    valid_images = {f.name for f in image_files if f.name in ground_truth}
    if not valid_images:
        raise FileNotFoundError(
            f"No images in {images_dir} match ground truth keys. "
            f"Ground truth has: {list(ground_truth.keys())[:5]}..."
        )

    ordered_names = sorted(valid_images, key=lambda n: _natural_sort_key(Path(n)))
    if limit is not None:
        ordered_names = ordered_names[:limit]

    if use_mistral_ocr:
        engine_label = "Mistral OCR"
    elif use_llm:
        engine_label = "EasyOCR+LLM"
    else:
        engine_label = "EasyOCR"
    if use_hf_section:
        engine_label += "+HF-section"

    if ocr_cache is None:
        ocr_cache = {}

    dataset = []
    total = len(ordered_names)
    cache_hits = 0

    for img_name in ordered_names:
        img_path = images_dir / img_name
        try:
            # Use cached OCR text when available
            if img_name in ocr_cache:
                ocr_text = ocr_cache[img_name]
                cache_hits += 1
                source_tag = "cache"
            else:
                image_data = img_path.read_bytes()
                ocr_text = extract_text_from_image(image_data, use_mistral_ocr=use_mistral_ocr)
                ocr_cache[img_name] = ocr_text
                source_tag = "live"

            if use_llm:
                llm_result = extract_ingredients_with_llm(ocr_text)
                extracted = llm_result.get("ingredients", [])
            else:
                extracted = extract_ingredients(ocr_text, use_hf_section_detection=use_hf_section)
            true_ingredients = ground_truth.get(img_path.name, [])

            dataset.append({
                "image": img_path.name,
                "ocr_text": ocr_text,
                "extracted_ingredients": extracted,
                "true_ingredients": true_ingredients,
            })
            print(
                f"  [{len(dataset)}/{total}] {img_path.name} "
                f"[{engine_label}|{source_tag}] -> {len(extracted)} extracted, "
                f"{len(true_ingredients)} ground truth"
            )

        except Exception as e:
            print(f"  [{len(dataset) + 1}/{total}] {img_path.name} ERROR: {e}")
            dataset.append({
                "image": img_path.name,
                "ocr_text": "",
                "extracted_ingredients": [],
                "true_ingredients": ground_truth.get(img_path.name, []),
                "error": str(e),
            })

    if cache_hits:
        print(f"\n  OCR cache: {cache_hits}/{total} hits, {total - cache_hits} live calls")

    return dataset


def compare_with_ground_truth(
    images_dir: Optional[Path] = None,
    ground_truth_path: Optional[Path] = None,
    fuzzy_threshold: float = FUZZY_THRESHOLD,
    use_mistral_ocr: bool = False,
    use_llm: bool = False,
    use_hf_section: bool = False,
    limit: Optional[int] = None,
    no_cache: bool = False,
) -> Dict[str, Any]:
    """
    Run full pipeline on images, compare with ground truth.

    Returns dict with exact, fuzzy, summary, details.
    """
    images_dir = images_dir or IMAGES_DIR
    ground_truth_path = ground_truth_path or GROUND_TRUTH_PATH

    if not images_dir.exists():
        raise FileNotFoundError(f"Images directory not found: {images_dir}")

    ground_truth = _load_ground_truth(ground_truth_path)

    # Load OCR cache (skip when --no_cache is set)
    ocr_cache: Dict[str, str] = {} if no_cache else _load_ocr_cache()

    if use_mistral_ocr:
        engine_label = "Mistral OCR"
    elif use_llm:
        engine_label = "EasyOCR+LLM"
    else:
        engine_label = "EasyOCR"
    if use_hf_section:
        engine_label += "+HF-section"
    print(f"\nOCR engine : {engine_label}")
    if not no_cache and ocr_cache:
        print(f"OCR cache  : {len(ocr_cache)} entries loaded from {OCR_CACHE_PATH.name}")
    if limit is not None:
        print(f"Processing images from {images_dir} (limit: first {limit} with ground truth)...")
    else:
        print(f"Processing images from {images_dir} (ground truth: {len(ground_truth)} images)...")
    dataset = _run_pipeline(
        images_dir, ground_truth, use_mistral_ocr=use_mistral_ocr,
        use_llm=use_llm, use_hf_section=use_hf_section, limit=limit,
        ocr_cache=ocr_cache,
    )

    # Persist cache with any newly-added entries
    if not no_cache:
        _save_ocr_cache(ocr_cache)

    metrics = EvaluationMetrics()
    details: List[Dict[str, Any]] = []
    merge_micro_hits_p = 0
    merge_micro_total_p = 0
    merge_micro_hits_r = 0
    merge_micro_total_r = 0

    for entry in dataset:
        image = entry.get("image", "unknown")
        extracted = entry.get("extracted_ingredients", [])
        ground_truth_ingredients = entry.get("true_ingredients", [])

        # Symmetric normalization (predictions + ground truth) for fair exact/fuzzy/merge scores
        extracted_norm = _normalize_for_comparison(extracted)
        truth_norm = _normalize_for_comparison(ground_truth_ingredients)

        metrics.add_extraction_result(
            image,
            extracted_norm,
            truth_norm,
            metadata={"ocr_text_preview": (entry.get("ocr_text") or "")[:80]},
        )

        exact_precision = calculate_precision(extracted_norm, truth_norm)
        exact_recall = calculate_recall(extracted_norm, truth_norm)
        exact_f1 = calculate_f1_score(extracted_norm, truth_norm)

        fuzzy = calculate_fuzzy_match_accuracy(
            extracted_norm, truth_norm, threshold=fuzzy_threshold
        )

        # Merge-based: check containment in joined text (quantifies splitting error)
        merge_precision = calculate_merge_precision(extracted_norm, truth_norm)
        merge_recall = calculate_merge_recall(extracted_norm, truth_norm)
        merge_f1 = calculate_merge_f1(extracted_norm, truth_norm)

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

        details.append({
            "image": image,
            "extracted_count": len(extracted),
            "ground_truth_count": len(ground_truth_ingredients),
            "exact": {"precision": exact_precision, "recall": exact_recall, "f1": exact_f1},
            "fuzzy": fuzzy,
            "merge": {"precision": merge_precision, "recall": merge_recall, "f1": merge_f1},
            # Gap: merge - split indicates splitting error (text found but wrong boundaries)
            "split_gap_recall": merge_recall - exact_recall,
            "split_gap_precision": merge_precision - exact_precision,
        })

    summary = metrics.get_summary()
    extraction = summary.get("extraction", {})
    extraction_cases = [c for c in metrics.test_cases if c["type"] == "extraction"]

    def _avg_fuzzy(cases: List[Dict]) -> Dict[str, float]:
        if not cases:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
        fuzzy = [c.get("fuzzy_metrics", {}) for c in cases]
        return {
            "precision": sum(f.get("precision", 0) for f in fuzzy) / len(fuzzy),
            "recall": sum(f.get("recall", 0) for f in fuzzy) / len(fuzzy),
            "f1": sum(f.get("f1", 0) for f in fuzzy) / len(fuzzy),
        }

    fuzzy_avg = _avg_fuzzy(extraction_cases)

    def _avg_merge(det: List[Dict]) -> Dict[str, float]:
        if not det:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
        merge = [d.get("merge", {}) for d in det]
        return {
            "precision": sum(m.get("precision", 0) for m in merge) / len(merge),
            "recall": sum(m.get("recall", 0) for m in merge) / len(merge),
            "f1": sum(m.get("f1", 0) for m in merge) / len(merge),
        }

    merge_avg = _avg_merge(details)
    micro_mp = (
        merge_micro_hits_p / merge_micro_total_p if merge_micro_total_p else 0.0
    )
    micro_mr = (
        merge_micro_hits_r / merge_micro_total_r if merge_micro_total_r else 0.0
    )
    micro_mf1 = (
        2 * micro_mp * micro_mr / (micro_mp + micro_mr)
        if (micro_mp + micro_mr) > 0
        else 0.0
    )
    avg_split_gap_recall = sum(d.get("split_gap_recall", 0) for d in details) / len(details) if details else 0
    avg_split_gap_precision = sum(d.get("split_gap_precision", 0) for d in details) / len(details) if details else 0

    # Build dataset for export: merge pipeline output with metrics
    details_by_image = {d["image"]: d for d in details}
    dataset_for_export: List[Dict[str, Any]] = []
    for entry in dataset:
        image = entry.get("image", "unknown")
        d = details_by_image.get(image, {})
        dataset_for_export.append({
            "image": image,
            "ocr_text": entry.get("ocr_text", ""),
            "extracted_ingredients": entry.get("extracted_ingredients", []),
            "true_ingredients": entry.get("true_ingredients", []),
            "exact": d.get("exact", {}),
            "fuzzy": d.get("fuzzy", {}),
        })

    return {
        "engine": engine_label,
        "exact": {
            "precision": extraction.get("avg_precision", 0),
            "recall": extraction.get("avg_recall", 0),
            "f1": extraction.get("avg_f1", 0),
        },
        "fuzzy": fuzzy_avg,
        "merge": merge_avg,
        "merge_micro": {
            "precision": micro_mp,
            "recall": micro_mr,
            "f1": micro_mf1,
            "total_predictions": merge_micro_total_p,
            "total_ground_truth": merge_micro_total_r,
        },
        "summary": {
            "total_images": len(dataset),
            "avg_exact_precision": extraction.get("avg_precision", 0),
            "avg_exact_recall": extraction.get("avg_recall", 0),
            "avg_exact_f1": extraction.get("avg_f1", 0),
            "avg_fuzzy_precision": fuzzy_avg.get("precision", 0),
            "avg_fuzzy_recall": fuzzy_avg.get("recall", 0),
            "avg_fuzzy_f1": fuzzy_avg.get("f1", 0),
            "avg_merge_precision": merge_avg.get("precision", 0),
            "avg_merge_recall": merge_avg.get("recall", 0),
            "avg_merge_f1": merge_avg.get("f1", 0),
            "avg_merge_precision_micro": micro_mp,
            "avg_merge_recall_micro": micro_mr,
            "avg_merge_f1_micro": micro_mf1,
            "avg_split_gap_recall": avg_split_gap_recall,
            "avg_split_gap_precision": avg_split_gap_precision,
        },
        "details": details,
        "metrics": metrics,
        "dataset_for_export": dataset_for_export,
    }


def save_comparison_result(results: Dict[str, Any], output_path: Path = COMPARISON_RESULT_PATH) -> None:
    """Save the full comparison result (summary + per-image details) to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Enrich details with extracted + true ingredients from dataset_for_export
    export_by_image = {e["image"]: e for e in results.get("dataset_for_export", [])}
    enriched_details = []
    for d in results["details"]:
        export = export_by_image.get(d["image"], {})
        enriched_details.append({
            **d,
            "extracted_ingredients": export.get("extracted_ingredients", []),
            "true_ingredients": export.get("true_ingredients", []),
        })

    payload = {
        "summary": results["summary"],
        "exact": results["exact"],
        "fuzzy": results["fuzzy"],
        "merge": results.get("merge", {}),
        "merge_micro": results.get("merge_micro", {}),
        "details": enriched_details,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"\n  Comparison result saved to {output_path}")


def print_summary(results: Dict[str, Any]) -> None:
    """Print a formatted summary of the comparison results."""
    s = results["summary"]
    exact = results["exact"]
    fuzzy = results["fuzzy"]
    merge = results.get("merge", {})

    print("\n" + "=" * 80)
    print("  INGREDIENT EXTRACTION vs GROUND TRUTH")
    print(f"  OCR engine : {results.get('engine', 'EasyOCR')}")
    print("  Pipeline   : OCR + extract_ingredients | Ground truth: true_ingredients.json")
    print("=" * 80)
    print(f"  Total images: {s['total_images']}")
    print()
    print("  " + "-" * 76)
    print("  " + f"{'Metric':<18} {'Split (exact)':>14} {'Fuzzy (0.8)':>14} {'Merge (containment)':>18}")
    print("  " + "-" * 76)
    print(f"  {'Precision':<18} {exact['precision']:>13.2%} {fuzzy['precision']:>13.2%} {merge.get('precision', 0):>17.2%}")
    print(f"  {'Recall':<18} {exact['recall']:>13.2%} {fuzzy['recall']:>13.2%} {merge.get('recall', 0):>17.2%}")
    print(f"  {'F1 Score':<18} {exact['f1']:>13.2%} {fuzzy['f1']:>13.2%} {merge.get('f1', 0):>17.2%}")
    print("  " + "=" * 76)
    mm = s.get("avg_merge_precision_micro")
    if mm is not None:
        print(
            f"  {'Merge (pooled)*':<18} {mm:>13.2%} "
            f"{s.get('avg_merge_recall_micro', 0):>13.2%} "
            f"{s.get('avg_merge_f1_micro', 0):>17.2%}"
        )
        print(
            "    *Pooled over all ingredient tokens (not per-image mean). "
            "Less dominated by a few noisy packs."
        )
    print()
    print("  Split vs Merge (splitting error indicator):")
    print(f"    Recall gap (merge - split):  {s.get('avg_split_gap_recall', 0):+.2%}  "
          f"(positive = text found but wrong boundaries)")
    print(f"    Precision gap (merge - split): {s.get('avg_split_gap_precision', 0):+.2%}  "
          f"(positive = extracted text exists in GT but split wrong)")
    print()


def print_worst_cases(results: Dict[str, Any], n: int = 10) -> None:
    """Print the N images with lowest F1 scores."""
    details = sorted(
        results["details"],
        key=lambda d: d["exact"]["f1"],
    )
    worst = details[:n]

    print("\n  Worst performing images (by exact F1):")
    print("  " + "-" * 66)
    print(f"  {'Image':<15} {'Extracted':>10} {'Truth':>8} {'Prec':>8} {'Recall':>8} {'F1':>8}")
    print("  " + "-" * 66)
    for d in worst:
        print(
            f"  {d['image']:<15} {d['extracted_count']:>10} {d['ground_truth_count']:>8} "
            f"{d['exact']['precision']:>7.2%} {d['exact']['recall']:>7.2%} {d['exact']['f1']:>7.2%}"
        )
    print()


def print_splitting_gap(results: Dict[str, Any], n: int = 10) -> None:
    """Print images with largest recall gap (merge - split), indicating splitting error."""
    details = sorted(
        results["details"],
        key=lambda d: d.get("split_gap_recall", 0),
        reverse=True,
    )
    top = details[:n]

    print("\n  Highest splitting error (merge recall >> split recall):")
    print("  " + "-" * 78)
    print(f"  {'Image':<12} {'Split Rec':>10} {'Merge Rec':>10} {'Gap':>10} {'Split Prec':>10} {'Merge Prec':>10}")
    print("  " + "-" * 78)
    for d in top:
        ex, m = d.get("exact", {}), d.get("merge", {})
        gap = d.get("split_gap_recall", 0)
        if gap <= 0:
            break
        print(
            f"  {d['image']:<12} {ex.get('recall', 0):>9.2%} {m.get('recall', 0):>9.2%} "
            f"{gap:>+9.2%} {ex.get('precision', 0):>9.2%} {m.get('precision', 0):>9.2%}"
        )
    print()


def print_worst_precision(results: Dict[str, Any], n: int = 15) -> None:
    """Print the N images with lowest precision (most false positives)."""
    details = sorted(
        results["details"],
        key=lambda d: d["exact"]["precision"],
    )
    worst = details[:n]

    print("\n  Worst precision images (most false positives):")
    print("  " + "-" * 66)
    print(f"  {'Image':<15} {'Extracted':>10} {'Truth':>8} {'Prec':>8} {'Recall':>8} {'F1':>8}")
    print("  " + "-" * 66)
    for d in worst:
        print(
            f"  {d['image']:<15} {d['extracted_count']:>10} {d['ground_truth_count']:>8} "
            f"{d['exact']['precision']:>7.2%} {d['exact']['recall']:>7.2%} {d['exact']['f1']:>7.2%}"
        )
    print()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare OCR + ingredient extraction against ground truth."
    )
    parser.add_argument(
        "--use_mistral_ocr",
        action="store_true",
        default=False,
        help="Use Mistral OCR cloud API instead of local EasyOCR. "
             "Requires MISTRAL_API_KEY in .env.",
    )
    parser.add_argument(
        "--use_llm",
        action="store_true",
        default=False,
        help="Use LLM for ingredient extraction instead of SymSpell. "
             "Requires a configured LLM provider (LLM_PROVIDER / API key in settings).",
    )
    parser.add_argument(
        "--use_hf_section",
        action="store_true",
        default=False,
        help="Use the HuggingFace openfoodfacts/ingredient-detection NER model "
             "for section detection instead of regex patterns.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Process only the first N images (sorted naturally). Default: all.",
    )
    parser.add_argument(
        "--images_dir",
        type=Path,
        default=None,
        help=f"Directory of test images. Default: {IMAGES_DIR}",
    )
    parser.add_argument(
        "--ground_truth",
        type=Path,
        default=None,
        help=f"Path to true_ingredients.json. Default: {GROUND_TRUTH_PATH}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=f"Path to save the JSON result. Default: {COMPARISON_RESULT_PATH}",
    )
    parser.add_argument(
        "--fuzzy_threshold",
        type=float,
        default=FUZZY_THRESHOLD,
        help=f"Fuzzy match threshold (0–1). Default: {FUZZY_THRESHOLD}",
    )
    parser.add_argument(
        "--no_cache",
        action="store_true",
        default=False,
        help="Ignore OCR cache and re-run OCR for every image.",
    )
    return parser.parse_args()


def main() -> int:
    """Run pipeline, compare with ground truth, print results."""
    args = _parse_args()

    if args.limit is not None and args.limit < 1:
        print("Error: --limit must be >= 1", file=sys.stderr)
        return 1

    try:
        results = compare_with_ground_truth(
            images_dir=args.images_dir,
            ground_truth_path=args.ground_truth,
            fuzzy_threshold=args.fuzzy_threshold,
            use_mistral_ocr=args.use_mistral_ocr,
            use_llm=args.use_llm,
            use_hf_section=args.use_hf_section,
            limit=args.limit,
            no_cache=args.no_cache,
        )
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print_summary(results)
    print_worst_cases(results, n=10)
    print_splitting_gap(results, n=10)
    print_worst_precision(results, n=15)
    save_comparison_result(results, output_path=args.output or COMPARISON_RESULT_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
