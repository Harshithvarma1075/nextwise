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

## Data and model boundary

The architecture deliberately separates **offline data science work** from **online application work**. Offline scripts are the only code permitted to read raw CSV files, validate schemas, produce processed datasets, create sparse representations, train recommendation artifacts, and calculate metrics. This makes every reported number traceable to a repeatable command.

The online Flask application does not retrain a model, alter interaction data, or calculate evaluation metrics. At startup it loads the already-selected artifacts. For each valid request it validates query parameters, asks the appropriate artifact for ranked item IDs, excludes previously seen items as implemented by the model/router, reads only the required catalog records through parameterized MySQL queries, and returns a stable JSON contract.

MySQL contains relational application entities—users, products, and recorded interactions—not ML internals. Sparse user-item matrices, nearest-neighbor structures, TF-IDF vectors, and Joblib artifacts remain local files because they are training/serving assets rather than transactional data.

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

## Request lifecycle and failure boundaries

1. The React client requests a dataset user, recent activity, or recommendations from the local Flask API.
2. Flask validates the algorithm, user ID, and result limit before any model/database operation.
3. The recommendation service returns a ranked result and provenance route: CF, content, validation-selected hybrid/CF, or popularity cold start.
4. The catalog repository hydrates returned item IDs from MySQL using parameterized read-only queries.
5. Flask returns the documented JSON response. Expected request failures use safe 400/404/503 shapes; unexpected errors are logged server-side without exposing credentials or tracebacks.

The activity endpoint is deliberately separate from ranking. It returns recent recorded source events newest first so a reviewer can see the behavioral context. It is not a claim that a particular event directly caused a particular recommended item.

Product images are not part of the design because the frozen catalog does not establish a reliable local image mapping.
