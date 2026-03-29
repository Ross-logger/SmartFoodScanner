# SmartFoodScanner — App Pipeline

## Overview

The app has two scan modes. Both end at the same analysis step.

```
Image Upload  ──►  OCR  ──►  Ingredient Extraction  ──►  Dietary Analysis  ──►  Response
Barcode Scan  ──────────────────────────────────────►  Dietary Analysis  ──►  Response
```

---

## Image Scan Pipeline (`POST /scan/ocr`)

### Stage 1 — Image Preprocessing

**File:** `backend/services/ocr/preprocess.py`

Runs automatically before EasyOCR on every image.

- **EXIF rotation** — applies the EXIF orientation tag so sideways iPhone photos are upright before OCR (`ImageOps.exif_transpose`)
- **Upscale** — if the shortest image edge is below 1000 px, the image is upscaled (helps with small text)
- **Downscale** — if the longest edge exceeds 2400 px, the image is downscaled (memory/speed)
- **CLAHE contrast enhancement** — equalises uneven lighting in the LAB colour space
- **Bilateral denoise** — light noise removal without blurring edges

Controlled by `OCR_PREPROCESS_ENABLED`, `OCR_PREPROCESS_TARGET_SHORT_EDGE`, `OCR_PREPROCESS_MAX_LONG_EDGE` in `.env`.

---

### Stage 2 — OCR (text extraction from pixels)

**File:** `backend/services/ocr/service.py` → `extract_text_from_image()`

Two engines, selectable per-user via `DietaryProfile.use_mistral_ocr`:

| Engine | How it works |
|---|---|
| **EasyOCR** (default) | Runs end-to-end locally on the preprocessed image. Detects and recognises text in one pass. |
| **Mistral OCR** | The original image is base64-encoded and sent to the Mistral AI cloud OCR API (`mistral-ocr-latest`). Preprocessing is skipped — the cloud model handles the raw image. Requires `MISTRAL_API_KEY` in `.env`. |

Output: a raw multi-line string of all text found on the label (not yet split into ingredients).

> **There is no separate OCR correction stage.** The raw OCR string is passed directly to extraction. Any OCR errors are handled by the LLM (Stage 3a) or the box classifier + OCR corrector (Stage 3b).

---

### Stage 3 — Ingredient Extraction (OCR text → ingredient list)

Two paths depending on user settings and OCR engine used.

#### Path A — LLM extraction

**File:** `backend/services/ingredients_extraction/llm_extraction.py` → `extract_ingredients_with_llm()`

The raw OCR string is sent as-is to the configured LLM (Groq / Gemini / OpenAI / Anthropic / Ollama / LM Studio). The prompt instructs the model to:

- Extract only actual food ingredients
- Translate non-English text to English
- Expand E-numbers where identifiable
- Return a clean JSON `{"ingredients": [...]}` array

**The LLM implicitly corrects OCR errors** as a side-effect of understanding context — it can infer that `"Whet Fleur"` means `"Wheat Flour"`. This is not a dedicated OCR correction stage; it is the extraction stage doing double duty.

#### Path B — Box classifier extraction (EasyOCR, when LLM is off)

**Files:** `backend/services/ingredients_extraction/ingredient_box_classifier.py`, `backend/services/ingredients_extraction/ocr_corrector.py`

When EasyOCR is used and LLM extraction is disabled, raw EasyOCR detection results (bounding boxes with text and confidence scores) are processed by the box classifier, which assigns ingredient probability to each box. Boxes above the threshold are merged into coherent ingredient text, split into candidates, and corrected via the OCR corrector (dictionary-constrained spelling correction and junk filtering).

If the box classifier produces no results, the system falls back to LLM extraction.

---

### Stage 4 — Dietary Analysis

**File:** `backend/services/ingredients_analysis/`

Takes the final ingredient list and the user's `DietaryProfile` and checks:

- Flagged allergens (gluten, dairy, nuts, etc.)
- Dietary restrictions (vegan, halal, kosher, …)
- User-defined banned ingredients

Returns `is_safe`, `warnings[]`, and a full `analysis_result`.

---

## Barcode Scan Pipeline (`POST /scan/barcode`)

```
Barcode  ──►  Open Food Facts lookup  ──►  ingredients[]  ──►  Dietary Analysis  ──►  Response
```

No OCR or extraction is performed. Ingredients come pre-parsed from the Open Food Facts API (`backend/services/barcode/`). Dietary Analysis (Stage 4) is identical to the image scan path.

---

## Per-User Settings (DietaryProfile)

| Field | Controls |
|---|---|
| `use_mistral_ocr` | Stage 2: local EasyOCR vs Mistral OCR cloud API |
| `use_llm_ingredient_extractor` | Stage 3: LLM extraction vs box classifier pipeline |

---

## Summary: does LLM fix OCR errors?

**Yes, indirectly.** When LLM extraction is used, the raw OCR text (including any OCR typos) is handed to the LLM. The LLM's language understanding lets it recover from many OCR errors as part of extraction — e.g. `"Suqar"` → `"Sugar"`. This is not a dedicated correction stage; it happens inside the extraction prompt.

With the box classifier path, OCR errors are corrected by the OCR corrector module (dictionary-constrained spelling correction).

**Neither path has a standalone OCR correction stage** that rewrites the OCR text before extraction. The `corrected_text` field stored in the database is currently set to the same value as `ocr_text`.
