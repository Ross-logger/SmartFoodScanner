#!/usr/bin/env python3
"""
Auto-label EasyOCR detection boxes as ingredient-section (1) or not (0).

Reads:
  - tests/data/easyocr_raw_results.json   (box-level OCR detections)
  - tests/data/true_ingredients.json       (ground-truth ingredient lists)

Outputs:
  - tests/data/ocr_box_labels.csv

Labeling strategy:
  For each image, join the ground-truth ingredients into a single lowercased
  reference string.  For each OCR box, check whether the box text (lowered,
  stripped) is a substring of the reference OR fuzzy-matches any ground-truth
  ingredient above a threshold.  Boxes matching are labeled 1; everything
  else is labeled 0.

  Known non-ingredient patterns (storage, allergen, nutrition, addresses)
  are force-labeled 0 regardless of fuzzy score.

After running, manually review the CSV (especially rows where the script
was unsure) and correct any mistakes before using as training data.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

RAW_RESULTS_PATH = PROJECT_ROOT / "tests" / "data" / "easyocr_raw_results.json"
GROUND_TRUTH_PATH = PROJECT_ROOT / "tests" / "data" / "true_ingredients.json"
OUTPUT_PATH = PROJECT_ROOT / "tests" / "data" / "ocr_box_labels.csv"

FUZZY_THRESHOLD = 0.55

_STOP_PATTERNS = re.compile(
    r"(?i)"
    r"(?:storage|store in|for best before|keep refriger|not suitable for freez)"
    r"|(?:nutrition|typical values?|energy k[jJ]|per 100|reference intake|saturates|trans fat|total fat|dietary fibre|sodium|carbohydrate)"
    r"|(?:allergen|allergy|for allergens|contains? (?:milk|wheat|soy|gluten|nuts?|peanut))"
    r"|(?:suitable for veg|vegan recipe|made in|distributed|marks and spencer|m&s|po box|dublin|ireland|united kingdom|kowloon|hong kong|wang chlu|marksandspencer)"
    r"|(?:recycle|fsc|film|box tray|best before|use by|bdd|amm|printed on pack|refer t)"
    r"|(?:serving|serve chilled|shake before|once opened)"
    r"|(?:fairtrade|certified|sourcing|mass balance|non-certified)"
    r"|(?:deliciously healthy|best enjoyed|lifestyle|balanced varied diet|high in fibre)"
    r"|(?:ingredients? in bold|not suitable for those)"
    r"|(?:sc\d{4}|ch99|9qs|po box|ravensdale)"
)

_HEADER_RE = re.compile(r"(?i)^(?:in[cg]re[dg]i[oe]n[ts]|incredients|ingredients?)[:;]?\s*$")

_JUNK_RE = re.compile(
    r"^[A-Z]{1,2}$"
    r"|^\d{1,5}$"
    r"|^[.\-,;:!?]+$"
    r"|^(?:mg|kJ|kcal|g|ml|kg)$"
)


def _bbox_corners(bbox: list) -> tuple:
    """Return (x1, y1, x2, y2) from 4-corner bbox."""
    xs = [p[0] for p in bbox]
    ys = [p[1] for p in bbox]
    return round(min(xs), 1), round(min(ys), 1), round(max(xs), 1), round(max(ys), 1)


def _is_stop(text: str) -> bool:
    return bool(_STOP_PATTERNS.search(text))


def _is_header(text: str) -> bool:
    return bool(_HEADER_RE.match(text.strip()))


def _is_junk(text: str) -> bool:
    return bool(_JUNK_RE.match(text.strip()))


def _fuzzy_match(needle: str, haystack_items: list[str], threshold: float) -> bool:
    needle_low = needle.lower().strip()
    if len(needle_low) < 2:
        return False
    for item in haystack_items:
        item_low = item.lower().strip()
        if needle_low in item_low or item_low in needle_low:
            return True
        ratio = SequenceMatcher(None, needle_low, item_low).ratio()
        if ratio >= threshold:
            return True
    return False


def _substring_in_joined(needle: str, joined: str) -> bool:
    n = needle.lower().strip().rstrip(".,;:)")
    if len(n) < 3:
        return False
    return n in joined


def label_image(image_name: str, detections: list, true_ingredients: list[str]) -> list[dict]:
    joined_gt = " ".join(t.lower() for t in true_ingredients)
    rows = []

    for i, det in enumerate(detections):
        text = det.get("text", "")
        conf = det.get("confidence", 0.0)
        bbox = det.get("bbox", [[0, 0], [0, 0], [0, 0], [0, 0]])
        x1, y1, x2, y2 = _bbox_corners(bbox)

        if not text or not text.strip():
            label = 0
        elif _is_header(text):
            label = 0
        elif _is_junk(text):
            label = 0
        elif _is_stop(text):
            label = 0
        elif _substring_in_joined(text, joined_gt):
            label = 1
        elif _fuzzy_match(text, true_ingredients, FUZZY_THRESHOLD):
            label = 1
        else:
            label = 0

        rows.append({
            "image_id": image_name,
            "box_id": i,
            "text": text,
            "confidence": round(conf, 6),
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "label": label,
        })

    return rows


def main() -> int:
    with open(RAW_RESULTS_PATH, encoding="utf-8") as f:
        raw = json.load(f)

    with open(GROUND_TRUTH_PATH, encoding="utf-8") as f:
        gt_list = json.load(f)

    gt_by_image = {e["image"]: e.get("true_ingredients", []) for e in gt_list}

    all_rows: list[dict] = []
    images_labeled = 0

    for image_name, detections in raw.items():
        if image_name.startswith("_"):
            continue
        true_ing = gt_by_image.get(image_name, [])
        if not true_ing:
            continue
        rows = label_image(image_name, detections, true_ing)
        all_rows.extend(rows)
        images_labeled += 1

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["image_id", "box_id", "text", "confidence", "x1", "y1", "x2", "y2", "label"],
        )
        writer.writeheader()
        writer.writerows(all_rows)

    total_boxes = len(all_rows)
    pos = sum(1 for r in all_rows if r["label"] == 1)
    neg = total_boxes - pos
    print(f"Labeled {total_boxes} boxes across {images_labeled} images")
    print(f"  label=1 (ingredient): {pos}  ({100*pos/total_boxes:.1f}%)")
    print(f"  label=0 (other):      {neg}  ({100*neg/total_boxes:.1f}%)")
    print(f"Output: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
