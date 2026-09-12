# TODO

## Phase 0 — complete

- [x] Establish Amazon Retail Demo Store as the final frozen dataset.
- [x] Create project foundation, source-of-truth docs, configuration example, and dependency skeleton.

## Phase 1 — complete

- [x] Inspect all raw files, distributions, quality, and referential integrity.
- [x] Decide that the full 675,004-event dataset requires no subset.

## Phase 2 — complete: preprocessing

- [x] Add `src/preprocessing.py` for reproducible raw-to-processed validation and transformation.
- [x] Produce validated users, items, cleaned events, user-item aggregates, and a report.
- [x] Normalize timestamps, discount, gender, and promotion state without inventing source values.
- [x] Preserve repeated interactions as count features; do not assign model weights yet.
- [x] Add Pytest preprocessing coverage and run all tests successfully.

## Phase 3 — next: MySQL

- [ ] Design MySQL schema for processed users, products, and interactions.
- [ ] Add indexes, foreign keys, parameterized loader, and representative query checks.
- [ ] Load only the processed data required by the future application.

## Later phases — not started

- [ ] Phase 4–9: baselines, models, evaluation, and cold start.
- [ ] Phase 10–12: Flask, React, testing/robustness.
- [ ] Phase 13–14: final documentation and QA.
