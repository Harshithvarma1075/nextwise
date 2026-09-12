# TODO

## Phase 0 — complete

- [x] Establish Amazon Retail Demo Store as the final frozen dataset.
- [x] Create source-of-truth documentation, project layout, `.env.example`, and `requirements.txt` skeleton.

## Phase 1 — complete: dataset inspection and EDA

- [x] Create and run saved read-only inspection script, `src/inspect_dataset.py`.
- [x] Inspect interaction events, timestamps, discount distribution, data quality, and user activity.
- [x] Inspect catalog metadata completeness, categories, prices, promotion field, and description quality.
- [x] Inspect user data completeness, ages, and gender values.
- [x] Verify zero item/user orphan records across the three CSVs.
- [x] Decide that full data is feasible and no subset is needed.

## Phase 2 — next: preprocessing

- [ ] Implement reproducible raw-to-processed validation and transformations.
- [ ] Define timestamp, `DISCOUNT`, and missing `PROMOTED` normalization rules.
- [ ] Investigate repeated user-item event behavior and document interaction aggregation/strength policy.
- [ ] Create processed users, products, and interactions datasets.
- [ ] Add and run preprocessing tests with Pytest.

## Later phases — not started

- [ ] Phase 3: MySQL schema and load.
- [ ] Phase 4–9: baselines, models, evaluation, cold start.
- [ ] Phase 10–12: Flask, React, testing/robustness.
- [ ] Phase 13–14: final documentation and QA.
