#!/usr/bin/env python3
"""
Compare extracted ingredients with ground truth.

Runs the full pipeline (OCR + ingredient extraction) on each image in
tests/data/images, loads ground truth from tests/data/true_ingredients.json
(by default). For SymSpell-style evaluation against atomic sub-ingredients, use
``tests/data/true_ingredients_symspell.json`` (regenerate with
``python scripts/build_true_ingredients_symspell.py``).
and reports fuzzy and merge (containment) metrics.

Usage:
  python scripts/compare_ingredients_accuracy.py
  python scripts/compare_ingredients_accuracy.py --use_mistral_ocr
  python scripts/compare_ingredients_accuracy.py --use_llm
  python scripts/compare_ingredients_accuracy.py --limit 5
  python scripts/compare_ingredients_accuracy.py --use_hf_section --output tests/data/comparison_result_symspell_hf_section.json
  python scripts/compare_ingredients_accuracy.py --only IMG_0050.png in11.jpg --use_hf_section
  python scripts/compare_ingredients_accuracy.py --ground_truth tests/data/true_ingredients_symspell.json
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
from backend.services.ingredients_extraction import extract_ingredients_with_llm
from tests.utils.metrics import (
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
COMPARISON_RESULT_SUBSET_PATH = (
    PROJECT_ROOT / "tests" / "data" / "comparison_result_only_subset.json"
)
MISTRAL_OCR_CACHE_PATH = PROJECT_ROOT / "tests" / "data" / "cached_mistral_ocr_results.json"
EASYOCR_CACHE_PATH = PROJECT_ROOT / "tests" / "data" / "cached_easyocr_results.json"
FUZZY_THRESHOLD = 0.8

# Strip percentages before comparison (we don't evaluate percentages)
_PCT_RE = re.compile(r"\s*\(\d+(?:\.\d+)?%\)|\s*\(\d+(?:\.\d+)?%|\s*\d+(?:\.\d+)?%\)?")
_COLON_SPACE = re.compile(r"\s*:\s*")


def _normalize_for_comparison(ingredients: list[str]) -> list[str]:
    """Strip percentages and normalize for symmetric fuzzy/merge comparison."""
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
        # Label / OCR variants aligned with ground truth for fair comparison
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


def _expand_single_ingredients_block(extracted: List[str]) -> List[str]:
    """Expand one-element ``INGREDIENTS: a, b, c`` API output for benchmark metrics."""
    if not extracted or len(extracted) != 1:
        return list(extracted)
    s = extracted[0]
    if not isinstance(s, str):
        return list(extracted)
    body = s.strip()
    if re.match(r"^ingredients\s*:", body, re.I):
        body = re.sub(r"^ingredients\s*:\s*", "", body, count=1, flags=re.I).strip()
    parts = [p.strip() for p in body.split(",") if p.strip()]
    return parts if parts else list(extracted)



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


def _ocr_cache_path(use_mistral_ocr: bool = False) -> Path:
    """Return the cache file path for the given OCR engine."""
    return MISTRAL_OCR_CACHE_PATH if use_mistral_ocr else EASYOCR_CACHE_PATH


def _load_ocr_cache(path: Path) -> Dict[str, str]:
    """Load cached OCR results: image -> ocr_text."""
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_ocr_cache(cache: Dict[str, str], path: Path) -> None:
    """Persist the OCR cache back to disk (includes any newly-added entries)."""
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
    only_images: Optional[List[str]] = None,
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
    if only_images:
        want = {n.strip() for n in only_images if n.strip()}
        missing_gt = want - valid_images
        if missing_gt:
            print(
                f"  Warning: --only names not in images+ground-truth (skipped): "
                f"{sorted(missing_gt)}"
            )
        ordered_names = [n for n in ordered_names if n in want]
        if not ordered_names:
            raise FileNotFoundError(
                f"No --only images left after filtering. Requested: {sorted(want)}"
            )
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

            llm_result = extract_ingredients_with_llm(ocr_text)
            extracted = llm_result.get("ingredients", [])
            true_ingredients = ground_truth.get(img_path.name, [])

            dataset.append({
                "image": img_path.name,
                "ocr_text": ocr_text,
                "extracted_ingredients": extracted,
                "true_ingredients": true_ingredients,
            })
            print(
                f"  [{len(dataset)}/{total}] {img_path.name} "
                f"[{engine_label}|{source_tag}] -> {len(_expand_single_ingredients_block(extracted))} segments ({len(extracted)} stored), "
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
    only_images: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Run full pipeline on images, compare with ground truth.

    Returns dict with fuzzy, merge, summary, details.
    """
    images_dir = images_dir or IMAGES_DIR
    ground_truth_path = ground_truth_path or GROUND_TRUTH_PATH

    if not images_dir.exists():
        raise FileNotFoundError(f"Images directory not found: {images_dir}")

    ground_truth = _load_ground_truth(ground_truth_path)

    # Load OCR cache (skip when --no_cache is set)
    cache_path = _ocr_cache_path(use_mistral_ocr)
    ocr_cache: Dict[str, str] = {} if no_cache else _load_ocr_cache(cache_path)

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
        print(f"OCR cache  : {len(ocr_cache)} entries loaded from {cache_path.name}")
    if only_images:
        print(f"Processing images from {images_dir} (--only: {len(only_images)} names)...")
    elif limit is not None:
        print(f"Processing images from {images_dir} (limit: first {limit} with ground truth)...")
    else:
        print(f"Processing images from {images_dir} (ground truth: {len(ground_truth)} images)...")
    dataset = _run_pipeline(
        images_dir, ground_truth, use_mistral_ocr=use_mistral_ocr,
        use_llm=use_llm, use_hf_section=use_hf_section, limit=limit,
        ocr_cache=ocr_cache,
        only_images=only_images,
    )

    # Persist cache with any newly-added entries
    if not no_cache:
        _save_ocr_cache(ocr_cache, cache_path)

    metrics = EvaluationMetrics()
    details: List[Dict[str, Any]] = []
    merge_micro_hits_p = 0
    merge_micro_total_p = 0
    merge_micro_hits_r = 0
    merge_micro_total_r = 0

    for entry in dataset:
        image = entry.get("image", "unknown")
        extracted = entry.get("extracted_ingredients", [])
        expanded = _expand_single_ingredients_block(extracted)
        ground_truth_ingredients = entry.get("true_ingredients", [])

        # Symmetric normalization (predictions + ground truth) for fair fuzzy/merge scores
        extracted_norm = _normalize_for_comparison(expanded)
        truth_norm = _normalize_for_comparison(ground_truth_ingredients)

        metrics.add_extraction_result(
            image,
            extracted_norm,
            truth_norm,
            metadata={"ocr_text_preview": (entry.get("ocr_text") or "")[:80]},
        )

        raw_fuzzy = calculate_fuzzy_match_accuracy(
            extracted_norm, truth_norm, threshold=fuzzy_threshold
        )
        fuzzy = {k: round(v, 2) for k, v in raw_fuzzy.items()}

        # Merge-based: check containment in joined text (quantifies splitting error)
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

        details.append({
            "image": image,
            "extracted_count": len(expanded),
            "ground_truth_count": len(ground_truth_ingredients),
            "fuzzy": fuzzy,
            "merge": {"precision": merge_precision, "recall": merge_recall, "f1": merge_f1},
            # Gap: merge vs fuzzy token match (splitting / boundary effects)
            "split_gap_recall": round(merge_recall - fuzzy["recall"], 2),
            "split_gap_precision": round(merge_precision - fuzzy["precision"], 2),
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
        else 0.0, 2
    )
    merge_summary = {
        "precision": merge_pooled_precision,
        "recall": merge_pooled_recall,
        "f1": merge_pooled_f1,
        "total_predictions": merge_micro_total_p,
        "total_ground_truth": merge_micro_total_r,
    }
    avg_split_gap_recall = round(sum(d.get("split_gap_recall", 0) for d in details) / len(details), 2) if details else 0
    avg_split_gap_precision = round(sum(d.get("split_gap_precision", 0) for d in details) / len(details), 2) if details else 0

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
            "fuzzy": d.get("fuzzy", {}),
        })

    return {
        "engine": engine_label,
        "fuzzy": fuzzy_avg,
        "merge": merge_summary,
        "summary": {
            "total_images": len(dataset),
            "avg_fuzzy_precision": fuzzy_avg.get("precision", 0),
            "avg_fuzzy_recall": fuzzy_avg.get("recall", 0),
            "avg_fuzzy_f1": fuzzy_avg.get("f1", 0),
            "avg_merge_precision": merge_pooled_precision,
            "avg_merge_recall": merge_pooled_recall,
            "avg_merge_f1": merge_pooled_f1,
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
        "fuzzy": results["fuzzy"],
        "merge": results.get("merge", {}),
        "details": enriched_details,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"\n  Comparison result saved to {output_path}")


def print_summary(results: Dict[str, Any]) -> None:
    """Print a formatted summary of the comparison results."""
    s = results["summary"]
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
    print("  " + f"{'Metric':<18} {'Fuzzy (token)':>18} {'Merge (pooled)':>18}")
    print("  " + "-" * 76)
    print(f"  {'Precision':<18} {fuzzy['precision']:>17.2%} {merge.get('precision', 0):>17.2%}")
    print(f"  {'Recall':<18} {fuzzy['recall']:>17.2%} {merge.get('recall', 0):>17.2%}")
    print(f"  {'F1 Score':<18} {fuzzy['f1']:>17.2%} {merge.get('f1', 0):>17.2%}")
    print("  " + "=" * 76)
    print(
        "    Fuzzy = per-image SequenceMatcher @ threshold, averaged across images. "
        "Merge = micro containment over all tokens."
    )
    print()
    print("  Merge vs fuzzy (boundary / splitting indicator):")
    print(f"    Recall gap (merge - fuzzy):  {s.get('avg_split_gap_recall', 0):+.2%}  "
          f"(positive = text found in merge sense but token match differs)")
    print(f"    Precision gap (merge - fuzzy): {s.get('avg_split_gap_precision', 0):+.2%}")
    print()


def print_worst_cases(results: Dict[str, Any], n: int = 10) -> None:
    """Print the N images with lowest fuzzy F1."""
    details = sorted(
        results["details"],
        key=lambda d: d["fuzzy"]["f1"],
    )
    worst = details[:n]

    print("\n  Worst performing images (by fuzzy F1):")
    print("  " + "-" * 66)
    print(f"  {'Image':<15} {'Extracted':>10} {'Truth':>8} {'Prec':>8} {'Recall':>8} {'F1':>8}")
    print("  " + "-" * 66)
    for d in worst:
        fz = d["fuzzy"]
        print(
            f"  {d['image']:<15} {d['extracted_count']:>10} {d['ground_truth_count']:>8} "
            f"{fz['precision']:>7.2%} {fz['recall']:>7.2%} {fz['f1']:>7.2%}"
        )
    print()


def print_splitting_gap(results: Dict[str, Any], n: int = 10) -> None:
    """Print images with largest recall gap (merge - fuzzy), indicating splitting error."""
    details = sorted(
        results["details"],
        key=lambda d: d.get("split_gap_recall", 0),
        reverse=True,
    )
    top = details[:n]

    print("\n  Highest merge–fuzzy recall gap (merge recall >> fuzzy recall):")
    print("  " + "-" * 78)
    print(f"  {'Image':<12} {'Fuzzy Rec':>10} {'Merge Rec':>10} {'Gap':>10} {'Fuzzy Prec':>10} {'Merge Prec':>10}")
    print("  " + "-" * 78)
    for d in top:
        fz, m = d.get("fuzzy", {}), d.get("merge", {})
        gap = d.get("split_gap_recall", 0)
        if gap <= 0:
            break
        print(
            f"  {d['image']:<12} {fz.get('recall', 0):>9.2%} {m.get('recall', 0):>9.2%} "
            f"{gap:>+9.2%} {fz.get('precision', 0):>9.2%} {m.get('precision', 0):>9.2%}"
        )
    print()


def print_worst_precision(results: Dict[str, Any], n: int = 15) -> None:
    """Print the N images with lowest fuzzy precision (most false positives)."""
    details = sorted(
        results["details"],
        key=lambda d: d["fuzzy"]["precision"],
    )
    worst = details[:n]

    print("\n  Worst fuzzy precision images (most false positives):")
    print("  " + "-" * 66)
    print(f"  {'Image':<15} {'Extracted':>10} {'Truth':>8} {'Prec':>8} {'Recall':>8} {'F1':>8}")
    print("  " + "-" * 66)
    for d in worst:
        fz = d["fuzzy"]
        print(
            f"  {d['image']:<15} {d['extracted_count']:>10} {d['ground_truth_count']:>8} "
            f"{fz['precision']:>7.2%} {fz['recall']:>7.2%} {fz['f1']:>7.2%}"
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
        help="SymSpell only: find the ingredients block with HF NER "
             "(token labels ING) instead of regex/header scanning. "
             "Ignored with --use_llm. First use downloads/loads the model.",
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
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="IMAGE",
        default=None,
        help="Process only these image basenames (must exist under --images_dir with ground truth).",
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
            only_images=args.only,
        )
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print_summary(results)
    print_worst_cases(results, n=10)
    print_splitting_gap(results, n=10)
    print_worst_precision(results, n=15)
    if args.output is not None:
        out = args.output
    elif args.only:
        out = COMPARISON_RESULT_SUBSET_PATH
    else:
        out = COMPARISON_RESULT_PATH
    save_comparison_result(results, output_path=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
