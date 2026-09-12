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

## Phase 4 — complete: popularity baseline

- [x] Define unique-user interaction count as the global popularity signal.
- [x] Implement saved popularity artifact and Top-N retrieval with seen-item filtering.
- [x] Establish and execute global temporal train/validation/test evaluation.
- [x] Test ranking, limit handling, seen-item filtering, metrics, and split behavior.

## Phase 5 — complete: collaborative filtering

- [x] Build a sparse binary user-item representation using the established temporal protocol.
- [x] Implement item-based cosine similarity and personalized unseen-item candidate generation.
- [x] Handle unknown users, empty candidates, seen filtering, and Top-N limits.
- [x] Test and evaluate CF against the recorded popularity baseline.

## Phase 6 — complete: content-based filtering

- [x] Build a TF-IDF product representation from verified catalog metadata.
- [x] Implement content-based candidate generation from a user's history.
- [x] Handle empty metadata, unknown items/users, zero vectors, and seen filtering.
- [x] Evaluate content filtering under the same temporal protocol.

## Later phases — not started

- [ ] Phase 7–9: hybrid model, full evaluation, and cold start.
- [ ] Phase 10–12: Flask, React, testing/robustness.
- [ ] Phase 13–14: final documentation and QA.
