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

## Phase 7 decisions

| Topic | Decision | Rationale |
| --- | --- | --- |
| Candidate fusion | Union the top 100 unseen candidates from CF and content | Bounds serving work while allowing either model to contribute an item. |
| Score normalization | Per-user max normalization, independently for CF and content | Their raw scores have different scales; normalization permits a meaningful weighted blend. |
| Weight search | Test CF weights 0.00–1.00 in 0.05 increments on validation only | Covers the complete blend range without leaking the test window into model selection. |
| Selection metric | Highest validation NDCG@10, then recall@10, precision@10, and greater CF weight | Optimizes ranked relevance with deterministic, documented ties. |
| Selected blend | CF 1.00, content 0.00 | This was the best validation result. A content-inclusive blend did not outperform pure CF. |
| Invalid/incomplete state | Fail on malformed interaction/catalog inputs or mismatched component catalogs; unknown users return no hybrid candidates | Prevents silently mixing incompatible artifacts; later cold-start handling remains explicit. |

## Phase 8 decisions

| Topic | Decision | Rationale |
| --- | --- | --- |
| Audit scope | Evaluate fixed Phase 4–7 artifacts; do not tune on test data | Separates evidence collection from model selection and preserves the holdout's integrity. |
| Uncertainty | 1,000 deterministic user-level bootstrap resamples with 95% percentile intervals | Reports stability of mean ranking metrics rather than a single point estimate alone. |
| Model comparison | Paired per-user NDCG@10 bootstrap differences | Models are evaluated on the same users, so paired differences are more informative than comparing separate intervals. |
| Robustness slices | 2–8, 9–12, and 13–15 distinct pre-test history items | Boundaries are derived from the pre-test history distribution, not selected for favorable test results. |
| Coverage/diversity | Report catalog coverage and category-level-2 intra-list diversity descriptively | Adds product exposure and list-variety context without pretending they measure relevance. |
| Artifact reliability | Regenerate Joblib artifacts through `src.*` module imports and load them in a fresh process | Prevents failures caused by serializing classes as `__main__`; configuration and reported metrics remain unchanged. |
| CF-only fast path | Skip content scoring when CF weight is 1.00 (and vice versa for 0.00) | Exact same output with lower serving work; the selected blend is CF-only. |

## Phase 9 decisions

| Topic | Decision | Rationale |
| --- | --- | --- |
| Cold-start policy | Use popularity for anonymous/unknown users and when personalized CF returns no candidates | Provides usable Top-N output when behavior-based personalization is impossible. |
| Personalized route | Use the validation-selected CF-only hybrid for known users with candidates | Preserves the strongest validated personalized model. |
| Seen-item filtering | Apply the same seen-item exclusion to both personalized and popularity routes | Prevents the fallback from violating the product requirement. |
| Response provenance | Return `personalized_cf` or `popularity_cold_start` with each result | Makes serving behavior auditable and lets the UI explain fallback output honestly. |
| Cold-start evaluation | Test routing, output count, determinism, and seen filtering; do not report relevance metrics | The dataset has no future labels for genuine new users, so relevance scoring would be fabricated. |

## Phase 10 decisions

| Topic | Decision | Rationale |
| --- | --- | --- |
| API design | One validated recommendation endpoint with an explicit `algorithm` value: `cf`, `content`, or `hybrid` | Lets the UI demonstrate each implemented recommender without duplicating response contracts. |
| Catalog hydration | Retrieve recommendation product details through parameterized, read-only MySQL queries | Recommendations are model item IDs; verified product data remains in the database and no SQL is built from user input. |
| Demo user | Validate but do not persist a new demo user | Demonstrates true cold start while avoiding fake interaction/user records in the governed dataset database. |
| Error handling | Structured JSON errors with 400/404/503/500 boundaries; log unexpected errors server-side only | Keeps API responses clear and prevents tracebacks or credentials leaking to the UI. |
| CORS | Allow only `localhost:5173` and `127.0.0.1:5173` local Vite origins by default | Enables local development without broadly opening the API to arbitrary browser origins. |
| UI scope | Simple single-page user selection, model comparison, route label, cards, loading and error states | Makes model behavior explainable during review without claiming content/hybrid is the top-performing choice. |
