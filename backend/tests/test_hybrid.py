import pandas as pd
import pytest

from src.collaborative import ItemCollaborativeFilter
from src.content_based import ContentBasedRecommender
from src.hybrid import HybridRecommender, choose_weight, normalize_scores


def items():
    return pd.DataFrame({
        "item_id": ["a", "b", "c"],
        "product_name": ["red shoe", "red boot", "kitchen pan"],
        "product_description": ["running shoe", "walking shoe", "nonstick cookware"],
        "category_l1": ["Fashion", "Fashion", "Kitchen"],
        "category_l2": ["Shoes", "Shoes", "Cookware"],
        "gender": ["Unisex", "Unisex", "Unisex"],
    })


def interactions():
    return pd.DataFrame({
        "user_id": [1, 2, 2, 3, 3],
        "item_id": ["a", "a", "b", "a", "b"],
        "timestamp_unix": [1, 1, 2, 1, 2],
    })


def model(weight=0.5):
    source = interactions()
    return HybridRecommender(
        ItemCollaborativeFilter.fit(source, items()["item_id"], max_neighbors=10),
        ContentBasedRecommender.fit(items(), source),
        weight,
        candidate_limit=10,
    )


def test_normalize_scores_removes_invalid_and_scales_to_one():
    assert normalize_scores([("a", 2.0), ("b", 1.0), ("c", 0.0)]) == {"a": 1.0, "b": 0.5}


def test_hybrid_recommends_unseen_items_and_rejects_bad_inputs():
    recommender = model()
    recommended = [item_id for item_id, _ in recommender.recommend(1)]
    assert recommended[0] == "b"
    assert "a" not in recommended
    assert recommender.recommend(999) == []
    with pytest.raises(ValueError, match="user_id"):
        recommender.recommend("not-an-id")
    with pytest.raises(ValueError, match="limit"):
        recommender.recommend(1, limit=0)


def test_hybrid_rejects_misaligned_component_catalogs():
    source = interactions()
    cf = ItemCollaborativeFilter.fit(source, ["a", "b"], max_neighbors=10)
    content = ContentBasedRecommender.fit(items(), source)
    with pytest.raises(ValueError, match="same ordered catalog"):
        HybridRecommender(cf, content, 0.5)


def test_weight_selection_uses_best_validation_metric():
    source = interactions()
    cf = ItemCollaborativeFilter.fit(source, items()["item_id"], max_neighbors=10)
    content = ContentBasedRecommender.fit(items(), source)
    validation = pd.DataFrame({"user_id": [1], "item_id": ["b"], "timestamp_unix": [3]})
    weight, trials = choose_weight(cf, content, source, validation, k=1, candidate_limit=10)
    best_ndcg = max(float(trial["ndcg_at_k"]) for trial in trials)
    selected = next(trial for trial in trials if trial["cf_weight"] == weight)
    assert float(selected["ndcg_at_k"]) == best_ndcg
