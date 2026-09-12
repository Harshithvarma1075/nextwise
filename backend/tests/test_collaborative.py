import pandas as pd
import pytest

from src.collaborative import ItemCollaborativeFilter, evaluate


def interactions():
    return pd.DataFrame({
        "user_id": [1, 1, 2, 2, 3, 3, 4, 4],
        "item_id": ["a", "b", "a", "b", "a", "c", "d", "c"],
        "timestamp_unix": list(range(1, 9)),
    })


def test_collaborative_recommends_unseen_neighbor():
    model = ItemCollaborativeFilter.fit(interactions(), ["a", "b", "c", "d"], max_neighbors=3)
    recommendation_ids = [item_id for item_id, _ in model.recommend(3, limit=3)]
    assert "b" in recommendation_ids
    assert "a" not in recommendation_ids
    assert "c" not in recommendation_ids


def test_collaborative_returns_empty_for_unknown_or_no_candidate_user():
    model = ItemCollaborativeFilter.fit(interactions(), ["a", "b", "c", "d"], max_neighbors=3)
    assert model.recommend(999) == []
    assert model.recommend(1, seen_item_ids={"a", "b", "c", "d"}) == []


def test_collaborative_rejects_invalid_configuration():
    with pytest.raises(ValueError, match="positive"):
        ItemCollaborativeFilter.fit(interactions(), ["a"], max_neighbors=0)


def test_collaborative_evaluation_filters_seen_holdout_items():
    history = pd.DataFrame({"user_id": [1, 1, 2, 2], "item_id": ["a", "b", "a", "c"], "timestamp_unix": [1, 2, 1, 2]})
    holdout = pd.DataFrame({"user_id": [1, 2], "item_id": ["c", "b"], "timestamp_unix": [3, 3]})
    model = ItemCollaborativeFilter.fit(history, ["a", "b", "c"], max_neighbors=2)
    result = evaluate(model, history, holdout, k=2)
    assert result["eligible_users"] == 2
    assert result["users_with_candidates"] == 2
