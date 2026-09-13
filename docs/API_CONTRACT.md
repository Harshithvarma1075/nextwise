# API contract

## Status: Phase 10 implemented

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Application health. |
| GET | `/api/users?limit=20&search=<numeric-prefix>` | Dataset-user picker; maximum 50 results. |
| GET | `/api/users/<user_id>` | One dataset user. |
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

## Error contract

All expected client and service failures have the same safe shape:

```json
{"error": {"code": "invalid_request", "message": "limit must be between 1 and 50"}}
```

Typical status codes: 400 invalid request, 404 dataset user not found, 503 catalog/model unavailable, and 500 unexpected server error. Credentials and tracebacks are never returned. CORS accepts only the local Vite development origins `http://localhost:5173` and `http://127.0.0.1:5173` by default.
