import pandas as pd
import pytest

from src.content_based import ContentBasedRecommender, product_document


def items():
    return pd.DataFrame({
        "item_id": ["a", "b", "c"], "product_name": ["red shoe", "blue shoe", "cooking book"],
        "product_description": ["running sneaker", "running sneaker", "kitchen recipes"],
        "category_l1": ["footwear", "footwear", "books"], "category_l2": ["sneaker", "sneaker", "cookbook"],
        "gender": ["ANY", "ANY", "ANY"],
    })


def interactions():
    return pd.DataFrame({"user_id": [1, 2], "item_id": ["a", "c"], "timestamp_unix": [1, 2]})


def test_product_document_uses_prefixed_interpretable_categories():
    document = product_document(items().iloc[0])
    assert "category_l1_footwear" in document
    assert "catalog_gender_any" in document


def test_content_recommends_similar_unseen_item():
    model = ContentBasedRecommender.fit(items(), interactions())
    recommended = [item_id for item_id, _ in model.recommend(1)]
    assert recommended[0] == "b"
    assert "a" not in recommended


def test_content_returns_empty_for_unknown_user_and_invalid_limit():
    model = ContentBasedRecommender.fit(items(), interactions())
    assert model.recommend(999) == []
    with pytest.raises(ValueError, match="positive"):
        model.recommend(1, limit=0)


def test_content_rejects_item_without_metadata():
    broken = items().copy()
    broken.loc[0, ["product_name", "product_description", "category_l1", "category_l2", "gender"]] = ""
    with pytest.raises(ValueError, match="no usable content"):
        ContentBasedRecommender.fit(broken, interactions())
