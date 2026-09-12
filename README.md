# H&M hybrid product recommender

A practical, explainable recommendation-system project for the NxtWise hiring assessment. It will combine item-based collaborative filtering and metadata-based content recommendations, then evaluate a normalized hybrid ranker.

## Status

**Phase 0 complete — H&M project foundation.** The earlier Retailrocket work was retired. No H&M dataset has been downloaded or inspected, and no preprocessing, database schema, ML model, API, or React feature has been implemented.

## Fixed stack

- Python, Flask, and a REST API
- MySQL for application data
- Pandas, NumPy, SciPy, scikit-learn, Joblib
- Pytest
- React + Vite, preferably TypeScript when practical

## Target architecture

```text
H&M dataset → inspection → preprocessing → processed users/products/transactions
                                      ├→ item-based CF
                                      └→ TF-IDF content model
                                            ↓
                              normalized hybrid ranking → artifacts

React → Flask → recommendation service → MySQL + saved artifacts
```

## Repository layout

```text
app/          Future Flask layers
config/       Future application configuration
data/raw/     Local H&M source data (Git-ignored)
data/processed/ Generated datasets (Git-ignored)
docs/         Source-of-truth documentation
frontend/     Future React/Vite application
ml/           Future offline pipeline and models
models/       Generated model artifacts (Git-ignored)
scripts/      Operational scripts
tests/        Automated tests
```

## Next step

Phase 1 will acquire and inspect the actual H&M files before selecting a reproducible working subset or making data-dependent decisions.

## Disclosure

The project is developed with AI coding assistance. The final README will disclose the dataset, libraries, external resources, and AI assistance used.
