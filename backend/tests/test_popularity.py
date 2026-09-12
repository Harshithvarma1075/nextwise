import pandas as pd
import pytest

from src.popularity import PopularityRecommender, evaluate, ranking_metrics, temporal_split


def interaction_frame():
    return pd.DataFrame({
        "user_id": [1, 1, 2, 2, 3, 3],
        "item_id": ["a", "b", "a", "c", "a", "d"],
        "timestamp_unix": [1, 5, 2, 6, 3, 7],
    })


def test_popularity_uses_unique_users_and_seen_filtering():
    model = PopularityRecommender.fit(interaction_frame(), ["a", "b", "c", "d", "e"])
    assert model.ranked_item_ids[:2] == ("a", "b")
    assert model.recommend(seen_item_ids={"a"}, limit=3) == ["b", "c", "d"]


def test_popularity_rejects_invalid_limit():
    model = PopularityRecommender.fit(interaction_frame(), ["a"])
    with pytest.raises(ValueError, match="positive"):
        model.recommend(limit=0)


def test_temporal_split_is_ordered_and_nonoverlapping():
    train, validation, test, boundaries = temporal_split(interaction_frame(), 0.5, 0.75)
    assert train.timestamp_unix.max() <= boundaries["train_end_timestamp"]
    assert validation.timestamp_unix.min() > boundaries["train_end_timestamp"]
    assert test.timestamp_unix.min() > boundaries["validation_end_timestamp"]


def test_metrics_and_evaluation_exclude_seen_items():
    assert ranking_metrics(["a", "b"], {"a"}, 2)["ndcg_at_k"] == 1.0
    history = pd.DataFrame({"user_id": [1, 2], "item_id": ["a", "a"], "timestamp_unix": [1, 1]})
    holdout = pd.DataFrame({"user_id": [1, 2], "item_id": ["b", "c"], "timestamp_unix": [2, 2]})
    model = PopularityRecommender.fit(history, ["a", "b", "c"])
    result = evaluate(model, history, holdout, 2)
    assert result["eligible_users"] == 2
    assert 0 <= result["precision_at_k"] <= 1


def test_evaluation_excludes_holdout_items_seen_in_history():
    history = pd.DataFrame({"user_id": [1], "item_id": ["a"], "timestamp_unix": [1]})
    holdout = pd.DataFrame({"user_id": [1], "item_id": ["a"], "timestamp_unix": [2]})
    model = PopularityRecommender.fit(history, ["a", "b"])
    with pytest.raises(ValueError, match="No users"):
        evaluate(model, history, holdout, 2)
