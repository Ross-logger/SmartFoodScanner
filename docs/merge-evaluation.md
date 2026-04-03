# Merge Pipeline Evaluation

## What This Script Does

`training/evaluate.py` measures how well the **merge pipeline** (box classifier + spatial merge) reconstructs ingredient text from OCR boxes, by comparing the merged output against a human-labelled ground truth.

It answers two questions:

1. **Recall** -- Did we find all the real ingredients?
2. **Precision** -- Is everything we extracted actually an ingredient?

---

## Inputs

| Input | Description |
|---|---|
| `--predictions` CSV | Box-level predictions: each row is one OCR text box with `image_id`, `text`, bounding-box coordinates (`x1, y1, x2, y2`), and `pred_prob` (classifier probability that the box is an ingredient). |
| `--ground-truth-json` | A JSON array where each entry has `"image"` (filename) and `"true_ingredients"` (list of correct ingredient strings). |

---

## Pipeline Flow

```
Box-level CSV
    │
    ▼
┌──────────────────────────────┐
│  run_extraction_for_all_images│   (from merge_ingredients.py)
│  - filter boxes by threshold  │
│  - cluster boxes spatially    │
│  - merge into final_text      │
└──────────────┬───────────────┘
               │
               ▼
         final_text per image
               │
       ┌───────┴────────┐
       │  (optional)     │
       │  OCR Corrector  │   --use-ocr-corrector flag
       │  spell-correct  │
       └───────┬─────────┘
               │
               ▼
    Compare against ground truth
               │
       ┌───────┴────────┐
       │                │
    RECALL          PRECISION
```

---

## How Recall Is Computed

**Question:** "For each real ingredient in the ground truth, can we find it somewhere in the extracted text?"

### Steps

1. Take the full `final_text` (the merged OCR output for one image) as a single string.
2. For each ground-truth ingredient, compute a **fuzzy similarity score** between that ingredient and the entire `final_text`.
3. If the score is above the **fuzzy threshold** (default 85, or 100 for exact matching), count it as **found**.
4. Recall = found / total ground-truth ingredients.

### Fuzzy Scoring

For each ground-truth ingredient vs the extracted text, the script computes **four** RapidFuzz scores and takes the **maximum**:

| Scorer | What it does |
|---|---|
| `fuzz.partial_ratio` | Finds the best matching substring (good for when the ingredient appears inside a longer text). |
| `fuzz.token_set_ratio` | Ignores word order and duplicates; checks if the same words appear. |
| `fuzz.token_sort_ratio` | Sorts words alphabetically then compares (handles reordering). |
| `fuzz.ratio` | Simple character-level similarity of the two full strings. |

There is also an **exact substring shortcut**: if the ground-truth ingredient (normalised) appears literally inside the extracted text, the score is 100 immediately.

### Example

Suppose:

```
Ground truth:  ["Sugar", "Salt", "Wheat Flour", "E330"]
Extracted text: "sugar, wheat flour, palm oil, e330"
Fuzzy threshold: 85
```

| GT ingredient | Best score | Found? |
|---|---|---|
| Sugar | 100 (substring match: "sugar" is in the text) | Yes |
| Salt | 72 (partial match against "palm oil, e330"... not close enough) | No |
| Wheat Flour | 100 (substring match: "wheat flour" is in the text) | Yes |
| E330 | 100 (substring match: "e330" is in the text) | Yes |

**Recall = 3 found / 4 total = 0.75**

In plain words: we found 3 out of 4 real ingredients, so recall is 75%. We missed "Salt".

---

## How Precision Is Computed

**Question:** "For each segment we extracted, does it correspond to a real ingredient?"

### Steps

1. Split `final_text` into **segments** by delimiters (commas, semicolons, newlines, pipe characters).
2. For each predicted segment, compute the best fuzzy score against **every** ground-truth ingredient.
3. If the best score is above the threshold, count the segment as a **true positive** (it matches something real).
4. Precision = true positives / total predicted segments.

### Example (same data)

```
Extracted text: "sugar, wheat flour, palm oil, e330"
Segments after splitting: ["sugar", "wheat flour", "palm oil", "e330"]
Ground truth: ["Sugar", "Salt", "Wheat Flour", "E330"]
```

| Predicted segment | Best GT match | Score | True positive? |
|---|---|---|---|
| sugar | Sugar | 100 | Yes |
| wheat flour | Wheat Flour | 100 | Yes |
| palm oil | (no close match) | 62 | No |
| e330 | E330 | 100 | Yes |

**Precision = 3 true positives / 4 predicted segments = 0.75**

In plain words: 3 of the 4 things we extracted are real ingredients. "palm oil" was noise/wrong.

---

## F1 Score

F1 is the harmonic mean of precision and recall. It gives a single number that balances both:

```
F1 = 2 * precision * recall / (precision + recall)
```

Using the example above:

```
F1 = 2 * 0.75 * 0.75 / (0.75 + 0.75) = 0.75
```

### What each metric tells you

| Metric | Low value means... |
|---|---|
| **Recall** | The pipeline is **missing** real ingredients (not extracting enough). |
| **Precision** | The pipeline is extracting **junk** that is not a real ingredient (extracting too much). |
| **F1** | Overall quality is poor (either missing things, adding junk, or both). |

---

## Fuzzy Threshold

The `--fuzzy-threshold` flag controls how strict the matching is:

| Threshold | Meaning |
|---|---|
| **85** (default) | Allows minor spelling differences, OCR noise, punctuation variations. |
| **100** | Exact match only -- the ingredient text must appear character-for-character (after normalisation). |

A lower threshold is more forgiving of OCR errors; a higher threshold reveals how accurate the raw text is.

---

## OCR Corrector (optional)

When `--use-ocr-corrector` is passed, the script applies spelling correction to `final_text` before evaluation:

1. Split the merged text into individual ingredient candidates.
2. Run each through the OCR corrector (SymSpell + RapidFuzz dictionary lookup).
3. Rejoin the corrected list.

This lets you measure whether the spelling corrector improves or hurts the final metrics.

---

## Output CSV Columns

| Column | Description |
|---|---|
| `image_id` | Image filename. |
| `final_text` | The merged (and optionally corrected) ingredient text. |
| `raw_text_before_correction` | Original text before OCR correction (only present with `--use-ocr-corrector`). |
| `ground_truth` | Ground-truth ingredients joined by ` \| `. |
| `gt_matched` | Number of ground-truth ingredients found in the extracted text. |
| `gt_total` | Total ground-truth ingredients. |
| `pred_matched` | Number of predicted segments that match a real ingredient. |
| `pred_total` | Total predicted segments. |
| `ingredient_recall` | `gt_matched / gt_total`. |
| `ingredient_precision` | `pred_matched / pred_total`. |
| `ingredient_f1` | Harmonic mean of precision and recall. |
| `match_details` | Per-ingredient recall breakdown: `ingredient -> score -> matched`. |
| `pred_match_details` | Per-segment precision breakdown: `segment -> score -> matched`. |

---

## Usage

```bash
# Basic evaluation (default fuzzy threshold = 85)
python3 evaluate.py \
  --predictions outputs/model_predictions.csv \
  --ground-truth-json datasets/true_ingredients_augmented_1000.json

# Strict exact-match evaluation
python3 evaluate.py \
  --predictions outputs/model_predictions.csv \
  --ground-truth-json datasets/true_ingredients_augmented_1000.json \
  --fuzzy-threshold 100

# With OCR spelling correction
python3 evaluate.py \
  --predictions outputs/model_predictions.csv \
  --ground-truth-json datasets/true_ingredients_augmented_1000.json \
  --fuzzy-threshold 100 \
  --use-ocr-corrector
```

### All CLI flags

| Flag | Default | Description |
|---|---|---|
| `--predictions` | `outputs/test_box_predictions.csv` | Box-level CSV. |
| `--ground-truth-json` | `tests/data/true_ingredients_for_box_classifier.json` | Ground-truth JSON. |
| `--output` | `outputs/merge_evaluation_review_fuzzy.csv` | Where to write the per-image results CSV. |
| `--threshold` | `0.4` | Minimum `pred_prob` to keep a box. |
| `--row-gap` | `90.0` | Max vertical pixel gap to group boxes into the same row. |
| `--cluster-gap` | `120.0` | Max vertical pixel gap to merge adjacent row clusters. |
| `--fuzzy-threshold` | `85.0` | Minimum fuzzy score to count a match. |
| `--use-ocr-corrector` | off | Apply OCR spelling correction before scoring. |
