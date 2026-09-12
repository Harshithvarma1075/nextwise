"""Cold-start router: personalized recommendations with popularity fallback."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import joblib
import pandas as pd

from src.hybrid import HybridRecommender
from src.popularity import PopularityRecommender, ranking_metrics, temporal_split


REQUIRED_INTERACTION_COLUMNS = {"user_id", "item_id", "timestamp_unix"}


def validate_limit(limit: int) -> int:
    if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
        raise ValueError("limit must be a positive integer")
    return limit


def validate_user_id(user_id: int | None) -> int | None:
    if user_id is None:
        return None
    if isinstance(user_id, bool):
        raise ValueError("user_id must be a positive integer or None")
    try:
        normalized = int(user_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("user_id must be a positive integer or None") from exc
    if normalized <= 0:
        raise ValueError("user_id must be a positive integer or None")
    return normalized


def normalize_seen(seen_item_ids: Iterable[str] | None) -> set[str]:
    if seen_item_ids is None:
        return set()
    if isinstance(seen_item_ids, (str, bytes)):
        raise ValueError("seen_item_ids must be an iterable of item IDs, not a string")
    try:
        return {str(item_id) for item_id in seen_item_ids}
    except TypeError as exc:
        raise ValueError("seen_item_ids must be an iterable of item IDs") from exc


@dataclass(frozen=True)
class RoutedRecommendations:
    item_ids: tuple[str, ...]
    source: str
    personalized: bool


@dataclass
class ColdStartRouter:
    """Route known users to the selected hybrid, otherwise to popularity."""

    personalized_model: HybridRecommender
    popularity_model: PopularityRecommender

    def __post_init__(self) -> None:
        if not callable(getattr(self.personalized_model, "recommend", None)):
            raise ValueError("personalized_model must expose recommend")
        if not callable(getattr(self.popularity_model, "recommend", None)):
            raise ValueError("popularity_model must expose recommend")
        if not self.popularity_model.ranked_item_ids:
            raise ValueError("popularity_model has no ranked items")

    @property
    def known_user_ids(self) -> set[int]:
        return set(self.personalized_model.collaborative.user_histories)

    def recommend(self, user_id: int | None, seen_item_ids: Iterable[str] | None = None, limit: int = 10) -> RoutedRecommendations:
        normalized_user_id = validate_user_id(user_id)
        seen = normalize_seen(seen_item_ids)
        validate_limit(limit)
        if normalized_user_id is not None and normalized_user_id in self.known_user_ids:
            personalized = self.personalized_model.recommend(normalized_user_id, seen, limit)
            item_ids = tuple(str(item_id) for item_id, _ in personalized)
            if item_ids:
                return RoutedRecommendations(item_ids, "personalized_cf", True)
        fallback = tuple(self.popularity_model.recommend(seen, limit))
        return RoutedRecommendations(fallback, "popularity_cold_start", False)


def load_router(models_dir: Path) -> ColdStartRouter:
    hybrid_path, popularity_path = models_dir / "hybrid_recommender.joblib", models_dir / "popularity_baseline.json"
    if not hybrid_path.is_file() or not popularity_path.is_file():
        raise FileNotFoundError("Missing hybrid or popularity model artifact required for cold-start routing")
    try:
        hybrid = joblib.load(hybrid_path)
        payload = json.loads(popularity_path.read_text(encoding="utf-8"))
        popularity = PopularityRecommender(
            tuple(str(item_id) for item_id in payload["ranked_item_ids"]),
            {str(item_id): int(value) for item_id, value in payload["unique_user_counts"].items()},
        )
    except (KeyError, TypeError, ValueError, OSError) as exc:
        raise ValueError("Cold-start input artifact is malformed or incompatible") from exc
    if not isinstance(hybrid, HybridRecommender):
        raise ValueError("Saved hybrid artifact has an unexpected type")
    return ColdStartRouter(hybrid, popularity)


def require_interactions(frame: pd.DataFrame) -> None:
    missing = REQUIRED_INTERACTION_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Interactions are missing required columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("Interactions are empty")


def evaluate_known_users(router: ColdStartRouter, history: pd.DataFrame, holdout: pd.DataFrame, k: int) -> dict[str, Any]:
    require_interactions(history)
    require_interactions(holdout)
    validate_limit(k)
    seen_by_user = history.groupby("user_id", observed=True)["item_id"].agg(lambda values: set(values.astype(str))).to_dict()
    truth_by_user = holdout.groupby("user_id", observed=True)["item_id"].agg(lambda values: set(values.astype(str))).to_dict()
    eligible = sorted(user_id for user_id in set(seen_by_user).intersection(truth_by_user) if truth_by_user[user_id].difference(seen_by_user[user_id]))
    if not eligible:
        raise ValueError("No users have both history and unseen holdout interactions")
    metrics: list[dict[str, float]] = []
    route_counts = {"personalized_cf": 0, "popularity_cold_start": 0}
    for user_id in eligible:
        result = router.recommend(int(user_id), seen_by_user[user_id], k)
        route_counts[result.source] += 1
        metrics.append(ranking_metrics(list(result.item_ids), truth_by_user[user_id].difference(seen_by_user[user_id]), k))
    return {
        "eligible_users": len(eligible),
        "route_counts": route_counts,
        "precision_at_k": sum(metric["precision_at_k"] for metric in metrics) / len(metrics),
        "recall_at_k": sum(metric["recall_at_k"] for metric in metrics) / len(metrics),
        "ndcg_at_k": sum(metric["ndcg_at_k"] for metric in metrics) / len(metrics),
    }


def run(interactions_path: Path, models_dir: Path, report_path: Path, k: int = 10) -> dict[str, Any]:
    interactions = pd.read_csv(interactions_path)
    require_interactions(interactions)
    router = load_router(models_dir)
    train, validation, test, boundaries = temporal_split(interactions)
    history = pd.concat([train, validation], ignore_index=True)
    known_result = evaluate_known_users(router, history, test, k)
    simulated_new = router.recommend(None, limit=k)
    simulated_unknown = router.recommend(max(router.known_user_ids) + 1, limit=k)
    seen_probe = set(simulated_new.item_ids[:3])
    seen_filtered = router.recommend(None, seen_probe, k)
    if simulated_new.source != "popularity_cold_start" or simulated_unknown.source != "popularity_cold_start":
        raise RuntimeError("Unknown-user routing did not select popularity fallback")
    if set(seen_filtered.item_ids).intersection(seen_probe):
        raise RuntimeError("Popularity fallback did not respect seen-item filtering")
    models_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(router, models_dir / "cold_start_router.joblib")
    report: dict[str, Any] = {
        "phase": 9,
        "policy": "Known users with personalized candidates use the selected CF-only hybrid; unknown users or empty personalized results use popularity.",
        "k": k,
        "split": {**boundaries, "history_rows": len(history), "test_rows": len(test)},
        "known_user_holdout_evaluation": known_result,
        "simulated_cold_start_checks": {
            "anonymous_user_source": simulated_new.source,
            "unknown_user_source": simulated_unknown.source,
            "anonymous_item_count": len(simulated_new.item_ids),
            "unknown_item_count": len(simulated_unknown.item_ids),
            "seen_item_filtering_respected": not bool(set(seen_filtered.item_ids).intersection(seen_probe)),
            "relevance_metric_available": False,
            "reason": "The frozen dataset has no interactions for a genuinely new user after the recommendation point, so cold-start relevance cannot be measured without fabricating a proxy target.",
        },
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and audit popularity-backed cold-start routing.")
    parser.add_argument("--interactions", type=Path, default=Path("data/processed/interactions_processed.csv"))
    parser.add_argument("--models-dir", type=Path, default=Path("models"))
    parser.add_argument("--report", type=Path, default=Path("data/processed/cold_start_evaluation.json"))
    parser.add_argument("--k", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(run(args.interactions, args.models_dir, args.report, args.k), indent=2))


if __name__ == "__main__":
    main()
