# API contract

## Status: planned, not implemented

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Application health. |
| GET | `/api/products` | Catalog products from verified fields. |
| GET | `/api/products/<item_id>` | One catalog product. |
| GET | `/api/recommendations/<user_id>?limit=10` | Validated personalized Top-N recommendations. |
| POST | `/api/recommendations/cold-start` | Optional popularity-based cold-start response. |

Final JSON fields, pagination, errors, and cold-start body are pending data and implementation phases. The API will use structured safe errors and never expose credentials or tracebacks.
