# Amazon Retail Demo Store hybrid recommender

An end-to-end, explainable product recommendation system for the NxtWise hiring assessment. The system will combine item-based collaborative filtering with TF-IDF content similarity using the frozen Amazon Retail Demo Store synthetic e-commerce dataset.

## Status

**Phase 4 complete — popularity baseline.** A saved global-popularity artifact, Top-N retrieval with seen-item filtering, and real temporal evaluation are in place. Collaborative/content/hybrid models, Flask, and React are not yet implemented.

## Frozen dataset

`data/raw/amazon_retail_demo/` contains:

- `interactions.csv`
- `items.csv`
- `users.csv`

This is the only permitted dataset. Raw files are Git-ignored and must never be edited.

## Planned stack

Python, Flask, MySQL, Pandas, NumPy, SciPy, scikit-learn, Joblib, Pytest, React, and Vite.

## Target architecture

```text
Raw CSVs → validation/preprocessing → processed users, items, interactions
                                   ├→ sparse item-based CF
                                   └→ TF-IDF content model
                                         ↓
                            normalized hybrid ranker → Top-N

React → Flask REST API → recommendation service → MySQL + model artifacts
```

## Layout

```text
backend/    Future Flask application and backend tests
src/        Future offline preprocessing, models, training, evaluation
data/       Git-ignored raw and generated data
docs/       Project source of truth
frontend/   Future React/Vite interface
models/     Git-ignored generated model artifacts
```

## Next phase

The next development phase is Phase 5: item-based collaborative filtering.

## Disclosure

This project uses the Amazon Retail Demo Store synthetic e-commerce dataset and AI coding assistance. Final documentation will disclose all libraries and external resources used.
