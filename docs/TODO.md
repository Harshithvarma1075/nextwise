# TODO

## Phase 0 — complete

- [x] Establish Amazon Retail Demo Store as the final frozen dataset.
- [x] Keep raw CSVs in Git-ignored local storage.
- [x] Create source-of-truth documentation, project layout, `.env.example`, and `requirements.txt` skeleton.
- [x] Define initial architecture and non-data-dependent technical decisions.

## Phase 1 — next: dataset inspection and EDA

- [ ] Inspect actual interaction events, quality, timestamp range, and discount distribution.
- [ ] Inspect catalog metadata completeness and distributions.
- [ ] Inspect user data quality and distributions.
- [ ] Check item/user referential consistency across files.
- [ ] Decide from evidence whether all interactions can be used or a reproducible subset is needed.

## Later phases — not started

- [ ] Phase 2: preprocessing and final data contract.
- [ ] Phase 3: MySQL schema and load.
- [ ] Phase 4–9: baselines, models, evaluation, cold start.
- [ ] Phase 10–12: Flask, React, testing/robustness.
- [ ] Phase 13–14: final documentation and QA.
