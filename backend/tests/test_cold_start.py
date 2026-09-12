import pandas as pd
import pytest

from src.cold_start import ColdStartRouter, normalize_seen
from src.collaborative import ItemCollaborativeFilter
from src.content_based import ContentBasedRecommender
from src.hybrid import HybridRecommender
from src.popularity import PopularityRecommender


def items():
    return pd.DataFrame({
        "item_id": ["a", "b", "c"], "product_name": ["red shoe", "red boot", "pan"],
        "product_description": ["running", "walking", "cookware"], "category_l1": ["Fashion", "Fashion", "Kitchen"],
        "category_l2": ["Shoes", "Shoes", "Cookware"], "gender": ["Unisex", "Unisex", "Unisex"],
    })


def source():
    return pd.DataFrame({"user_id": [1, 2, 2], "item_id": ["a", "a", "b"], "timestamp_unix": [1, 1, 2]})


def router():
    data = source()
    hybrid = HybridRecommender(
        ItemCollaborativeFilter.fit(data, items()["item_id"], max_neighbors=10),
        ContentBasedRecommender.fit(items(), data), 1.0, 10,
    )
    popularity = PopularityRecommender.fit(data, items()["item_id"])
    return ColdStartRouter(hybrid, popularity)


def test_known_user_uses_personalized_route_and_unknown_uses_popularity():
    service = router()
    known = service.recommend(1, limit=2)
    unknown = service.recommend(99, limit=2)
    anonymous = service.recommend(None, limit=2)
    assert known.source == "personalized_cf"
    assert known.personalized is True
    assert unknown.source == anonymous.source == "popularity_cold_start"
    assert unknown.personalized is False


def test_fallback_filters_seen_items_and_input_validation():
    service = router()
    baseline = service.recommend(None, limit=2)
    filtered = service.recommend(None, {baseline.item_ids[0]}, limit=2)
    assert baseline.item_ids[0] not in filtered.item_ids
    with pytest.raises(ValueError, match="positive integer"):
        service.recommend(0)
    with pytest.raises(ValueError, match="not a string"):
        normalize_seen("a")
    with pytest.raises(ValueError, match="limit"):
        service.recommend(None, limit=0)


def test_known_user_without_candidates_falls_back_to_popularity():
    data = source()
    hybrid = HybridRecommender(
        ItemCollaborativeFilter.fit(data, items()["item_id"], max_neighbors=10),
        ContentBasedRecommender.fit(items(), data), 1.0, 10,
    )
    service = ColdStartRouter(hybrid, PopularityRecommender.fit(data, items()["item_id"]))
    result = service.recommend(1, {"a", "b", "c"}, limit=2)
    assert result.source == "popularity_cold_start"
    assert result.item_ids == ()
