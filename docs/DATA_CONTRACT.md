# Data contract

## Status: Phase 1 inspection pending

## Frozen raw inputs

| File | Initial verified shape | Columns |
| --- | ---: | --- |
| `interactions.csv` | 675,004 × 5 | `ITEM_ID`, `USER_ID`, `EVENT_TYPE`, `TIMESTAMP`, `DISCOUNT` |
| `items.csv` | 2,465 × 8 | `ITEM_ID`, `PRICE`, `CATEGORY_L1`, `CATEGORY_L2`, `PRODUCT_NAME`, `PRODUCT_DESCRIPTION`, `GENDER`, `PROMOTED` |
| `users.csv` | 6,000 × 3 | `USER_ID`, `AGE`, `GENDER` |

The initial read observed UUID-like item IDs, numeric user IDs, Unix-like integer timestamps, and human-readable catalog metadata. It did not establish event types, missingness, duplicates, distributions, orphan counts, or final types/semantics.

## Phase 1 requirements

Inspect actual event types, counts, timestamp range, missingness, duplicate/invalid rows, discount values, catalog completeness, category/price/gender/promotion distributions, description quality, user age/gender coverage, and cross-file orphan records. Do not modify raw CSVs.

## Future processed contract

Phase 2 will document validated and normalized schemas, exclusions, timestamp conversion, interaction aggregation, and any reproducible subset rule. No processed schema has yet been chosen.
