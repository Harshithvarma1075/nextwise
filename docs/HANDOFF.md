# Handoff

## Current phase

Phase 1 — Amazon Retail Demo Store dataset inspection and EDA complete.

## Completed

- Added `src/inspect_dataset.py`, a saved read-only EDA script.
- Ran it against the frozen raw CSVs and wrote `data/processed/phase1_inspection_report.json` (Git-ignored).
- Verified schemas, missingness, duplicates, event/discount distributions, catalog/user quality, timestamp range, and cross-file consistency.
- Updated README, data contract, technical decisions, and TODO with only executed findings.

## Files changed

`src/inspect_dataset.py`, `README.md`, `docs/DATA_CONTRACT.md`, `docs/TECH_DECISIONS.md`, `docs/TODO.md`, and `docs/HANDOFF.md`. The generated JSON report is intentionally Git-ignored.

## Important decisions

- Use all 675,004 interactions; no subset is justified.
- Retain all verified event types for Phase 2; interaction weights require a documented policy and are not assumed.
- Use item names/descriptions and complete category/gender metadata as later TF-IDF candidates.
- Treat discount as categorical `Yes`/`No`.
- Treat missing `PROMOTED` as unknown until Phase 2 specifies a defensible normalization rule.

## Dataset facts discovered

- 6,000 users, 2,465 items, and complete referential consistency.
- Events: View 581,900; AddToCart 46,552; ViewCart 29,095; StartCheckout 11,638; Purchase 5,819.
- Interaction data has no missing values or duplicate event rows; catalog and user files have no duplicate IDs.
- Product descriptions are complete, but promotion has 1,856 missing values.

## Tests and checks

- `python src/inspect_dataset.py --raw-dir data/raw/amazon_retail_demo --report data/processed/phase1_inspection_report.json` completed successfully.
- `python -m py_compile src/inspect_dataset.py` completed successfully.
- No Pytest tests exist yet; Phase 2 must add them.

## Known issues

- `DISCOUNT` was described earlier as numeric but is actually categorical text; docs corrected.
- `PROMOTED` has a high missing rate; do not infer a business meaning without a documented rule.
- Pytest is declared in requirements but not installed in the current environment.

## Next phase

Phase 2: saved preprocessing pipeline, transformed data contract, and Pytest tests.

## Do not change

- Do not change or edit raw CSVs, replace the dataset, or introduce other data sources.
- Do not invent event weights or interpret missing `PROMOTED` as false without documenting the rule.
- Do not train models, create MySQL tables, API routes, or frontend features until each corresponding phase is explicitly approved.
