# Data contract

## Status: Phase 2 processed contract complete

## Frozen raw inputs

| File | Shape | Schema |
| --- | ---: | --- |
| `interactions.csv` | 675,004 × 5 | `ITEM_ID`, `USER_ID`, `EVENT_TYPE`, `TIMESTAMP`, `DISCOUNT` |
| `items.csv` | 2,465 × 8 | `ITEM_ID`, `PRICE`, `CATEGORY_L1`, `CATEGORY_L2`, `PRODUCT_NAME`, `PRODUCT_DESCRIPTION`, `GENDER`, `PROMOTED` |
| `users.csv` | 6,000 × 3 | `USER_ID`, `AGE`, `GENDER` |

Raw files are never edited. Run the reproducible pipeline:

```text
C:\Users\Harshith Varma\AppData\Local\Python\pythoncore-3.14-64\python.exe src\preprocessing.py --raw-dir data\raw\amazon_retail_demo --output-dir data\processed
```

## Validated transformations

- Required columns and non-empty files are required.
- IDs are trimmed and validated as nonblank (`item_id`) or positive integer (`user_id`).
- `age`, `price`, and Unix timestamps are validated as positive numeric values.
- Event types must be the Phase 1 observed set: `View`, `AddToCart`, `ViewCart`, `StartCheckout`, `Purchase`.
- `DISCOUNT` must be `Yes`/`No` and becomes boolean `discount_applied`.
- Unix timestamps are retained and converted to UTC `event_timestamp`.
- Exact duplicate source rows are removed. Non-identical repeated events are retained.
- Any interaction referencing a user/item absent from the validated catalogs stops the pipeline rather than silently dropping data.
- Item gender is normalized to `F`, `M`, or `ANY`.
- `PROMOTED=True` becomes `true`; a missing source value becomes `unknown`. Unexpected non-null values make the affected item invalid rather than being silently relabeled.
- No interaction-strength or recommendation weight is assigned in preprocessing.

## Generated processed outputs

| Output | Rows | Schema / purpose |
| --- | ---: | --- |
| `users_processed.csv` | 6,000 | `user_id`, `age`, `gender` |
| `items_processed.csv` | 2,465 | `item_id`, `price`, `category_l1`, `category_l2`, `product_name`, `product_description`, `gender`, `promoted_status` |
| `interactions_processed.csv` | 675,004 | `user_id`, `item_id`, `event_type`, `timestamp_unix`, `event_timestamp`, `discount_applied` |
| `user_item_interactions.csv` | 66,262 | One row per user-item pair with first/last timestamp, total/discounted counts, and one count column per observed event type. |
| `preprocessing_report.json` | n/a | Executed input/output counts, drops, and transformation decisions. |

No raw row was removed in the executed dataset: all 6,000 users, 2,465 items, and 675,004 events passed validation; 609 item records are `promoted_status=true` and 1,856 are `unknown`.

## Output reliability

Processed CSVs are written through temporary files and atomically published, preventing a partially written artifact if output writing fails. All generated outputs remain Git-ignored.
