import re
from typing import Any

import numpy as np
import pandas as pd


HEADER_PATTERNS = [
    r"^\s*ingredients\s*:?\s*$",
    r"^\s*ingredient\s*:?\s*$",
]

GENERIC_BAD_HINTS = [
    "storage", "store", "nutrition", "energy", "protein",
    "allergy", "allergens", "manufactured", "distributed",
    "keep refrigerated", "serving", "calories",
    "best before", "made in", "suitable for",
    "po box", "www.", ".com", "recycle"
]

TAIL_CUT_HINTS = [
    "for allergens",
    "allergen advice",
    "allergens:",
    "storage",
    "store in",
    "keep refrigerated",
    "for best before",
    "best before",
    "made in",
    "manufactured by",
    "distributed by",
    "suitable for",
    "po box",
    "www.",
    ".com"
]


def normalize_text(s: str) -> str:
    return str(s).strip().lower()


def is_header(text: str) -> bool:
    t = normalize_text(text)
    return any(re.fullmatch(p, t) for p in HEADER_PATTERNS)


def has_bad_hint(text: str) -> bool:
    t = normalize_text(text)
    return any(w in t for w in GENERIC_BAD_HINTS)


def alpha_ratio(text: str) -> float:
    t = str(text)
    if not t:
        return 0.0
    alpha = sum(ch.isalpha() for ch in t)
    alnum = sum(ch.isalnum() for ch in t)
    return alpha / max(alnum, 1)


def digit_ratio(text: str) -> float:
    t = str(text)
    if not t:
        return 0.0
    digits = sum(ch.isdigit() for ch in t)
    alnum = sum(ch.isalnum() for ch in t)
    return digits / max(alnum, 1)


def symbol_ratio(text: str) -> float:
    t = str(text)
    if not t:
        return 0.0
    sym = sum(not ch.isalnum() and not ch.isspace() for ch in t)
    return sym / max(len(t), 1)


def looks_like_junk_fragment(text: str) -> bool:
    """
    General OCR junk heuristic.
    No hardcoded product-specific strings.
    """
    t = str(text).strip()
    if not t:
        return True

    # very short fragments
    if len(t) <= 2:
        return True

    # mostly digits
    if digit_ratio(t) > 0.75:
        return True

    # too little alphabetic content
    if alpha_ratio(t) < 0.25 and len(t) <= 6:
        return True

    # too many symbols for a short token
    if len(t) <= 8 and symbol_ratio(t) > 0.4:
        return True

    # looks like code / serial / garbage chunk
    if len(t) <= 8 and re.fullmatch(r"[A-Za-z0-9\-_/.]+", t) and alpha_ratio(t) < 0.5:
        return True

    return False


def looks_like_continuation(text: str) -> bool:
    """
    Fragment likely continuing previous ingredient text.
    """
    t = str(text).strip()
    tl = t.lower()

    if not t:
        return False

    if t.startswith(("(", "[", "%", ",", ";", ":", "&")):
        return True

    if re.fullmatch(r"\(?\d+([.,]\d+)?%\)?", t):
        return True

    if tl.startswith(("and ", "with ", "from ", "of ", "or ")):
        return True

    # box starts lowercase after split
    if t and t[0].islower() and len(t) <= 20:
        return True

    return False


def prepare_boxes(df_image: pd.DataFrame) -> pd.DataFrame:
    df = df_image.copy()

    required = ["x1", "y1", "x2", "y2", "pred_prob", "text"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    for col in ["x1", "y1", "x2", "y2", "pred_prob"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    if "confidence" not in df.columns:
        df["confidence"] = 1.0
    else:
        df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce").fillna(0.0)

    df["text"] = df["text"].fillna("").astype(str)

    df["width"] = df["x2"] - df["x1"]
    df["height"] = df["y2"] - df["y1"]
    df["x_center"] = (df["x1"] + df["x2"]) / 2.0
    df["y_center"] = (df["y1"] + df["y2"]) / 2.0

    return df


def find_header_box(df: pd.DataFrame):
    headers = df[df["text"].apply(is_header)].copy()
    if len(headers) == 0:
        return None
    headers = headers.sort_values("y_center")
    return headers.iloc[0]


def filter_positive_boxes(
    df: pd.DataFrame,
    threshold: float = 0.4,
    strong_keep_threshold: float = 0.8
) -> pd.DataFrame:
    pos = df[df["pred_prob"] >= threshold].copy()

    # remove header itself
    pos = pos[~pos["text"].apply(is_header)].copy()

    # remove generic junk unless model is very confident
    pos = pos[~(
        pos["text"].apply(looks_like_junk_fragment) &
        (pos["pred_prob"] < strong_keep_threshold)
    )]

    # remove generic non-ingredient hints unless model is extremely confident
    pos = pos[~(
        pos["text"].apply(has_bad_hint) &
        (pos["pred_prob"] < 0.92)
    )]

    return pos.reset_index(drop=True)


def apply_header_constraint(
    pos: pd.DataFrame,
    header_row,
    tolerance_above: float = 25.0
) -> pd.DataFrame:
    if header_row is None or len(pos) == 0:
        return pos
    return pos[pos["y_center"] >= header_row["y_center"] - tolerance_above].copy().reset_index(drop=True)


def remove_isolated_boxes(
    pos: pd.DataFrame,
    y_radius: float = 120.0,
    x_radius: float = 900.0
) -> pd.DataFrame:
    if len(pos) <= 1:
        return pos.copy()

    pos = pos.reset_index(drop=True)
    keep = []

    for i, row in pos.iterrows():
        dy = np.abs(pos["y_center"] - row["y_center"])
        dx = np.abs(pos["x_center"] - row["x_center"])
        neighbors = ((dy <= y_radius) & (dx <= x_radius)).sum() - 1

        if row["pred_prob"] >= 0.75 or neighbors >= 1 or looks_like_continuation(row["text"]):
            keep.append(True)
        else:
            keep.append(False)

    return pos[np.array(keep)].copy().reset_index(drop=True)


def cluster_boxes_by_rows(pos: pd.DataFrame, row_gap: float = 90.0) -> list[pd.DataFrame]:
    if len(pos) == 0:
        return []

    pos = pos.sort_values(["y_center", "x1"]).copy().reset_index(drop=True)
    clusters = []
    current = [pos.iloc[0]]

    for i in range(1, len(pos)):
        prev = current[-1]
        cur = pos.iloc[i]

        if abs(cur["y_center"] - prev["y_center"]) <= row_gap:
            current.append(cur)
        else:
            clusters.append(pd.DataFrame(current))
            current = [cur]

    clusters.append(pd.DataFrame(current))
    return clusters


def merge_close_clusters(clusters: list[pd.DataFrame], cluster_gap: float = 120.0) -> list[pd.DataFrame]:
    if not clusters:
        return []

    merged = [clusters[0].copy()]

    for c in clusters[1:]:
        prev = merged[-1]
        prev_bottom = prev["y2"].max()
        cur_top = c["y1"].min()

        if cur_top - prev_bottom <= cluster_gap:
            merged[-1] = pd.concat([prev, c], ignore_index=True)
        else:
            merged.append(c.copy())

    return merged


def score_cluster(cluster: pd.DataFrame, header_row=None) -> float:
    score = float(cluster["pred_prob"].sum())
    score += 0.18 * len(cluster)

    bad_count = cluster["text"].apply(has_bad_hint).sum()
    score -= 0.8 * bad_count

    avg_text_len = cluster["text"].astype(str).str.len().mean()
    score += min(avg_text_len / 50.0, 0.6)

    if header_row is not None:
        cluster_top = cluster["y1"].min()
        dist = max(0.0, cluster_top - header_row["y2"])
        score -= 0.002 * dist

    return float(score)


def choose_best_cluster(clusters: list[pd.DataFrame], header_row=None):
    if not clusters:
        return None

    scored = []
    for c in clusters:
        if len(c) == 0:
            continue
        scored.append((score_cluster(c, header_row=header_row), c))

    if not scored:
        return None

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1].copy().reset_index(drop=True)


def assign_rows(cluster: pd.DataFrame, row_gap: float = 45.0) -> pd.DataFrame:
    if len(cluster) == 0:
        return cluster.copy()

    cluster = cluster.sort_values(["y_center", "x1"]).copy().reset_index(drop=True)

    median_h = max(1.0, float(cluster["height"].median()))
    adaptive_gap = max(row_gap, median_h * 0.7)

    row_ids = []
    current_row = 0
    prev_y = None

    for _, r in cluster.iterrows():
        if prev_y is None:
            row_ids.append(current_row)
            prev_y = r["y_center"]
            continue

        if abs(r["y_center"] - prev_y) <= adaptive_gap:
            row_ids.append(current_row)
        else:
            current_row += 1
            row_ids.append(current_row)
            prev_y = r["y_center"]

    cluster["row_id"] = row_ids
    return cluster


def cleanup_row_boxes(row_df: pd.DataFrame) -> pd.DataFrame:
    row_df = row_df.sort_values("x1").copy().reset_index(drop=True)

    keep = []
    for _, r in row_df.iterrows():
        txt = str(r["text"]).strip()

        if looks_like_junk_fragment(txt) and not looks_like_continuation(txt):
            keep.append(False)
            continue

        keep.append(True)

    return row_df[np.array(keep)].copy().reset_index(drop=True)


def smart_join_row_texts(texts: list[str]) -> str:
    out = []

    for t in texts:
        t = str(t).strip()
        if not t:
            continue

        if not out:
            out.append(t)
            continue

        prev = out[-1]

        if looks_like_continuation(t):
            out[-1] = prev.rstrip() + " " + t
            continue

        if prev.endswith(("(", "[", "/", "-", "&", ":")):
            out[-1] = prev + " " + t
            continue

        out.append(t)

    line = " ".join(out)
    line = re.sub(r"\s+", " ", line).strip()
    return line


def reconstruct_text_from_cluster(cluster: pd.DataFrame) -> str:
    if cluster is None or len(cluster) == 0:
        return ""

    cluster = assign_rows(cluster)
    lines = []

    for _, row_df in cluster.groupby("row_id", sort=True):
        row_df = cleanup_row_boxes(row_df)
        if len(row_df) == 0:
            continue

        line = smart_join_row_texts(row_df["text"].astype(str).tolist())
        if line:
            lines.append(line)

    return "\n".join(lines).strip()


def trim_tail_by_hints(text: str) -> str:
    if not text:
        return ""

    lower = text.lower()
    cut_positions = []

    for hint in TAIL_CUT_HINTS:
        idx = lower.find(hint)
        if idx > 0:
            cut_positions.append(idx)

    if cut_positions:
        text = text[:min(cut_positions)].strip()

    return text


def remove_trailing_junk_lines(text: str) -> str:
    if not text:
        return ""

    cleaned_lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        if has_bad_hint(line):
            continue

        if looks_like_junk_fragment(line):
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def normalize_ingredient_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace(" ,", ",")
    text = text.replace(" .", ".")
    text = text.replace(" ;", ";")
    text = text.replace(" :", ":")
    text = text.replace(" )", ")")
    text = text.replace("( ", "(")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[\s,;:]+$", "", text).strip()

    return text


def postprocess_ingredient_text(text: str) -> str:
    text = trim_tail_by_hints(text)
    text = remove_trailing_junk_lines(text)
    text = normalize_ingredient_text(text)
    return text


def extract_ingredient_region_for_image(
    df_image: pd.DataFrame,
    threshold: float = 0.4,
    row_gap: float = 90.0,
    cluster_gap: float = 120.0
) -> dict[str, Any]:
    df = prepare_boxes(df_image)

    header_row = find_header_box(df)
    pos = filter_positive_boxes(df, threshold=threshold)
    pos = apply_header_constraint(pos, header_row)
    pos = remove_isolated_boxes(pos)

    clusters = cluster_boxes_by_rows(pos, row_gap=row_gap)
    clusters = merge_close_clusters(clusters, cluster_gap=cluster_gap)

    best_cluster = choose_best_cluster(clusters, header_row=header_row)
    raw_text = reconstruct_text_from_cluster(best_cluster)
    final_text = postprocess_ingredient_text(raw_text)

    return {
        "header_row": header_row,
        "positive_boxes": pos,
        "clusters": clusters,
        "best_cluster": best_cluster,
        "raw_text": raw_text,
        "final_text": final_text
    }


def run_extraction_for_all_images(
    df_predictions: pd.DataFrame,
    threshold: float = 0.4,
    row_gap: float = 90.0,
    cluster_gap: float = 120.0
) -> pd.DataFrame:
    rows = []

    for image_id, df_img in df_predictions.groupby("image_id", sort=True):
        result = extract_ingredient_region_for_image(
            df_img,
            threshold=threshold,
            row_gap=row_gap,
            cluster_gap=cluster_gap
        )

        header_row = result["header_row"]
        header_text = None if header_row is None else str(header_row["text"])
        header_y = None if header_row is None else float(header_row["y_center"])

        best_cluster = result["best_cluster"]
        cluster_size = 0 if best_cluster is None else int(len(best_cluster))
        cluster_mean_prob = None if best_cluster is None else float(best_cluster["pred_prob"].mean())

        rows.append({
            "image_id": image_id,
            "header_text": header_text,
            "header_y": header_y,
            "cluster_size": cluster_size,
            "cluster_mean_prob": cluster_mean_prob,
            "raw_text": result["raw_text"],
            "final_text": result["final_text"],
        })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    # Example:
    # df = pd.read_csv("test_box_predictions.csv")
    # out = run_extraction_for_all_images(df, threshold=0.4)
    # out.to_csv("final_ingredient_predictions.csv", index=False)
    pass