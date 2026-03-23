#!/usr/bin/env python3
"""
Update true_ingredients.json with Mistral OCR + LLM extraction results.

Reads each entry, runs Mistral OCR on the image, then LLM extraction,
and writes back the updated ocr_text + true_ingredients.
"""

import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.ocr import extract_text_from_image
from backend.services.ingredients_extraction import extract_ingredients_with_llm

TRUE_INGREDIENTS_PATH = PROJECT_ROOT / "tests" / "data" / "true_ingredients.json"
IMAGES_DIR = PROJECT_ROOT / "tests" / "data" / "images"
NEW_IMAGES_DIR = PROJECT_ROOT / "tests" / "data" / "new_images"


def find_image(name: str) -> Path | None:
    for d in [IMAGES_DIR, NEW_IMAGES_DIR]:
        p = d / name
        if p.exists():
            return p
    return None


def main() -> int:
    with open(TRUE_INGREDIENTS_PATH, encoding="utf-8") as f:
        data = json.load(f)

    total = len(data)
    updated = 0
    errors = 0

    for i, entry in enumerate(data, 1):
        name = entry["image"]
        img_path = find_image(name)

        if not img_path:
            print(f"  [{i}/{total}] {name} SKIP — image not found")
            continue

        try:
            image_data = img_path.read_bytes()

            ocr_text = extract_text_from_image(image_data, use_mistral_ocr=True)

            llm_result = extract_ingredients_with_llm(ocr_text)
            if llm_result["success"] and llm_result["ingredients"]:
                ingredients = llm_result["ingredients"]
            else:
                ingredients = entry.get("true_ingredients", [])
                print(f"  [{i}/{total}] {name} LLM failed, keeping existing true_ingredients")

            entry["ocr_text"] = ocr_text
            entry["true_ingredients"] = ingredients
            updated += 1

            print(f"  [{i}/{total}] {name} -> {len(ingredients)} ingredients")

        except Exception as e:
            errors += 1
            print(f"  [{i}/{total}] {name} ERROR: {e}")

    with open(TRUE_INGREDIENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nDone. {updated}/{total} updated, {errors} errors.")
    print(f"Saved to {TRUE_INGREDIENTS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
