#!/usr/bin/env python3
"""
Run EasyOCR on test images and write ``tests/data/cached_easyocr_results.json``.

Uses the same cache path as ``compare_ingredients_accuracy.py`` (default EasyOCR
cache). By default only processes images listed in ``true_ingredients_for_llm.json`` so
the cache aligns with the benchmark dataset.

Usage:
  python scripts/cache_easyocr_results.py
  python scripts/cache_easyocr_results.py --force
  python scripts/cache_easyocr_results.py --all
  python scripts/cache_easyocr_results.py --limit 5
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.ocr import extract_text_from_image

IMAGES_DIR = PROJECT_ROOT / "tests" / "data" / "images"
GROUND_TRUTH_PATH = PROJECT_ROOT / "tests" / "data" / "true_ingredients_for_llm.json"
EASYOCR_CACHE_PATH = PROJECT_ROOT / "tests" / "data" / "cached_easyocr_results.json"

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}


def _natural_sort_key(path: Path) -> List:
    parts = re.split(r"(\d+)", path.name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def _load_ground_truth_image_names(path: Path) -> Set[str]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {e["image"] for e in data if e.get("image")}


def _load_cache(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_cache(cache: Dict[str, str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def _image_files(images_dir: Path, names_filter: Optional[Set[str]]) -> List[Path]:
    files = [
        f
        for f in images_dir.iterdir()
        if f.is_file() and f.suffix.lower() in _IMAGE_EXTENSIONS
    ]
    if names_filter is not None:
        files = [f for f in files if f.name in names_filter]
    return sorted(files, key=_natural_sort_key)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--images_dir",
        type=Path,
        default=IMAGES_DIR,
        help=f"Image directory (default: {IMAGES_DIR})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=EASYOCR_CACHE_PATH,
        help=f"JSON output path (default: {EASYOCR_CACHE_PATH})",
    )
    parser.add_argument(
        "--ground_truth",
        type=Path,
        default=GROUND_TRUTH_PATH,
        help="Only OCR images listed here (default: true_ingredients_for_llm.json). Ignored with --all.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="OCR every image in --images_dir, not only ground-truth keys.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run EasyOCR even when the filename already exists in the cache.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Process at most N images (after sort).",
    )
    args = parser.parse_args()

    if not args.images_dir.is_dir():
        print(f"Error: images directory not found: {args.images_dir}", file=sys.stderr)
        return 1

    names_filter: Optional[Set[str]] = None
    if not args.all:
        if not args.ground_truth.exists():
            print(f"Error: ground truth not found: {args.ground_truth}", file=sys.stderr)
            return 1
        names_filter = _load_ground_truth_image_names(args.ground_truth)

    files = _image_files(args.images_dir, names_filter)
    if args.limit is not None:
        files = files[: max(0, args.limit)]

    if not files:
        print("No images to process.", file=sys.stderr)
        return 1

    cache = _load_cache(args.output)
    total = len(files)
    done = 0
    skipped = 0
    errors = 0

    print(f"Output: {args.output}")
    print(f"Images: {total} (force={args.force})")
    print()

    for i, img_path in enumerate(files, start=1):
        key = img_path.name
        if not args.force and key in cache and cache[key].strip():
            skipped += 1
            print(f"  [{i}/{total}] {key}  skip (cached)")
            continue
        try:
            ocr_text = extract_text_from_image(img_path.read_bytes(), use_mistral_ocr=False)
            cache[key] = ocr_text or ""
            done += 1
            preview = (ocr_text or "").replace("\n", "\\n")[:72]
            print(f"  [{i}/{total}] {key}  ok ({len(ocr_text or '')} chars) {preview!r}")
        except Exception as e:
            errors += 1
            print(f"  [{i}/{total}] {key}  ERROR: {e}", file=sys.stderr)

    _save_cache(cache, args.output)
    print()
    print(f"Saved {len(cache)} entries to {args.output.relative_to(PROJECT_ROOT)}")
    print(f"New/updated: {done}, skipped: {skipped}, errors: {errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
