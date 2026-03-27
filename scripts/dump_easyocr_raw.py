#!/usr/bin/env python3
"""
Print or JSON-dump raw EasyOCR readtext() output: (bbox, text, confidence) per detection.

Uses the same image preprocessing as backend OCR when OCR_PREPROCESS_ENABLED is true.
Does NOT apply OCR confidence filtering (shows all boxes).

Usage:
  python scripts/dump_easyocr_raw.py
  python scripts/dump_easyocr_raw.py --no_preprocess
  python scripts/dump_easyocr_raw.py IMG_0031.png in67.jpg
  python scripts/dump_easyocr_raw.py --json tests/data/easyocr_raw_results.json
  python scripts/dump_easyocr_raw.py --json out.json --images_dir path/to/images
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from PIL import Image, ImageOps

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import easyocr  # noqa: E402

from backend import settings  # noqa: E402
from backend.services.ocr.preprocess import preprocess_image_for_ocr  # noqa: E402

IMAGES_DIR = PROJECT_ROOT / "tests" / "data" / "images"

DEFAULT_IMAGES = [
    "IMG_0031.png",
    "IMG_0034.png",
    "IMG_0043.png",
    "IMG_0067.png",
    "in1.jpg",
    "in11.jpg",
    "in52.jpg",
    "in67.jpg",
    "in74.jpg",
    "in91.jpg",
]

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}


def _natural_sort_key(path: Path) -> List:
    parts = re.split(r"(\d+)", path.name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def _list_image_files(images_dir: Path) -> List[Path]:
    return sorted(
        (
            f
            for f in images_dir.iterdir()
            if f.is_file() and f.suffix.lower() in _IMAGE_EXTENSIONS
        ),
        key=_natural_sort_key,
    )


def _raw_to_serializable(raw: list) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in raw:
        if len(item) == 3:
            bbox, text, conf = item
        else:
            bbox, text = item[:2]
            conf = None
        corners = [[float(p[0]), float(p[1])] for p in bbox]
        row: Dict[str, Any] = {"bbox": corners, "text": text}
        if conf is not None:
            row["confidence"] = float(conf)
        out.append(row)
    return out


def _print_detections(name: str, raw: list) -> None:
    print("\n" + "=" * 80)
    print(f"IMAGE: {name}  |  detections: {len(raw)}")
    print("=" * 80)
    for i, item in enumerate(raw):
        if len(item) == 3:
            bbox, text, conf = item
        else:
            bbox, text = item[:2]
            conf = None
        print(f"\n  [{i}] confidence={conf}")
        print("      bbox (4 corners):")
        for j, pt in enumerate(bbox):
            print(f"         corner[{j}]: ({float(pt[0]):.2f}, {float(pt[1]):.2f})")
        xs = [float(p[0]) for p in bbox]
        ys = [float(p[1]) for p in bbox]
        print(
            f"      axis_aligned: x=[{min(xs):.1f}..{max(xs):.1f}]  "
            f"y=[{min(ys):.1f}..{max(ys):.1f}]  "
            f"w={max(xs) - min(xs):.1f} h={max(ys) - min(ys):.1f}"
        )
        print(f"      text: {text!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Dump raw EasyOCR readtext output.")
    parser.add_argument(
        "images",
        nargs="*",
        default=None,
        metavar="FILE",
        help=f"Basenames under --images_dir (default: 10 benchmark images, or all images with --json).",
    )
    parser.add_argument(
        "--images_dir",
        type=Path,
        default=IMAGES_DIR,
        help=f"Directory for image basenames (default: {IMAGES_DIR}).",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        metavar="OUT.json",
        help="Write one JSON object: filename -> list of {bbox, text, confidence}. "
        "With no positional images, processes every image file in --images_dir.",
    )
    parser.add_argument(
        "--no_preprocess",
        action="store_true",
        help="Skip CLAHE/resize (raw pixel array as RGB).",
    )
    args = parser.parse_args()

    images_dir: Path = args.images_dir
    if not images_dir.is_dir():
        print(f"Error: images directory not found: {images_dir}", file=sys.stderr)
        return 1

    if args.json is not None:
        if args.images:
            rel_paths = [images_dir / name for name in args.images]
        else:
            rel_paths = _list_image_files(images_dir)
    else:
        names = args.images if args.images is not None else DEFAULT_IMAGES
        rel_paths = [images_dir / name for name in names]

    reader = easyocr.Reader(["en"], gpu=settings.EASYOCR_USE_GPU)

    json_payload: Optional[Dict[str, Any]] = {} if args.json is not None else None
    if json_payload is not None:
        json_payload["_meta"] = {
            "images_dir": str(images_dir.resolve()),
            "preprocess": not args.no_preprocess and settings.OCR_PREPROCESS_ENABLED,
            "ocr_preprocess_target_short_edge": settings.OCR_PREPROCESS_TARGET_SHORT_EDGE,
            "ocr_preprocess_max_long_edge": settings.OCR_PREPROCESS_MAX_LONG_EDGE,
            "easyocr_gpu": settings.EASYOCR_USE_GPU,
        }

    total = len(rel_paths)
    for idx, path in enumerate(rel_paths, start=1):
        if not path.exists():
            print(f"\n### SKIP (missing): {path.name}\n", file=sys.stderr)
            continue
        img = Image.open(path)
        img = ImageOps.exif_transpose(img)
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img)
        if not args.no_preprocess and settings.OCR_PREPROCESS_ENABLED:
            arr = preprocess_image_for_ocr(
                arr,
                enabled=True,
                target_short_edge=settings.OCR_PREPROCESS_TARGET_SHORT_EDGE,
                max_long_edge=settings.OCR_PREPROCESS_MAX_LONG_EDGE,
            )
        raw = reader.readtext(arr)
        name = path.name
        if json_payload is not None:
            json_payload[name] = _raw_to_serializable(raw)
            print(f"  [{idx}/{total}] {name}  {len(raw)} detections", flush=True)
        else:
            _print_detections(name, raw)

    if json_payload is not None and args.json is not None:
        out_path: Path = args.json
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(json_payload, f, indent=2, ensure_ascii=False)
        print(f"Wrote {out_path.resolve()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
