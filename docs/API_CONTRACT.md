# API contract

## Status: Phase 10 implemented

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Application health. |
| GET | `/api/users?limit=20&search=<numeric-prefix>` | Dataset-user picker; maximum 50 results. |
| GET | `/api/users/<user_id>` | One dataset user. |
| GET | `/api/users/<user_id>/activity?limit=8` | Latest real recorded product events; maximum 20. |
| POST | `/api/demo-users` | Validate a temporary demo profile; does not write to MySQL. |
| GET | `/api/recommendations?algorithm=cf|content|hybrid&user_id=<id>&limit=10` | Hydrated Top-N recommendation response. Omit `user_id` for cold start. |

`GET /api/health` reports API/model status and catalog availability.

## Recommendation response

```json
{
  "algorithm": "hybrid",
  "route": "personalized_cf",
  "personalized": true,
  "user": {"user_id": 1, "age": 31, "gender": "M"},
  "recommendations": [{"item_id": "...", "product_name": "...", "price": 99.99, "category_l1": "...", "category_l2": "..."}],
  "count": 10
}
```

`route` is `collaborative_filter`, `content_based`, `personalized_cf`, or `popularity_cold_start`. It accurately describes how the response was generated; the selected hybrid currently routes to `personalized_cf` because validation selected CF weight 1.00.

## Recent activity response

```json
{
  "user_id": 1,
  "activity": [{
    "event_type": "View",
    "event_timestamp": "2026-01-25T21:05:00Z",
    "item_id": "...",
    "product_name": "Urban Oasis Desk Setup",
    "category_l2": "chairs"
  }]
}
```

Activity is newest-first and reports the exact recorded event type. It is an explanation aid only: the current CF model treats all validated event types as binary behavioral history, rather than treating `Purchase` as the sole signal.

## Error contract

All expected client and service failures have the same safe shape:

```json
{"error": {"code": "invalid_request", "message": "limit must be between 1 and 50"}}
```

Typical status codes: 400 invalid request, 404 dataset user not found, 503 catalog/model unavailable, and 500 unexpected server error. Credentials and tracebacks are never returned. CORS accepts only the local Vite development origins `http://localhost:5173` and `http://127.0.0.1:5173` by default.

## Final live API test

`backend/tests/test_api_integration.py` is an opt-in, real integration test. It does not mock the recommendation service or catalog repository. It checks the saved artifacts and configured MySQL database for health, all three algorithms, product hydration, activity, cold start, and validation errors.

```powershell
$env:RUN_LIVE_API_TESTS = "1"
& "C:\Users\Harshith Varma\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest backend\tests\test_api_integration.py -q
```
