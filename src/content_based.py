"""TF-IDF content-based recommendations from verified product catalog metadata."""
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
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from src.popularity import ranking_metrics, temporal_split


REQUIRED_ITEM_COLUMNS = {"item_id", "product_name", "product_description", "category_l1", "category_l2", "gender"}
REQUIRED_INTERACTION_COLUMNS = {"user_id", "item_id", "timestamp_unix"}


def product_document(row: pd.Series) -> str:
    """Build an interpretable document without treating price/promotion as text."""
    def text(value: object) -> str:
        return "" if pd.isna(value) else str(value).strip()

    categories = " ".join(
        f"{prefix}_{text(row[column]).replace(' ', '_').lower()}"
        for column, prefix in (("category_l1", "category_l1"), ("category_l2", "category_l2"), ("gender", "catalog_gender"))
        if text(row[column])
    )
    return " ".join(part for part in (text(row["product_name"]), text(row["product_description"]), categories) if part)


@dataclass
class ContentBasedRecommender:
    item_ids: tuple[str, ...]
    item_matrix: csr_matrix
    vectorizer: TfidfVectorizer
    user_histories: dict[int, set[str]]
    item_index: dict[str, int]

    @classmethod
    def fit(cls, items: pd.DataFrame, interactions: pd.DataFrame, max_features: int = 25_000) -> "ContentBasedRecommender":
        missing_items = REQUIRED_ITEM_COLUMNS.difference(items.columns)
        missing_interactions = REQUIRED_INTERACTION_COLUMNS.difference(interactions.columns)
        if missing_items:
            raise ValueError(f"Items are missing required columns: {sorted(missing_items)}")
        if missing_interactions:
            raise ValueError(f"Interactions are missing required columns: {sorted(missing_interactions)}")
        if items.empty or interactions.empty:
            raise ValueError("Items and interactions must not be empty")
        if not isinstance(max_features, int) or max_features < 1:
            raise ValueError("max_features must be a positive integer")
        catalog = items.loc[:, sorted(REQUIRED_ITEM_COLUMNS)].copy()
        catalog["item_id"] = catalog["item_id"].astype(str)
        if catalog["item_id"].duplicated().any():
            raise ValueError("Items contain duplicate item_id values")
        catalog["document"] = catalog.apply(product_document, axis=1)
        if catalog["document"].str.strip().eq("").any():
            raise ValueError("An item has no usable content metadata")
        catalog = catalog.sort_values("item_id", kind="stable").reset_index(drop=True)
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=max_features, sublinear_tf=True)
        item_matrix = vectorizer.fit_transform(catalog["document"]).tocsr()
        if item_matrix.shape[1] == 0:
            raise ValueError("TF-IDF produced zero content features")
        item_matrix = normalize(item_matrix, norm="l2", copy=False)
        item_ids = tuple(catalog["item_id"])
        item_index = {item_id: index for index, item_id in enumerate(item_ids)}
        pairs = interactions.loc[interactions["item_id"].astype(str).isin(item_index), ["user_id", "item_id"]].copy()
        pairs["item_id"] = pairs["item_id"].astype(str)
        histories = pairs.drop_duplicates().groupby("user_id", observed=True)["item_id"].agg(lambda values: set(values)).to_dict()
        return cls(item_ids, item_matrix, vectorizer, {int(user_id): history for user_id, history in histories.items()}, item_index)

    def recommend(self, user_id: int, seen_item_ids: Iterable[str] | None = None, limit: int = 10) -> list[tuple[str, float]]:
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        history = self.user_histories.get(int(user_id))
        if not history:
            return []
        seen = set(history) if seen_item_ids is None else {str(item_id) for item_id in seen_item_ids}
        positions = [self.item_index[item_id] for item_id in history if item_id in self.item_index]
        if not positions:
            return []
        # scipy sparse ``sum`` returns ``np.matrix``; convert it back to CSR so
        # scikit-learn normalization remains compatible with current NumPy.
        profile = normalize(csr_matrix(self.item_matrix[positions].sum(axis=0)), norm="l2", copy=False)
        scores = (self.item_matrix @ profile.T).toarray().ravel()
        candidates = ((item_id, float(scores[position])) for position, item_id in enumerate(self.item_ids) if item_id not in seen and scores[position] > 0)
        return sorted(candidates, key=lambda row: (-row[1], row[0]))[:limit]


def evaluate(model: ContentBasedRecommender, history: pd.DataFrame, holdout: pd.DataFrame, k: int = 10) -> dict[str, float | int]:
    seen_by_user = history.groupby("user_id", observed=True)["item_id"].agg(lambda values: set(values.astype(str))).to_dict()
    truth_by_user = holdout.groupby("user_id", observed=True)["item_id"].agg(lambda values: set(values.astype(str))).to_dict()
    eligible = sorted(user_id for user_id in set(seen_by_user).intersection(truth_by_user) if truth_by_user[user_id].difference(seen_by_user[user_id]))
    if not eligible:
        raise ValueError("No users have both history and unseen holdout interactions")
    metrics, users_with_candidates = [], 0
    for user_id in eligible:
        seen = seen_by_user[user_id]
        recommendations = [item_id for item_id, _ in model.recommend(int(user_id), seen, k)]
        users_with_candidates += bool(recommendations)
        metrics.append(ranking_metrics(recommendations, truth_by_user[user_id].difference(seen), k))
    return {
        "eligible_users": len(eligible), "users_with_candidates": users_with_candidates,
        "precision_at_k": sum(metric["precision_at_k"] for metric in metrics) / len(metrics),
        "recall_at_k": sum(metric["recall_at_k"] for metric in metrics) / len(metrics),
        "ndcg_at_k": sum(metric["ndcg_at_k"] for metric in metrics) / len(metrics),
    }


def run(interactions_path: Path, items_path: Path, models_dir: Path, report_path: Path, k: int = 10, max_features: int = 25_000) -> dict[str, object]:
    interactions, items = pd.read_csv(interactions_path), pd.read_csv(items_path)
    train, validation, test, boundaries = temporal_split(interactions)
    validation_model = ContentBasedRecommender.fit(items, train, max_features)
    validation_result = evaluate(validation_model, train, validation, k)
    test_history = pd.concat([train, validation], ignore_index=True)
    final_model = ContentBasedRecommender.fit(items, test_history, max_features)
    test_result = evaluate(final_model, test_history, test, k)
    models_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_model, models_dir / "content_based_filter.joblib")
    report = {
        "model": "TF-IDF content filtering from product name, description, category levels, and catalog gender",
        "k": k, "max_features": max_features,
        "split": {**boundaries, "train_rows": len(train), "validation_rows": len(validation), "test_rows": len(test)},
        "validation": validation_result, "test": test_result,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit and evaluate TF-IDF content-based recommendations.")
    parser.add_argument("--interactions", type=Path, default=Path("data/processed/interactions_processed.csv"))
    parser.add_argument("--items", type=Path, default=Path("data/processed/items_processed.csv"))
    parser.add_argument("--models-dir", type=Path, default=Path("models"))
    parser.add_argument("--report", type=Path, default=Path("data/processed/content_evaluation.json"))
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--max-features", type=int, default=25_000)
    args = parser.parse_args()
    print(json.dumps(run(args.interactions, args.items, args.models_dir, args.report, args.k, args.max_features), indent=2))


if __name__ == "__main__":
    main()
