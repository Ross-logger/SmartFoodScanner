from pathlib import Path

import joblib
import pandas as pd
import numpy as np
from scipy.sparse import hstack

from sklearn.model_selection import GroupShuffleSplit
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score, precision_recall_fscore_support


# -----------------------------
# 1. Load data
# -----------------------------
_TRAINING_DIR = Path(__file__).resolve().parent
_DATASETS_DIR = _TRAINING_DIR / "datasets"
_OUTPUTS_DIR = _TRAINING_DIR / "outputs"
_MODELS_DIR = _TRAINING_DIR / "models"
CSV_PATH = _DATASETS_DIR / "dataset_augmented_1000.csv"

df = pd.read_csv(CSV_PATH)

df["text"] = df["text"].fillna("").astype(str)
df["label"] = df["label"].astype(int)

for col in ["confidence", "x1", "y1", "x2", "y2"]:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

# geometry
df["width"] = df["x2"] - df["x1"]
df["height"] = df["y2"] - df["y1"]
df["x_center"] = (df["x1"] + df["x2"]) / 2.0
df["y_center"] = (df["y1"] + df["y2"]) / 2.0


# -----------------------------
# 2. Sort boxes within image and create prev/next context
# -----------------------------
def add_context_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame = frame.sort_values(["image_id", "y_center", "x1"]).reset_index(drop=True)

    prev_texts = []
    next_texts = []

    for image_id, grp in frame.groupby("image_id", sort=False):
        grp = grp.sort_values(["y_center", "x1"]).copy()
        texts = grp["text"].tolist()

        prev_local = [""] + texts[:-1]
        next_local = texts[1:] + [""]

        prev_texts.extend(prev_local)
        next_texts.extend(next_local)

    frame["prev_text"] = prev_texts
    frame["next_text"] = next_texts

    # combined context text
    frame["context_text"] = (
        frame["prev_text"].fillna("").astype(str)
        + " [SEP] "
        + frame["text"].fillna("").astype(str)
        + " [SEP] "
        + frame["next_text"].fillna("").astype(str)
    )

    return frame


df = add_context_columns(df)


# -----------------------------
# 3. Split by image_id
# -----------------------------
gss1 = GroupShuffleSplit(n_splits=1, test_size=0.30, random_state=42)
train_idx, temp_idx = next(gss1.split(df, groups=df["image_id"]))

train_df = df.iloc[train_idx].copy()
temp_df = df.iloc[temp_idx].copy()

gss2 = GroupShuffleSplit(n_splits=1, test_size=0.50, random_state=42)
val_idx, test_idx = next(gss2.split(temp_df, groups=temp_df["image_id"]))

val_df = temp_df.iloc[val_idx].copy()
test_df = temp_df.iloc[test_idx].copy()

print("Train images:", train_df["image_id"].nunique())
print("Val images:", val_df["image_id"].nunique())
print("Test images:", test_df["image_id"].nunique())


# -----------------------------
# 4. Manual features
# -----------------------------
INGREDIENT_HINTS = [
    "sugar", "salt", "oil", "flour", "milk", "wheat", "water",
    "glucose", "butter", "maize", "corn", "lecithin", "pectin",
    "citric", "flavour", "flavouring", "emulsifier", "strawberry",
    "cocoa", "egg", "yeast", "barley", "oat", "almond", "peanut"
]

NON_INGREDIENT_HINTS = [
    "storage", "store", "nutrition", "energy", "protein",
    "allergy", "allergens", "manufactured", "distributed",
    "keep refrigerated", "serving", "calories", "made in",
    "po box", "united kingdom", "ireland", "suitable for",
    "for best before", "best before", "recycle", "www.", ".com"
]

HEADER_HINTS = ["ingredients", "ingredients:", "ingredient", "ingredient:"]


def has_any(text: str, words: list[str]) -> int:
    t = str(text).lower()
    return int(any(w in t for w in words))


def make_manual_features(frame: pd.DataFrame):
    rows = []

    for _, r in frame.iterrows():
        t = str(r["text"]).lower()
        prev_t = str(r["prev_text"]).lower()
        next_t = str(r["next_text"]).lower()

        rows.append({
            "ocr_confidence": float(r["confidence"]),
            "char_len": len(t),
            "word_count": len(t.split()),
            "digit_count": sum(c.isdigit() for c in t),
            "comma_count": t.count(","),
            "percent_count": t.count("%"),
            "paren_count": t.count("(") + t.count(")"),
            "colon_count": t.count(":"),
            "is_all_caps": int(str(r["text"]).isupper()),

            "has_ingredient_hint": has_any(t, INGREDIENT_HINTS),
            "has_noningredient_hint": has_any(t, NON_INGREDIENT_HINTS),
            "has_header_hint": has_any(t, HEADER_HINTS),

            "prev_has_ingredient_hint": has_any(prev_t, INGREDIENT_HINTS),
            "prev_has_noningredient_hint": has_any(prev_t, NON_INGREDIENT_HINTS),
            "prev_has_header_hint": has_any(prev_t, HEADER_HINTS),

            "next_has_ingredient_hint": has_any(next_t, INGREDIENT_HINTS),
            "next_has_noningredient_hint": has_any(next_t, NON_INGREDIENT_HINTS),
            "next_has_header_hint": has_any(next_t, HEADER_HINTS),

            "width": float(r["width"]),
            "height": float(r["height"]),
            "x_center": float(r["x_center"]),
            "y_center": float(r["y_center"]),
        })

    return rows


# -----------------------------
# 5. Vectorize text + features
# -----------------------------
# Use context_text instead of only current box text
tfidf = TfidfVectorizer(
    analyzer="char",
    ngram_range=(3, 5),
    min_df=2,
    lowercase=True
)

dict_vec = DictVectorizer(sparse=True)

X_train_text = tfidf.fit_transform(train_df["context_text"])
X_val_text = tfidf.transform(val_df["context_text"])
X_test_text = tfidf.transform(test_df["context_text"])

X_train_manual = dict_vec.fit_transform(make_manual_features(train_df))
X_val_manual = dict_vec.transform(make_manual_features(val_df))
X_test_manual = dict_vec.transform(make_manual_features(test_df))

X_train = hstack([X_train_text, X_train_manual])
X_val = hstack([X_val_text, X_val_manual])
X_test = hstack([X_test_text, X_test_manual])

y_train = train_df["label"].values
y_val = val_df["label"].values
y_test = test_df["label"].values


# -----------------------------
# 6. Train model
# -----------------------------
model = LogisticRegression(
    max_iter=4000,
    class_weight="balanced",
    random_state=42
)
model.fit(X_train, y_train)


# -----------------------------
# 7. Tune threshold on validation
# -----------------------------
val_probs = model.predict_proba(X_val)[:, 1]

best_thr = 0.5
best_f1 = -1

for thr in np.arange(0.2, 0.81, 0.05):
    val_pred = (val_probs >= thr).astype(int)
    f1 = f1_score(y_val, val_pred)
    if f1 > best_f1:
        best_f1 = f1
        best_thr = thr

print("Best threshold on val:", best_thr)
print("Best val F1:", best_f1)


# -----------------------------
# 8. Final test
# -----------------------------
test_probs = model.predict_proba(X_test)[:, 1]
test_pred = (test_probs >= best_thr).astype(int)

print("\nTEST REPORT")
print(classification_report(y_test, test_pred, digits=4))

prec, rec, f1, _ = precision_recall_fscore_support(
    y_test, test_pred, average="binary", pos_label=1
)
print(f"Ingredient class -> precision={prec:.4f}, recall={rec:.4f}, f1={f1:.4f}")


# -----------------------------
# 9. Save predictions
# -----------------------------
test_out = test_df.copy()
test_out["pred_prob"] = test_probs
test_out["pred_label"] = test_pred
_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
_pred_path = _OUTPUTS_DIR / "model_predictions.csv"
test_out.to_csv(_pred_path, index=False)

print(f"\nSaved: {_pred_path}")

_MODELS_DIR.mkdir(parents=True, exist_ok=True)
_model_path = _MODELS_DIR / "ingredient_box_classifier.joblib"
joblib.dump(
    {
        "classifier": model,
        "tfidf": tfidf,
        "dict_vectorizer": dict_vec,
        "decision_threshold": float(best_thr),
    },
    _model_path,
)
print(f"Saved: {_model_path}")