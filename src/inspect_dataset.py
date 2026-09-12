"""Read-only Phase 1 inspection for the frozen Amazon Retail Demo Store CSVs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

FILES = {"interactions": "interactions.csv", "items": "items.csv", "users": "users.csv"}
REQUIRED = {
    "interactions": {"ITEM_ID", "USER_ID", "EVENT_TYPE", "TIMESTAMP", "DISCOUNT"},
    "items": {"ITEM_ID", "PRICE", "CATEGORY_L1", "CATEGORY_L2", "PRODUCT_NAME", "PRODUCT_DESCRIPTION", "GENDER", "PROMOTED"},
    "users": {"USER_ID", "AGE", "GENDER"},
}


def require_columns(name: str, frame: pd.DataFrame) -> None:
    missing = REQUIRED[name].difference(frame.columns)
    if missing:
        raise ValueError(f"{name} is missing required columns: {sorted(missing)}")


def frame_summary(frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "dtypes": {column: str(dtype) for column, dtype in frame.dtypes.items()},
        "missing_values": {column: int(count) for column, count in frame.isna().sum().items()},
        "exact_duplicate_rows": int(frame.duplicated().sum()),
    }


def inspect(raw_dir: Path) -> dict[str, Any]:
    paths = {name: raw_dir / filename for name, filename in FILES.items()}
    missing_files = [str(path) for path in paths.values() if not path.is_file()]
    if missing_files:
        raise FileNotFoundError(f"Missing required raw file(s): {missing_files}")

    interactions = pd.read_csv(paths["interactions"])
    items = pd.read_csv(paths["items"])
    users = pd.read_csv(paths["users"])
    for name, frame in (("interactions", interactions), ("items", items), ("users", users)):
        require_columns(name, frame)

    interaction_summary = frame_summary(interactions)
    interaction_summary.update({
        "event_counts": {str(key): int(value) for key, value in interactions["EVENT_TYPE"].value_counts(dropna=False).items()},
        "unique_users": int(interactions["USER_ID"].nunique(dropna=True)),
        "unique_items": int(interactions["ITEM_ID"].nunique(dropna=True)),
        "invalid_or_missing_user_ids": int(pd.to_numeric(interactions["USER_ID"], errors="coerce").isna().sum()),
        "missing_or_blank_item_ids": int(interactions["ITEM_ID"].isna().sum() + interactions["ITEM_ID"].astype("string").str.strip().eq("").sum()),
        "timestamp_min": int(interactions["TIMESTAMP"].min()),
        "timestamp_max": int(interactions["TIMESTAMP"].max()),
        "timestamp_min_utc": pd.to_datetime(interactions["TIMESTAMP"].min(), unit="s", utc=True).isoformat(),
        "timestamp_max_utc": pd.to_datetime(interactions["TIMESTAMP"].max(), unit="s", utc=True).isoformat(),
        "invalid_timestamp_count": int(pd.to_numeric(interactions["TIMESTAMP"], errors="coerce").isna().sum()),
        "discount_counts": {str(key): int(value) for key, value in interactions["DISCOUNT"].value_counts(dropna=False).items()},
        "duplicate_user_item_event_timestamp": int(interactions.duplicated(["USER_ID", "ITEM_ID", "EVENT_TYPE", "TIMESTAMP"]).sum()),
        "user_interaction_quantiles": {str(key): float(value) for key, value in interactions.groupby("USER_ID").size().quantile([0, .25, .5, .75, .95, .99, 1]).items()},
    })

    item_summary = frame_summary(items)
    descriptions = items["PRODUCT_DESCRIPTION"].fillna("").astype(str).str.strip()
    item_summary.update({
        "unique_item_ids": int(items["ITEM_ID"].nunique(dropna=True)),
        "duplicate_item_ids": int(items["ITEM_ID"].duplicated().sum()),
        "missing_or_blank_item_ids": int(items["ITEM_ID"].isna().sum() + items["ITEM_ID"].astype("string").str.strip().eq("").sum()),
        "category_l1_counts": {str(key): int(value) for key, value in items["CATEGORY_L1"].value_counts(dropna=False).items()},
        "category_l2_count": int(items["CATEGORY_L2"].nunique(dropna=True)),
        "gender_counts": {str(key): int(value) for key, value in items["GENDER"].value_counts(dropna=False).items()},
        "promoted_counts": {str(key): int(value) for key, value in items["PROMOTED"].value_counts(dropna=False).items()},
        "price_summary": {str(key): float(value) for key, value in items["PRICE"].describe(percentiles=[.25, .5, .75, .95]).items()},
        "invalid_or_nonpositive_prices": int((pd.to_numeric(items["PRICE"], errors="coerce").isna() | (pd.to_numeric(items["PRICE"], errors="coerce") <= 0)).sum()),
        "blank_descriptions": int(descriptions.eq("").sum()),
        "description_length_summary": {str(key): float(value) for key, value in descriptions.str.len().describe(percentiles=[.25, .5, .75, .95]).items()},
        "duplicate_name_description": int(items.duplicated(["PRODUCT_NAME", "PRODUCT_DESCRIPTION"]).sum()),
    })

    user_summary = frame_summary(users)
    user_summary.update({
        "unique_user_ids": int(users["USER_ID"].nunique(dropna=True)),
        "duplicate_user_ids": int(users["USER_ID"].duplicated().sum()),
        "invalid_or_missing_user_ids": int(pd.to_numeric(users["USER_ID"], errors="coerce").isna().sum()),
        "gender_counts": {str(key): int(value) for key, value in users["GENDER"].value_counts(dropna=False).items()},
        "age_summary": {str(key): float(value) for key, value in users["AGE"].describe(percentiles=[.25, .5, .75, .95]).items()},
        "invalid_ages": int((pd.to_numeric(users["AGE"], errors="coerce").isna() | (pd.to_numeric(users["AGE"], errors="coerce") <= 0)).sum()),
    })

    interaction_item_ids = set(interactions["ITEM_ID"].dropna())
    catalog_item_ids = set(items["ITEM_ID"].dropna())
    interaction_user_ids = set(interactions["USER_ID"].dropna())
    catalog_user_ids = set(users["USER_ID"].dropna())
    cross_file = {
        "interaction_item_ids_missing_from_catalog": len(interaction_item_ids - catalog_item_ids),
        "interactions_with_item_missing_from_catalog": int((~interactions["ITEM_ID"].isin(catalog_item_ids)).sum()),
        "catalog_items_without_interactions": len(catalog_item_ids - interaction_item_ids),
        "interaction_user_ids_missing_from_users": len(interaction_user_ids - catalog_user_ids),
        "interactions_with_user_missing_from_users": int((~interactions["USER_ID"].isin(catalog_user_ids)).sum()),
        "catalog_users_without_interactions": len(catalog_user_ids - interaction_user_ids),
    }
    density = len(interactions) / (interactions["USER_ID"].nunique() * interactions["ITEM_ID"].nunique())
    feasibility = {
        "user_item_matrix_shape": [int(interactions["USER_ID"].nunique()), int(interactions["ITEM_ID"].nunique())],
        "observed_interactions": int(len(interactions)),
        "matrix_density": float(density),
        "decision": "Full interaction file is feasible for this assessment; no Phase 1 sampling is justified by its 675,004-row size. Sparse representations remain required for later CF work.",
    }
    return {"files": {name: {"bytes": path.stat().st_size} for name, path in paths.items()}, "interactions": interaction_summary, "items": item_summary, "users": user_summary, "cross_file": cross_file, "feasibility": feasibility}


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect frozen Amazon Retail Demo Store CSVs without modifying them.")
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = inspect(args.raw_dir)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
