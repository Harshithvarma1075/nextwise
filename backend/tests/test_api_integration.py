"""Opt-in final API test against real saved artifacts and the configured MySQL catalog.

Run explicitly with:
    $env:RUN_LIVE_API_TESTS = "1"
    python -m pytest backend/tests/test_api_integration.py -q
"""
from __future__ import annotations

import os

import pytest

from backend.app import create_app


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def api_client():
    if os.getenv("RUN_LIVE_API_TESTS") != "1":
        pytest.skip("Set RUN_LIVE_API_TESTS=1 to run tests against local MySQL and saved artifacts")
    original_environment = os.environ.copy()
    try:
        app = create_app({"TESTING": True})
        yield app.test_client()
    finally:
        # Repository setup loads .env with setdefault. Restore process state so
        # this opt-in test cannot influence independent dotenv unit tests.
        os.environ.clear()
        os.environ.update(original_environment)


def _assert_error_shape(response, status_code: int, code: str) -> None:
    assert response.status_code == status_code
    body = response.get_json()
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str)


def _assert_products(body: dict, expected_count: int) -> None:
    assert body["count"] == expected_count
    assert len(body["recommendations"]) == expected_count
    assert len({product["item_id"] for product in body["recommendations"]}) == expected_count
    for product in body["recommendations"]:
        assert set(product) == {"item_id", "price", "category_l1", "category_l2", "product_name", "product_description", "gender", "promoted_status"}
        assert product["product_name"]
        assert product["price"] > 0


def test_final_live_api_contract(api_client):
    health = api_client.get("/api/health")
    assert health.status_code == 200
    assert health.get_json() == {"status": "ok", "models": "loaded", "catalog_database": "available"}

    users = api_client.get("/api/users?limit=1")
    assert users.status_code == 200
    user = users.get_json()["users"][0]
    user_id = user["user_id"]
    assert user_id > 0 and user["gender"] in {"F", "M"}

    for algorithm, expected_route in (("cf", "collaborative_filter"), ("content", "content_based"), ("hybrid", "personalized_cf")):
        response = api_client.get(f"/api/recommendations?algorithm={algorithm}&user_id={user_id}&limit=3")
        assert response.status_code == 200
        body = response.get_json()
        assert body["algorithm"] == algorithm
        assert body["route"] == expected_route
        assert body["personalized"] is True
        assert body["user"]["user_id"] == user_id
        _assert_products(body, 3)

    activity = api_client.get(f"/api/users/{user_id}/activity?limit=8")
    assert activity.status_code == 200
    events = activity.get_json()["activity"]
    assert 1 <= len(events) <= 8
    for event in events:
        assert set(event) == {"event_type", "event_timestamp", "item_id", "product_name", "category_l2"}
        assert event["event_type"] in {"View", "AddToCart", "ViewCart", "StartCheckout", "Purchase"}
        assert event["event_timestamp"].endswith("Z")
        assert event["product_name"]

    cold_start = api_client.get("/api/recommendations?algorithm=hybrid&limit=3")
    assert cold_start.status_code == 200
    cold_body = cold_start.get_json()
    assert cold_body["route"] == "popularity_cold_start"
    assert cold_body["personalized"] is False
    assert cold_body["user"] == {"is_demo": True, "cold_start": True}
    _assert_products(cold_body, 3)

    _assert_error_shape(api_client.get("/api/recommendations?algorithm=unsupported"), 400, "invalid_request")
    _assert_error_shape(api_client.get("/api/recommendations?limit=0"), 400, "invalid_request")
    _assert_error_shape(api_client.get("/api/users/999999999/activity"), 404, "user_not_found")
