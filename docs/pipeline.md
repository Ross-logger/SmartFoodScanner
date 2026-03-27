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

> **There is no separate OCR correction stage.** The raw OCR string is passed directly to extraction. Any OCR errors must be handled either by SymSpell (Stage 3a) or by the LLM (Stage 3b).

---

### Stage 3 — Ingredient Extraction (OCR text → ingredient list)

Two paths, selectable per-user via `DietaryProfile.use_llm_ingredient_extractor`. If LLM extraction is enabled but the LLM call fails, it automatically falls back to HF section + SymSpell.

#### Path A — HF section + SymSpell (default when LLM is off)

**File:** `backend/services/ingredients_extraction/symspell_extraction.py` → `extract_ingredients()`

The scan API always uses **HF NER for section detection**, then SymSpell **only inside** the extraction step (segments are not returned separately). Steps:

1. **Section detection (HF NER)** — `hf_section_detection.extract_ingredients_list_hf` runs the `openfoodfacts/ingredient-detection` NER model. It **splices character ranges** from the original OCR so commas and other gaps between `ING` spans are preserved (not only tokenizer `word` joins). On failure or no `ING` entities, the full OCR string is used.

   The **regex** helper `non_ingredient_filter.extract_ingredients_section` remains for tests/scripts: `extract_ingredients(..., use_hf_section_detection=False)`.

2. **Delimiter splitting** (`_split_ingredients_text`) — internal only: splits the section text for per-segment processing.

3. **Per-segment validation and SymSpell** (`is_valid_ingredient`, `_correct_text`) — invalid segments (addresses, footers, etc.) are dropped before correction.

4. **Final filter and post-process** (`filter_ingredients`, `post_process_ingredients`) — per-segment cleanup.

5. **API shape** — segments are joined with `", "` and returned as **one** string: `INGREDIENTS: item1, item2, ...` inside a **one-element JSON array** (`ingredients` on the scan response). The app does not return a separate list item per ingredient for this path.

**LLM path:** the model still returns a JSON array of strings; `POST /scan/ocr` **joins** them with the same `INGREDIENTS: ...` single-block format for a consistent stored shape.

#### Path B — LLM extraction

**File:** `backend/services/ingredients_extraction/llm_extraction.py` → `extract_ingredients_with_llm()`

The raw OCR string is sent as-is to the configured LLM (Groq / Gemini / OpenAI / Anthropic / Ollama / LM Studio). The prompt instructs the model to:

- Extract only actual food ingredients
- Translate non-English text to English
- Expand E-numbers where identifiable
- Return a clean JSON `{"ingredients": [...]}` array

**The LLM implicitly corrects OCR errors** as a side-effect of understanding context — it can infer that `"Whet Fleur"` means `"Wheat Flour"`. This is not a dedicated OCR correction stage; it is the extraction stage doing double duty.

No local dictionary or filtering is applied afterwards. For **stored scans**, `POST /scan/ocr` joins the LLM array into the same single `INGREDIENTS: ...` block as Path A.

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
| `use_hf_section_detection` | Stored on profile (default true); **not** toggled in the app — scans always use HF NER for section detection when using Path A |
| `use_llm_ingredient_extractor` | Stage 3: LLM vs HF section + SymSpell (falls back to HF + SymSpell on LLM failure) |

---

## Summary: does LLM fix OCR errors?

**Yes, indirectly.** When `use_llm_ingredient_extractor = True`, the raw OCR text (including any OCR typos) is handed to the LLM. The LLM's language understanding lets it recover from many OCR errors as part of extraction — e.g. `"Suqar"` → `"Sugar"`. This is not a dedicated correction stage; it happens inside the extraction prompt.

With the default SymSpell path, OCR errors are partially corrected by the dictionary lookup (edit-distance ≤ 2), but the correction is limited to known food terms.

**Neither path has a standalone OCR correction stage** that rewrites the OCR text before extraction. The `corrected_text` field stored in the database is currently set to the same value as `ocr_text`.
