#!/usr/bin/env python3
"""
Benchmark box classifier + OCR corrector only (no OCR, no SymSpell fallback, no analysis).

OCR runs once per image (untimed) to obtain EasyOCR boxes. The timed section is:
  classify_boxes → extract_ingredients_from_boxes → split_ingredients_text (if merged text)
  → correct_ingredient_list (if merged text).

Images without EasyOCR raw boxes are skipped (nothing to feed the model).

Default: 50 images; aggregate ``Sum`` and ``Scaled to 100`` extrapolate linearly to a
100-image equivalent (mean / min / max are per-image over the measured set).

Usage (from project root):
  python scripts/benchmark_box_classifier_pipeline.py
  python scripts/benchmark_box_classifier_pipeline.py --limit 50
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend import settings  # noqa: E402
from backend.services.ingredients_extraction.ingredient_box_classifier import (  # noqa: E402
    classify_boxes,
    extract_ingredients_from_boxes,
)
from backend.services.ingredients_extraction.ocr_corrector import correct_ingredient_list  # noqa: E402
from backend.services.ingredients_extraction.utils import split_ingredients_text  # noqa: E402
from backend.services.ocr import extract_ocr_from_image  # noqa: E402


IMAGES_DIR = PROJECT_ROOT / "tests" / "data" / "images"
GROUND_TRUTH_PATH = PROJECT_ROOT / "tests" / "data" / "true_ingredients_for_box_classifier.json"
DEFAULT_LIMIT = 50
# Report totals scaled to this many images (benchmark runs on ``DEFAULT_LIMIT``).
EXTRAPOLATE_TO_N_IMAGES = 100


def _natural_sort_key(path: Path):
    parts = re.split(r"(\d+)", path.name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def _load_ground_truth_images() -> list[str]:
    with open(GROUND_TRUTH_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return [e["image"] for e in data if e.get("image")]


def time_model_and_corrector(raw_results) -> float:
    """Wall time for classifier + merge + split + OCR corrector only."""
    t0 = time.perf_counter()
    df_boxes = classify_boxes(raw_results)
    merged_text = extract_ingredients_from_boxes(df_boxes)
    if merged_text.strip():
        candidates = split_ingredients_text(merged_text)
        correct_ingredient_list(
            candidates,
            use_ocr_corrector=settings.USE_OCR_CORRECTOR,
        )
    return time.perf_counter() - t0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark box classifier + OCR corrector (excludes OCR time)."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Max images to process (default: {DEFAULT_LIMIT}). Totals also scaled to "
        f"{EXTRAPOLATE_TO_N_IMAGES} images in the summary.",
    )
    parser.add_argument(
        "--scale-to",
        type=int,
        default=EXTRAPOLATE_TO_N_IMAGES,
        help=f"Extrapolate aggregate timings to this many images (default: {EXTRAPOLATE_TO_N_IMAGES}).",
    )
    parser.add_argument(
        "--images_dir",
        type=Path,
        default=IMAGES_DIR,
        help=f"Image directory (default: {IMAGES_DIR})",
    )
    args = parser.parse_args()

    names = _load_ground_truth_images()
    names = sorted(names, key=lambda n: _natural_sort_key(Path(n)))
    if args.limit is not None:
        names = names[: args.limit]

    image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
    times: list[float] = []
    missing: list[str] = []
    skipped_no_boxes: list[str] = []

    print(
        f"Timed: box classifier + OCR corrector only (OCR excluded)\n"
        f"USE_OCR_CORRECTOR={settings.USE_OCR_CORRECTOR}\n"
        f"Model: {settings.BOX_CLASSIFIER_MODEL_PATH}\n"
        f"Images (cap): {len(names)}\n",
        flush=True,
    )

    # Untimed warmup so first timed inference does not dominate Max.
    for wname in names:
        wpath = args.images_dir / wname
        if not wpath.is_file() or wpath.suffix.lower() not in image_extensions:
            continue
        try:
            wocr = extract_ocr_from_image(wpath.read_bytes(), use_mistral_ocr=False)
            if wocr.easyocr_raw_results:
                time_model_and_corrector(wocr.easyocr_raw_results)
                print(f"Warmup (untimed): {wname}", flush=True)
                break
        except Exception:
            continue

    t0_all = time.perf_counter()
    for i, name in enumerate(names, 1):
        path = args.images_dir / name
        if not path.is_file() or path.suffix.lower() not in image_extensions:
            missing.append(name)
            continue
        data = path.read_bytes()
        try:
            ocr_result = extract_ocr_from_image(data, use_mistral_ocr=False)
        except Exception as e:
            print(f"  [{i}/{len(names)}] {name} OCR ERROR: {e}", flush=True)
            continue

        raw = ocr_result.easyocr_raw_results
        if not raw:
            skipped_no_boxes.append(name)
            print(f"  [{i}/{len(names)}] {name} (skip: no EasyOCR boxes)", flush=True)
            continue

        try:
            elapsed = time_model_and_corrector(raw)
        except Exception as e:
            print(f"  [{i}/{len(names)}] {name} ERROR: {e}", flush=True)
            continue

        times.append(elapsed)
        print(f"  [{i}/{len(names)}] {name} {elapsed*1000:.1f} ms", flush=True)

    total_wall = time.perf_counter() - t0_all

    if missing:
        print(f"\nSkipped (missing or wrong type): {missing}", flush=True)
    if skipped_no_boxes:
        print(f"Skipped (no boxes after OCR): {len(skipped_no_boxes)}", flush=True)

    if not times:
        print("No timed runs.", flush=True)
        return 1

    n = len(times)
    scale_to = max(args.scale_to, 1)
    scale_factor = scale_to / n if n else 0.0
    sum_measured = sum(times)
    sum_scaled = sum_measured * scale_factor

    print("\n=== Summary (model + OCR corrector only; OCR not timed) ===", flush=True)
    print(f"Measured images:   {n}", flush=True)
    print(f"Sum (model+corr):  {sum_measured:.3f} s  (over {n} images)", flush=True)
    print(
        f"Scaled to {scale_to} img: ~{sum_scaled:.1f} s total model+corrector "
        f"(×{scale_factor:.2f} from {n} images)",
        flush=True,
    )
    print(f"Mean per image:    {statistics.mean(times)*1000:.1f} ms ({statistics.mean(times):.4f} s)", flush=True)
    print(f"Min:               {min(times)*1000:.1f} ms", flush=True)
    print(f"Max:               {max(times)*1000:.1f} ms", flush=True)
    if len(times) > 1:
        print(f"Stdev:             {statistics.stdev(times)*1000:.1f} ms", flush=True)
    print(
        f"\n(End-to-end wall {total_wall:.1f} s includes untimed OCR — omit from poster.)",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
