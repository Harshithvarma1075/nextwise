"""Popularity baseline and temporal evaluation utilities for Phase 4."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

REQUIRED_INTERACTION_COLUMNS = {"user_id", "item_id", "timestamp_unix"}


def require_interaction_columns(interactions: pd.DataFrame) -> None:
    missing = REQUIRED_INTERACTION_COLUMNS.difference(interactions.columns)
    if missing:
        raise ValueError(f"Interactions are missing required columns: {sorted(missing)}")
    if interactions.empty:
        raise ValueError("Interactions are empty")


def temporal_split(interactions: pd.DataFrame, train_quantile: float = 0.70, validation_quantile: float = 0.85) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, int]]:
    """Create global non-overlapping temporal windows without random future leakage."""
    require_interaction_columns(interactions)
    if not 0 < train_quantile < validation_quantile < 1:
        raise ValueError("Temporal quantiles must satisfy 0 < train < validation < 1")
    timestamps = pd.to_numeric(interactions["timestamp_unix"], errors="coerce")
    if timestamps.isna().any() or timestamps.le(0).any():
        raise ValueError("Interactions have invalid timestamps")
    train_end = int(timestamps.quantile(train_quantile, interpolation="higher"))
    validation_end = int(timestamps.quantile(validation_quantile, interpolation="higher"))
    train = interactions.loc[timestamps <= train_end].copy()
    validation = interactions.loc[(timestamps > train_end) & (timestamps <= validation_end)].copy()
    test = interactions.loc[timestamps > validation_end].copy()
    if train.empty or validation.empty or test.empty:
        raise ValueError("Temporal split produced an empty window")
    metadata = {"train_end_timestamp": train_end, "validation_end_timestamp": validation_end}
    return train, validation, test, metadata


@dataclass(frozen=True)
class PopularityRecommender:
    ranked_item_ids: tuple[str, ...]
    unique_user_counts: dict[str, int]

    @classmethod
    def fit(cls, interactions: pd.DataFrame, catalog_item_ids: Iterable[str]) -> "PopularityRecommender":
        require_interaction_columns(interactions)
        catalog = {str(item_id) for item_id in catalog_item_ids}
        if not catalog:
            raise ValueError("Catalog is empty")
        observed = interactions.loc[interactions["item_id"].astype(str).isin(catalog), ["user_id", "item_id"]].drop_duplicates()
        counts = observed.groupby("item_id", observed=True)["user_id"].nunique().astype(int).to_dict()
        ranked = tuple(sorted(catalog, key=lambda item_id: (-counts.get(item_id, 0), item_id)))
        return cls(ranked, {str(item_id): int(count) for item_id, count in counts.items()})

    def recommend(self, seen_item_ids: Iterable[str] = (), limit: int = 10) -> list[str]:
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        seen = {str(item_id) for item_id in seen_item_ids}
        return [item_id for item_id in self.ranked_item_ids if item_id not in seen][:limit]

    def to_dict(self) -> dict[str, object]:
        return {"method": "unique_user_interaction_count", "ranked_item_ids": list(self.ranked_item_ids), "unique_user_counts": self.unique_user_counts}


def ranking_metrics(recommendations: list[str], relevant: set[str], k: int) -> dict[str, float]:
    if k <= 0:
        raise ValueError("k must be positive")
    top_k = recommendations[:k]
    hits = [int(item_id in relevant) for item_id in top_k]
    precision = sum(hits) / k
    recall = sum(hits) / len(relevant) if relevant else 0.0
    dcg = sum(hit / __import__("math").log2(index + 2) for index, hit in enumerate(hits))
    ideal_hits = min(len(relevant), k)
    idcg = sum(1 / __import__("math").log2(index + 2) for index in range(ideal_hits))
    return {"precision_at_k": precision, "recall_at_k": recall, "ndcg_at_k": dcg / idcg if idcg else 0.0}


def evaluate(model: PopularityRecommender, history: pd.DataFrame, holdout: pd.DataFrame, k: int = 10) -> dict[str, float | int]:
    require_interaction_columns(history)
    require_interaction_columns(holdout)
    seen_by_user = history.groupby("user_id", observed=True)["item_id"].agg(lambda values: set(values.astype(str))).to_dict()
    truth_by_user = holdout.groupby("user_id", observed=True)["item_id"].agg(lambda values: set(values.astype(str))).to_dict()
    eligible_users = sorted(
        user_id
        for user_id in set(seen_by_user).intersection(truth_by_user)
        if truth_by_user[user_id].difference(seen_by_user[user_id])
    )
    if not eligible_users:
        raise ValueError("No users have both history and holdout interactions")
    per_user = [
        ranking_metrics(
            model.recommend(seen_by_user[user_id], k),
            truth_by_user[user_id].difference(seen_by_user[user_id]),
            k,
        )
        for user_id in eligible_users
    ]
    return {
        "eligible_users": len(eligible_users),
        "precision_at_k": sum(metric["precision_at_k"] for metric in per_user) / len(per_user),
        "recall_at_k": sum(metric["recall_at_k"] for metric in per_user) / len(per_user),
        "ndcg_at_k": sum(metric["ndcg_at_k"] for metric in per_user) / len(per_user),
    }


def run(interactions_path: Path, items_path: Path, models_dir: Path, report_path: Path, k: int = 10) -> dict[str, object]:
    interactions = pd.read_csv(interactions_path)
    items = pd.read_csv(items_path)
    if "item_id" not in items.columns:
        raise ValueError("Processed item catalog is missing item_id")
    catalog = items["item_id"].astype(str).tolist()
    train, validation, test, boundaries = temporal_split(interactions)
    validation_model = PopularityRecommender.fit(train, catalog)
    validation_result = evaluate(validation_model, train, validation, k)
    test_history = pd.concat([train, validation], ignore_index=True)
    final_model = PopularityRecommender.fit(test_history, catalog)
    test_result = evaluate(final_model, test_history, test, k)
    models_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    (models_dir / "popularity_baseline.json").write_text(json.dumps(final_model.to_dict(), indent=2), encoding="utf-8")
    report: dict[str, object] = {
        "model": "Popularity baseline by unique users per item",
        "k": k,
        "split": {**boundaries, "train_rows": len(train), "validation_rows": len(validation), "test_rows": len(test)},
        "validation": validation_result,
        "test": test_result,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit and evaluate the popularity baseline.")
    parser.add_argument("--interactions", type=Path, default=Path("data/processed/interactions_processed.csv"))
    parser.add_argument("--items", type=Path, default=Path("data/processed/items_processed.csv"))
    parser.add_argument("--models-dir", type=Path, default=Path("models"))
    parser.add_argument("--report", type=Path, default=Path("data/processed/popularity_evaluation.json"))
    parser.add_argument("--k", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(run(args.interactions, args.items, args.models_dir, args.report, args.k), indent=2))


if __name__ == "__main__":
    main()
