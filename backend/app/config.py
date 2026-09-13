"""Runtime configuration with explicit, validated defaults."""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _positive_int(value: object, name: str, maximum: int | None = None) -> int:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if parsed < 1 or (maximum is not None and parsed > maximum):
        suffix = f" no greater than {maximum}" if maximum is not None else ""
        raise ValueError(f"{name} must be positive{suffix}")
    return parsed


def load_config() -> dict[str, object]:
    default_limit = _positive_int(os.getenv("DEFAULT_RECOMMENDATION_LIMIT", "10"), "DEFAULT_RECOMMENDATION_LIMIT", 50)
    max_limit = _positive_int(os.getenv("MAX_RECOMMENDATION_LIMIT", "50"), "MAX_RECOMMENDATION_LIMIT", 100)
    if default_limit > max_limit:
        raise ValueError("DEFAULT_RECOMMENDATION_LIMIT must not exceed MAX_RECOMMENDATION_LIMIT")
    return {
        "MODEL_DIR": Path(os.getenv("MODEL_DIR", str(PROJECT_ROOT / "models"))),
        "DEFAULT_RECOMMENDATION_LIMIT": default_limit,
        "MAX_RECOMMENDATION_LIMIT": max_limit,
        "CORS_ORIGINS": frozenset(origin.strip().rstrip("/") for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()),
        "JSON_SORT_KEYS": False,
    }
