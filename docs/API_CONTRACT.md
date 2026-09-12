# API contract

## Status: planned, not implemented

The intended minimal API is:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Health status. |
| GET | `/api/products` | Paginated/listed verified product records. |
| GET | `/api/products/<article_id>` | One verified product record. |
| GET | `/api/recommendations/<customer_id>?limit=10` | Validated personalized Top-N results. |
| POST | `/api/recommendations/cold-start` | Optional cold-start preferences when mapped to verified metadata. |

Response fields remain undecided until Phase 1 verifies the H&M metadata schema. Errors will use safe, consistent JSON without internal exceptions or secrets.
