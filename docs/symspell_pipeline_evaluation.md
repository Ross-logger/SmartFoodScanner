# Why the SymSpell pipeline scores low on benchmark metrics

This note explains why runs such as **~43% exact** / **~54% fuzzy** / **~50% merge F1** (macro-averaged over images) appear when using:

- [`extract_ingredients` (SymSpell)](/backend/services/ingredients_extraction/symspell_extraction.py)
- Cached Mistral-style OCR in [`tests/data/cached_mistral_ocr_results.json`](/tests/data/cached_mistral_ocr_results.json)
- Ground truth in [`tests/data/true_ingredients_for_llm.json`](/tests/data/true_ingredients_for_llm.json)
- Evaluation in [`scripts/compare_ingredients_accuracy.py`](/scripts/compare_ingredients_accuracy.py)

Low scores are expected from **stacked mismatch** between section detection, splitting, dictionary correction, and strict set-based scoring—not from a single SymSpell bug.

## 1. Cached OCR format vs regex section detection

[`extract_ingredients_section`](/backend/services/ingredients_extraction/non_ingredient_filter.py) walks **lines** and sets `in_ingredients_section` only when [`START_PATTERNS`](/backend/services/ingredients_extraction/non_ingredient_filter.py) match (e.g. `Ingredients:` / `ingredients` with optional colon, plus common OCR typos).

Cached Mistral text is often **Markdown-heavy** (`# …`, `## INGREDIENTS`, `**Ingredients:**`, tables, `![img-…]`). Headers like **`INSREDIENTS:`** (missing `G`) do not match normal `ingred…` patterns, so the scanner may **never** enter the ingredients block and **fall back to the full document** (see `if not ingredients_lines: return text` in `extract_ingredients_section`).

When the wrong span is used, splitting runs on nutrition text, disclaimers, and addresses—not the same boundaries as hand-labeled ground truth.

**Mitigation (implemented in code):** normalize Markdown heading/bold wrappers before matching start patterns, and add start patterns for common Mistral/typo headers (e.g. `INSREDIENTS`).

## 2. Stop / validation rules cut real lines or keep junk

[`STOP_PATTERNS`](/backend/services/ingredients_extraction/non_ingredient_filter.py) include phrases such as `best before`, `store in`, and `made in`. After the section has started, the **first line that matches a stop ends extraction**. On real labels, legal or marketing lines can appear near the list, which **reduces recall**. If section detection failed and the **full OCR** is used, **fewer** line-level stops apply in the right place, so **wrong spans** can survive and **hurt precision**.

[`is_valid_ingredient`](/backend/services/ingredients_extraction/non_ingredient_filter.py) also drops segments that hit stop-like or allergen-style rules, so long OCR clauses that mix ingredients with warnings may disappear or fragment oddly.

## 3. Delimiter-based splitting ≠ ground-truth item boundaries

[`_split_ingredients_text`](/backend/services/ingredients_extraction/symspell_extraction.py) splits on commas, `;`, `&`, and ` and ` / ` or ` **outside** parentheses. Ground truth is often **one row per ingredient** with nested `()`, `[]`, `{}`, INS/E-numbers, and the word “and” **inside** a single ingredient. The splitter’s tokens and human **granularity** diverge: you may get **too few** segments (a whole paragraph) or **too many** small fragments (e.g. dozens of tokens vs a short GT list).

## 4. Small dictionary + spell correction ≠ semantic extraction

SymSpell is loaded from [`FOOD_INGREDIENTS`](/backend/services/ingredients_extraction/data.py) (on the order of **~10³** terms). Ground truth strings are often **long legal phrases** (e.g. wheat/gluten declarations, Indian **INS** wording). [`_correct_text`](/backend/services/ingredients_extraction/symspell_extraction.py) maps text to dictionary entries; when the full line is not a known compound, **word-level** suggestions can drift to **plausible food words that are not the GT string**, collapsing **exact** overlap even when the output is “sort of” right.

## 5. Evaluation is strict and asymmetric on normalization

[`compare_ingredients_accuracy.py`](/scripts/compare_ingredients_accuracy.py) applies [`_normalize_for_comparison`](/scripts/compare_ingredients_accuracy.py) (e.g. stripping percentage-like substrings) **only to predicted** lists before [`calculate_precision` / `calculate_recall`](/tests/utils/metrics.py), which use **sets** of lowercased strings. Duplicates, punctuation, and **one long GT line vs several short predictions** all reduce overlap. **Fuzzy** matching (default threshold 0.8) helps but still fails on **long, structurally different** strings.

## 6. Why merge recall is much higher than split recall

[`calculate_merge_recall`](/tests/utils/metrics.py) checks whether each GT ingredient appears as a **substring** of the **joined** predicted text. A large **merge − split** recall gap means the **wording of GT often appears somewhere** in the noisy blob, but **not as the same token boundaries** as ground truth—consistent with (1)–(4), not with “OCR missed the ingredients entirely.”

---

## Bottom line

Low SymSpell benchmark scores are dominated by **pipeline–label mismatch** (section window + splitting + dictionary shaping) and **strict token/set evaluation**, amplified by **Mistral Markdown and typo headers** that classic regex sectioning was not originally designed for.

Improving headline metrics usually requires **aligning section detection and splitting with your OCR and label style**, **expanding or specializing the dictionary** for your corpus, and/or **adjusting evaluation** (e.g. symmetric normalization, chunking, or containment-aware metrics)—not only increasing SymSpell edit distance.
