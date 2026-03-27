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


def evaluate(
    df_predictions: pd.DataFrame,
    gt_by_image: dict[str, list[str]],
    threshold: float,
    row_gap: float,
    cluster_gap: float,
    fuzzy_threshold: float,
) -> tuple[pd.DataFrame, float]:
    pred_merged = run_extraction_for_all_images(
        df_predictions,
        threshold=threshold,
        row_gap=row_gap,
        cluster_gap=cluster_gap,
    )

    rows = []
    recalls: list[float] = []

    for _, r in pred_merged.iterrows():
        iid = str(r["image_id"])
        final_text = str(r["final_text"])
        gt_list = gt_by_image.get(iid)

        if gt_list is None:
            ground_truth_str = ""
            gt_matched = 0
            gt_total = 0
            recall = float("nan")
            match_details_str = ""
        else:
            ground_truth_str = " | ".join(gt_list)
            gt_matched, gt_total, match_details = count_fuzzy_matches(
                final_text,
                gt_list,
                fuzzy_threshold=fuzzy_threshold,
            )
            recall = float(gt_matched / gt_total) if gt_total else float("nan")
            recalls.append(recall)

            match_details_str = " | ".join(
                f'{d["ingredient"]} -> {d["best_score"]} -> {d["matched"]}'
                for d in match_details
            )

        rows.append(
            {
                "image_id": iid,
                "final_text": final_text,
                "ground_truth": ground_truth_str,
                "gt_matched": gt_matched,
                "gt_total": gt_total,
                "ingredient_recall": recall,
                "match_details": match_details_str,
            }
        )

    out = pd.DataFrame(rows)
    mean_recall = float(pd.Series(recalls).mean()) if recalls else float("nan")
    return out, mean_recall


def main() -> None:
    p = argparse.ArgumentParser(
        description="Compare merged predictions to true_ingredients JSON using fuzzy ingredient recall."
    )
    p.add_argument(
        "--predictions",
        type=Path,
        default=_TRAINING_DIR / "test_box_predictions.csv",
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
        default=_TRAINING_DIR / "merge_evaluation_review_fuzzy.csv",
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

    review, mean_recall = evaluate(
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

    n = review["ingredient_recall"].notna().sum()
    missing = int(review["ingredient_recall"].isna().sum())

    print(f"Wrote {outp} ({len(review)} rows)")
    print(f"Mean fuzzy ingredient_recall (n={n}): {mean_recall:.4f}")
    print(f"Fuzzy threshold: {args.fuzzy_threshold}")

    if missing:
        print(f"Note: {missing} row(s) have no JSON ground truth (NaN ingredient_recall)")


if __name__ == "__main__":
    main()