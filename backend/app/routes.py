"""Flask JSON routes and boundary validation."""
from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app, jsonify, request

from backend.app.db.repository import CatalogRepository, DatabaseUnavailableError
from backend.app.services.recommendations import ALGORITHMS, RecommendationService

api = Blueprint("api", __name__, url_prefix="/api")


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        self.status, self.code, self.message = status, code, message
        super().__init__(message)


def _repository() -> CatalogRepository:
    return current_app.extensions["catalog_repository"]


def _service() -> RecommendationService:
    return current_app.extensions["recommendation_service"]


def _int_argument(name: str, default: int, maximum: int) -> int:
    raw = request.args.get(name, str(default))
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ApiError(400, "invalid_request", f"{name} must be an integer") from exc
    if value < 1 or value > maximum:
        raise ApiError(400, "invalid_request", f"{name} must be between 1 and {maximum}")
    return value


def _optional_user_id() -> int | None:
    raw = request.args.get("user_id")
    if raw is None or raw == "":
        return None
    try:
        user_id = int(raw)
    except ValueError as exc:
        raise ApiError(400, "invalid_request", "user_id must be a positive integer") from exc
    if user_id < 1:
        raise ApiError(400, "invalid_request", "user_id must be a positive integer")
    return user_id


@api.get("/health")
def health():
    try:
        _repository().ping()
        return jsonify({"status": "ok", "models": "loaded", "catalog_database": "available"})
    except DatabaseUnavailableError:
        return jsonify({"status": "degraded", "models": "loaded", "catalog_database": "unavailable"}), 503


@api.get("/users")
def users():
    limit = _int_argument("limit", 20, min(50, int(current_app.config["MAX_RECOMMENDATION_LIMIT"])))
    search = request.args.get("search")
    try:
        return jsonify({"users": _repository().list_users(limit, search or None)})
    except ValueError as exc:
        raise ApiError(400, "invalid_request", str(exc)) from exc


@api.get("/users/<int:user_id>")
def user(user_id: int):
    result = _repository().get_user(user_id)
    if result is None:
        raise ApiError(404, "user_not_found", "No dataset user exists for this user_id")
    return jsonify({"user": result})


@api.get("/users/<int:user_id>/activity")
def user_activity(user_id: int):
    limit = _int_argument("limit", 8, 20)
    if _repository().get_user(user_id) is None:
        raise ApiError(404, "user_not_found", "No dataset user exists for this user_id")
    return jsonify({"user_id": user_id, "activity": _repository().recent_activity(user_id, limit)})


@api.post("/demo-users")
def demo_user():
    body: Any = request.get_json(silent=True)
    if body is None:
        body = {}
    if not isinstance(body, dict):
        raise ApiError(400, "invalid_request", "JSON body must be an object")
    age, gender = body.get("age"), body.get("gender")
    if age is not None and (isinstance(age, bool) or not isinstance(age, int) or not 18 <= age <= 120):
        raise ApiError(400, "invalid_request", "age must be an integer between 18 and 120")
    if gender is not None and gender not in {"F", "M"}:
        raise ApiError(400, "invalid_request", "gender must be F or M")
    return jsonify({"user": {"is_demo": True, "age": age, "gender": gender, "cold_start": True}, "message": "Demo profile is not stored; recommendations will use popularity fallback."}), 201


@api.get("/recommendations")
def recommendations():
    algorithm = request.args.get("algorithm", "hybrid")
    if algorithm not in ALGORITHMS:
        raise ApiError(400, "invalid_request", "algorithm must be one of: cf, content, hybrid")
    limit = _int_argument("limit", int(current_app.config["DEFAULT_RECOMMENDATION_LIMIT"]), int(current_app.config["MAX_RECOMMENDATION_LIMIT"]))
    user_id = _optional_user_id()
    user_context = None
    if user_id is not None:
        user_context = _repository().get_user(user_id)
        if user_context is None:
            raise ApiError(404, "user_not_found", "No dataset user exists for this user_id; create a demo user for cold start")
    result = _service().recommend(algorithm, user_id, limit)
    products = _repository().get_products_by_ids(result.item_ids)
    return jsonify({"algorithm": algorithm, "route": result.source, "personalized": result.personalized, "user": user_context if user_context is not None else {"is_demo": True, "cold_start": True}, "recommendations": products, "count": len(products)})
