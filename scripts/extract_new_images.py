#!/usr/bin/env python3
"""
Run OCR + ingredient extraction on all images in tests/data/new_images and
produce a JSON in the same format as old_images_comparison_result.json.

Since no ground truth exists yet, true_ingredients is left empty so the file
can be manually reviewed and corrected to serve as a new ground truth.

Usage:
  python scripts/extract_new_images.py
  python scripts/extract_new_images.py --use_mistral_ocr
  python scripts/extract_new_images.py --use_llm
  python scripts/extract_new_images.py --limit 10
  python scripts/extract_new_images.py --images_dir tests/data/new_images
  python scripts/extract_new_images.py --output tests/data/new_images_result.json
"""

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.ocr import extract_text_from_image, extract_ingredients
from backend.services.ingredients_extraction import extract_ingredients_with_llm

IMAGES_DIR = PROJECT_ROOT / "tests" / "data" / "new_images"
OUTPUT_PATH = PROJECT_ROOT / "tests" / "data" / "new_images_result.json"
OCR_CACHE_PATH = PROJECT_ROOT / "tests" / "data" / "cached_mistral_ocr_results.json"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}


def _natural_sort_key(path: Path):
    parts = re.split(r"(\d+)", path.name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract ingredients from new images (no ground truth required)."
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
        help=(
            "Use LLM for ingredient extraction instead of SymSpell. "
            "Requires LLM_PROVIDER / API key configured in settings."
        ),
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
        default=IMAGES_DIR,
        help=f"Directory of images to process. Default: {IMAGES_DIR}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help=f"Output JSON path. Default: {OUTPUT_PATH}",
    )
    parser.add_argument(
        "--no_cache",
        action="store_true",
        default=False,
        help="Ignore OCR cache and re-run OCR for every image.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    images_dir: Path = args.images_dir
    output_path: Path = args.output

    if not images_dir.exists():
        print(f"Error: images directory not found: {images_dir}", file=sys.stderr)
        return 1

    image_files = sorted(
        (f for f in images_dir.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS),
        key=_natural_sort_key,
    )

    if not image_files:
        print(f"Error: no images found in {images_dir}", file=sys.stderr)
        return 1

    if args.limit is not None:
        image_files = image_files[: args.limit]

    if args.use_mistral_ocr and args.use_llm:
        engine_label = "Mistral OCR+LLM"
    elif args.use_mistral_ocr:
        engine_label = "Mistral OCR"
    elif args.use_llm:
        engine_label = "EasyOCR+LLM"
    else:
        engine_label = "EasyOCR"

    # Load OCR cache
    ocr_cache = {}
    if not args.no_cache and OCR_CACHE_PATH.exists():
        with open(OCR_CACHE_PATH, encoding="utf-8") as f:
            ocr_cache = json.load(f)

    total = len(image_files)
    print(f"\nOCR engine : {engine_label}")
    if not args.no_cache and ocr_cache:
        print(f"OCR cache  : {len(ocr_cache)} entries loaded from {OCR_CACHE_PATH.name}")
    print(f"Processing {total} images from {images_dir} ...")
    print()

    details = []
    errors = 0
    cache_hits = 0

    for i, img_path in enumerate(image_files, 1):
        try:
            if img_path.name in ocr_cache:
                ocr_text = ocr_cache[img_path.name]
                cache_hits += 1
                source_tag = "cache"
            else:
                image_data = img_path.read_bytes()
                ocr_text = extract_text_from_image(image_data, use_mistral_ocr=args.use_mistral_ocr)
                ocr_cache[img_path.name] = ocr_text
                source_tag = "live"

            if args.use_llm:
                llm_result = extract_ingredients_with_llm(ocr_text)
                extracted = llm_result.get("ingredients", [])
            else:
                extracted = extract_ingredients(ocr_text)

            details.append({
                "image": img_path.name,
                "ocr_text": ocr_text,
                "extracted_count": len(extracted),
                "ground_truth_count": 0,
                "extracted_ingredients": extracted,
                "true_ingredients": [],
            })
            print(f"  [{i}/{total}] {img_path.name} [{source_tag}] -> {len(extracted)} ingredients extracted")

        except Exception as e:
            errors += 1
            print(f"  [{i}/{total}] {img_path.name} ERROR: {e}")
            details.append({
                "image": img_path.name,
                "ocr_text": "",
                "extracted_count": 0,
                "ground_truth_count": 0,
                "extracted_ingredients": [],
                "true_ingredients": [],
                "error": str(e),
            })

    if cache_hits:
        print(f"\n  OCR cache: {cache_hits}/{total} hits, {total - cache_hits} live calls")

    # Persist cache with any newly-added entries
    if not args.no_cache:
        OCR_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OCR_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(ocr_cache, f, indent=2, ensure_ascii=False)

    payload = {
        "summary": {
            "total_images": total,
            "engine": engine_label,
            "errors": errors,
            "note": (
                "true_ingredients is empty — fill in manually to create ground truth. "
                "Metrics are not computed since no ground truth exists."
            ),
        },
        "details": details,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"\n  Done. {total - errors}/{total} images processed successfully.")
    print(f"  Result saved to {output_path}")
    print(f"\n  Next step: edit true_ingredients in each entry to create ground truth.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
