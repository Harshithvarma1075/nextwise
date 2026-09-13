# Quality Assurance Report

## Scope

This report records the final quality checks performed after Phases 10 and 11. It distinguishes fast isolated tests from the opt-in live test that requires the configured MySQL database and saved model artifacts.

## Automated test layers

| Layer | Coverage |
| --- | --- |
| Preprocessing tests | Required fields, validation, normalization, atomic output behavior, aggregation contracts. |
| Database loader tests | Environment parsing, schema/load sequencing, batched upserts, boolean conversion, rollback-oriented behavior. |
| Model tests | Popularity ranking, CF seen filtering and candidate generation, TF-IDF content behavior, hybrid selection, cold start. |
| Evaluation tests | Split validation, metrics, bootstrap helpers, robustness slices, artifact compatibility. |
| API contract tests | Request validation, safe errors, CORS, algorithms, demo user, activity response. |
| Live integration test | Real MySQL catalog, saved artifacts, Flask app factory, health, users, activity, CF/content/hybrid, cold start, error responses. |
| UI checks | Vite production build, browser walkthrough of personalized content and cold start. |

## Final executed checks

The following final pass was re-executed on **2026-09-13** after the delivery documentation was completed. The live test was deliberately enabled, so these results include the configured MySQL database and saved model artifacts rather than only mocked components.

| Command or check | Result |
| --- | --- |
| `RUN_LIVE_API_TESTS=1 python -m pytest backend/tests -q` | **41 passed, 12 upstream deprecation warnings, 10.34 s** |
| `python -m compileall -q src backend` | Passed |
| Real Flask test-client API smoke check | Passed for health, CF, content, hybrid, cold start, and activity |
| `npm run build` from `frontend/` | Passed |
| `npm audit --omit=dev` from `frontend/` | 0 vulnerabilities |
| Fresh-process Joblib model/router load | Passed |
| `git diff --check` | Passed |

## Live integration assertion set

The final live test in `backend/tests/test_api_integration.py` requires `RUN_LIVE_API_TESTS=1`. It uses the application factory and does not inject fake repository or model implementations. It confirms:

1. `/api/health` reports loaded models and an available catalog database.
2. `/api/users` returns a valid real dataset user.
3. CF, content, and hybrid each return three unique hydrated catalog records for that user.
4. The API labels routes correctly: `collaborative_filter`, `content_based`, and `personalized_cf`.
5. Recent activity returns valid source event types and UTC timestamps.
6. Cold start returns `popularity_cold_start`, is marked non-personalized, and returns hydrated products.
7. Invalid algorithms/limits and missing users produce structured 400/404 errors.

## Defects discovered and resolved during finalization

| Finding | Resolution |
| --- | --- |
| UI could not reach API from `127.0.0.1` because only `localhost` was CORS-allowed | Added both explicit local Vite origins and contract coverage. |
| Joblib artifacts serialized from `__main__` could not load in a fresh process | Regenerated artifacts through stable `src.*` imports and tested fresh-process loading. |
| Hybrid tuning recomputed content candidates for every weight | Cached source candidates once per user; the weight search now repeats only blend/ranking work. |
| Activity patch initially duplicated a Flask route/method | API tests caught the endpoint collision; duplicate declarations were removed. |
| Live test left `.env` values in pytest’s process environment | The integration fixture restores the original environment after completion. |

## Known non-blocking warnings

The live integration run emitted 12 deprecation warnings from NumPy/Joblib serialization internals: a future NumPy version will reject a shape-setting behavior currently used by the installed Joblib dependency. No application test failed, and the saved artifacts load successfully in a fresh process. This is tracked as an upstream dependency compatibility warning, not suppressed as though it were a project pass.

## Release conclusion

The API, database catalog access, saved recommendation artifacts, activity explanation, cold-start routing, and UI build have all been verified. No open functional blocker was identified in the final test run. The next maintenance priority is monitoring the NumPy/Joblib compatibility warning when dependency versions are upgraded.
