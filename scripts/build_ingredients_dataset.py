#!/usr/bin/env python3
"""
Build image -> extracted ingredients dataset.

Processes all images in tests/data/images using the same extraction pipeline
as the scan API (OCR + SymSpell ingredient extraction) and saves results to
tests/data/ingredients_dataset.json and ingredients_dataset.csv.
"""

import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.ocr import extract_text_from_image, extract_ingredients

IMAGES_DIR = PROJECT_ROOT / "tests" / "data" / "images"
OUTPUT_JSON = PROJECT_ROOT / "tests" / "data" / "ingredients_dataset.json"
OUTPUT_CSV = PROJECT_ROOT / "tests" / "data" / "ingredients_dataset.csv"


def main() -> None:
    image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
    image_files = sorted(
        f for f in IMAGES_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in image_extensions
    )

    if not image_files:
        print(f"No images found in {IMAGES_DIR}")
        return

    print(f"Processing {len(image_files)} images from {IMAGES_DIR}...")

    dataset = []
    for i, img_path in enumerate(image_files):
        try:
            image_data = img_path.read_bytes()
            ocr_text = extract_text_from_image(image_data)
            ingredients = extract_ingredients(ocr_text)

            entry = {
                "image": img_path.name,
                "ocr_text": ocr_text,
                "extracted_ingredients": ingredients,
                "true_ingredients": list(ingredients),
            }
            dataset.append(entry)
            print(f"  [{i + 1}/{len(image_files)}] {img_path.name} -> {len(ingredients)} ingredients")

        except Exception as e:
            print(f"  [{i + 1}/{len(image_files)}] {img_path.name} ERROR: {e}")
            dataset.append({
                "image": img_path.name,
                "ocr_text": "",
                "extracted_ingredients": [],
                "true_ingredients": [],
                "error": str(e),
            })

    # Save JSON
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    print(f"\nSaved JSON: {OUTPUT_JSON}")

    # Save CSV (image, extracted_ingredients as comma-separated)
    import csv
    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["image", "extracted_ingredients"])
        for entry in dataset:
            ingredients = entry.get("extracted_ingredients", [])
            writer.writerow([entry["image"], ", ".join(ingredients)])

    print(f"Saved CSV: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
