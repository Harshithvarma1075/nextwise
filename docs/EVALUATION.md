# Evaluation

## Status: Phase 4 popularity baseline evaluated

## Protocol

The global temporal split uses processed event timestamps:

| Window | Rows | Boundary |
| --- | ---: | --- |
| Train | 472,504 | `timestamp_unix <= 1767539907` |
| Validation | 101,250 | `1767539907 < timestamp_unix <= 1768500029` |
| Test | 101,250 | `timestamp_unix > 1768500029` |

Users are eligible only when they have history in the corresponding training window and at least one **unseen** item in the holdout window. Existing historical items are filtered from recommendation candidates and relevance to reflect the product requirement that seen products are not recommended.

## Popularity baseline

The baseline ranks catalog items by the number of unique training users who interacted with them. It uses no event-strength weights. This deliberately simple baseline is used for cold-start fallback and as a comparator for later models.

| Model | Split | Eligible users | Precision@10 | Recall@10 | NDCG@10 |
| --- | --- | ---: | ---: | ---: | ---: |
| Popularity | Validation | 2,804 | 0.004280 | 0.038932 | 0.017636 |
| Popularity | Test | 2,275 | 0.004352 | 0.041758 | 0.018441 |

These are executed results from `src/popularity.py`, saved in the Git-ignored `data/processed/popularity_evaluation.json`. Low absolute scores are expected for a global, non-personalized baseline and establish a real benchmark for collaborative, content, and hybrid experiments.

## Collaborative filtering

Item-based CF represents an interaction as binary (the user interacted with the item) and calculates cosine similarity between item interaction vectors. At serving time, it sums each unseen candidate’s precomputed similarities to a user’s historical items. The model stores only the top 100 positive neighbors for each item.

| Model | Split | Eligible users | Users with candidates | Precision@10 | Recall@10 | NDCG@10 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Collaborative filtering | Validation | 2,804 | 2,804 | 0.064765 | 0.489135 | 0.330726 |
| Collaborative filtering | Test | 2,275 | 2,275 | 0.066110 | 0.549275 | 0.354436 |

These are executed results from `src.collaborative`, saved in the Git-ignored `data/processed/collaborative_evaluation.json`. Under the same test protocol, CF materially outperformed global popularity (NDCG@10 0.354436 vs. 0.018441). This supports—not proves universally—that this dataset's repeated user-item patterns carry useful personalized signal.

## Remaining evaluation work

Evaluate content filtering and validation-selected hybrid weights under this same protocol. Do not choose hybrid weights using test results.
