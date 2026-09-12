# Amazon Retail Demo Store hybrid recommender

An end-to-end, explainable product recommendation system for the NxtWise hiring assessment. The system will combine item-based collaborative filtering with TF-IDF content similarity using the frozen Amazon Retail Demo Store synthetic e-commerce dataset.

## Status

**Phase 9 complete — cold-start routing.** The system now uses personalized CF for known users with usable history and a safe popularity fallback for anonymous, unknown, or exhausted-personalization cases. Flask and React are not yet implemented.

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

The next development phase is Phase 10: implement the Flask recommendation API around the saved cold-start router and MySQL product data.

## Disclosure

This project uses the Amazon Retail Demo Store synthetic e-commerce dataset and AI coding assistance. Final documentation will disclose all libraries and external resources used.
