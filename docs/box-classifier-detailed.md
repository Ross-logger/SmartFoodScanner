# Box Classifier — Detailed Technical Explanation

This document explains every step of the ingredient box classifier pipeline in detail: how the model detects ingredient text, how boxes are filtered, how spatial clustering works, and how the final ingredient string is reconstructed.

---

## Table of Contents

1. [High-Level Overview](#1-high-level-overview)
2. [Stage 1 — EasyOCR Input](#2-stage-1--easyocr-input)
3. [Stage 2 — Converting Raw Boxes to a DataFrame](#3-stage-2--converting-raw-boxes-to-a-dataframe)
4. [Stage 3 — Building Context (Reading Order)](#4-stage-3--building-context-reading-order)
5. [Stage 4 — Feature Extraction](#5-stage-4--feature-extraction)
   - [4a. TF-IDF Character N-Grams](#4a-tf-idf-character-n-grams)
   - [4b. Manual (Hand-Crafted) Features](#4b-manual-hand-crafted-features)
   - [4c. Feature Concatenation](#4c-feature-concatenation)
6. [Stage 5 — Binary Classification (Logistic Regression)](#6-stage-5--binary-classification-logistic-regression)
7. [Stage 6 — Box Filtering](#7-stage-6--box-filtering)
   - [6a. Probability Threshold Filter](#6a-probability-threshold-filter)
   - [6b. Header Row Removal](#6b-header-row-removal)
   - [6c. Junk Fragment Removal](#6c-junk-fragment-removal)
   - [6d. Non-Ingredient Hint Filter](#6d-non-ingredient-hint-filter)
   - [6e. Header Constraint (Spatial)](#6e-header-constraint-spatial)
   - [6f. Isolated Box Removal](#6f-isolated-box-removal)
8. [Stage 7 — Spatial Clustering](#8-stage-7--spatial-clustering)
   - [7a. Row Clustering](#7a-row-clustering)
   - [7b. Merging Close Clusters](#7b-merging-close-clusters)
   - [7c. Cluster Scoring & Selection](#7c-cluster-scoring--selection)
9. [Stage 8 — Text Reconstruction](#9-stage-8--text-reconstruction)
   - [8a. Row Assignment (Fine-Grained)](#8a-row-assignment-fine-grained)
   - [8b. Row-Level Cleanup](#8b-row-level-cleanup)
   - [8c. Smart Text Joining](#8c-smart-text-joining)
10. [Stage 9 — Post-Processing](#10-stage-9--post-processing)
    - [9a. Tail Trimming by Hints](#9a-tail-trimming-by-hints)
    - [9b. Trailing Junk Line Removal](#9b-trailing-junk-line-removal)
    - [9c. Text Normalisation](#9c-text-normalisation)
11. [Stage 10 — Splitting & OCR Correction](#11-stage-10--splitting--ocr-correction)
12. [Model Training Summary](#12-model-training-summary)
13. [End-to-End Example](#13-end-to-end-example)

---

## 1. High-Level Overview

A food label image contains many pieces of text: product name, nutritional tables, barcodes, marketing claims, storage instructions — and somewhere among them, the ingredients list. The box classifier's job is to **identify which specific text regions belong to the ingredients list** and stitch them back together into a single clean string.

```
Image
  → EasyOCR (produces ~20-80 text boxes per image)
  → Feature Extraction (per box)
  → Logistic Regression (ingredient probability per box)
  → Filtering (remove non-ingredient boxes)
  → Spatial Clustering (group surviving boxes into regions)
  → Cluster Scoring (pick the best region = the ingredients list)
  → Text Reconstruction (merge boxes back into readable text)
  → Post-Processing (trim noise, normalise)
  → Split + OCR Correction (final ingredient list)
```

---

## 2. Stage 1 — EasyOCR Input

**Source:** `backend/services/ocr/service.py`

EasyOCR runs on the preprocessed image and returns a list of detections. Each detection is a tuple:

```python
(bbox, text, confidence)
# bbox = [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]  — four corner coordinates
# text = "Sugar, Wheat Flour"                      — recognised text string
# confidence = 0.87                                 — OCR confidence score (0.0–1.0)
```

A typical food label produces 20–80 such boxes. Each box corresponds to a contiguous line or fragment of text that EasyOCR was able to detect and recognise.

---

## 3. Stage 2 — Converting Raw Boxes to a DataFrame

**Function:** `_easyocr_results_to_dataframe()`

Each raw EasyOCR tuple is converted into a structured row with geometric properties:

| Column | How it is calculated |
|---|---|
| `x1` | Minimum x across all 4 corner points (left edge) |
| `y1` | Minimum y across all 4 corner points (top edge) |
| `x2` | Maximum x across all 4 corner points (right edge) |
| `y2` | Maximum y across all 4 corner points (bottom edge) |
| `width` | `x2 - x1` |
| `height` | `y2 - y1` |
| `x_center` | `(x1 + x2) / 2` — horizontal midpoint |
| `y_center` | `(y1 + y2) / 2` — vertical midpoint |
| `text` | The recognised text string (stripped of whitespace) |
| `confidence` | The OCR confidence score |
| `image_id` | Identifier for the image (used when processing batches) |
| `box_id` | Sequential index of the box |

Empty text boxes are discarded. The bounding box is simplified from a quadrilateral (4 corners) to an axis-aligned rectangle (min/max of x and y coordinates).

---

## 4. Stage 3 — Building Context (Reading Order)

**Function:** `_add_context_columns()`

A single box's text in isolation is often ambiguous. "Sugar" could be an ingredient or part of "Sugar content: 12g" in a nutrition table. To disambiguate, the classifier needs to see **what text is above and below each box** — its reading-order context.

### How reading order is established:

1. Boxes are **sorted by `y_center` (top to bottom), then by `x1` (left to right)** within each image. This simulates a human reading a label from top-left to bottom-right.
2. For each box, the **previous box's text** (`prev_text`) and **next box's text** (`next_text`) in this order are recorded.
3. These are concatenated into a single `context_text` string using `[SEP]` tokens as delimiters:

```
context_text = "{prev_text} [SEP] {current_text} [SEP] {next_text}"
```

**Example:** If three consecutive boxes read "Ingredients:", "Sugar, Wheat Flour, Salt", and "Nutrition Information", the middle box gets:

```
"Ingredients: [SEP] Sugar, Wheat Flour, Salt [SEP] Nutrition Information"
```

This gives the classifier a **3-box sliding window** of textual context.

---

## 5. Stage 4 — Feature Extraction

The classifier uses **two complementary feature sets** that are concatenated into a single sparse feature vector per box.

### 4a. TF-IDF Character N-Grams

**Vectoriser:** `TfidfVectorizer(analyzer="char", ngram_range=(3, 5), min_df=2)`

Instead of splitting `context_text` into words, it is split into **overlapping character sequences** of length 3, 4, and 5. For example, the text `"Sugar"` produces character n-grams:

- 3-grams: `"Sug"`, `"uga"`, `"gar"`
- 4-grams: `"Suga"`, `"ugar"`
- 5-grams: `"Sugar"`

**Why character n-grams instead of words?**

- **OCR-robust:** Misspelled words like `"Suqar"` still share most character n-grams with `"Sugar"`, so the model can still recognise it.
- **Sub-word patterns:** Ingredient suffixes like `"-ose"` (glucose, fructose, sucrose), `"-ate"` (sodium benzoate), or `"-in"` (lecithin, casein) are captured as character patterns.
- **Language-agnostic:** No need for tokenisation rules; works equally well for E-numbers like `"E330"`.

Each n-gram is weighted by **TF-IDF** (Term Frequency–Inverse Document Frequency): n-grams that appear in many boxes get down-weighted, while n-grams distinctive to ingredients are amplified.

The `context_text` (not just the current box text) is vectorised, so the TF-IDF features capture patterns like "the word 'Ingredients:' appearing in the previous box".

### 4b. Manual (Hand-Crafted) Features

**Function:** `_make_manual_features()`

23 hand-crafted features per box, organised into four groups:

#### Text statistics (current box):

| Feature | Description | Rationale |
|---|---|---|
| `ocr_confidence` | EasyOCR's confidence (0.0–1.0) | Low confidence = noisy/unclear text, less likely to be clean ingredient text |
| `char_len` | Number of characters | Ingredient lines tend to be medium-length; very short = fragment, very long = paragraph |
| `word_count` | Number of words | Similar to char_len but at word level |
| `digit_count` | Count of digit characters | High digit count → nutritional table ("12g", "5%") rather than ingredients |
| `comma_count` | Count of commas | Ingredient lists are comma-separated; high comma count is a strong signal |
| `percent_count` | Count of `%` symbols | Percentages appear in nutrition facts, not usually in ingredient lists |
| `paren_count` | Count of `(` and `)` | Ingredients often have parenthetical sub-ingredients like "Emulsifier (Soy Lecithin)" |
| `colon_count` | Count of `:` characters | Headers like "Ingredients:" contain colons |
| `is_all_caps` | Whether text is entirely uppercase | All-caps text is often headings or warnings, not ingredient body text |

#### Keyword hint features (current box):

| Feature | Description |
|---|---|
| `has_ingredient_hint` | Does the text contain any of 26 common ingredient keywords? (sugar, salt, oil, flour, milk, wheat, water, glucose, butter, lecithin, etc.) |
| `has_noningredient_hint` | Does the text contain any of 21 non-ingredient keywords? (storage, nutrition, energy, protein, allergens, manufactured, etc.) |
| `has_header_hint` | Does the text match an ingredients header? ("ingredients", "ingredients:", etc.) |

#### Context keyword hints (previous and next box):

The same three keyword features are computed for `prev_text` and `next_text`, giving 6 additional features:

- `prev_has_ingredient_hint`, `prev_has_noningredient_hint`, `prev_has_header_hint`
- `next_has_ingredient_hint`, `next_has_noningredient_hint`, `next_has_header_hint`

These are critical: a box that follows a header box (`prev_has_header_hint = 1`) and is followed by another ingredient box (`next_has_ingredient_hint = 1`) is very likely an ingredient.

#### Geometric features:

| Feature | Description | Rationale |
|---|---|---|
| `width` | Box width in pixels | Ingredient list lines tend to have consistent, moderate width |
| `height` | Box height in pixels | Consistent font size → consistent height |
| `x_center` | Horizontal midpoint | Ingredient lists are typically in a specific column/region of the label |
| `y_center` | Vertical midpoint | Vertical position can distinguish ingredients (middle of label) from headers (top) or storage instructions (bottom) |

These features are encoded as a sparse matrix using `DictVectorizer`.

### 4c. Feature Concatenation

The TF-IDF matrix and the manual feature matrix are horizontally stacked using `scipy.sparse.hstack`:

```
X = [TF-IDF features | Manual features]
```

This gives a single sparse feature vector per box that combines textual patterns with structural/geometric signals.

---

## 6. Stage 5 — Binary Classification (Logistic Regression)

**Model:** `sklearn.linear_model.LogisticRegression(max_iter=4000, class_weight="balanced")`

The model outputs a **probability** that each box is an ingredient box:

```python
probs = classifier.predict_proba(X)[:, 1]  # P(ingredient) per box
```

A **decision threshold** (tuned during training, not fixed at 0.5) converts probabilities to binary labels:

```python
pred_label = (probs >= threshold).astype(int)
# 1 = ingredient box, 0 = non-ingredient box
```

**Why logistic regression?**

- Fast inference (milliseconds for ~50 boxes)
- Interpretable (coefficients show which features matter)
- Works well with sparse TF-IDF features
- `class_weight="balanced"` handles the class imbalance (most boxes on a label are NOT ingredients)

**Why a tuned threshold?**

The default threshold of 0.5 maximises accuracy, but for this task **recall matters more** — missing an ingredient box is worse than including a non-ingredient box (which can be filtered later). The threshold is tuned on validation data to maximise F1-score, typically landing around 0.35–0.50.

---

## 7. Stage 6 — Box Filtering

After classification, several filtering steps remove boxes that are unlikely to be useful ingredient text, even if the model gave them a moderate probability.

### 6a. Probability Threshold Filter

**Function:** `filter_positive_boxes(df, threshold=0.4)`

Only boxes with `pred_prob >= 0.4` are kept. This is a **lenient** threshold — it keeps boxes that the model is only moderately confident about, because subsequent stages can clean up false positives more easily than they can recover missed boxes.

### 6b. Header Row Removal

```python
pos = pos[~pos["text"].apply(is_header)]
```

Boxes that match header patterns like `"Ingredients:"`, `"Ingredients"`, `"List of Ingredients:"` are removed. The header itself is not an ingredient — it just labels the section. These patterns are matched using regex:

```python
HEADER_PATTERNS = [
    r"^\s*ingredients?\s*:?\s*$",
    r"^\s*(list|table)\s+of\s+ingredients?\s*:?\s*$",
    r"^\s*ingredients?\s+list\s*:?\s*$",
]
```

The header box is **still recorded** for later use as a spatial anchor (see 6e).

### 6c. Junk Fragment Removal

```python
pos = pos[~(pos["text"].apply(looks_like_junk_fragment) & (pos["pred_prob"] < 0.8))]
```

Boxes identified as "junk fragments" are removed **unless** the model is very confident (>0.8) they are ingredients. A box is considered junk if:

- It is empty or has ≤2 characters
- More than 75% of its characters are digits (e.g. "12345")
- Less than 25% alphabetic and ≤6 characters long (e.g. "3.5g")
- High symbol ratio and short (e.g. "---" or "//")
- Alphanumeric-only short string with low alpha ratio (e.g. "V2.1")

This prevents numeric fragments from nutritional tables or stray OCR noise from polluting the ingredient text.

### 6d. Non-Ingredient Hint Filter

```python
pos = pos[~(pos["text"].apply(has_bad_hint) & (pos["pred_prob"] < 0.92))]
```

Boxes containing text from a comprehensive list of ~80 non-ingredient phrases are removed unless the model confidence exceeds 0.92. These phrases include:

- **Nutritional:** "nutrition facts", "energy", "protein", "calories", "per 100g", "serving size"
- **Allergen warnings:** "allergen advice", "may also contain", "traces of"
- **Storage/dates:** "store in a cool", "best before", "use by", "refrigerate after opening"
- **Legal/contact:** "manufactured by", "distributed by", "www.", ".com", "customer service"

The very high threshold (0.92) means that even if a box does contain one of these phrases, it is only removed if the model was not extremely confident it is an ingredient.

### 6e. Header Constraint (Spatial)

**Function:** `apply_header_constraint()`

If a header box like "Ingredients:" was found, any surviving boxes **above the header** (minus a 25px tolerance) are removed. The logic: ingredients always appear *after* their header on a label, never before it.

```python
cutoff = header_y_center - 25.0  # 25px tolerance for slight overlap
pos = pos[pos["y_center"] >= cutoff]
```

### 6f. Isolated Box Removal

**Function:** `remove_isolated_boxes(y_radius=120, x_radius=900)`

A box is considered "isolated" if it has **no neighbours** within 120px vertically and 900px horizontally. Ingredient boxes tend to cluster together (because the ingredients list is a contiguous block of text). A lone box far from any other positive box is likely a false positive.

Exceptions: boxes with high confidence (≥0.75) or boxes that look like continuations (start with parentheses, commas, or connectors like "and", "with") are never removed.

---

## 8. Stage 7 — Spatial Clustering

After filtering, the remaining boxes need to be grouped into coherent regions. A label might have ingredient text in one area and the model might have a few surviving false positives scattered elsewhere.

### 7a. Row Clustering

**Function:** `cluster_boxes_by_rows(pos, row_gap=90.0)`

Boxes are sorted by `y_center` (top to bottom), then `x1` (left to right). A new cluster starts whenever the vertical gap between consecutive boxes exceeds `row_gap` (90 pixels):

```
Box A (y=100) ──┐
Box B (y=115) ──┤ Cluster 1 (gap ≤ 90px between consecutive boxes)
Box C (y=140) ──┘
                   gap = 250px → new cluster
Box D (y=390) ──┐
Box E (y=410) ──┤ Cluster 2
Box F (y=435) ──┘
```

This groups boxes that are physically close together on the label.

### 7b. Merging Close Clusters

**Function:** `merge_close_clusters(clusters, cluster_gap=120.0)`

Adjacent clusters whose bottom-to-top distance is ≤120px are merged. This handles cases where a slightly larger gap within the ingredient list (e.g. around a sub-heading or line break) initially split it into two clusters.

```
Cluster 1 (bottom y2 = 300)
                              gap = 80px ≤ 120px → MERGE into one cluster
Cluster 2 (top y1 = 380)
```

### 7c. Cluster Scoring & Selection

**Function:** `score_cluster()` and `choose_best_cluster()`

Each cluster receives a score:

```python
score = sum(pred_prob)          # Sum of ingredient probabilities: reward confident ingredient boxes
     + 0.18 * box_count         # Bonus for cluster size: ingredient lists tend to be large
     - 0.8 * bad_hint_count     # Penalty for non-ingredient phrases present in the cluster
     + min(avg_text_len/50, 0.6)# Bonus for longer text per box: ingredient text is descriptive
     - 0.002 * dist_to_header   # Penalty for distance from header: ingredients are near their header
```

**Scoring rationale:**

- **`sum(pred_prob)`**: The core signal. A cluster of 10 boxes each with 0.9 probability scores much higher than a cluster of 3 boxes with 0.5 probability.
- **`0.18 * box_count`**: Ingredient lists typically span many lines; this biases towards larger clusters.
- **`-0.8 * bad_hint_count`**: Penalises clusters contaminated with nutritional or legal text.
- **`min(avg_text_len / 50, 0.6)`**: Ingredient descriptions tend to be longer than fragments; this rewards meaningful text.
- **`-0.002 * dist_to_header`**: If an "Ingredients:" header was found, clusters near it are preferred.

The cluster with the **highest score** is selected as the ingredient region.

---

## 9. Stage 8 — Text Reconstruction

The winning cluster contains boxes scattered across multiple rows. These need to be assembled into a readable string that preserves the original reading order.

### 8a. Row Assignment (Fine-Grained)

**Function:** `assign_rows(cluster, row_gap=45.0)`

Within the selected cluster, boxes are assigned to rows. Two boxes are on the same row if their `y_center` values differ by at most `adaptive_gap`:

```python
adaptive_gap = max(45.0, median_box_height * 0.7)
```

The gap adapts to the actual text size: larger text means larger line spacing, so the threshold increases. This handles both tiny ingredient text and large-print labels.

### 8b. Row-Level Cleanup

**Function:** `cleanup_row_boxes()`

Within each row, boxes are sorted left-to-right (`x1`). Junk fragments that are not continuations are removed. This catches small stray OCR artefacts that survived earlier filtering.

### 8c. Smart Text Joining

**Function:** `smart_join_row_texts()`

Boxes within a row are joined with intelligent spacing:

1. **Continuation fragments** (text starting with `(`, `[`, `%`, `,`, `and`, `with`, `from`, `of`, `or`, or a lowercase letter) are appended to the previous text with a space, not treated as a new segment.
2. **After open brackets/hyphens**: if the previous box ends with `(`, `[`, `/`, `-`, `&`, or `:`, the next box is attached directly.
3. **Otherwise**: boxes are joined with a space.

**Example:** Three boxes in a row: `"Sugar"`, `"("`, `"from cane)"`

- `"("` starts with `(` → continuation → appends to "Sugar" → `"Sugar ("`
- `"from cane)"` starts with `from` → continuation → appends → `"Sugar ( from cane)"`

Multiple whitespace is collapsed and the result is trimmed.

Rows are then joined with newline characters to form the raw text block.

---

## 10. Stage 9 — Post-Processing

**Function:** `postprocess_ingredient_text()`

Three sequential cleanup passes on the reconstructed text.

### 9a. Tail Trimming by Hints

**Function:** `trim_tail_by_hints()`

Scans the text for the first occurrence of any non-ingredient hint phrase (from the same ~80 phrase list used in filtering). Everything from that point onwards is cut off.

**Example:**
```
"Sugar, Wheat Flour, Salt, Emulsifier (E472e). For allergens see ingredients in bold."
                                                 ↑ cut here (matches "for allergens")
→ "Sugar, Wheat Flour, Salt, Emulsifier (E472e)."
```

This handles cases where the ingredient list runs into the next label section without a clear visual boundary.

### 9b. Trailing Junk Line Removal

**Function:** `remove_trailing_junk_lines()`

Each line is checked individually. Lines that:
- Contain non-ingredient hint phrases, or
- Look like junk fragments (too short, too numeric, too symbolic)

are removed entirely.

### 9c. Text Normalisation

**Function:** `normalize_ingredient_text()`

Fixes common spacing issues left over from OCR and text joining:

- `" ,"` → `","` (space before comma)
- `" ."` → `"."` (space before period)
- `" )"` → `")"` and `"( "` → `"("` (space inside parentheses)
- Multiple spaces → single space
- Multiple newlines → single newline
- Trailing punctuation (`,.;:`) stripped

---

## 11. Stage 10 — Splitting & OCR Correction

After the box classifier produces a clean merged text, two more steps happen before the ingredients are passed to dietary analysis.

### Splitting

**Function:** `split_ingredients_text()` in `utils.py`

The merged text block is split into individual ingredient candidates using delimiters:

- Commas `,` and semicolons `;`
- Middot `·` and bullet `•`
- Newlines
- `&` and phrases like `" and "`, `" or "`

**Parentheses are respected:** `"Emulsifier (E322 and E476)"` is kept as one segment, not split on "and".

### OCR Correction

**Function:** `correct_ingredient_list()` in `ocr_corrector.py`

Each individual ingredient candidate goes through a correction pipeline:

1. **Junk filter:** Obvious non-ingredients (nutritional text, URLs, storage instructions) are discarded.
2. **OCR text cleanup:** Lowercase, normalise whitespace, remove stray punctuation, fix E-number spacing.
3. **Exact alias lookup:** Known aliases (e.g. "soya lecithin" → "soy lecithin") are resolved.
4. **Exact vocabulary match:** If the cleaned text is already in the food ingredient dictionary, keep it as-is.
5. **SymSpell correction:** Edit distance ≤2 spell correction against a food-specific dictionary (common ingredients are weighted 10× higher). Conservative: maximum edit distance of 1 for short words (≤5 chars), 2 for longer words.
6. **SymSpell word segmentation:** For compound terms that were merged by OCR (e.g. "wheatsyrup" → "wheat syrup"), the word segmentation algorithm attempts to split them.
7. **RapidFuzz matching:** Fuzzy string matching (score ≥90) against the vocabulary. Very strict threshold to prevent hallucinating ingredients.
8. **Word-by-word fallback:** For multi-word phrases that didn't match as a whole, each word is corrected individually.
9. **Dangerous correction guard:** Known false-friend pairs (e.g. "salt" ↔ "malt", "cumin" ↔ "curcumin") are never auto-corrected into each other.
10. **Deduplication:** Duplicate ingredients (case-insensitive) are removed, preserving first occurrence order.
11. **Post-processing:** Percentage removal, bracket normalisation, accent stripping, and known OCR phrase fixes.

---

## 12. Model Training Summary

**File:** `training/training_code.py`

### Dataset

- Source CSV: `datasets/dataset_augmented_1000.csv`
- Each row = one EasyOCR box with: `image_id`, `text`, `confidence`, `x1`, `y1`, `x2`, `y2`, `label` (0 or 1)
- Labels: `1` = ingredient box, `0` = non-ingredient box

### Data Split

The data is split by `image_id` (not by individual box) using `GroupShuffleSplit`:

- **80% Train** — model learns from these images
- **10% Validation** — used to tune the decision threshold
- **10% Test** — final evaluation, untouched during development

Group splitting ensures that all boxes from a single image stay in the same split, preventing data leakage.

### Feature Pipeline

1. Context columns are added (prev/next text, context_text).
2. TF-IDF vectoriser is fit on training context_text (character 3–5 grams, min_df=2).
3. DictVectorizer is fit on training manual features.
4. Training/validation/test sets are transformed using the fitted vectorisers.
5. Feature matrices are horizontally stacked: `[TF-IDF | Manual]`.

### Model Training

```python
LogisticRegression(max_iter=4000, class_weight="balanced", random_state=42)
```

- `class_weight="balanced"` automatically up-weights the minority class (ingredient boxes) during training, compensating for the fact that most boxes on a label are not ingredients.
- `max_iter=4000` ensures convergence for the high-dimensional sparse feature space.

### Threshold Tuning

The default decision threshold of 0.5 is replaced by the threshold that maximises **F1-score** on the validation set:

```python
for threshold in [0.20, 0.25, 0.30, ..., 0.80]:
    predictions = (val_probs >= threshold)
    f1 = f1_score(y_val, predictions)
    if f1 > best_f1:
        best_threshold = threshold
```

### Saved Artefact

The final model bundle (`ingredient_box_classifier.joblib`) contains:

| Key | Object | Purpose |
|---|---|---|
| `classifier` | Fitted `LogisticRegression` | Predicts P(ingredient) |
| `tfidf` | Fitted `TfidfVectorizer` | Transforms context_text to character n-gram features |
| `dict_vectorizer` | Fitted `DictVectorizer` | Transforms manual feature dicts to sparse matrix |
| `decision_threshold` | `float` | Optimal threshold from validation tuning |

---

## 13. End-to-End Example

Consider a food label image with 30 EasyOCR boxes. Here is a simplified walkthrough:

**Raw EasyOCR output (selected boxes):**

| Box | Text | Confidence | Position |
|---|---|---|---|
| 0 | "ORGANIC PEANUT BUTTER" | 0.95 | Top of label |
| 1 | "Crunchy" | 0.91 | Below product name |
| 2 | "350g e" | 0.88 | Right side |
| 3 | "Ingredients:" | 0.97 | Middle-left |
| 4 | "Roasted Peanuts (95%)," | 0.89 | Below header |
| 5 | "Sea Salt." | 0.92 | Below box 4 |
| 6 | "ALLERGENS: See" | 0.85 | Below ingredients |
| 7 | "ingredients in bold." | 0.82 | Below box 6 |
| 8 | "Nutrition Information" | 0.94 | Right column |
| 9 | "Energy 2606kJ" | 0.90 | Nutrition table |
| ... | ... | ... | ... |

**After classification:**

| Box | pred_prob | pred_label |
|---|---|---|
| 0 | 0.12 | 0 (product name) |
| 1 | 0.08 | 0 (marketing text) |
| 2 | 0.05 | 0 (weight) |
| 3 | 0.78 | 1 (header — will be used as anchor, then removed) |
| 4 | 0.96 | 1 (ingredient) |
| 5 | 0.94 | 1 (ingredient) |
| 6 | 0.31 | 0 (allergen warning) |
| 7 | 0.22 | 0 (allergen warning continuation) |
| 8 | 0.04 | 0 (nutrition section) |
| 9 | 0.02 | 0 (nutrition data) |

**After filtering:** Boxes 4 and 5 survive. Box 3 is recorded as the header anchor.

**After clustering:** Boxes 4 and 5 form a single cluster near the header.

**After text reconstruction:**

```
Roasted Peanuts (95%),
Sea Salt.
```

**After post-processing:** `"Roasted Peanuts (95%), Sea Salt."`

**After splitting:** `["Roasted Peanuts (95%)", "Sea Salt"]`

**After OCR correction:** `["roasted peanuts", "sea salt"]` (percentage stripped, normalised)

These are passed to the dietary analysis engine for allergen/restriction checking.
