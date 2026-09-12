# Handoff

## Current phase

Phase 5 — collaborative filtering complete.

## Completed

- Added `backend/app/db/schema.sql` for `users`, `products`, and `interactions`.
- Added `backend/app/db/loader.py`, which reads `.env`, creates tables, performs parameterized batched upserts in one transaction, and verifies loaded counts/referential integrity.
- Added `backend/tests/test_database_loader.py` and `docs/MYSQL_SETUP.md`.
- Retained all completed Phase 2 pipeline/data artifacts and tests.
- Connected to the configured local MySQL database, created the schema, loaded processed data, and executed row-count/foreign-key verification.
- Added `src/popularity.py`, a saved popularity artifact, and real global-temporal baseline evaluation.
- Added behavior-oriented popularity tests and updated evaluation documentation with executed results.
- Added `src/collaborative.py`, sparse item-based CF artifact generation, personalized seen-filtered candidates, and temporal evaluation.
- Added collaborative behavior tests and recorded real comparison metrics.

## Files changed

`src/collaborative.py`, `backend/tests/test_collaborative.py`, `README.md`, `docs/EVALUATION.md`, `docs/TECH_DECISIONS.md`, `docs/TODO.md`, and `docs/HANDOFF.md`. Generated model/evaluation files remain Git-ignored.

## Dataset facts and outputs

- Live verification returned exactly 6,000 users, 2,465 products, and 675,004 interactions with no orphan foreign-key records.
- The schema prevents invalid ages/prices/event types, duplicate natural events, and orphan interaction rows.
- Popularity evaluation used 472,504 train, 101,250 validation, and 101,250 test events; final eligible-user test metrics were Precision@10 0.004352, Recall@10 0.041758, and NDCG@10 0.018441.
- CF test evaluation used the same split and 2,275 eligible users; every eligible user had candidates. Results: Precision@10 0.066110, Recall@10 0.549275, NDCG@10 0.354436.

## Important decisions

- MySQL stores application data only; no sparse matrices, TF-IDF vectors, or similarity artifacts enter the database.
- Re-running the loader is safe because it uses natural-key upserts.
- Popularity is based on unique training users per item, not raw event count; no event weights were invented.
- CF uses binary interaction incidence and top-100 sparse cosine neighbors per item; no full dense similarity matrix or arbitrary event weighting is used.

## Tests and checks

- `python -m pytest backend/tests/test_preprocessing.py backend/tests/test_database_loader.py backend/tests/test_popularity.py backend/tests/test_collaborative.py -q`: **22 passed**.
- `python -m src.collaborative --k 10 --max-neighbors 100` completed and wrote `collaborative_filter.joblib` and its evaluation report. `git diff --check` passes.

## Resolved issues

1. Initial MySQL authentication failed; user corrected the local account and the successful live run followed.
2. MySQL strict mode rejected CSV boolean strings (`False`) for `discount_applied`; the loader now converts them to `0`/`1`, with a regression test.
3. The loader reads `.env` itself and rejects missing/placeholder credentials, avoiding accidental loads against an unintended database.
4. Initial baseline evaluation counted previously seen holdout items as relevant even though they were correctly filtered from recommendations. Evaluation now excludes seen holdout items, with a regression test; metrics above are from the corrected run.
5. Brute-force nearest-neighbor fitting was too slow on the full data. Replaced it with sparse normalized item-matrix multiplication and top-neighbor pruning; full evaluation then completed.
6. Running `python src/collaborative.py` fails because `src` is not importable from a file execution context. Use `python -m src.collaborative` as documented.

## Known issues

- No Phase 5 blockers remain. CF requires a known user with interaction history; the later cold-start layer must provide the popularity fallback.

## Next phase

Phase 6: implement and evaluate TF-IDF content-based filtering from verified product metadata.

## Do not change

- Do not alter raw data, use another dataset, or store ML matrices/similarities in MySQL.
- Do not change the database schemas or processed-data contract without updating their tests and documentation.
- Do not change temporal boundaries or reported baseline metrics without rerunning and documenting all affected experiments.
- Do not change CF's binary interaction assumption or neighbor limit without re-evaluating and documenting the impact.
