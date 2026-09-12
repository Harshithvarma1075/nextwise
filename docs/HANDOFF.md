# Handoff

## Current phase

Phase 4 — popularity baseline complete.

## Completed

- Added `backend/app/db/schema.sql` for `users`, `products`, and `interactions`.
- Added `backend/app/db/loader.py`, which reads `.env`, creates tables, performs parameterized batched upserts in one transaction, and verifies loaded counts/referential integrity.
- Added `backend/tests/test_database_loader.py` and `docs/MYSQL_SETUP.md`.
- Retained all completed Phase 2 pipeline/data artifacts and tests.
- Connected to the configured local MySQL database, created the schema, loaded processed data, and executed row-count/foreign-key verification.
- Added `src/popularity.py`, a saved popularity artifact, and real global-temporal baseline evaluation.
- Added behavior-oriented popularity tests and updated evaluation documentation with executed results.

## Files changed

`src/popularity.py`, `backend/tests/test_popularity.py`, `README.md`, `docs/EVALUATION.md`, `docs/TECH_DECISIONS.md`, `docs/TODO.md`, and `docs/HANDOFF.md`. Generated model/evaluation files remain Git-ignored.

## Dataset facts and outputs

- Live verification returned exactly 6,000 users, 2,465 products, and 675,004 interactions with no orphan foreign-key records.
- The schema prevents invalid ages/prices/event types, duplicate natural events, and orphan interaction rows.
- Popularity evaluation used 472,504 train, 101,250 validation, and 101,250 test events; final eligible-user test metrics were Precision@10 0.004352, Recall@10 0.041758, and NDCG@10 0.018441.

## Important decisions

- MySQL stores application data only; no sparse matrices, TF-IDF vectors, or similarity artifacts enter the database.
- Re-running the loader is safe because it uses natural-key upserts.
- Popularity is based on unique training users per item, not raw event count; no event weights were invented.

## Tests and checks

- `python -m pytest backend/tests/test_preprocessing.py backend/tests/test_database_loader.py backend/tests/test_popularity.py -q`: **18 passed**.
- `python src/popularity.py --k 10` completed and wrote the saved model/report. `git diff --check` is run before phase completion.

## Resolved issues

1. Initial MySQL authentication failed; user corrected the local account and the successful live run followed.
2. MySQL strict mode rejected CSV boolean strings (`False`) for `discount_applied`; the loader now converts them to `0`/`1`, with a regression test.
3. The loader reads `.env` itself and rejects missing/placeholder credentials, avoiding accidental loads against an unintended database.
4. Initial baseline evaluation counted previously seen holdout items as relevant even though they were correctly filtered from recommendations. Evaluation now excludes seen holdout items, with a regression test; metrics above are from the corrected run.

## Known issues

- No Phase 4 blockers remain. Popularity is intentionally non-personalized and has low absolute metrics; this is a baseline, not evidence of good personalization.

## Next phase

Phase 5: implement sparse item-based collaborative filtering using the same temporal protocol and compare against the recorded baseline.

## Do not change

- Do not alter raw data, use another dataset, or store ML matrices/similarities in MySQL.
- Do not change the database schemas or processed-data contract without updating their tests and documentation.
- Do not change temporal boundaries or reported baseline metrics without rerunning and documenting all affected experiments.
