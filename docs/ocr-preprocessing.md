# Automatic OCR preprocessing

All uploaded images are **automatically** enhanced in the backend before EasyOCR runs. The user does not crop, rotate, or adjust anything.

## What runs (default)

1. **Resize**
   - If the short side is smaller than `OCR_PREPROCESS_TARGET_SHORT_EDGE` (default **1000 px**), the image is **upscaled** so small label text has more pixels.
   - If the long side would exceed `OCR_PREPROCESS_MAX_LONG_EDGE` (default **2400 px**), it is **downscaled** for speed and memory.

2. **Contrast (CLAHE)** on the L channel in LAB colour space — helps uneven lighting and low-contrast phone photos.

3. **Light denoise** — bilateral filter (fast, unlike heavy NLM on large images).

## Configuration (environment)

| Variable | Default | Meaning |
|----------|---------|---------|
| `OCR_PREPROCESS_ENABLED` | `true` | Set `false` to skip preprocessing (raw image to EasyOCR). |
| `OCR_PREPROCESS_TARGET_SHORT_EDGE` | `1000` | Upscale until min(height, width) ≥ this (before max-edge cap). |
| `OCR_PREPROCESS_MAX_LONG_EDGE` | `2400` | Maximum long side after resize. |

## Code

- `backend/services/ocr/preprocess.py` — `preprocess_image_for_ocr()`
- `backend/services/ocr/service.py` — called inside `extract_text_from_image()` before `readtext()`

## Automatic “crop”

True **ingredients-only** cropping without the user requires detecting the text block (e.g. layout model or heuristics). This pipeline processes the **full frame**; cropping can be added later as a separate step if needed.
