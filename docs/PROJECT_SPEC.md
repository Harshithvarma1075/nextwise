# Project specification

## Objective

Build a practical, explainable, reproducible hybrid product recommender for the NxtWise hiring assessment. It must include preprocessing, user/product profiles, popularity baseline, item-based collaborative filtering, content-based filtering, hybrid Top-N ranking, seen-item filtering, cold start, REST API, React UI, evaluation, testing, and documentation.

## Frozen dataset

Use only **Amazon Retail Demo Store synthetic e-commerce dataset** in `data/raw/amazon_retail_demo/`: `interactions.csv`, `items.csv`, and `users.csv`. Do not use Retailrocket, H&M, MovieLens, or any substitute dataset. Do not invent product, user, image, or interaction fields.

## Technology constraints

Python + Flask, MySQL, Pandas, NumPy, SciPy, scikit-learn, Joblib, Pytest, React, and Vite. Keep architecture monolithic and simple; do not introduce deep learning, vector databases, queues, microservices, or other unnecessary infrastructure.

## Non-negotiable rules

- Source data remains untouched; all transformations must be scripted and reproducible.
- Validate actual file content before making data-dependent decisions.
- Keep offline preparation/training separate from online API serving.
- MySQL stores application data, never large sparse matrices or similarity matrices.
- Every metric, count, and performance claim must be produced by executed code.
- Explain recommendations only with signals the implemented model actually uses.

## Current boundary

Phase 10 is complete. The frozen dataset has reproducible preprocessing, MySQL loading, popularity/CF/content/hybrid artifacts, a validation-selected CF-only hybrid, cold-start routing, evaluation/robustness evidence, a Flask API, and a React/Vite demonstration UI. The next work is integration hardening and final review preparation; do not reopen model selection using the held-out test data.
