# Architecture

## Target design

```text
H&M source files
  → inspection and subset decision
  → validated preprocessing
  ├→ processed customers
  ├→ processed articles and metadata features
  └→ processed purchase interactions
       ├→ sparse user-item matrix → item-based collaborative candidates
       └→ TF-IDF product vectors → content candidates
             → normalized hybrid scorer → seen-item filtering → Top-N
             → persisted model artifacts and evaluation reports

React/Vite → Flask REST API → recommendation service → MySQL + model artifacts
```

## Responsibilities

| Layer | Responsibility |
| --- | --- |
| `ml/` | Reproducible offline inspection, preprocessing, features, models, evaluation, artifact creation. |
| `app/` | Flask routes, input validation, safe REST responses, online recommendation orchestration. |
| MySQL | Processed users, products, interactions, optional recommendation logs. |
| `frontend/` | Product browsing, customer selection, recommendations, explanations, and error/loading/empty states. |

No H&M-specific schema decision has been made yet.
