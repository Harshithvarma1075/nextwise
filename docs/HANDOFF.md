# Handoff

## Current phase

Phase 9 — cold-start routing complete.

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
- Added `src/content_based.py`, which builds a TF-IDF representation from verified product metadata and returns seen-filtered personalized content candidates.
- Added content-model behavior tests and recorded its real temporal metrics.
- Added `src/hybrid.py`, which score-normalizes CF/content candidates per user, selects a blend weight exclusively on validation, and saves a final hybrid artifact.
- Added hybrid behavior, compatibility, and selection tests; optimized validation trials so candidates are computed once per user rather than once per candidate weight.
- Added `src/robustness.py`, a fixed-artifact audit with bootstrap CIs, paired differences, history slices, catalog coverage, category diversity, and artifact validation.
- Regenerated saved Joblib artifacts through stable `src.*` imports and verified they load in a new Python process.
- Added `src/cold_start.py`, which routes known users to the selected CF-only model and unknown/anonymous/empty-candidate cases to popularity with explicit provenance labels.
- Added cold-start behavior tests and saved a fresh-process-loadable router artifact.

## Files changed

`src/cold_start.py`, `backend/tests/test_cold_start.py`, `README.md`, `docs/EVALUATION.md`, `docs/TECH_DECISIONS.md`, `docs/TODO.md`, and `docs/HANDOFF.md`. Generated model/evaluation files remain Git-ignored.

## Dataset facts and outputs

- Live verification returned exactly 6,000 users, 2,465 products, and 675,004 interactions with no orphan foreign-key records.
- The schema prevents invalid ages/prices/event types, duplicate natural events, and orphan interaction rows.
- Popularity evaluation used 472,504 train, 101,250 validation, and 101,250 test events; final eligible-user test metrics were Precision@10 0.004352, Recall@10 0.041758, and NDCG@10 0.018441.
- CF test evaluation used the same split and 2,275 eligible users; every eligible user had candidates. Results: Precision@10 0.066110, Recall@10 0.549275, NDCG@10 0.354436.
- Content test evaluation used the same split and 2,275 eligible users; every eligible user had candidates. Results: Precision@10 0.003912, Recall@10 0.036557, NDCG@10 0.026511.
- Hybrid validation selected CF weight 1.00 and content weight 0.00. Its final test results therefore match CF: Precision@10 0.066110, Recall@10 0.549275, NDCG@10 0.354436, with candidates for all 2,275 eligible users.
- Phase 8 paired bootstrap result: hybrid minus popularity NDCG@10 difference 0.335995, 95% CI [0.322371, 0.349737]; all values are executed, not inferred.
- Hybrid history-slice NDCG@10: 0.397143 for 2–8 history items (286 users), 0.304601 for 9–12 (1,520), and 0.489905 for 13–15 (469). CF/hybrid exposed 2,454 of 2,465 catalog items (99.55%) across all test Top-10 lists.
- Cold-start routing audit retained personalized CF for all 2,275 eligible test users (zero fallback) with unchanged NDCG@10 0.354436. Simulated anonymous and unknown users each received 10 popularity items and seen-item filtering passed. No cold-start relevance metric is claimed because the frozen data contains no real-new-user future labels.

## Important decisions

- MySQL stores application data only; no sparse matrices, TF-IDF vectors, or similarity artifacts enter the database.
- Re-running the loader is safe because it uses natural-key upserts.
- Popularity is based on unique training users per item, not raw event count; no event weights were invented.
- CF uses binary interaction incidence and top-100 sparse cosine neighbors per item; no full dense similarity matrix or arbitrary event weighting is used.
- Content uses only verified names, descriptions, category levels, and catalog gender. Category/gender are field-prefixed feature tokens; price and promotion were excluded pending a justified experiment.
- Hybrid source scores are independently max-normalized per user; its 21 weights (CF 0.00–1.00 in 0.05 increments) are selected by validation NDCG@10, then recall, precision, and CF weight. Test data is never used for selection.
- Phase 8 uses 1,000 deterministic, user-level bootstrap resamples for 95% CIs. Coverage and category-level-2 diversity are descriptive diagnostics, not optimization objectives.
- Cold-start responses expose `personalized_cf` or `popularity_cold_start`; MySQL/API phases can use this provenance without inferring user preferences.

## Tests and checks

- `python -m pytest backend/tests/test_preprocessing.py backend/tests/test_database_loader.py backend/tests/test_popularity.py backend/tests/test_collaborative.py -q`: **22 passed**.
- `python -m pytest backend/tests -q`: **26 passed** after Phase 6, including the **4** new content-model tests.
- `python -m pytest backend/tests -q`: **30 passed** after Phase 7, including the **4** new hybrid-model tests.
- `python -m pytest backend/tests -q`: **33 passed** after Phase 8, including the **3** new robustness-audit tests. Fresh-process loading of all three Joblib artifacts also passes.
- `python -m pytest backend/tests -q`: **36 passed** after Phase 9, including the **3** new cold-start tests. The regenerated `cold_start_router.joblib` also loads and returns fallback results in a fresh process.
- `python -m src.collaborative --k 10 --max-neighbors 100` completed and wrote `collaborative_filter.joblib` and its evaluation report. `git diff --check` passes.

## Resolved issues

1. Initial MySQL authentication failed; user corrected the local account and the successful live run followed.
2. MySQL strict mode rejected CSV boolean strings (`False`) for `discount_applied`; the loader now converts them to `0`/`1`, with a regression test.
3. The loader reads `.env` itself and rejects missing/placeholder credentials, avoiding accidental loads against an unintended database.
4. Initial baseline evaluation counted previously seen holdout items as relevant even though they were correctly filtered from recommendations. Evaluation now excludes seen holdout items, with a regression test; metrics above are from the corrected run.
5. Brute-force nearest-neighbor fitting was too slow on the full data. Replaced it with sparse normalized item-matrix multiplication and top-neighbor pruning; full evaluation then completed.
6. Running `python src/collaborative.py` fails because `src` is not importable from a file execution context. Use `python -m src.collaborative` as documented.
7. Current scikit-learn rejects NumPy's legacy `np.matrix`, and sparse conversion initially made content scoring return an object array. The content profile now explicitly uses CSR and dense final score extraction; regression tests cover recommendation behavior.
8. The initial hybrid grid loop recomputed content candidates for every one of 21 weights, creating long-running duplicate attempts when the command launcher returned early. Weight selection now caches source candidates once per user; only the lightweight blending/ranking is repeated per weight. The duplicate Phase 7 processes were stopped before the successful clean run.
9. Phase 8 discovered saved Joblib artifacts could not load in a fresh process because earlier runs serialized model classes as `__main__`. All model artifacts were regenerated via stable `src.*` imports with unchanged settings and matching recorded metrics; fresh-process loading now passes. Hybrid skips zero-weight source scoring, which preserves the selected CF-only output and reduces serving work.
10. The initial Phase 9 router artifact had the same `__main__` serialization issue. It was regenerated through a stable `src.cold_start` import; the fresh-process router check now passes with unchanged NDCG and fallback routing results.

## Known issues

- No Phase 9 blockers remain. Cold-start routing makes every anonymous/unknown user eligible for a popularity response; it does not make the fallback personalized. Content is available for all eligible users but does not improve CF in the tested normalized blend, so the saved hybrid intentionally selects CF-only. Bootstrap results support the CF advantage on this held-out synthetic dataset but do not guarantee production performance.

## Next phase

Phase 10: implement a Flask recommendation API around the saved cold-start router and validated MySQL product records.

## Do not change

- Do not alter raw data, use another dataset, or store ML matrices/similarities in MySQL.
- Do not change the database schemas or processed-data contract without updating their tests and documentation.
- Do not change temporal boundaries or reported baseline metrics without rerunning and documenting all affected experiments.
- Do not change CF's binary interaction assumption or neighbor limit without re-evaluating and documenting the impact.
- Do not add untested content fields or claim content improves hybrid results before executing validation experiments.
- Do not replace the selected CF-only hybrid with a content blend unless a new validation experiment is executed and documented.
- Do not tune model weights, similarity parameters, or TF-IDF fields against the Phase 8 test results.
- Do not report a new-user relevance score without real post-recommendation interaction labels.
