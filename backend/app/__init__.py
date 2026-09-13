"""Flask application factory for the recommendation API."""
from __future__ import annotations

from typing import Any

from flask import Flask, jsonify, request

from backend.app.config import load_config
from backend.app.db.repository import CatalogRepository, DatabaseUnavailableError
from backend.app.routes import ApiError, api
from backend.app.services.recommendations import ModelUnavailableError, RecommendationService


def create_app(test_config: dict[str, Any] | None = None, *, repository: CatalogRepository | None = None, recommendation_service: RecommendationService | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(load_config())
    if test_config:
        app.config.update(test_config)
    try:
        app.extensions["recommendation_service"] = recommendation_service or RecommendationService.from_model_dir(app.config["MODEL_DIR"])
    except ModelUnavailableError:
        if not app.config.get("TESTING"):
            raise
        app.extensions["recommendation_service"] = recommendation_service
    app.extensions["catalog_repository"] = repository or CatalogRepository()
    app.register_blueprint(api)

    @app.after_request
    def cors(response):
        origin = request.headers.get("Origin")
        if origin in app.config["CORS_ORIGINS"]:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    @app.errorhandler(ApiError)
    def api_error(error: ApiError):
        return jsonify({"error": {"code": error.code, "message": error.message}}), error.status

    @app.errorhandler(DatabaseUnavailableError)
    def database_error(_: DatabaseUnavailableError):
        return jsonify({"error": {"code": "catalog_unavailable", "message": "Catalog data is temporarily unavailable"}}), 503

    @app.errorhandler(ModelUnavailableError)
    def model_error(_: ModelUnavailableError):
        return jsonify({"error": {"code": "model_unavailable", "message": "Recommendation model is temporarily unavailable"}}), 503

    @app.errorhandler(Exception)
    def unexpected_error(error: Exception):
        app.logger.exception("Unhandled API error")
        return jsonify({"error": {"code": "internal_error", "message": "Unexpected server error"}}), 500

    return app
