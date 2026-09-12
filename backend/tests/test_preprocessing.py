import pandas as pd
import pytest

from src.preprocessing import (
    aggregate_user_item_interactions,
    clean_interactions,
    clean_items,
    clean_users,
    write_csv_atomically,
)


def users():
    return pd.DataFrame({"USER_ID": [1, 2], "AGE": [25, 30], "GENDER": ["F", "M"]})


def items():
    return pd.DataFrame({
        "ITEM_ID": ["a", "b"], "PRICE": [10.0, 20.0], "CATEGORY_L1": ["x", "y"], "CATEGORY_L2": ["x1", "y1"],
        "PRODUCT_NAME": ["one", "two"], "PRODUCT_DESCRIPTION": ["first", "second"], "GENDER": ["Any", "F"], "PROMOTED": [True, None],
    })


def interactions():
    return pd.DataFrame({
        "ITEM_ID": ["a", "a", "b"], "USER_ID": [1, 1, 2], "EVENT_TYPE": ["View", "View", "Purchase"],
        "TIMESTAMP": [100, 100, 200], "DISCOUNT": ["No", "No", "Yes"],
    })


def test_users_normalize_and_remove_exact_duplicates():
    clean, report = clean_users(pd.concat([users(), users().iloc[[0]]], ignore_index=True))
    assert list(clean.columns) == ["user_id", "age", "gender"]
    assert len(clean) == 2
    assert report["dropped_exact_duplicates"] == 1


def test_items_keep_missing_promotion_as_unknown():
    clean, report = clean_items(items())
    assert clean.promoted_status.tolist() == ["true", "unknown"]
    assert report["promoted_unknown"] == 1


def test_items_reject_unexpected_promotion_value():
    clean, report = clean_items(items().assign(PROMOTED="unexpected"))
    assert clean.empty
    assert report["dropped_invalid_rows"] == 2


def test_interactions_deduplicate_and_convert_discount():
    clean_users_frame, _ = clean_users(users())
    clean_items_frame, _ = clean_items(items())
    clean, report = clean_interactions(interactions(), set(clean_items_frame.item_id), set(clean_users_frame.user_id))
    assert len(clean) == 2
    assert report["dropped_exact_duplicates"] == 1
    assert clean.discount_applied.tolist() == [False, True]
    assert str(clean.event_timestamp.dtype).endswith(", UTC]")


def test_interactions_reject_unknown_catalog_item():
    clean_users_frame, _ = clean_users(users())
    with pytest.raises(ValueError, match="unknown items"):
        clean_interactions(interactions().assign(ITEM_ID="missing"), {"a", "b"}, set(clean_users_frame.user_id))


def test_aggregation_retains_event_counts_without_weights():
    clean_users_frame, _ = clean_users(users())
    clean_items_frame, _ = clean_items(items())
    raw = interactions().copy()
    raw.loc[1, "TIMESTAMP"] = 101
    events, _ = clean_interactions(raw, set(clean_items_frame.item_id), set(clean_users_frame.user_id))
    aggregated = aggregate_user_item_interactions(events)
    first = aggregated.loc[(aggregated.user_id == 1) & (aggregated.item_id == "a")].iloc[0]
    assert first.view_count == 2
    assert first.interaction_count == 2
    assert first.discounted_event_count == 0


def test_atomic_csv_writer_replaces_destination(tmp_path):
    destination = tmp_path / "processed.csv"
    destination.write_text("old\n", encoding="utf-8")
    write_csv_atomically(pd.DataFrame({"value": [1]}), destination)
    assert destination.read_text(encoding="utf-8") == "value\n1\n"
    assert not (tmp_path / "processed.csv.tmp").exists()


