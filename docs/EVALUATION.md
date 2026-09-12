# Evaluation

## Status: Phase 6 content filtering evaluated

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

## Content-based filtering

The content model turns each catalog product into a TF-IDF document containing its verified product name, description, category levels, and catalog gender. Category and gender values are field-prefixed tokens; the user profile is the normalized sum of their historical product vectors. Price and promotion are deliberately excluded because they have not been evaluated as useful structured signals.

| Model | Split | Eligible users | Users with candidates | Precision@10 | Recall@10 | NDCG@10 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| TF-IDF content filtering | Validation | 2,804 | 2,804 | 0.004066 | 0.033999 | 0.022580 |
| TF-IDF content filtering | Test | 2,275 | 2,275 | 0.003912 | 0.036557 | 0.026511 |

These are executed results from `src.content_based`, saved in the Git-ignored `data/processed/content_evaluation.json`. Content filtering improves test NDCG@10 over global popularity (0.026511 vs. 0.018441), but is substantially weaker than CF (0.354436). The later hybrid phase must choose weights on validation only; it must not presume that adding content improves CF.

## Validation-selected hybrid

The hybrid collects each source's top 100 unseen candidates, max-normalizes CF and content scores independently for each user, and combines them as `cf_weight × CF + (1 − cf_weight) × content`. It evaluates all CF weights from 0.00 through 1.00 in 0.05 steps on validation only. Ties are broken deterministically by NDCG@10, recall@10, precision@10, then greater CF weight.

Validation selected **CF weight 1.00** and **content weight 0.00**. The best content-inclusive setting was CF weight 0.95, but it was weaker on validation than pure CF. The final model was then refit on train + validation and evaluated once on the untouched test window.

| Model | Split | Eligible users | Users with candidates | Precision@10 | Recall@10 | NDCG@10 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Validation-selected hybrid (CF 1.00, content 0.00) | Validation | 2,804 | 2,804 | 0.064765 | 0.489135 | 0.330726 |
| Validation-selected hybrid (CF 1.00, content 0.00) | Test | 2,275 | 2,275 | 0.066110 | 0.549275 | 0.354436 |

These are executed results from `src.hybrid`, saved in the Git-ignored `data/processed/hybrid_evaluation.json`. The result matches CF because validation selected CF-only; that is evidence that this particular content representation does not add measurable value to this blend, not evidence that content is universally unhelpful.

## Phase 8 robustness audit

This is a post-selection audit of the fixed Phase 4–7 artifacts. It does not tune any model, alter a weight, or use the test result for a decision. The test unit is an eligible user (2,275 users). Each mean has a deterministic 1,000-resample percentile bootstrap 95% confidence interval (CI); these describe uncertainty in this test population, not guaranteed production performance.

| Model | NDCG@10 (95% CI) | Precision@10 (95% CI) | Recall@10 (95% CI) | Catalog coverage | Category diversity |
| --- | --- | --- | --- | ---: | ---: |
| Popularity | 0.018441 [0.014806, 0.022454] | 0.004352 [0.003516, 0.005276] | 0.041758 [0.033846, 0.050989] | 0.61% | 0.9113 |
| Content | 0.026511 [0.021118, 0.033195] | 0.003912 [0.003208, 0.004747] | 0.036557 [0.029670, 0.044546] | 77.36% | 0.5722 |
| CF / selected hybrid | 0.354436 [0.339695, 0.369477] | 0.066110 [0.063648, 0.068529] | 0.549275 [0.529735, 0.567927] | 99.55% | 0.8717 |

Catalog coverage is the fraction of the 2,465 catalog items that appeared at least once across all test Top-10 lists. Category diversity is the mean within-list pairwise category-level-2 diversity; 1 means each item pair belongs to different categories. It is descriptive, not an optimization target.

Paired user-level comparison gives CF/selected hybrid minus popularity NDCG@10 = **0.335995**, bootstrap 95% CI **[0.322371, 0.349737]**. Because the entire interval is above zero, the tested CF advantage is robust within this held-out population. The hybrid-minus-CF difference is exactly zero because Phase 7 validation correctly selected CF weight 1.00.

| Distinct pre-test history items | Eligible users | Hybrid Precision@10 | Hybrid Recall@10 | Hybrid NDCG@10 |
| --- | ---: | ---: | ---: | ---: |
| 2–8 | 286 | 0.059441 | 0.517133 | 0.397143 |
| 9–12 | 1,520 | 0.062895 | 0.492237 | 0.304601 |
| 13–15 | 469 | 0.080597 | 0.753731 | 0.489905 |

The slice boundaries were defined from the pre-test history distribution, not optimized using test outcomes. Performance is strongest for the longest-history group, which is consistent with a collaborative model having more behavioral signal. The middle group is the largest, so its result has the greatest influence on the aggregate.

Executed details are saved in Git-ignored `data/processed/phase8_evaluation.json` and are generated by `src.robustness`. The audit also found and resolved an artifact reliability issue: earlier Joblib models were serialized from `__main__` and could not be loaded in a fresh process. They were regenerated using stable `src.*` imports with unchanged configuration and matching recorded metrics; fresh-process loading was then verified.

## Remaining evaluation work

Implement and evaluate cold-start fallback under this same protocol. Do not choose parameters using test results.
