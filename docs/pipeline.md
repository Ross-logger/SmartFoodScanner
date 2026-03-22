# SmartFoodScanner — App Pipeline

## Overview

The app has two scan modes. Both end at the same analysis step.

```
Image Upload  ──►  OCR  ──►  Ingredient Extraction  ──►  Dietary Analysis  ──►  Response
Barcode Scan  ──────────────────────────────────────►  Dietary Analysis  ──►  Response
```

---

## Image Scan Pipeline (`POST /scan/ocr`)

### Stage 1 — Image Preprocessing (EasyOCR path only)

**File:** `backend/services/ocr/preprocess.py`

Runs automatically before EasyOCR on every image. Skipped when TrOCR is used.

- **EXIF rotation** — applies the EXIF orientation tag so sideways iPhone photos are upright before OCR (`ImageOps.exif_transpose`)
- **Upscale** — if the shortest image edge is below 1000 px, the image is upscaled (helps with small text)
- **Downscale** — if the longest edge exceeds 2400 px, the image is downscaled (memory/speed)
- **CLAHE contrast enhancement** — equalises uneven lighting in the LAB colour space
- **Bilateral denoise** — light noise removal without blurring edges

Controlled by `OCR_PREPROCESS_ENABLED`, `OCR_PREPROCESS_TARGET_SHORT_EDGE`, `OCR_PREPROCESS_MAX_LONG_EDGE` in `.env`.

---

### Stage 2 — OCR (text extraction from pixels)

**File:** `backend/services/ocr/service.py` → `extract_text_from_image()`

Two engines, selectable per-user via `DietaryProfile.use_trocr`:

| Engine | How it works |
|---|---|
| **EasyOCR** (default) | Runs end-to-end on the preprocessed image. Detects and recognises text in one pass. |
| **TrOCR** | EasyOCR is used only to detect bounding boxes. Each cropped region is then fed to the `microsoft/trocr-large-printed` transformer for higher-quality recognition. Preprocessing is skipped because TrOCR works on the raw crop. |

Output: a raw multi-line string of all text found on the label (not yet split into ingredients).

> **There is no separate OCR correction stage.** The raw OCR string is passed directly to extraction. Any OCR errors must be handled either by SymSpell (Stage 3a) or by the LLM (Stage 3b).

---

### Stage 3 — Ingredient Extraction (OCR text → ingredient list)

Two paths, selectable per-user via `DietaryProfile.use_llm_ingredient_extractor`. If LLM extraction is enabled but the LLM call fails, it automatically falls back to SymSpell.

#### Path A — SymSpell (default)

**File:** `backend/services/ingredients_extraction/symspell_extraction.py` → `extract_ingredients()`

A purely local, offline pipeline. Four sequential steps:

1. **Section detection** (`non_ingredient_filter.extract_ingredients_section`) — scans the raw OCR text for an `INGREDIENTS:` header (with ~15 OCR-error variants handled) and discards everything outside that section (storage instructions, allergen warnings, website URLs, etc.)

2. **Delimiter splitting** (`_split_ingredients_text`) — splits the ingredients block on commas, semicolons, `&`, ` and `, ` or `. Respects parentheses, so `"Emulsifier (E322 and E476)"` stays as one token.

3. **Per-token spell correction** (`_correct_text`) — each token is looked up against a food-specific SymSpell dictionary (~1 199 food terms + E-numbers). Corrections within edit-distance 2 are accepted; word segmentation handles run-together OCR output. Unknown tokens are kept as-is.

4. **Validity filter** (`filter_ingredients`) — removes tokens that are clearly not ingredients: pure numbers, single characters, addresses, marketing phrases, etc. Percentage annotations (e.g. `(35%)`) are stripped from ingredient names.

#### Path B — LLM extraction

**File:** `backend/services/ingredients_extraction/llm_extraction.py` → `extract_ingredients_with_llm()`

The raw OCR string is sent as-is to the configured LLM (Groq / Gemini / OpenAI / Anthropic / Ollama / LM Studio). The prompt instructs the model to:

- Extract only actual food ingredients
- Translate non-English text to English
- Expand E-numbers where identifiable
- Return a clean JSON `{"ingredients": [...]}` array

**The LLM implicitly corrects OCR errors** as a side-effect of understanding context — it can infer that `"Whet Fleur"` means `"Wheat Flour"`. This is not a dedicated OCR correction stage; it is the extraction stage doing double duty.

No local dictionary or filtering is applied afterwards; the LLM output is used directly.

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
| `use_trocr` | Stage 2: EasyOCR end-to-end vs TrOCR hybrid |
| `use_llm_ingredient_extractor` | Stage 3: SymSpell (offline) vs LLM (online, falls back to SymSpell on failure) |

---

## Summary: does LLM fix OCR errors?

**Yes, indirectly.** When `use_llm_ingredient_extractor = True`, the raw OCR text (including any OCR typos) is handed to the LLM. The LLM's language understanding lets it recover from many OCR errors as part of extraction — e.g. `"Suqar"` → `"Sugar"`. This is not a dedicated correction stage; it happens inside the extraction prompt.

With the default SymSpell path, OCR errors are partially corrected by the dictionary lookup (edit-distance ≤ 2), but the correction is limited to known food terms.

**Neither path has a standalone OCR correction stage** that rewrites the OCR text before extraction. The `corrected_text` field stored in the database is currently set to the same value as `ocr_text`.
