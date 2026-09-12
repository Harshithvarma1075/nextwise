# Data contract

## Status: Phase 1 raw inspection complete; processed contract pending Phase 2

## Frozen raw inputs

| File | Size | Shape | Columns |
| --- | ---: | ---: | --- |
| `interactions.csv` | 42,458,562 bytes | 675,004 × 5 | `ITEM_ID`, `USER_ID`, `EVENT_TYPE`, `TIMESTAMP`, `DISCOUNT` |
| `items.csv` | 1,018,383 bytes | 2,465 × 8 | `ITEM_ID`, `PRICE`, `CATEGORY_L1`, `CATEGORY_L2`, `PRODUCT_NAME`, `PRODUCT_DESCRIPTION`, `GENDER`, `PROMOTED` |
| `users.csv` | 58,912 bytes | 6,000 × 3 | `USER_ID`, `AGE`, `GENDER` |

## Verified interaction facts

- Columns contain no missing values, exact duplicate rows, invalid/missing IDs, or duplicate `(USER_ID, ITEM_ID, EVENT_TYPE, TIMESTAMP)` combinations.
- Event counts: `View` 581,900; `AddToCart` 46,552; `ViewCart` 29,095; `StartCheckout` 11,638; `Purchase` 5,819.
- All 6,000 users and all 2,465 items appear in interactions.
- Timestamps are integer Unix seconds: 2025-11-13T18:40:59Z to 2026-01-26T20:42:43Z.
- `DISCOUNT` is a complete categorical `Yes`/`No` field, not a numeric field: `No` 411,850 and `Yes` 263,154.
- User interaction counts range from 24 to 219 (median 115).

## Verified catalog facts

- No missing or duplicate item IDs, exact duplicate rows, blank descriptions, duplicate name/description pairs, or non-positive prices.
- 20 `CATEGORY_L1` values and 84 `CATEGORY_L2` values exist. Product gender values are `Any` (1,716), `F` (431), and `M` (318).
- `PROMOTED` is object-typed with `True` for 609 records and missing values for 1,856; missing must not be assumed false without a documented Phase 2 rule.
- Price median is 79.99, 95th percentile is 1,299.99, and maximum is 24,999.99; the distribution is right-skewed.
- Descriptions are complete and non-empty (median length 310 characters), supporting later TF-IDF content representation.

## Verified user facts

- No missing values, exact duplicate rows, duplicate user IDs, or invalid ages.
- Gender values: `F` 3,068 and `M` 2,932.
- Age range 18–84; median 35 and mean approximately 36.13.

## Cross-file integrity and feasibility

There are zero interaction items missing from the catalog, zero interaction users missing from the user file, zero catalog items without interactions, and zero catalog users without interactions.

The user-item matrix is 6,000 × 2,465 with 675,004 observed events (observed-event density ≈ 0.04564). The full file is practical for this assessment; no Phase 1 subset is justified. Later CF work must still use sparse matrices because a dense similarity representation would be unnecessary.

## Phase 2 contract work

Phase 2 must preserve raw files and script validation/type normalization, timestamp conversion, duplicate policy, interaction aggregation, categorical treatment for `DISCOUNT`, and an explicit missing-value policy for `PROMOTED`. The final processed schemas and any interaction-strength weights are not selected yet.
