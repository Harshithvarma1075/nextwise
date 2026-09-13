from backend.app import create_app
from src.cold_start import RoutedRecommendations


class FakeRepository:
    def ping(self):
        return None

    def list_users(self, limit, search=None):
        return [{"user_id": 7, "age": 25, "gender": "F"}][:limit]

    def get_user(self, user_id):
        return {"user_id": user_id, "age": 25, "gender": "F"} if user_id == 7 else None

    def recent_activity(self, user_id, limit):
        return [{"event_type": "Purchase", "event_timestamp": "2026-01-01T12:00:00Z", "item_id": "recent-1", "product_name": "Recent product", "category_l2": "Shoes"}][:limit]

    def get_products_by_ids(self, item_ids):
        return [{"item_id": item_id, "price": 9.99, "category_l1": "Fashion", "category_l2": "Shoes", "product_name": f"Product {item_id}", "product_description": "Verified catalog product", "gender": "ANY", "promoted_status": "unknown"} for item_id in item_ids]


class FakeService:
    def recommend(self, algorithm, user_id, limit):
        if user_id is None:
            return RoutedRecommendations(tuple(f"cold-{index}" for index in range(limit)), "popularity_cold_start", False)
        return RoutedRecommendations(tuple(f"{algorithm}-{index}" for index in range(limit)), f"{algorithm}_route", True)


def client():
    app = create_app({"TESTING": True, "CORS_ORIGINS": frozenset({"http://localhost:5173", "http://127.0.0.1:5173"}), "DEFAULT_RECOMMENDATION_LIMIT": 3, "MAX_RECOMMENDATION_LIMIT": 10}, repository=FakeRepository(), recommendation_service=FakeService())
    return app.test_client()


def test_health_users_and_cors_contract():
    response = client().get("/api/users?limit=1", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200
    assert response.get_json() == {"users": [{"user_id": 7, "age": 25, "gender": "F"}]}
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    loopback_response = client().get("/api/users?limit=1", headers={"Origin": "http://127.0.0.1:5173"})
    assert loopback_response.headers["Access-Control-Allow-Origin"] == "http://127.0.0.1:5173"
    assert client().get("/api/health").get_json()["status"] == "ok"


def test_recommendation_response_supports_all_algorithms_and_cold_start():
    for algorithm in ("cf", "content", "hybrid"):
        response = client().get(f"/api/recommendations?user_id=7&algorithm={algorithm}&limit=2")
        body = response.get_json()
        assert response.status_code == 200
        assert body["algorithm"] == algorithm
        assert body["personalized"] is True
        assert body["count"] == 2
        assert len(body["recommendations"]) == 2
    cold = client().get("/api/recommendations?algorithm=hybrid&limit=2").get_json()
    assert cold["route"] == "popularity_cold_start"
    assert cold["user"]["is_demo"] is True


def test_recent_activity_contract_and_missing_user():
    activity = client().get("/api/users/7/activity?limit=1")
    assert activity.status_code == 200
    assert activity.get_json()["activity"][0]["event_type"] == "Purchase"
    assert client().get("/api/users/7/activity?limit=21").status_code == 400
    assert client().get("/api/users/999/activity").status_code == 404


def test_api_rejects_bad_requests_and_does_not_create_persistent_demo_user():
    api_client = client()
    assert api_client.get("/api/recommendations?algorithm=bad").status_code == 400
    assert api_client.get("/api/recommendations?user_id=999").status_code == 404
    assert api_client.get("/api/recommendations?limit=99").status_code == 400
    bad_demo = api_client.post("/api/demo-users", json={"age": 4}).get_json()
    assert bad_demo["error"]["code"] == "invalid_request"
    demo = api_client.post("/api/demo-users", json={"age": 30, "gender": "M"})
    assert demo.status_code == 201
    assert demo.get_json()["user"]["cold_start"] is True
