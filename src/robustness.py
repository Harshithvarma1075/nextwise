"""Phase 8 fixed-model evaluation, uncertainty, coverage, and slice analysis."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

import joblib
import numpy as np
import pandas as pd

from src.popularity import PopularityRecommender, ranking_metrics, temporal_split


K = 10
BOOTSTRAP_SAMPLES = 1_000
RANDOM_SEED = 20_260_912
REQUIRED_INTERACTION_COLUMNS = {"user_id", "item_id", "timestamp_unix"}
REQUIRED_ITEM_COLUMNS = {"item_id", "category_l2"}


def require_columns(frame: pd.DataFrame, required: set[str], label: str) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{label} is missing required columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError(f"{label} is empty")


def bootstrap_mean_ci(values: np.ndarray, samples: int = BOOTSTRAP_SAMPLES, seed: int = RANDOM_SEED) -> list[float]:
    """Return a deterministic percentile bootstrap CI for a mean."""
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all():
        raise ValueError("values must be a non-empty finite one-dimensional array")
    if not isinstance(samples, int) or isinstance(samples, bool) or samples < 100:
        raise ValueError("samples must be an integer of at least 100")
    rng = np.random.default_rng(seed)
    means = np.empty(samples, dtype=float)
    for index in range(samples):
        means[index] = values[rng.integers(0, len(values), size=len(values))].mean()
    return [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]


def history_slice(count: int) -> str:
    if count < 1:
        raise ValueError("history count must be positive")
    if count <= 8:
        return "2-8"
    if count <= 12:
        return "9-12"
    return "13-15"


def load_models(models_dir: Path) -> dict[str, Any]:
    required_paths = {
        "popularity": models_dir / "popularity_baseline.json",
        "collaborative": models_dir / "collaborative_filter.joblib",
        "content": models_dir / "content_based_filter.joblib",
        "hybrid": models_dir / "hybrid_recommender.joblib",
    }
    missing = [str(path) for path in required_paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing required Phase 4-7 model artifacts: {missing}")
    try:
        popularity_payload = json.loads(required_paths["popularity"].read_text(encoding="utf-8"))
        popularity = PopularityRecommender(
            tuple(str(item_id) for item_id in popularity_payload["ranked_item_ids"]),
            {str(item_id): int(count) for item_id, count in popularity_payload["unique_user_counts"].items()},
        )
        models = {
            "popularity": popularity,
            "collaborative": joblib.load(required_paths["collaborative"]),
            "content": joblib.load(required_paths["content"]),
            "hybrid": joblib.load(required_paths["hybrid"]),
        }
    except (KeyError, TypeError, ValueError, OSError) as exc:
        raise ValueError("A saved model artifact is malformed or incompatible") from exc
    for name in ("collaborative", "content", "hybrid"):
        if not callable(getattr(models[name], "recommend", None)):
            raise ValueError(f"Saved {name} artifact does not expose recommend")
    return models


def recommend(model_name: str, model: Any, user_id: int, seen: set[str], k: int) -> list[str]:
    rows = model.recommend(seen, k) if model_name == "popularity" else model.recommend(user_id, seen, k)
    item_ids = [str(row if model_name == "popularity" else row[0]) for row in rows]
    if len(item_ids) != len(set(item_ids)):
        raise ValueError(f"{model_name} returned duplicate recommendation IDs")
    if set(item_ids).intersection(seen):
        raise ValueError(f"{model_name} returned a historically seen item")
    return item_ids


def per_user_evaluation(models: dict[str, Any], history: pd.DataFrame, holdout: pd.DataFrame, k: int) -> tuple[pd.DataFrame, dict[str, list[list[str]]]]:
    require_columns(history, REQUIRED_INTERACTION_COLUMNS, "history")
    require_columns(holdout, REQUIRED_INTERACTION_COLUMNS, "holdout")
    if not isinstance(k, int) or isinstance(k, bool) or k <= 0:
        raise ValueError("k must be a positive integer")
    seen_by_user = history.groupby("user_id", observed=True)["item_id"].agg(lambda values: set(values.astype(str))).to_dict()
    truth_by_user = holdout.groupby("user_id", observed=True)["item_id"].agg(lambda values: set(values.astype(str))).to_dict()
    eligible_users = sorted(user_id for user_id in set(seen_by_user).intersection(truth_by_user) if truth_by_user[user_id].difference(seen_by_user[user_id]))
    if not eligible_users:
        raise ValueError("No users have both history and unseen holdout interactions")
    rows: list[dict[str, Any]] = []
    recommendations: dict[str, list[list[str]]] = {name: [] for name in models}
    for user_id in eligible_users:
        seen = seen_by_user[user_id]
        relevant = truth_by_user[user_id].difference(seen)
        base = {"user_id": int(user_id), "history_items": len(seen), "slice": history_slice(len(seen)), "relevant_items": len(relevant)}
        for name, model in models.items():
            item_ids = recommend(name, model, int(user_id), seen, k)
            recommendations[name].append(item_ids)
            metrics = ranking_metrics(item_ids, relevant, k)
            base.update({f"{name}_{metric}": value for metric, value in metrics.items()})
            base[f"{name}_candidate_count"] = len(item_ids)
        rows.append(base)
    return pd.DataFrame(rows), recommendations


def mean_metrics(frame: pd.DataFrame, model_name: str) -> dict[str, float]:
    return {metric: float(frame[f"{model_name}_{metric}"].mean()) for metric in ("precision_at_k", "recall_at_k", "ndcg_at_k")}


def category_diversity(recommendation_lists: list[list[str]], category_by_item: dict[str, str]) -> float:
    scores: list[float] = []
    for item_ids in recommendation_lists:
        categories = [category_by_item.get(item_id) for item_id in item_ids]
        categories = [category for category in categories if category is not None]
        if len(categories) < 2:
            continue
        pairs = len(categories) * (len(categories) - 1) / 2
        same_pairs = sum(categories[left] == categories[right] for left in range(len(categories)) for right in range(left + 1, len(categories)))
        scores.append(1.0 - same_pairs / pairs)
    return float(np.mean(scores)) if scores else 0.0


def model_summary(frame: pd.DataFrame, model_name: str, recommendation_lists: list[list[str]], catalog_size: int, category_by_item: dict[str, str]) -> dict[str, Any]:
    summary: dict[str, Any] = {"eligible_users": int(len(frame)), "users_with_candidates": int((frame[f"{model_name}_candidate_count"] > 0).sum())}
    for metric in ("precision_at_k", "recall_at_k", "ndcg_at_k"):
        values = frame[f"{model_name}_{metric}"].to_numpy(dtype=float)
        summary[metric] = float(values.mean())
        summary[f"{metric}_bootstrap_95_ci"] = bootstrap_mean_ci(values)
    flattened = [item_id for item_ids in recommendation_lists for item_id in item_ids]
    summary["unique_recommended_items"] = len(set(flattened))
    summary["catalog_coverage"] = len(set(flattened)) / catalog_size
    summary["mean_category_l2_intra_list_diversity"] = category_diversity(recommendation_lists, category_by_item)
    return summary


def paired_ndcg_difference(frame: pd.DataFrame, left: str, right: str) -> dict[str, Any]:
    difference = frame[f"{left}_ndcg_at_k"].to_numpy(dtype=float) - frame[f"{right}_ndcg_at_k"].to_numpy(dtype=float)
    return {"comparison": f"{left} minus {right}", "mean_ndcg_at_k_difference": float(difference.mean()), "bootstrap_95_ci": bootstrap_mean_ci(difference, seed=RANDOM_SEED + 1)}


def run(interactions_path: Path, items_path: Path, models_dir: Path, report_path: Path, k: int = K) -> dict[str, Any]:
    interactions = pd.read_csv(interactions_path)
    items = pd.read_csv(items_path)
    require_columns(interactions, REQUIRED_INTERACTION_COLUMNS, "processed interactions")
    require_columns(items, REQUIRED_ITEM_COLUMNS, "processed catalog")
    if items["item_id"].isna().any() or items["item_id"].astype(str).duplicated().any():
        raise ValueError("Processed catalog contains missing or duplicate item IDs")
    _, validation, test, boundaries = temporal_split(interactions)
    history = interactions.loc[interactions["timestamp_unix"] <= boundaries["validation_end_timestamp"]].copy()
    models = load_models(models_dir)
    hybrid = models["hybrid"]
    if getattr(hybrid, "cf_weight", None) != 1.0:
        raise ValueError("Phase 8 audits the validation-selected hybrid; its expected cf_weight is 1.0")
    catalog_ids = set(items["item_id"].astype(str))
    for name in ("collaborative", "content"):
        if set(getattr(models[name], "item_ids", ())) != catalog_ids:
            raise ValueError(f"Saved {name} artifact catalog does not match processed catalog")
    frame, recommendation_lists = per_user_evaluation(models, history, test, k)
    category_by_item = items.assign(item_id=items["item_id"].astype(str)).set_index("item_id")["category_l2"].astype(str).to_dict()
    summaries = {name: model_summary(frame, name, recommendation_lists[name], len(catalog_ids), category_by_item) for name in models}
    slices = {
        slice_name: {name: mean_metrics(slice_frame, name) | {"eligible_users": int(len(slice_frame))} for name in models}
        for slice_name, slice_frame in frame.groupby("slice", sort=True)
    }
    report: dict[str, Any] = {
        "phase": 8,
        "purpose": "Post-selection audit of fixed Phase 4-7 artifacts; no test result is used for tuning.",
        "k": k,
        "bootstrap": {"samples": BOOTSTRAP_SAMPLES, "confidence_level": 0.95, "random_seed": RANDOM_SEED, "unit": "eligible user"},
        "split": {**boundaries, "history_rows": int(len(history)), "validation_rows_not_used_for_tuning": int(len(validation)), "test_rows": int(len(test))},
        "history_slices": {"2-8": "2 to 8 distinct history items", "9-12": "9 to 12 distinct history items", "13-15": "13 to 15 distinct history items"},
        "model_summaries": summaries,
        "hybrid_history_slices": {slice_name: slices[slice_name]["hybrid"] for slice_name in slices},
        "paired_ndcg_differences": [paired_ndcg_difference(frame, "hybrid", "popularity"), paired_ndcg_difference(frame, "hybrid", "content"), paired_ndcg_difference(frame, "hybrid", "collaborative")],
        "notes": [
            "The hybrid was already selected in Phase 7 and is not changed here.",
            "Bootstrap intervals quantify user-level sampling uncertainty, not guaranteed future production performance.",
            "Category diversity is descriptive: 1 means every pair in a list belongs to different category_l2 values.",
        ],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit fixed recommender artifacts with uncertainty and robustness slices.")
    parser.add_argument("--interactions", type=Path, default=Path("data/processed/interactions_processed.csv"))
    parser.add_argument("--items", type=Path, default=Path("data/processed/items_processed.csv"))
    parser.add_argument("--models-dir", type=Path, default=Path("models"))
    parser.add_argument("--report", type=Path, default=Path("data/processed/phase8_evaluation.json"))
    parser.add_argument("--k", type=int, default=K)
    args = parser.parse_args()
    print(json.dumps(run(args.interactions, args.items, args.models_dir, args.report, args.k), indent=2))


if __name__ == "__main__":
    main()
