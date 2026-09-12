# Handoff

## Current phase

Phase 0 — H&M project restart complete.

## Completed

- The new master prompt superseded Retailrocket and required an H&M restart from Phase 0.
- Removed Retailrocket raw archive/extracts, generated outputs, legacy preprocessing/test files, bytecode caches, and the Retailrocket EDA document.
- Rewrote source-of-truth documentation and README to describe only the H&M system.
- Kept the general directory skeleton, `.gitignore`, and `.env.example`.

## Files changed

`README.md`, all required documents under `docs/`, and deletion of legacy Retailrocket assets/code. `data/raw/` and `data/processed/` now contain only `.gitkeep` placeholders.

## Important decisions

- H&M Personalized Fashion Recommendations is the sole dataset.
- H&M files must be inspected before assumptions about schema, metadata, images, or subset selection.
- Use H&M’s verified human-readable metadata for content features and product presentation.
- No ML, preprocessing, MySQL, Flask, or React implementation exists in this reset state.

## Tests and checks

- Verified legacy Retailrocket targets before removal.
- Verified raw/processed data folders are reset to placeholders.
- No software tests apply because Phase 0 contains no executable H&M code.

## Known issues / limitations

- H&M dataset is not yet downloaded.
- Existing `.env.example` has a generic `DATASET_DIR`; it is compatible but no H&M-specific runtime configuration exists yet.

## Next phase

Phase 1: acquire and inspect the actual H&M dataset, assess feasibility, and document a reproducible subset decision if necessary.

## Do not change

- Do not restore or use Retailrocket.
- Do not invent H&M fields, products, images, customer data, evaluation results, or product semantics.
- Do not start preprocessing, models, APIs, database schema, or UI until Phase 1 is explicitly approved and data is inspected.
