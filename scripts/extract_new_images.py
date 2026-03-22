#!/usr/bin/env python3
"""
Run OCR + ingredient extraction on all images in tests/data/new_images and
produce a JSON in the same format as old_images_comparison_result.json.

Since no ground truth exists yet, true_ingredients is left empty so the file
can be manually reviewed and corrected to serve as a new ground truth.

Usage:
  python scripts/extract_new_images.py
  python scripts/extract_new_images.py --use_trocr
  python scripts/extract_new_images.py --use_llm
  python scripts/extract_new_images.py --use_trocr --use_llm
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

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}


def _natural_sort_key(path: Path):
    parts = re.split(r"(\d+)", path.name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract ingredients from new images (no ground truth required)."
    )
    parser.add_argument(
        "--use_trocr",
        action="store_true",
        default=False,
        help="Use TrOCR for recognition instead of EasyOCR end-to-end.",
    )
    parser.add_argument(
        "--use_llm",
        action="store_true",
        default=False,
        help=(
            "Use LLM for ingredient extraction instead of SymSpell. "
            "Requires LLM_PROVIDER / API key configured in settings. "
            "Can be combined with --use_trocr."
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

    if args.use_trocr and args.use_llm:
        engine_label = "TrOCR+LLM"
    elif args.use_trocr:
        engine_label = "TrOCR"
    elif args.use_llm:
        engine_label = "EasyOCR+LLM"
    else:
        engine_label = "EasyOCR"

    total = len(image_files)
    print(f"\nOCR engine : {engine_label}")
    print(f"Processing {total} images from {images_dir} ...")
    print()

    details = []
    errors = 0

    for i, img_path in enumerate(image_files, 1):
        try:
            image_data = img_path.read_bytes()
            ocr_text = extract_text_from_image(image_data, use_trocr=args.use_trocr)

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
            print(f"  [{i}/{total}] {img_path.name} -> {len(extracted)} ingredients extracted")

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
