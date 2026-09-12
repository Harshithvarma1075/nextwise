# Handoff

## Current phase

Phase 3 — MySQL schema and live data loading complete.

## Completed

- Added `backend/app/db/schema.sql` for `users`, `products`, and `interactions`.
- Added `backend/app/db/loader.py`, which reads `.env`, creates tables, performs parameterized batched upserts in one transaction, and verifies loaded counts/referential integrity.
- Added `backend/tests/test_database_loader.py` and `docs/MYSQL_SETUP.md`.
- Retained all completed Phase 2 pipeline/data artifacts and tests.
- Connected to the configured local MySQL database, created the schema, loaded processed data, and executed row-count/foreign-key verification.

## Files changed

`backend/app/db/schema.sql`, `backend/app/db/loader.py`, `backend/tests/test_database_loader.py`, `docs/MYSQL_SETUP.md`, `README.md`, `docs/TECH_DECISIONS.md`, `docs/TODO.md`, and `docs/HANDOFF.md`. Generated processed data and `.env` are Git-ignored.

## Dataset facts and outputs

- Live verification returned exactly 6,000 users, 2,465 products, and 675,004 interactions with no orphan foreign-key records.
- The schema prevents invalid ages/prices/event types, duplicate natural events, and orphan interaction rows.

## Important decisions

- MySQL stores application data only; no sparse matrices, TF-IDF vectors, or similarity artifacts enter the database.
- Re-running the loader is safe because it uses natural-key upserts.

## Tests and checks

- `python -m pytest backend/tests/test_preprocessing.py backend/tests/test_database_loader.py -q`: **13 passed**.
- Live `verify_database(...)` returned `{'users': 6000, 'products': 2465, 'interactions': 675004}`. `git diff --check` passes.

## Resolved issues

1. Initial MySQL authentication failed; user corrected the local account and the successful live run followed.
2. MySQL strict mode rejected CSV boolean strings (`False`) for `discount_applied`; the loader now converts them to `0`/`1`, with a regression test.
3. The loader reads `.env` itself and rejects missing/placeholder credentials, avoiding accidental loads against an unintended database.

## Known issues

- No Phase 3 blockers remain. The database is populated with the Phase 2 processed snapshot. Re-run preprocessing and loader after any deliberate data-pipeline change.

## Next phase

Phase 4: implement and evaluate a popularity baseline using the established processed data.

## Do not change

- Do not alter raw data, use another dataset, or store ML matrices/similarities in MySQL.
- Do not change the database schemas or processed-data contract without updating their tests and documentation.
