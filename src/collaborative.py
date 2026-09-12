"""Sparse item-based collaborative filtering for Phase 5."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import joblib
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.preprocessing import normalize

from src.popularity import ranking_metrics, temporal_split


REQUIRED_COLUMNS = {"user_id", "item_id", "timestamp_unix"}


def require_columns(interactions: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS.difference(interactions.columns)
    if missing:
        raise ValueError(f"Interactions are missing required columns: {sorted(missing)}")
    if interactions.empty:
        raise ValueError("Interactions are empty")


@dataclass
class ItemCollaborativeFilter:
    item_ids: tuple[str, ...]
    user_histories: dict[int, set[str]]
    neighbor_item_ids: dict[str, tuple[str, ...]]
    neighbor_scores: dict[str, tuple[float, ...]]
    max_neighbors: int

    @classmethod
    def fit(cls, interactions: pd.DataFrame, catalog_item_ids: Iterable[str], max_neighbors: int = 100) -> "ItemCollaborativeFilter":
        require_columns(interactions)
        if not isinstance(max_neighbors, int) or max_neighbors < 1:
            raise ValueError("max_neighbors must be a positive integer")
        item_ids = tuple(sorted({str(item_id) for item_id in catalog_item_ids}))
        if not item_ids:
            raise ValueError("Catalog is empty")
        catalog = set(item_ids)
        pairs = interactions.loc[interactions["item_id"].astype(str).isin(catalog), ["user_id", "item_id"]].copy()
        pairs["item_id"] = pairs["item_id"].astype(str)
        pairs = pairs.drop_duplicates()
        if pairs.empty:
            raise ValueError("No catalog interactions are available for collaborative filtering")

        user_ids = tuple(sorted(int(user_id) for user_id in pairs["user_id"].unique()))
        user_index = {user_id: index for index, user_id in enumerate(user_ids)}
        item_index = {item_id: index for index, item_id in enumerate(item_ids)}
        matrix = csr_matrix(
            (np.ones(len(pairs), dtype=np.float32), ([user_index[int(user_id)] for user_id in pairs["user_id"]], [item_index[item_id] for item_id in pairs["item_id"]])),
            shape=(len(user_ids), len(item_ids)),
            dtype=np.float32,
        )
        matrix.sum_duplicates()
        matrix.data[:] = 1.0  # binary implicit interaction; repeat event volume is not a preference weight.
        item_matrix = normalize(matrix.transpose().tocsr(), norm="l2", copy=True)
        similarities = (item_matrix @ item_matrix.transpose()).tocsr()
        similarities.setdiag(0)
        similarities.eliminate_zeros()

        neighbor_item_ids: dict[str, tuple[str, ...]] = {}
        neighbor_scores: dict[str, tuple[float, ...]] = {}
        for item_id, item_position in item_index.items():
            row_start, row_end = similarities.indptr[item_position], similarities.indptr[item_position + 1]
            positions = similarities.indices[row_start:row_end]
            scores = similarities.data[row_start:row_end]
            ranked = sorted(
                ((item_ids[int(position)], float(score)) for position, score in zip(positions, scores, strict=True) if score > 0),
                key=lambda row: (-row[1], row[0]),
            )[:max_neighbors]
            neighbor_item_ids[item_id] = tuple(candidate for candidate, _ in ranked)
            neighbor_scores[item_id] = tuple(score for _, score in ranked)
        histories = pairs.groupby("user_id", observed=True)["item_id"].agg(lambda values: set(values)).to_dict()
        return cls(item_ids, {int(user_id): history for user_id, history in histories.items()}, neighbor_item_ids, neighbor_scores, max_neighbors)

    def recommend(self, user_id: int, seen_item_ids: Iterable[str] | None = None, limit: int = 10) -> list[tuple[str, float]]:
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        history = self.user_histories.get(int(user_id))
        if not history:
            return []
        seen = set(history) if seen_item_ids is None else {str(item_id) for item_id in seen_item_ids}
        scores: dict[str, float] = {}
        for source_item in history:
            for candidate, similarity in zip(self.neighbor_item_ids.get(source_item, ()), self.neighbor_scores.get(source_item, ()), strict=True):
                if candidate not in seen:
                    scores[candidate] = scores.get(candidate, 0.0) + similarity
        return sorted(scores.items(), key=lambda row: (-row[1], row[0]))[:limit]


def evaluate(model: ItemCollaborativeFilter, history: pd.DataFrame, holdout: pd.DataFrame, k: int = 10) -> dict[str, float | int]:
    require_columns(history)
    require_columns(holdout)
    seen_by_user = history.groupby("user_id", observed=True)["item_id"].agg(lambda values: set(values.astype(str))).to_dict()
    truth_by_user = holdout.groupby("user_id", observed=True)["item_id"].agg(lambda values: set(values.astype(str))).to_dict()
    eligible_users = sorted(
        user_id for user_id in set(seen_by_user).intersection(truth_by_user)
        if truth_by_user[user_id].difference(seen_by_user[user_id])
    )
    if not eligible_users:
        raise ValueError("No users have both history and unseen holdout interactions")
    metrics = []
    users_with_candidates = 0
    for user_id in eligible_users:
        seen = seen_by_user[user_id]
        recommendations = [item_id for item_id, _ in model.recommend(int(user_id), seen, k)]
        if recommendations:
            users_with_candidates += 1
        metrics.append(ranking_metrics(recommendations, truth_by_user[user_id].difference(seen), k))
    return {
        "eligible_users": len(eligible_users),
        "users_with_candidates": users_with_candidates,
        "precision_at_k": sum(metric["precision_at_k"] for metric in metrics) / len(metrics),
        "recall_at_k": sum(metric["recall_at_k"] for metric in metrics) / len(metrics),
        "ndcg_at_k": sum(metric["ndcg_at_k"] for metric in metrics) / len(metrics),
    }


def run(interactions_path: Path, items_path: Path, models_dir: Path, report_path: Path, k: int = 10, max_neighbors: int = 100) -> dict[str, object]:
    interactions = pd.read_csv(interactions_path)
    items = pd.read_csv(items_path)
    if "item_id" not in items.columns:
        raise ValueError("Processed item catalog is missing item_id")
    catalog = items["item_id"].astype(str).tolist()
    train, validation, test, boundaries = temporal_split(interactions)
    validation_model = ItemCollaborativeFilter.fit(train, catalog, max_neighbors)
    validation_result = evaluate(validation_model, train, validation, k)
    test_history = pd.concat([train, validation], ignore_index=True)
    final_model = ItemCollaborativeFilter.fit(test_history, catalog, max_neighbors)
    test_result = evaluate(final_model, test_history, test, k)
    models_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_model, models_dir / "collaborative_filter.joblib")
    report: dict[str, object] = {
        "model": "Item-based collaborative filtering with binary implicit interactions and cosine similarity",
        "k": k,
        "max_neighbors": max_neighbors,
        "split": {**boundaries, "train_rows": len(train), "validation_rows": len(validation), "test_rows": len(test)},
        "validation": validation_result,
        "test": test_result,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit and evaluate sparse item-based collaborative filtering.")
    parser.add_argument("--interactions", type=Path, default=Path("data/processed/interactions_processed.csv"))
    parser.add_argument("--items", type=Path, default=Path("data/processed/items_processed.csv"))
    parser.add_argument("--models-dir", type=Path, default=Path("models"))
    parser.add_argument("--report", type=Path, default=Path("data/processed/collaborative_evaluation.json"))
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--max-neighbors", type=int, default=100)
    args = parser.parse_args()
    print(json.dumps(run(args.interactions, args.items, args.models_dir, args.report, args.k, args.max_neighbors), indent=2))


if __name__ == "__main__":
    main()
