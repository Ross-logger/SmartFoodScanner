#!/usr/bin/env python3
"""
Run EasyOCR + ingredient box classifier on a single image and print pipeline stages.

Outputs:
  1) OCR text — confidence-filtered lines joined with newlines (same as ``OCRResult.text``).
  2) Merged OCR text — every EasyOCR box in reading order (y, then x), newline-joined;
     no confidence filter (all non-empty boxes).
  3) Text after model + merge — ``extract_ingredients_from_boxes`` (classifier + merge + postprocess).
  4) Text after OCR correction — ``split_ingredients_text`` → ``correct_ingredient_list``,
     joined with ", " (same shape as the scan API ingredient string).

Usage (with .venv activated):

  From repo root (``SmartFoodScanner/``):
    python scripts/run_box_classifier_on_image.py tests/data/images/IMG_0028.png

  From another directory, pass the script by absolute path or ``../scripts/...``;
  image paths like ``tests/data/...`` are resolved from the repo root automatically:
    cd training && python ../scripts/run_box_classifier_on_image.py tests/data/images/IMG_0028.png
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend import settings  # noqa: E402
from backend.services.ingredients_extraction.ingredient_box_classifier import (  # noqa: E402
    _easyocr_results_to_dataframe,
    classify_boxes,
    extract_ingredients_from_boxes,
)
from backend.services.ingredients_extraction.ocr_corrector import correct_ingredient_list  # noqa: E402
from backend.services.ingredients_extraction.utils import split_ingredients_text  # noqa: E402
from backend.services.ocr import extract_ocr_from_image  # noqa: E402


def _merged_raw_ocr_text(raw_results: list) -> str:
    """All detection boxes in reading order, newline-separated (no confidence filter)."""
    df = _easyocr_results_to_dataframe(raw_results, image_id="cli")
    if df.empty:
        return ""
    df = df.sort_values(["y_center", "x1"]).reset_index(drop=True)
    return "\n".join(str(t).strip() for t in df["text"] if str(t).strip())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run EasyOCR + box classifier pipeline on one image and print stages."
    )
    parser.add_argument(
        "image",
        type=Path,
        help="Path to an image file (JPEG, PNG, WebP, etc.)",
    )
    parser.add_argument(
        "--no-ocr-corrector",
        action="store_true",
        help="Skip SymSpell/RapidFuzz correction (still split + cleanup path).",
    )
    args = parser.parse_args()

    # So relative image paths (e.g. tests/data/...) work when cwd is not the repo root.
    os.chdir(PROJECT_ROOT)

    path = args.image.expanduser().resolve()
    if not path.is_file():
        print(f"Error: not a file: {path}", file=sys.stderr)
        return 1

    image_bytes = path.read_bytes()
    print(f"Image: {path}")
    print(f"Model: {settings.BOX_CLASSIFIER_MODEL_PATH}")
    print(f"USE_OCR_CORRECTOR={settings.USE_OCR_CORRECTOR} (override with --no-ocr-corrector)\n")

    ocr_result = extract_ocr_from_image(image_bytes, use_mistral_ocr=False)
    raw = ocr_result.easyocr_raw_results or []

    print("=" * 72)
    print("1) OCR text (confidence-filtered lines, newline-joined)")
    print("=" * 72)
    print(ocr_result.text or "(empty)")
    print()

    print("=" * 72)
    print("2) Merged OCR text (all boxes, reading order, newline-joined)")
    print("=" * 72)
    merged_raw = _merged_raw_ocr_text(raw)
    print(merged_raw or "(empty)")
    print()

    if not raw:
        print("No EasyOCR raw boxes — cannot run box classifier.", file=sys.stderr)
        return 1

    df_boxes = classify_boxes(raw, image_id=path.stem)
    merged_model = extract_ingredients_from_boxes(df_boxes)

    print("=" * 72)
    print("3) Text after model + merge (classifier + region merge + postprocess)")
    print("=" * 72)
    print(merged_model or "(empty)")
    print()

    use_corr = settings.USE_OCR_CORRECTOR and not args.no_ocr_corrector
    candidates = split_ingredients_text(merged_model) if merged_model.strip() else []
    corrected_list = correct_ingredient_list(
        candidates,
        use_ocr_corrector=use_corr,
    )
    corrected_text = ", ".join(corrected_list)

    print("=" * 72)
    print(
        "4) Text after OCR correction (split → correct_ingredient_list → joined)"
    )
    print("=" * 72)
    if not merged_model.strip():
        print("(skipped — no merged text from step 3)")
    else:
        print(corrected_text or "(empty after correction / filtering)")
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
