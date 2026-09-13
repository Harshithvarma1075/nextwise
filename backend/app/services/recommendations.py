"""Model selection and recommendation orchestration for Flask routes."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib

from src.cold_start import ColdStartRouter, RoutedRecommendations, load_router
from src.collaborative import ItemCollaborativeFilter
from src.content_based import ContentBasedRecommender
from src.hybrid import HybridRecommender
from src.popularity import PopularityRecommender


ALGORITHMS = {"cf", "content", "hybrid"}


class ModelUnavailableError(RuntimeError):
    """Raised when model artifacts are missing, malformed, or incompatible."""


@dataclass
class RecommendationService:
    router: ColdStartRouter
    collaborative: ItemCollaborativeFilter
    content: ContentBasedRecommender
    hybrid: HybridRecommender
    popularity: PopularityRecommender

    @classmethod
    def from_model_dir(cls, models_dir: Path) -> "RecommendationService":
        try:
            router = load_router(models_dir)
            collaborative = joblib.load(models_dir / "collaborative_filter.joblib")
            content = joblib.load(models_dir / "content_based_filter.joblib")
            hybrid = joblib.load(models_dir / "hybrid_recommender.joblib")
            payload = json.loads((models_dir / "popularity_baseline.json").read_text(encoding="utf-8"))
            popularity = PopularityRecommender(tuple(str(item_id) for item_id in payload["ranked_item_ids"]), {str(item_id): int(value) for item_id, value in payload["unique_user_counts"].items()})
        except Exception as exc:
            raise ModelUnavailableError("Recommendation model artifacts are unavailable or incompatible") from exc
        if not isinstance(collaborative, ItemCollaborativeFilter) or not isinstance(content, ContentBasedRecommender) or not isinstance(hybrid, HybridRecommender):
            raise ModelUnavailableError("Recommendation model artifacts have unexpected types")
        return cls(router, collaborative, content, hybrid, popularity)

    @staticmethod
    def _route(model: Any, user_id: int | None, limit: int, label: str, fallback: PopularityRecommender) -> RoutedRecommendations:
        if user_id is not None:
            rows = model.recommend(user_id, limit=limit)
            item_ids = tuple(str(row[0]) for row in rows)
            if item_ids:
                return RoutedRecommendations(item_ids, label, True)
        return RoutedRecommendations(tuple(fallback.recommend(limit=limit)), "popularity_cold_start", False)

    def recommend(self, algorithm: str, user_id: int | None, limit: int) -> RoutedRecommendations:
        if algorithm not in ALGORITHMS:
            raise ValueError("algorithm must be one of: cf, content, hybrid")
        if algorithm == "hybrid":
            return self.router.recommend(user_id, limit=limit)
        if algorithm == "cf":
            return self._route(self.collaborative, user_id, limit, "collaborative_filter", self.popularity)
        return self._route(self.content, user_id, limit, "content_based", self.popularity)
