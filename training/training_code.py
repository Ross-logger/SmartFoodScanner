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
df = pd.read_csv("ocr_box_labels_fixed_v2.csv")

# basic cleanup
df["text"] = df["text"].fillna("").astype(str)
df["label"] = df["label"].astype(int)

# -----------------------------
# 2. Split by image_id
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
# 3. Manual features
# -----------------------------
INGREDIENT_HINTS = [
    "sugar", "salt", "oil", "flour", "milk", "wheat", "water",
    "glucose", "butter", "maize", "corn", "vitamin", "iron"
]

NON_INGREDIENT_HINTS = [
    "storage", "store", "nutrition", "energy", "protein",
    "allergy", "allergens", "manufactured", "distributed",
    "keep refrigerated", "serving", "calories"
]

def make_manual_features(texts, confs):
    rows = []
    for text, conf in zip(texts, confs):
        t = str(text).lower()
        rows.append({
            "ocr_confidence": float(conf),
            "char_len": len(t),
            "word_count": len(t.split()),
            "digit_count": sum(c.isdigit() for c in t),
            "comma_count": t.count(","),
            "percent_count": t.count("%"),
            "paren_count": t.count("(") + t.count(")"),
            "has_ingredient_hint": int(any(w in t for w in INGREDIENT_HINTS)),
            "has_noningredient_hint": int(any(w in t for w in NON_INGREDIENT_HINTS)),
            "is_all_caps": int(t.isupper()),
        })
    return rows

# -----------------------------
# 4. Vectorize
# -----------------------------
tfidf = TfidfVectorizer(
    analyzer="char",
    ngram_range=(3, 5),
    min_df=2,
    lowercase=True
)

dict_vec = DictVectorizer(sparse=True)

X_train_text = tfidf.fit_transform(train_df["text"])
X_val_text = tfidf.transform(val_df["text"])
X_test_text = tfidf.transform(test_df["text"])

X_train_manual = dict_vec.fit_transform(
    make_manual_features(train_df["text"], train_df["confidence"])
)
X_val_manual = dict_vec.transform(
    make_manual_features(val_df["text"], val_df["confidence"])
)
X_test_manual = dict_vec.transform(
    make_manual_features(test_df["text"], test_df["confidence"])
)

X_train = hstack([X_train_text, X_train_manual])
X_val = hstack([X_val_text, X_val_manual])
X_test = hstack([X_test_text, X_test_manual])

y_train = train_df["label"].values
y_val = val_df["label"].values
y_test = test_df["label"].values

# -----------------------------
# 5. Train model
# -----------------------------
model = LogisticRegression(
    max_iter=2000,
    class_weight="balanced",
    random_state=42
)
model.fit(X_train, y_train)

# -----------------------------
# 6. Validate
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
# 7. Final test
# -----------------------------
test_probs = model.predict_proba(X_test)[:, 1]
test_pred = (test_probs >= best_thr).astype(int)

print("\nTEST REPORT")
print(classification_report(y_test, test_pred, digits=4))

# save predictions
test_out = test_df.copy()
test_out["pred_prob"] = test_probs
test_out["pred_label"] = test_pred
test_out.to_csv("test_box_predictions.csv", index=False)

print("\nSaved: test_box_predictions.csv")

# save model + vectorizers + threshold (all required for inference)
joblib.dump(
    {
        "model": model,
        "tfidf": tfidf,
        "dict_vec": dict_vec,
        "best_thr": float(best_thr),
        "ingredient_hints": INGREDIENT_HINTS,
        "non_ingredient_hints": NON_INGREDIENT_HINTS,
    },
    "ingredient_box_classifier.joblib",
)
print("Saved: ingredient_box_classifier.joblib")