# Accuracy Improvement Suggestions

Based on comparing **extracted ingredients** (from the SymSpell pipeline) with **ground truth** in `true_ingredients.json` and `ingredients_dataset.json`.

**Dataset:** 75 entries (filtered to only images present in `true_ingredients.json`).

**Current performance (exact match):**

- Precision: 84.7%
- Recall: 83.9%
- F1: 84.0%

**Fuzzy match (0.85 threshold):** 90.4% precision, 90.0% recall, 89.8% F1.

**Summary:** 57/75 (76%) perfect matches; 10 images with F1 < 0.5; 8 with F1 < 0.3.

**Worst performers (F1=0 or very low):** in0, in2, in10, in11, in24, in27, in35, in29, in23, in22, in1, in9.

---

## 1. Fix Allergen vs Ingredients Confusion

**Problem:** The system sometimes extracts from the allergen warning section instead of the ingredients list. Example: in0.jpg returns "wheat, gluten, egg, milk, tree nut walnut" (from "CONTAINS: WHEAT; GLUTEN, EGG, MILK & TREE NUT") instead of the actual ingredients (wheat flour, sugar, hydrogenated palm olein, etc.).

**Suggestions:**

- Add a **stop pattern** that cuts extraction as soon as you see "ALLERGEN", "CONTAINS:", or "CONTAINS:" followed by allergen-style text.
- Treat allergen sections as **separate** from ingredients. Extract allergens for trace warnings only, not as ingredients.
- If the label has both English and another language (e.g. French), detect the second "INGREDIENTS" / "INOREDIENTS" and extract only the first block before allergen text.

---

## 2. Improve Spell Correction for Common OCR Errors

**Problem:** OCR misreads characters (0/O, 1/l, 5/S, etc.), leading to wrong words that SymSpell does not correct. Examples: "colifornion" → "californian", "tamari" → "tamarind", "shellac" → "shell" (wrong), "jamun" → "kamut" (OCR misread), "corlander" → "coriander", "tapary" vs "tamari" for "moth dal".

**Suggestions:**

- Add **OCR-specific correction rules**: e.g. "0"↔"O", "1"↔"l", "5"↔"S" in common positions.
- Expand the **food dictionary** with variants and common OCR mistakes: "californian", "tamarind", "moth dal", "tapary beans", "coriander", "pomegranate juice" (not "rice"), "bread improvers" (not "cream improvers").
- Add a **pre-processing step** that fixes known OCR patterns (e.g. "6570" → "65%" when in a percentage context, "3896" → "38%").
- Consider a **phonetic or edit-distance** fallback for words that are close to known ingredients but not in the dictionary.

---

## 3. Fix Percentage and Number OCR Errors

**Problem:** OCR often misreads "%" as digits. Examples: "6570" instead of "65%", "3896" instead of "38%", "3096" instead of "30%".

**Suggestions:**

- Add a **post-processing rule**: if a segment ends with 2–4 digits that look like a percentage (e.g. 38, 65, 30), and the OCR text has similar patterns, replace with "%".
- Use **regex patterns** to detect "(\d{2,3})%" or "(\d{1,2}\d)%" and normalize them.
- When you see "(\d{4})" in an ingredient context (e.g. "Mango Pieces (6570)"), try interpreting as "65%" or "65.70%" based on context.

---

## 4. Split Merged Ingredients Correctly

**Problem:** Sometimes many ingredients are merged into one long string. Examples: in10.jpg (5 extracted vs 16 true), in29.jpg (6 extracted vs 15 true). The splitter treats commas/semicolons inside parentheses as part of the same segment, but layout or OCR can still glue segments together.

**Suggestions:**

- Improve **delimiter handling**: ensure " and ", " or ", ";", "," are split correctly even when text is poorly formatted.
- Add **length-based splitting**: if a segment is very long (>60 chars) and contains multiple known ingredient keywords, try splitting on internal commas.
- Handle **line breaks**: OCR may join lines; split on newlines when they separate clear ingredient-like phrases.
- For **nested structures** like "Breadcrumbs {Wheat Flour; Yeast; ...}", parse the braces and extract inner items as separate ingredients.

---

## 5. Remove Section Headers from Output

**Problem:** Headers like "ingrodlonts:", "ingnedienes", "ingredients:" sometimes appear in the extracted list.

**Suggestions:**

- Add **garbage patterns** for "ingred*", "ingrod*", "ingned*", "inoredients", etc.
- Strip any segment that **starts with** these patterns (with optional colon).
- Apply this **before** spell correction so "ingrodlonts" is not turned into a food term.

---

## 6. Expand the Food Dictionary

**Problem:** Missing or rare terms cause wrong corrections or no correction. Examples: "besan", "maida", "atta", "jaggery", "asafoetida", "ajwain", "moth dal", "channa dal", "polydextrose", "maltitol", "oligofructose", Indian/spice names.

**Suggestions:**

- Add **regional ingredients**: Indian (besan, maida, atta, jaggery, asafoetida, ajwain, dal types), Asian, etc.
- Add **additives and E-numbers**: more INS/E numbers and their names.
- Add **compound terms**: "fully hydrogenated palm oil", "refined palm olein oil", "isolated soy protein", etc.
- Add **common OCR variants** as dictionary entries with high frequency so they are preferred during correction.

---

## 7. Use Context for Ambiguous Terms

**Problem:** "fully hydrogenated oil" appears without the oil type; "palm" may be on another line. The system outputs "fully hydrogenated oil" but ground truth has "fully hydrogenated palm oil".

**Suggestions:**

- Use a **sliding window** or nearby lines: if "palm" appears within a few words of "oil" or "hydrogenated", attach it to that ingredient.
- Maintain a **context buffer**: when you see "oil" or "fat", check recent tokens for "palm", "vegetable", "soybean", etc.
- Add **compound-ingredient rules**: e.g. "hydrogenated oil" + nearby "palm" → "hydrogenated palm oil".

---

## 8. Improve Section Boundary Detection

**Problem:** Extraction starts too late or ends too early. Some labels have "Ingredients:" then blank lines, addresses, or multilingual blocks. STOP_PATTERNS may cut too early (e.g. before all ingredients) or too late (including addresses).

**Suggestions:**

- Make **START_PATTERNS** more robust: handle "INGREDIENTS", "Ingredicnt", "Ingnedienes", and similar OCR variants.
- Add **language detection**: if you see a second "INGREDIENTS" or "INOREDIENTS" in another language, stop the first block before it.
- Refine **STOP_PATTERNS**: "Store in", "Address", "Instructions" are good; avoid stopping on "contains" when it is part of "contains permitted preservative" (still ingredients).
- Consider **confidence-based** boundaries: use OCR confidence to decide when text is likely non-ingredient (addresses, instructions).

---

## 9. Handle Nested and Hierarchical Ingredients

**Problem:** Labels use brackets and braces for sub-ingredients, e.g. "Breadcrumbs {Wheat Flour; Yeast; Salt; ...}". The system sometimes keeps them as one block or splits incorrectly.

**Suggestions:**

- **Parse nested structures** explicitly: when you see `{` or `[`, extract items inside as separate ingredients.
- Use **parenthesis depth** correctly when splitting: split on top-level commas/semicolons only, but flatten nested items into the main list.
- For **composite ingredients** like "Choco Cream (36%) [Sugar, Vegetable Fat, ...]", extract both the parent and the inner list, or at least the inner list.

---

## 10. Consider LLM-Based Extraction for Hard Cases

**Problem:** SymSpell works well for clean text but struggles with heavy OCR noise, complex layouts, and multilingual labels.

**Suggestions:**

- Use **LLM extraction** as an option for users who need higher accuracy (already supported in the system).
- Implement a **hybrid approach**: run SymSpell first; if the result looks bad (e.g. very few ingredients, many unknown words, section headers in output), automatically fall back to LLM.
- Use **confidence scoring**: low confidence → suggest LLM extraction to the user.

---

## 11. Filter Non-Ingredient Text More Aggressively

**Problem:** Phrases like "beet beer salt contain peanuts", "1oo% natural", "for reference only", "Best Before", addresses, and distributor info sometimes appear in the output.

**Suggestions:**

- Add **NON_INGREDIENT_WORDS**: "natural", "reference", "distributor", "address", "picture", "product", etc.
- Add **percentage-only patterns**: "1oo%", "100% natural" as standalone segments to drop.
- Strengthen **GARBAGE_PATTERNS** for numeric-only or single-word segments that are not ingredients.
- Use **ALLERGEN_WARNING_PATTERNS** to exclude "Contains peanuts" when it is a warning, not an ingredient.

---

## 12. Normalize and Deduplicate Output

**Problem:** Similar ingredients appear in different forms: "wheat flour" vs "Wheat Flour", "salt" vs "iodized salt", duplicates from nested structures.

**Suggestions:**

- **Normalize case** (e.g. lowercase) before comparison and output.
- **Deduplicate** by normalizing and removing duplicates.
- **Merge variants** where appropriate: e.g. "salt" and "iodized salt" might be the same; keep the more specific one.
- **Standardize E-numbers**: "E322", "INS 322", "322" → one consistent format.

---

## Summary: Quick Wins vs Larger Changes


| Priority | Suggestion                                       | Effort |
| -------- | ------------------------------------------------ | ------ |
| High     | Fix allergen vs ingredients confusion            | Medium |
| High     | Add section headers to garbage filter            | Low    |
| High     | Expand food dictionary (Indian terms, compounds) | Low    |
| High     | Fix percentage OCR (e.g. 6570→65%)               | Low    |
| Medium   | Improve merged-ingredient splitting              | Medium |
| Medium   | Context for "palm oil" etc.                      | Medium |
| Medium   | OCR-specific spell rules                         | Medium |
| Lower    | Nested structure parsing                         | High   |
| Lower    | Hybrid SymSpell + LLM fallback                   | Medium |


Implementing the high-priority items first should noticeably improve accuracy, especially for the worst-performing images.

---

## Prioritized Action Plan (Post-Filter Evaluation)

Based on the 75-entry filtered evaluation, focus on these in order:

1. **Fix in0.jpg (allergen extraction)** – Highest impact. Stop at "ALLERGEN WARNING" / "CONTAINS:" and extract only the block before it.
2. **Fix in2.jpg, in29.jpg (section header in output)** – Add "ingrodlonts", "ingnedienes" to garbage filter; strip from start of segments.
3. **Fix in10.jpg, in11.jpg (merged ingredients)** – Improve splitting on semicolons and commas; handle long segments (>80 chars) by splitting on internal delimiters.
4. **Fix in1.jpg, in9.jpg (context + spell)** – "fully hydrogenated oil" + nearby "palm" → "fully hydrogenated palm oil"; "6570" → "65%"; "mango spices" → "mango pieces" + "65%"; remove false "lard".
5. **Fix in24.jpg, in27.jpg (spell)** – "colifornion" → "californian"; "shellac" → "shell" (OCR misread); add "1oo% natural" to garbage.
6. **Fix in22.jpg, in23.jpg (fragmented OCR)** – Tomato Paste vs "tomato date"; reassemble split E-numbers (260,#8330 → ins 260, ins 330); handle "green 259)" → "green chilli (25%)".
7. **Fix in35.jpg (trace text merged)** – "contains natural occuring sugar" should be in trace_warning only, not in ingredients.

