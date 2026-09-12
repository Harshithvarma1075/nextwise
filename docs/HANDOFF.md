# Handoff

## Current phase

Phase 0 — Amazon Retail Demo Store project foundation complete.

## Completed

- The project owner froze the dataset as Amazon Retail Demo Store synthetic e-commerce data in `data/raw/amazon_retail_demo/`.
- Downloaded the exact three user-specified raw files; the initial shape/header inspection is recorded in `DATA_CONTRACT.md`.
- Replaced abandoned H&M-oriented project documentation with Amazon-specific Phase 0 source-of-truth documents.
- Added `requirements.txt`; reshaped empty source folders to `backend/`, `src/`, and `frontend/` for the intended architecture.
- No EDA beyond initial shape/header reading, preprocessing, model, database, API, or UI has been implemented.

## Files changed

`README.md`, `.env.example`, `requirements.txt`, all required documents under `docs/`, plus empty source directories.

## Important decisions

- Dataset cannot be replaced or supplemented.
- Catalog metadata is authoritative; frontend must use actual catalog values.
- Event types, discount semantics, interaction aggregation, subset need, content fields, and all model parameters remain unselected pending Phase 1.
- Product cards are image-free unless a later phase verifies a local authoritative mapping.

## Dataset facts discovered

The raw directory has `interactions.csv` (675,004 × 5), `items.csv` (2,465 × 8), and `users.csv` (6,000 × 3). These are preliminary shape/header facts only, not full EDA conclusions.

## Tests and checks

- Verified required Phase 0 docs and raw directory exist.
- No executable application code exists, so no software tests apply.

## Known issues

- None blocking Phase 1. Pytest is declared but not yet installed in the current Python environment.

## Next phase

Phase 1: inspect the frozen CSVs read-only and document evidence-based EDA and feasibility.

## Do not change

- Do not use H&M, Retailrocket, MovieLens, or any other dataset.
- Do not edit raw CSVs or invent product/user metadata, images, metrics, or event semantics.
- Do not implement preprocessing, models, MySQL, Flask, or React before explicit Phase 1 approval.
