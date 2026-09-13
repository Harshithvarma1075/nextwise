# Architecture

## Target flow

```text
Raw Amazon Retail Demo Store CSVs
  → inspection → reproducible preprocessing
  ├→ processed users
  ├→ processed catalog / TF-IDF product features
  └→ processed event interactions / sparse user-item matrix
       ├→ popularity baseline
       ├→ item-based collaborative candidates
       └→ content candidates
             → normalized hybrid ranking → seen-item filter → Top-N
             → persisted artifacts + evaluation reports

React/Vite → Flask REST API → recommendation service → MySQL + local artifacts
```

## Layer responsibilities

| Layer | Responsibility |
| --- | --- |
| `src/` | Offline validation, preprocessing, feature construction, models, evaluation, artifact creation. |
| `backend/app/` | Flask routes, safe input validation, recommendation orchestration, MySQL access. |
| MySQL | Processed users, catalog products, interactions, and optional logs. |
| `frontend/` | Customer selection, product browsing, recommendation display, explanations, and safe UI states. |

## Implemented serving path

```text
React UI (algorithm selection + dataset/demo user)
  → Flask boundary validation and safe JSON errors
  → RecommendationService
      ├─ CF artifact
      ├─ content artifact
      └─ selected hybrid/cold-start router
  → parameterized MySQL catalog hydration
  → response with route provenance + verified product fields
```

The UI supports CF, content, and hybrid for transparent model comparison. New demo profiles are session-only UI/API objects; they never write synthetic users into MySQL and therefore correctly receive the popularity cold-start route.

Product images are not part of the design unless Phase 1 discovers a reliable local mapping.
