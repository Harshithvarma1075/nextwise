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

## Phase 3 — complete: MySQL

- [x] Design schema for validated users, products, and interactions.
- [x] Add foreign keys, check constraints, natural event uniqueness, query indexes, and parameterized transactional loader.
- [x] Add database-independent loader tests and `.env` handling.
- [x] Create schema, load processed data, and verify actual database counts and foreign-key integrity.

## Phase 4 — next: popularity baseline

- [ ] Define a simple, defensible interaction-based popularity signal from the processed data.
- [ ] Implement saved popularity artifacts and Top-N retrieval.
- [ ] Establish temporal evaluation eligibility/split required for baseline measurement.
- [ ] Test ranking, limit handling, and cold-start fallback behavior.

## Later phases — not started

- [ ] Phase 5–9: collaborative/content/hybrid models, evaluation, and cold start.
- [ ] Phase 10–12: Flask, React, testing/robustness.
- [ ] Phase 13–14: final documentation and QA.
