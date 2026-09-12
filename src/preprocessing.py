"""Phase 2 reproducible preprocessing for the frozen Amazon Retail Demo Store data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = {
    "interactions": ["ITEM_ID", "USER_ID", "EVENT_TYPE", "TIMESTAMP", "DISCOUNT"],
    "items": ["ITEM_ID", "PRICE", "CATEGORY_L1", "CATEGORY_L2", "PRODUCT_NAME", "PRODUCT_DESCRIPTION", "GENDER", "PROMOTED"],
    "users": ["USER_ID", "AGE", "GENDER"],
}
VALID_EVENTS = {"View", "AddToCart", "ViewCart", "StartCheckout", "Purchase"}
VALID_DISCOUNTS = {"Yes", "No"}
VALID_USER_GENDERS = {"F", "M"}
VALID_ITEM_GENDERS = {"F", "M", "ANY"}


def require_columns(frame: pd.DataFrame, source: str) -> None:
    missing = set(REQUIRED_COLUMNS[source]).difference(frame.columns)
    if missing:
        raise ValueError(f"{source} is missing required columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError(f"{source} is empty")


def _string_id(series: pd.Series) -> pd.Series:
    value = series.astype("string").str.strip()
    return value.mask(value.eq(""))


def _positive_integer(series: pd.Series) -> pd.Series:
    value = pd.to_numeric(series, errors="coerce")
    return value.where(value.gt(0)).astype("Int64")


def _report_drop(report: dict[str, int], key: str, mask: pd.Series) -> None:
    report[key] = int(mask.sum())


def clean_users(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    require_columns(raw, "users")
    users = raw[REQUIRED_COLUMNS["users"]].copy()
    report = {"input_rows": len(users)}
    users["USER_ID"] = _positive_integer(users["USER_ID"])
    users["AGE"] = _positive_integer(users["AGE"])
    users["GENDER"] = users["GENDER"].astype("string").str.strip().str.upper()
    invalid = users["USER_ID"].isna() | users["AGE"].isna() | ~users["GENDER"].isin(VALID_USER_GENDERS)
    _report_drop(report, "dropped_invalid_rows", invalid)
    users = users.loc[~invalid].copy()
    _report_drop(report, "dropped_exact_duplicates", users.duplicated())
    users = users.drop_duplicates()
    _report_drop(report, "dropped_duplicate_user_ids", users.duplicated("USER_ID"))
    users = users.drop_duplicates("USER_ID", keep="first")
    users = users.rename(columns={"USER_ID": "user_id", "AGE": "age", "GENDER": "gender"}).astype({"user_id": "int64", "age": "int64"})
    users = users.sort_values("user_id", kind="stable").reset_index(drop=True)
    report["output_rows"] = len(users)
    return users, report


def clean_items(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    require_columns(raw, "items")
    items = raw[REQUIRED_COLUMNS["items"]].copy()
    report = {"input_rows": len(items)}
    items["ITEM_ID"] = _string_id(items["ITEM_ID"])
    items["PRICE"] = pd.to_numeric(items["PRICE"], errors="coerce")
    for field in ("CATEGORY_L1", "CATEGORY_L2", "PRODUCT_NAME", "PRODUCT_DESCRIPTION", "GENDER"):
        items[field] = items[field].astype("string").str.strip().mask(lambda s: s.eq(""))
    items["GENDER"] = items["GENDER"].str.upper()
    promoted_source = items["PROMOTED"]
    promoted_status = promoted_source.map({True: "true", "True": "true"})
    invalid_promoted = promoted_source.notna() & promoted_status.isna()
    items["promoted_status"] = promoted_status.fillna("unknown")
    invalid = (
        items["ITEM_ID"].isna() | items["PRICE"].isna() | items["PRICE"].le(0)
        | items[["CATEGORY_L1", "CATEGORY_L2", "PRODUCT_NAME", "PRODUCT_DESCRIPTION"]].isna().any(axis=1)
        | ~items["GENDER"].isin(VALID_ITEM_GENDERS)
        | invalid_promoted
    )
    _report_drop(report, "dropped_invalid_rows", invalid)
    items = items.loc[~invalid].copy()
    _report_drop(report, "dropped_exact_duplicates", items.duplicated())
    items = items.drop_duplicates()
    _report_drop(report, "dropped_duplicate_item_ids", items.duplicated("ITEM_ID"))
    items = items.drop_duplicates("ITEM_ID", keep="first")
    items = items.rename(columns={
        "ITEM_ID": "item_id", "PRICE": "price", "CATEGORY_L1": "category_l1", "CATEGORY_L2": "category_l2",
        "PRODUCT_NAME": "product_name", "PRODUCT_DESCRIPTION": "product_description", "GENDER": "gender",
    })[["item_id", "price", "category_l1", "category_l2", "product_name", "product_description", "gender", "promoted_status"]]
    items["price"] = items["price"].astype(float)
    items = items.sort_values("item_id", kind="stable").reset_index(drop=True)
    report["promoted_true"] = int(items["promoted_status"].eq("true").sum())
    report["promoted_unknown"] = int(items["promoted_status"].eq("unknown").sum())
    report["output_rows"] = len(items)
    return items, report


def clean_interactions(raw: pd.DataFrame, item_ids: set[str], user_ids: set[int]) -> tuple[pd.DataFrame, dict[str, int]]:
    require_columns(raw, "interactions")
    interactions = raw[REQUIRED_COLUMNS["interactions"]].copy()
    report = {"input_rows": len(interactions)}
    interactions["ITEM_ID"] = _string_id(interactions["ITEM_ID"])
    interactions["USER_ID"] = _positive_integer(interactions["USER_ID"])
    interactions["EVENT_TYPE"] = interactions["EVENT_TYPE"].astype("string").str.strip()
    interactions["TIMESTAMP"] = _positive_integer(interactions["TIMESTAMP"])
    interactions["DISCOUNT"] = interactions["DISCOUNT"].astype("string").str.strip()
    invalid = (
        interactions["ITEM_ID"].isna() | interactions["USER_ID"].isna() | interactions["TIMESTAMP"].isna()
        | ~interactions["EVENT_TYPE"].isin(VALID_EVENTS) | ~interactions["DISCOUNT"].isin(VALID_DISCOUNTS)
    )
    _report_drop(report, "dropped_invalid_rows", invalid)
    interactions = interactions.loc[~invalid].copy()
    _report_drop(report, "dropped_exact_duplicates", interactions.duplicated())
    interactions = interactions.drop_duplicates()
    orphan_items = ~interactions["ITEM_ID"].isin(item_ids)
    orphan_users = ~interactions["USER_ID"].isin(user_ids)
    if orphan_items.any() or orphan_users.any():
        raise ValueError(
            f"cross-file integrity failure: {int(orphan_items.sum())} interaction rows have unknown items; "
            f"{int(orphan_users.sum())} have unknown users"
        )
    interactions["event_timestamp"] = pd.to_datetime(interactions["TIMESTAMP"], unit="s", utc=True)
    interactions["discount_applied"] = interactions["DISCOUNT"].eq("Yes")
    interactions = interactions.rename(columns={
        "ITEM_ID": "item_id", "USER_ID": "user_id", "EVENT_TYPE": "event_type", "TIMESTAMP": "timestamp_unix",
    })[["user_id", "item_id", "event_type", "timestamp_unix", "event_timestamp", "discount_applied"]]
    interactions = interactions.astype({"user_id": "int64", "timestamp_unix": "int64", "discount_applied": bool})
    interactions = interactions.sort_values(["timestamp_unix", "user_id", "item_id", "event_type"], kind="stable").reset_index(drop=True)
    report["output_rows"] = len(interactions)
    return interactions, report


def aggregate_user_item_interactions(events: pd.DataFrame) -> pd.DataFrame:
    """Aggregate repeated events without assigning recommendation weights."""
    counts = (
        events.groupby(["user_id", "item_id", "event_type"], observed=True).size()
        .unstack(fill_value=0).reindex(columns=sorted(VALID_EVENTS), fill_value=0)
        .rename(columns={event: f"{event.lower()}_count" for event in VALID_EVENTS}).reset_index()
    )
    aggregate = events.groupby(["user_id", "item_id"], observed=True).agg(
        first_timestamp_unix=("timestamp_unix", "min"),
        last_timestamp_unix=("timestamp_unix", "max"),
        interaction_count=("event_type", "size"),
        discounted_event_count=("discount_applied", "sum"),
    ).reset_index()
    result = aggregate.merge(counts, on=["user_id", "item_id"], validate="one_to_one")
    return result.sort_values(["user_id", "item_id"], kind="stable").reset_index(drop=True)


def write_csv_atomically(frame: pd.DataFrame, destination: Path) -> None:
    """Avoid publishing a partially written processed CSV if a write fails."""
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    try:
        frame.to_csv(temporary, index=False)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def run(raw_dir: Path, output_dir: Path) -> dict[str, Any]:
    paths = {name: raw_dir / f"{name}.csv" for name in REQUIRED_COLUMNS}
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing required raw file(s): {missing}")
    users, user_report = clean_users(pd.read_csv(paths["users"]))
    items, item_report = clean_items(pd.read_csv(paths["items"]))
    events, interaction_report = clean_interactions(
        pd.read_csv(paths["interactions"]), set(items["item_id"]), set(users["user_id"])
    )
    aggregated = aggregate_user_item_interactions(events)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv_atomically(users, output_dir / "users_processed.csv")
    write_csv_atomically(items, output_dir / "items_processed.csv")
    write_csv_atomically(events, output_dir / "interactions_processed.csv")
    write_csv_atomically(aggregated, output_dir / "user_item_interactions.csv")
    report: dict[str, Any] = {
        "users": user_report, "items": item_report, "interactions": interaction_report,
        "outputs": {"users_processed": len(users), "items_processed": len(items), "interactions_processed": len(events), "user_item_interactions": len(aggregated)},
        "decisions": [
            "All source IDs are validated, trimmed, and normalized to lower_snake_case output columns.",
            "Unix timestamps are retained and converted to UTC event_timestamp.",
            "DISCOUNT Yes/No is normalized to boolean discount_applied.",
            "PROMOTED True becomes true; missing source values become unknown, not false.",
            "Exact duplicate events are removed; repeated non-identical events are retained then aggregated as event counts.",
            "No recommendation weights are assigned during preprocessing.",
        ],
    }
    (output_dir / "preprocessing_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Create validated Amazon Retail Demo Store processed CSVs.")
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.raw_dir, args.output_dir), indent=2))


if __name__ == "__main__":
    main()

