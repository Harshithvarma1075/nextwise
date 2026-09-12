# Handoff

## Current phase

Phase 2 — preprocessing complete.

## Completed

- Added `src/preprocessing.py`, a saved raw-to-processed pipeline.
- Generated Git-ignored processed users, items, event-level interactions, user-item aggregates, and `preprocessing_report.json`.
- Added `backend/tests/test_preprocessing.py` with seven behavior-oriented tests.
- Installed Pytest 8.4.2 in the local Python 3.14 environment and ran the suite successfully.
- Updated documentation with the final Phase 2 data contract and decisions.

## Files changed

`src/preprocessing.py`, `backend/tests/test_preprocessing.py`, `README.md`, `docs/DATA_CONTRACT.md`, `docs/TECH_DECISIONS.md`, `docs/TODO.md`, and `docs/HANDOFF.md`. Generated processed data is Git-ignored.

## Dataset facts and outputs

- All 6,000 raw users, 2,465 catalog items, and 675,004 raw events passed executed validation; no raw rows were dropped.
- Aggregation creates 66,262 unique user-item pairs, keeping per-event counts, first/last timestamps, and discounted-event count.
- `DISCOUNT` is now `discount_applied` boolean; missing `PROMOTED` remains `unknown` rather than false.

## Important decisions

- Preprocessing is model-neutral: it does not assign event weights.
- Cross-file orphans cause a safe failure rather than silent removal.
- Atomic writes prevent partially published output artifacts.

## Tests and checks

- `python -m pytest backend/tests/test_preprocessing.py -q`: **7 passed**.
- Pipeline run completed with output counts: 6,000 users, 2,465 items, 675,004 events, 66,262 user-item pairs.
- `git diff --check` is run before phase completion.

## Resolved issues

1. Gender normalization initially uppercased `Any` to `ANY` but validation expected mixed-case, dropping 1,716 valid items. The validator now uses normalized `ANY`; rerun retained all items.
2. Windows temporarily locked an existing processed CSV during a rerun. The pipeline now writes temporary files and atomically publishes outputs, avoiding partial artifacts.
3. Two initial tests were overly brittle (Pandas datetime unit and accidental duplicate removal). They were corrected to test behavior, not implementation incidental details.
4. The shell stopped resolving `python`; commands now use the verified Python 3.14 executable path. This is environment-specific, not a project runtime requirement.

## Known issues

- Processed CSVs are Git-ignored by design; rerun preprocessing after cloning.
- MySQL has not yet been configured or loaded.

## Next phase

Phase 3: design and implement MySQL schema and a loader for processed application data only.

## Do not change

- Do not alter raw data or use another dataset.
- Do not infer `PROMOTED=false` from missing source values.
- Do not add event weights until the popularity/model phase documents and evaluates them.
- Do not store ML matrices or similarities in MySQL.
