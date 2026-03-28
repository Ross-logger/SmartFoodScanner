from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz

from merge_ingredients import run_extraction_for_all_images

_TRAINING_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TRAINING_DIR.parent


def normalize_text(s: str) -> str:
    t = str(s).strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t


def normalize_for_fuzzy(s: str) -> str:
    t = normalize_text(s)
    # keep letters, digits, %, parentheses, commas, semicolons, colon
    t = re.sub(r"[^a-z0-9%\(\)\[\],;:\.\+\-\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def load_ground_truth_json(path: Path) -> dict[str, list[str]]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    out: dict[str, list[str]] = {}
    for entry in data:
        img = str(entry["image"])
        ingredients = entry.get("true_ingredients") or []
        out[img] = [str(x) for x in ingredients if str(x).strip()]
    return out


def best_fuzzy_score(ingredient: str, extracted_text: str) -> float:
    gt = normalize_for_fuzzy(ingredient)
    ex = normalize_for_fuzzy(extracted_text)

    if not gt or not ex:
        return 0.0

    # exact substring shortcut
    if gt in ex:
        return 100.0

    scores = [
        fuzz.partial_ratio(gt, ex),
        fuzz.token_set_ratio(gt, ex),
        fuzz.token_sort_ratio(gt, ex),
        fuzz.ratio(gt, ex),
    ]
    return float(max(scores))


def split_predicted_segments(final_text: str) -> list[str]:
    t = str(final_text).strip()
    if not t:
        return []
    chunks = re.split(r"[\n|;,]+", t)
    return [c.strip() for c in chunks if c.strip()]


def segment_matches_any_gt(segment: str, true_ingredients: list[str]) -> float:
    nonempty = [str(g) for g in true_ingredients if str(g).strip()]
    if not nonempty or not segment.strip():
        return 0.0
    return float(max(best_fuzzy_score(g, segment) for g in nonempty))


def count_fuzzy_precision(
    final_text: str,
    true_ingredients: list[str],
    fuzzy_threshold: float = 85.0,
) -> tuple[int, int, list[dict]]:
    segments = split_predicted_segments(final_text)
    nonempty_gt = [str(g) for g in true_ingredients if str(g).strip()]
    matched = 0
    details = []

    for seg in segments:
        score = segment_matches_any_gt(seg, true_ingredients)
        is_match = score >= fuzzy_threshold and bool(nonempty_gt)
        matched += int(is_match)
        details.append(
            {
                "segment": seg,
                "best_score": round(score, 2),
                "matched": int(is_match),
            }
        )

    return matched, len(segments), details


def count_fuzzy_matches(
    final_text: str,
    true_ingredients: list[str],
    fuzzy_threshold: float = 85.0,
) -> tuple[int, int, list[dict]]:
    extracted = str(final_text)
    nonempty = [str(g) for g in true_ingredients if str(g).strip()]

    matched = 0
    details = []

    for g in nonempty:
        score = best_fuzzy_score(g, extracted)
        is_match = score >= fuzzy_threshold
        matched += int(is_match)

        details.append(
            {
                "ingredient": g,
                "best_score": round(score, 2),
                "matched": int(is_match),
            }
        )

    return matched, len(nonempty), details


def ingredient_f1(precision: float, recall: float) -> float:
    if precision != precision or recall != recall:
        return float("nan")
    if precision + recall == 0:
        return 0.0
    return 2.0 * precision * recall / (precision + recall)


def evaluate(
    df_predictions: pd.DataFrame,
    gt_by_image: dict[str, list[str]],
    threshold: float,
    row_gap: float,
    cluster_gap: float,
    fuzzy_threshold: float,
) -> tuple[pd.DataFrame, dict[str, float]]:
    pred_merged = run_extraction_for_all_images(
        df_predictions,
        threshold=threshold,
        row_gap=row_gap,
        cluster_gap=cluster_gap,
    )

    rows = []
    recalls: list[float] = []
    precisions: list[float] = []
    f1s: list[float] = []

    for _, r in pred_merged.iterrows():
        iid = str(r["image_id"])
        final_text = str(r["final_text"])
        gt_list = gt_by_image.get(iid)

        if gt_list is None:
            ground_truth_str = ""
            gt_matched = 0
            gt_total = 0
            pred_matched = 0
            pred_total = 0
            recall = float("nan")
            precision = float("nan")
            f1 = float("nan")
            match_details_str = ""
            pred_match_details_str = ""
        else:
            ground_truth_str = " | ".join(gt_list)
            gt_matched, gt_total, match_details = count_fuzzy_matches(
                final_text,
                gt_list,
                fuzzy_threshold=fuzzy_threshold,
            )
            pred_matched, pred_total, pred_details = count_fuzzy_precision(
                final_text,
                gt_list,
                fuzzy_threshold=fuzzy_threshold,
            )
            recall = float(gt_matched / gt_total) if gt_total else float("nan")
            if pred_total:
                precision = float(pred_matched / pred_total)
            elif gt_total:
                precision = 0.0
            else:
                precision = float("nan")

            f1 = ingredient_f1(precision, recall)

            if recall == recall:
                recalls.append(recall)
            if precision == precision:
                precisions.append(precision)
            if f1 == f1:
                f1s.append(f1)

            match_details_str = " | ".join(
                f'{d["ingredient"]} -> {d["best_score"]} -> {d["matched"]}'
                for d in match_details
            )
            pred_match_details_str = " | ".join(
                f'{d["segment"]} -> {d["best_score"]} -> {d["matched"]}'
                for d in pred_details
            )

        rows.append(
            {
                "image_id": iid,
                "final_text": final_text,
                "ground_truth": ground_truth_str,
                "gt_matched": gt_matched,
                "gt_total": gt_total,
                "pred_matched": pred_matched,
                "pred_total": pred_total,
                "ingredient_recall": recall,
                "ingredient_precision": precision,
                "ingredient_f1": f1,
                "match_details": match_details_str,
                "pred_match_details": pred_match_details_str,
            }
        )

    out = pd.DataFrame(rows)
    metrics = {
        "mean_recall": float(pd.Series(recalls).mean()) if recalls else float("nan"),
        "mean_precision": float(pd.Series(precisions).mean()) if precisions else float("nan"),
        "mean_f1": float(pd.Series(f1s).mean()) if f1s else float("nan"),
    }
    return out, metrics


def main() -> None:
    p = argparse.ArgumentParser(
        description="Compare merged predictions to true_ingredients JSON using fuzzy "
        "ingredient recall, precision, and F1."
    )
    p.add_argument(
        "--predictions",
        type=Path,
        default=_TRAINING_DIR / "outputs" / "test_box_predictions.csv",
        help="Box-level CSV with image_id, text, coords, pred_prob",
    )
    p.add_argument(
        "--ground-truth-json",
        type=Path,
        default=_REPO_ROOT / "tests/data/true_ingredients_symspell.json",
        help="JSON array of {image, true_ingredients}",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=_TRAINING_DIR / "outputs" / "merge_evaluation_review_fuzzy.csv",
    )
    p.add_argument("--threshold", type=float, default=0.4)
    p.add_argument("--row-gap", type=float, default=90.0, dest="row_gap")
    p.add_argument("--cluster-gap", type=float, default=120.0, dest="cluster_gap")
    p.add_argument("--fuzzy-threshold", type=float, default=85.0, dest="fuzzy_threshold")
    args = p.parse_args()

    pred_path = args.predictions.resolve()
    gt_path = args.ground_truth_json.resolve()

    if not pred_path.is_file():
        raise SystemExit(f"Predictions not found: {pred_path}")
    if not gt_path.is_file():
        raise SystemExit(f"Ground truth JSON not found: {gt_path}")

    df_predictions = pd.read_csv(pred_path)
    gt_by_image = load_ground_truth_json(gt_path)

    review, metrics = evaluate(
        df_predictions,
        gt_by_image,
        threshold=args.threshold,
        row_gap=args.row_gap,
        cluster_gap=args.cluster_gap,
        fuzzy_threshold=args.fuzzy_threshold,
    )

    outp = args.output.resolve()
    outp.parent.mkdir(parents=True, exist_ok=True)
    review.to_csv(outp, index=False)

    n_r = review["ingredient_recall"].notna().sum()
    n_p = review["ingredient_precision"].notna().sum()
    n_f1 = review["ingredient_f1"].notna().sum()
    missing = int(review["ingredient_recall"].isna().sum())

    print(f"Wrote {outp} ({len(review)} rows)")
    print(f"Mean fuzzy ingredient_recall (n={n_r}): {metrics['mean_recall']:.4f}")
    print(f"Mean fuzzy ingredient_precision (n={n_p}): {metrics['mean_precision']:.4f}")
    print(f"Mean fuzzy ingredient_f1 (n={n_f1}): {metrics['mean_f1']:.4f}")
    print(f"Fuzzy threshold: {args.fuzzy_threshold}")

    if missing:
        print(
            f"Note: {missing} row(s) have no JSON ground truth "
            "(NaN ingredient_recall / precision / f1)"
        )


if __name__ == "__main__":
    main()