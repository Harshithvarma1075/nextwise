"""Validation-selected, score-normalized CF/content hybrid recommendations."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import joblib
import numpy as np
import pandas as pd

from src.collaborative import ItemCollaborativeFilter
from src.content_based import ContentBasedRecommender
from src.popularity import ranking_metrics, temporal_split


REQUIRED_COLUMNS = {"user_id", "item_id", "timestamp_unix"}


def require_interactions(interactions: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS.difference(interactions.columns)
    if missing:
        raise ValueError(f"Interactions are missing required columns: {sorted(missing)}")
    if interactions.empty:
        raise ValueError("Interactions are empty")


def validate_weight(cf_weight: float) -> float:
    if isinstance(cf_weight, bool) or not isinstance(cf_weight, (int, float)):
        raise ValueError("cf_weight must be a finite number between 0 and 1")
    value = float(cf_weight)
    if not np.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError("cf_weight must be a finite number between 0 and 1")
    return value


def validate_positive_int(value: int, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def normalize_scores(rows: list[tuple[str, float]]) -> dict[str, float]:
    """Max-normalize one source's non-negative candidate scores safely."""
    scores = {str(item_id): float(score) for item_id, score in rows if np.isfinite(score) and score > 0}
    if not scores:
        return {}
    maximum = max(scores.values())
    if maximum <= 0:
        return {}
    return {item_id: score / maximum for item_id, score in scores.items()}


@dataclass
class HybridRecommender:
    collaborative: ItemCollaborativeFilter
    content: ContentBasedRecommender
    cf_weight: float
    candidate_limit: int = 100

    def __post_init__(self) -> None:
        self.cf_weight = validate_weight(self.cf_weight)
        self.candidate_limit = validate_positive_int(self.candidate_limit, "candidate_limit")
        if self.collaborative.item_ids != self.content.item_ids:
            raise ValueError("Collaborative and content models must use the same ordered catalog")

    def source_scores(self, user_id: int, seen_item_ids: Iterable[str] | None = None) -> tuple[dict[str, float], dict[str, float]]:
        """Return independently normalized CF and content candidates for one user."""
        try:
            normalized_user_id = int(user_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("user_id must be an integer") from exc
        seen = None if seen_item_ids is None else {str(item_id) for item_id in seen_item_ids}
        cf_scores = normalize_scores(self.collaborative.recommend(normalized_user_id, seen, self.candidate_limit))
        content_scores = normalize_scores(self.content.recommend(normalized_user_id, seen, self.candidate_limit))
        return cf_scores, content_scores

    def combine_scores(self, cf_scores: dict[str, float], content_scores: dict[str, float], limit: int) -> list[tuple[str, float]]:
        validate_positive_int(limit, "limit")
        if not cf_scores and not content_scores:
            return []
        content_weight = 1.0 - self.cf_weight
        candidates = set(cf_scores).union(content_scores)
        scored = (
            (item_id, self.cf_weight * cf_scores.get(item_id, 0.0) + content_weight * content_scores.get(item_id, 0.0))
            for item_id in candidates
        )
        return sorted(scored, key=lambda row: (-row[1], row[0]))[:limit]

    def recommend(self, user_id: int, seen_item_ids: Iterable[str] | None = None, limit: int = 10) -> list[tuple[str, float]]:
        cf_scores, content_scores = self.source_scores(user_id, seen_item_ids)
        return self.combine_scores(cf_scores, content_scores, limit)


def evaluate(model: HybridRecommender, history: pd.DataFrame, holdout: pd.DataFrame, k: int = 10) -> dict[str, float | int]:
    require_interactions(history)
    require_interactions(holdout)
    validate_positive_int(k, "k")
    seen_by_user = history.groupby("user_id", observed=True)["item_id"].agg(lambda values: set(values.astype(str))).to_dict()
    truth_by_user = holdout.groupby("user_id", observed=True)["item_id"].agg(lambda values: set(values.astype(str))).to_dict()
    eligible = sorted(
        user_id for user_id in set(seen_by_user).intersection(truth_by_user)
        if truth_by_user[user_id].difference(seen_by_user[user_id])
    )
    if not eligible:
        raise ValueError("No users have both history and unseen holdout interactions")
    metrics: list[dict[str, float]] = []
    users_with_candidates = 0
    for user_id in eligible:
        recommendations = [item_id for item_id, _ in model.recommend(int(user_id), seen_by_user[user_id], k)]
        users_with_candidates += bool(recommendations)
        metrics.append(ranking_metrics(recommendations, truth_by_user[user_id].difference(seen_by_user[user_id]), k))
    return {
        "eligible_users": len(eligible),
        "users_with_candidates": users_with_candidates,
        "precision_at_k": sum(metric["precision_at_k"] for metric in metrics) / len(metrics),
        "recall_at_k": sum(metric["recall_at_k"] for metric in metrics) / len(metrics),
        "ndcg_at_k": sum(metric["ndcg_at_k"] for metric in metrics) / len(metrics),
    }


def choose_weight(collaborative: ItemCollaborativeFilter, content: ContentBasedRecommender, train: pd.DataFrame, validation: pd.DataFrame, k: int, candidate_limit: int) -> tuple[float, list[dict[str, float | int]]]:
    """Tune weights without recomputing source candidates for every trial."""
    probe = HybridRecommender(collaborative, content, 0.5, candidate_limit)
    seen_by_user = train.groupby("user_id", observed=True)["item_id"].agg(lambda values: set(values.astype(str))).to_dict()
    truth_by_user = validation.groupby("user_id", observed=True)["item_id"].agg(lambda values: set(values.astype(str))).to_dict()
    cached_candidates: list[tuple[dict[str, float], dict[str, float], set[str]]] = []
    for user_id in sorted(set(seen_by_user).intersection(truth_by_user)):
        relevant = truth_by_user[user_id].difference(seen_by_user[user_id])
        if relevant:
            cf_scores, content_scores = probe.source_scores(int(user_id), seen_by_user[user_id])
            cached_candidates.append((cf_scores, content_scores, relevant))
    if not cached_candidates:
        raise ValueError("No users have both history and unseen holdout interactions")
    trials: list[dict[str, float | int]] = []
    for cf_weight in np.linspace(0.0, 1.0, 21):
        model = HybridRecommender(collaborative, content, float(cf_weight), candidate_limit)
        metrics: list[dict[str, float]] = []
        users_with_candidates = 0
        for cf_scores, content_scores, relevant in cached_candidates:
            recommendations = [item_id for item_id, _ in model.combine_scores(cf_scores, content_scores, k)]
            users_with_candidates += bool(recommendations)
            metrics.append(ranking_metrics(recommendations, relevant, k))
        metrics_summary: dict[str, float | int] = {
            "eligible_users": len(cached_candidates),
            "users_with_candidates": users_with_candidates,
            "precision_at_k": sum(metric["precision_at_k"] for metric in metrics) / len(metrics),
            "recall_at_k": sum(metric["recall_at_k"] for metric in metrics) / len(metrics),
            "ndcg_at_k": sum(metric["ndcg_at_k"] for metric in metrics) / len(metrics),
        }
        trials.append({"cf_weight": round(float(cf_weight), 2), **metrics_summary})
    best = max(
        trials,
        key=lambda result: (
            float(result["ndcg_at_k"]),
            float(result["recall_at_k"]),
            float(result["precision_at_k"]),
            float(result["cf_weight"]),
        ),
    )
    return float(best["cf_weight"]), trials


def run(interactions_path: Path, items_path: Path, models_dir: Path, report_path: Path, k: int = 10, max_neighbors: int = 100, max_features: int = 25_000, candidate_limit: int = 100) -> dict[str, object]:
    validate_positive_int(k, "k")
    validate_positive_int(max_neighbors, "max_neighbors")
    validate_positive_int(max_features, "max_features")
    validate_positive_int(candidate_limit, "candidate_limit")
    interactions = pd.read_csv(interactions_path)
    items = pd.read_csv(items_path)
    require_interactions(interactions)
    if "item_id" not in items.columns or items["item_id"].isna().any() or items["item_id"].astype(str).duplicated().any():
        raise ValueError("Processed item catalog must contain unique non-null item_id values")
    catalog = items["item_id"].astype(str).tolist()
    train, validation, test, boundaries = temporal_split(interactions)
    validation_cf = ItemCollaborativeFilter.fit(train, catalog, max_neighbors)
    validation_content = ContentBasedRecommender.fit(items, train, max_features)
    selected_weight, trials = choose_weight(validation_cf, validation_content, train, validation, k, candidate_limit)
    validation_model = HybridRecommender(validation_cf, validation_content, selected_weight, candidate_limit)
    validation_result = evaluate(validation_model, train, validation, k)
    test_history = pd.concat([train, validation], ignore_index=True)
    final_cf = ItemCollaborativeFilter.fit(test_history, catalog, max_neighbors)
    final_content = ContentBasedRecommender.fit(items, test_history, max_features)
    final_model = HybridRecommender(final_cf, final_content, selected_weight, candidate_limit)
    test_result = evaluate(final_model, test_history, test, k)
    models_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_model, models_dir / "hybrid_recommender.joblib")
    report: dict[str, object] = {
        "model": "Per-user max-normalized weighted blend of item-based CF and TF-IDF content scores",
        "k": k,
        "max_neighbors": max_neighbors,
        "max_features": max_features,
        "candidate_limit": candidate_limit,
        "selected_cf_weight": selected_weight,
        "selected_content_weight": 1.0 - selected_weight,
        "weight_selection_split": "validation",
        "validation_weight_trials": trials,
        "split": {**boundaries, "train_rows": len(train), "validation_rows": len(validation), "test_rows": len(test)},
        "validation": validation_result,
        "test": test_result,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit and evaluate a validation-selected CF/content hybrid recommender.")
    parser.add_argument("--interactions", type=Path, default=Path("data/processed/interactions_processed.csv"))
    parser.add_argument("--items", type=Path, default=Path("data/processed/items_processed.csv"))
    parser.add_argument("--models-dir", type=Path, default=Path("models"))
    parser.add_argument("--report", type=Path, default=Path("data/processed/hybrid_evaluation.json"))
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--max-neighbors", type=int, default=100)
    parser.add_argument("--max-features", type=int, default=25_000)
    parser.add_argument("--candidate-limit", type=int, default=100)
    args = parser.parse_args()
    print(json.dumps(run(args.interactions, args.items, args.models_dir, args.report, args.k, args.max_neighbors, args.max_features, args.candidate_limit), indent=2))


if __name__ == "__main__":
    main()
