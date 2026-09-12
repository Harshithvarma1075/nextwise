# Technical decisions

| Topic | Decision | Status / rationale |
| --- | --- | --- |
| Dataset | Amazon Retail Demo Store synthetic e-commerce dataset | Frozen by project owner. |
| Interaction source | `interactions.csv` | Actual event semantics and aggregation rules await Phase 1 inspection. |
| Collaborative method | Item-based CF with sparse matrices | Explainable and practical for user-item interaction data. |
| Content method | TF-IDF + cosine similarity | Candidate catalog fields: name, description, category levels, gender; final selection awaits data-quality inspection. |
| Price/promotion | Excluded from initial TF-IDF representation | May be evaluated later as structured signals only if useful. |
| Hybrid method | Normalized weighted CF/content score blend | Validation—not test—will select the weight. |
| Baseline/cold start | Popularity recommendation | Exact definition awaits event distribution inspection. |
| Images | Image-free cards by default | No image file/mapping has been verified. |
| Database | MySQL for application records only | Artifacts and sparse matrices remain on disk. |

No event weights, subset rule, model parameters, or metrics have been chosen.

## Phase 1 evidence updates

| Topic | Decision | Evidence |
| --- | --- | --- |
| Working subset | Use all 675,004 raw interactions | 42.5 MB input, 6,000 users, 2,465 items, and no referential gaps make sampling unnecessary. |
| Interaction event semantics | Preserve all five verified event types until Phase 2 aggregation | `View`, `AddToCart`, `ViewCart`, `StartCheckout`, and `Purchase` exist; weights are not dataset facts. |
| Content fields | Use catalog text/category fields as the primary later content candidates | Names/descriptions are complete; category levels and gender are complete. |
| Discount | Treat as categorical `Yes`/`No` | Inspection disproved the prior numeric-field assumption. |
| Promotion | Treat missing values as unknown pending documented normalization | 1,856 of 2,465 values are missing; inferring false would be an unsupported assumption. |

## Phase 2 decisions

| Topic | Decision | Rationale |
| --- | --- | --- |
| Processed event log | Retain every validated event, with UTC timestamp and boolean discount flag | Maintains auditability and defers model strength choices. |
| User-item aggregate | One row per user-item with event-specific counts and temporal bounds | Preserves repeated behavior without treating all events as equal preference. |
| `PROMOTED` normalization | `true` or `unknown`; no inferred false state | Source lacks explicit false values for 1,856 products. |
| Cross-file violations | Fail preprocessing rather than silently remove interaction rows | Prevents hidden referential-data loss. |
| Artifact publication | Atomic CSV writes | Protects against partially written processed files after Windows output-lock failure. |

## Phase 3 decisions

| Topic | Decision | Rationale |
| --- | --- | --- |
| Persisted tables | `users`, `products`, `interactions` | Directly supports API product/user lookup and recommendation history without storing ML artifacts. |
| Database engine | MySQL InnoDB with `utf8mb4` | Supports transactions, foreign keys, and catalog text safely. |
| Event identity | Unique `(user_id, item_id, event_type, timestamp_unix)` | Matches Phase 2's validated raw-event identity and prevents duplicate loads. |
| Load strategy | Parameterized batched upserts in FK order inside one transaction | Safe reruns, bounded memory, and complete rollback on failure. |
| Production integrity | DB checks + foreign keys plus preprocessing validation | Database constraints are a final safety net, not a substitute for pipeline validation. |
| CSV boolean conversion | Convert processed `True`/`False` text to MySQL `1`/`0` in the loader | Prevents MySQL strict-mode type error while preserving the processed-data contract. |

## Phase 4 decisions

| Topic | Decision | Rationale |
| --- | --- | --- |
| Popularity signal | Unique users who interacted with an item in the training window | A transparent global baseline that prevents repeated views from a small set of users dominating rank. |
| Rank tie-breaker | Lexicographic `item_id` | Deterministic output when item counts match. |
| Split | Global temporal 70% train / 15% validation / 15% test | Earlier events train the model; later windows remain unseen for evaluation. |
| Test refit | Fit final baseline on train + validation before held-out test | Uses all data available before the test window without test leakage. |
| Seen-item evaluation | Remove historical items from both recommendations and each user’s holdout relevance set | Avoids penalizing a model for intentionally enforcing seen-item filtering. |

## Phase 5 decisions

| Topic | Decision | Rationale |
| --- | --- | --- |
| CF signal | Binary user-item interaction incidence | Uses verified interaction history without inventing relative event weights before experimentation. |
| Similarity | Item-item cosine similarity | Transparent: items are related when the same users interacted with both. |
| Neighbor storage | Keep top 100 positive-scoring neighbors per item | Provides bounded, efficient online candidate generation without storing all pairwise scores. |
| Similarity computation | Sparse normalized item matrix multiplication | Replaced slow brute-force nearest-neighbor fitting; maintains cosine semantics while completing feasibly on the full dataset. |
| Unknown/empty user | Return no CF candidates | Lets the planned popularity cold-start layer handle users without history rather than fabricating personalized output. |

## Phase 6 decisions

| Topic | Decision | Rationale |
| --- | --- | --- |
| Content inputs | Product name, description, category level 1, category level 2, and catalog gender | These fields are complete, human-readable, and verified in the frozen item catalog. |
| Field encoding | Prefix category and catalog-gender tokens in each product document | Keeps structured values distinguishable from ordinary words while retaining interpretable content. |
| Content representation | TF-IDF with English stop words, unigrams/bigrams, sublinear term frequency, and at most 25,000 features | A compact, reproducible text representation that supports cosine similarity without external embeddings. |
| User content profile | L2-normalized sum of historical product vectors | Represents the catalog content a user has actually interacted with, without inventing event weights. |
| Excluded fields | Price and promotion | Neither has been empirically assessed as a helpful structured recommendation signal; promotion is also often unknown. |
| Evaluation outcome | Retain content model as an explainable candidate source, not as a CF replacement | Its test NDCG@10 (0.026511) exceeded popularity but was much lower than CF (0.354436) under the identical protocol. |
