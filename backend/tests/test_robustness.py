import numpy as np
import pandas as pd
import pytest

from src.robustness import bootstrap_mean_ci, history_slice, per_user_evaluation


class EchoModel:
    def recommend(self, user_id, seen, limit):
        return [("b", 1.0)][:limit]


class EchoPopularity:
    def recommend(self, seen, limit):
        return ["b"][:limit]


def test_bootstrap_ci_is_deterministic_and_validates_input():
    values = np.array([0.0, 1.0, 1.0])
    assert bootstrap_mean_ci(values, samples=100, seed=9) == bootstrap_mean_ci(values, samples=100, seed=9)
    with pytest.raises(ValueError, match="non-empty"):
        bootstrap_mean_ci(np.array([]), samples=100)


def test_history_slices_have_explicit_boundaries():
    assert [history_slice(value) for value in (2, 8, 9, 12, 13, 15)] == ["2-8", "2-8", "9-12", "9-12", "13-15", "13-15"]
    with pytest.raises(ValueError, match="positive"):
        history_slice(0)


def test_per_user_evaluation_filters_seen_and_scores_models():
    history = pd.DataFrame({"user_id": [1, 1], "item_id": ["a", "c"], "timestamp_unix": [1, 2]})
    holdout = pd.DataFrame({"user_id": [1], "item_id": ["b"], "timestamp_unix": [3]})
    frame, recommendations = per_user_evaluation({"popularity": EchoPopularity(), "hybrid": EchoModel()}, history, holdout, 10)
    assert frame.loc[0, "hybrid_ndcg_at_k"] == 1.0
    assert recommendations["hybrid"] == [["b"]]
