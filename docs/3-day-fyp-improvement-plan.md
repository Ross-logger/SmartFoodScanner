# 3-Day FYP Improvement Plan

**Current status:** ~53% precision, ~47% recall (split). Merge recall ~72% → **~25% loss from splitting error**.

**Target:** 65%+ precision, 60%+ recall.

---

## Day 1: Quick Wins (4–6 hours)

### 1.1 Stop all allergen text from being extracted (HIGH IMPACT)

**Problem:** in0, in35, in90 extract from "CONTAINS: wheat, milk..." instead of the real ingredients list.

**Fix:** In `non_ingredient_filter.py`, strengthen `extract_ingredients_section()` so it stops before allergen lines.

**Steps:**
1. In `extract_ingredients_section()`, when a line matches `CONTAINS:` followed by allergen words (wheat, gluten, milk, egg, nut, soy, tree), stop extraction.
2. Add a stronger STOP for `CONTAINS NATURALLY OCCURRING` / `CONTAINS NATURALLY OCCURING SUGARS`.
3. For multilingual labels (e.g. in0 with French), stop at the first `INSTRUCTIONS:` or `AVERTISSEMENT` / `INOREDIENTS` (second language).

**Files:** `backend/services/ingredients_extraction/non_ingredient_filter.py`

**Expected gain:** +5–10% recall on in0, in35, in90.

---

### 1.2 Fix long-segment splitting (HIGH IMPACT)

**Problem:** in10 (5 extracted vs 16 true), in48 (2 vs 7), in29 (6 vs 15). Merge recall is high but split recall is low → text is there but merged.

**Fix:** In `symspell_extraction.py`, after `_split_ingredients_text()`, add a second pass: if a segment is >60 chars and contains commas/semicolons, split it again.

**Steps:**
1. In `extract_ingredients_section()` or in `_split_ingredients_text()`, add a post-processing step:
   - For each segment with length > 60 chars:
   - Split on `,` and `;` (ignore paren depth for this pass, or use a simpler split).
   - Append the sub-segments to the result.
2. Optionally: split on newlines inside long segments (OCR sometimes joins lines).

**Files:** `backend/services/ingredients_extraction/symspell_extraction.py`

**Expected gain:** +5–10% recall on in10, in48, in29, in82, in83.

---

### 1.3 Add more garbage patterns

**Problem:** "1oo% natural", "for reference only", "allergen advice contains oats" still appear.

**Fix:** Add to `GARBAGE_PATTERNS` and `ALLERGEN_WARNING_PATTERNS` and `VALIDATION_GARBAGE_PATTERNS`:
- `allergen advice contains`
- `allergen info contains`
- `for reference only`
- `nothing else`
- `no preservatives`
- `additives used`

**Files:** `backend/services/ingredients_extraction/non_ingredient_filter.py`

**Expected gain:** +2–3% precision.

---

## Day 2: Splitting and Boundaries (4–6 hours)

### 2.1 Split on newlines in ingredients section

**Problem:** OCR often joins lines with spaces. "tomato pureed salt tamarind concentrate" as one blob when it should be 3–4 items.

**Fix:** In `extract_ingredients_section()`, before splitting by comma/semicolon, split the raw text by newlines first. Keep each line as a logical unit, then split each line by `,` and `;` (respecting parens).

**Files:** `backend/services/ingredients_extraction/non_ingredient_filter.py`, `symspell_extraction.py`

**Expected gain:** +3–5% recall.

---

### 2.2 Parse nested brackets `{` `[`

**Problem:** "Breadcrumbs {Wheat Flour; Yeast; Salt}" stays as one segment.

**Fix:** In `_split_ingredients_text()`, add handling for `{` and `[`:
- When you see `{` or `[`, treat the content inside as a separate block.
- Split on `;` and `,` inside that block.
- Flatten the inner items into the main list.
- For "Choco Cream (36%) [Sugar, Vegetable Fat, ...]", extract the inner list.

**Files:** `backend/services/ingredients_extraction/symspell_extraction.py`

**Expected gain:** +2–4% recall on in31, in32, in52.

---

### 2.3 Improve section boundary detection

**Problem:** Extraction starts too late or includes non-ingredient text.

**Fix:**
- Add more START_PATTERNS for OCR variants (e.g. "Ingredicnt", "Ingnedienes").
- Add STOP for `CONTAINS:` when followed by allergen list.
- Add STOP for `CONTAINS PERMITTED` when it's a preservative notice (optional – keep as ingredient if it’s a preservative name).

**Files:** `backend/services/ingredients_extraction/non_ingredient_filter.py`

**Expected gain:** +2–3% precision/recall.

---

## Day 3: Polish and Report (4–6 hours)

### 3.1 Add more food dictionary entries

**Problem:** OCR variants: "cococa", "corlander", "colifornion", "pomegranate rice", "cream improvers".

**Fix:** Add to `common_ingredients.py`:
- OCR variants: "cococa", "corlander", "colifornion", "pomegranate rice", "cream improvers", "raisin agents" (for raising agents), "squid glucose" (liquid).
- Compound terms: "greek yogurt", "processed blueberry pulp", "active culture", "live cultures".

**Files:** `backend/services/ingredients_extraction/data/common_ingredients.py`

**Expected gain:** +2–4% recall.

---

### 3.2 Context for oil/fat types (optional)

**Problem:** "fully hydrogenated oil" without "palm" when "palm" is on the next line.

**Fix:** In `extract_ingredients_section()` or in `_split_ingredients_text()`, add a post-pass: if a segment ends with "oil" or "fat" and the next segment (or nearby) is "palm", "vegetable", "soybean", etc., merge them.

**Files:** `backend/services/ingredients_extraction/symspell_extraction.py`

**Expected gain:** +1–2% recall on in1.

---

### 3.3 Run evaluation and document

**Steps:**
1. Run `python scripts/compare_ingredients_accuracy.py` after each change.
2. Record before/after metrics.
3. Update FYP report with:
   - Baseline metrics
   - Changes made
   - Final metrics
   - Discussion of splitting error (merge vs split gap)

---

## Summary Table

| Day | Task | Effort | Expected gain |
|-----|------|--------|---------------|
| 1 | Stop allergen extraction | 1–2 h | +5–10% recall |
| 1 | Long-segment splitting | 2–3 h | +5–10% recall |
| 1 | More garbage patterns | 30 min | +2–3% precision |
| 2 | Split on newlines | 1–2 h | +3–5% recall |
| 2 | Nested brackets | 2–3 h | +2–4% recall |
| 2 | Section boundaries | 1 h | +2–3% |
| 3 | Dictionary expansion | 1 h | +2–4% recall |
| 3 | Context for oil (optional) | 1 h | +1–2% recall |
| 3 | Evaluation + report | 2–3 h | — |

---

## If Time is Short

**Minimum viable (Day 1 only):**
1. Stop allergen extraction
2. Long-segment splitting (>60 chars)

**These two should give ~10–15% recall improvement.**

---

## Files to Modify

| File | Changes |
|------|---------|
| `non_ingredient_filter.py` | STOP_PATTERNS, GARBAGE_PATTERNS, extract_ingredients_section |
| `symspell_extraction.py` | _split_ingredients_text, long-segment split, nested brackets |
| `common_ingredients.py` | Add OCR variants and compound terms |

---

## Testing

After each change:
```bash
python scripts/compare_ingredients_accuracy.py
```

Check:
- Split precision/recall
- Merge recall (should stay high if splitting improves)
- Split gap (merge - split) – should decrease as splitting improves
