# Final Project Report — NxtWise Recommendation Studio

## 1. Executive summary

NxtWise Recommendation Studio is an end-to-end, explainable product recommendation application built on the Amazon Retail Demo Store synthetic e-commerce dataset. The system processes a frozen event log and product catalog, loads validated application data into MySQL, trains several recommendation approaches offline, and serves ranked product recommendations through a Flask API and React interface.

The central product question is: **given a shopper’s prior behavior, which unseen products should appear in their next Top-10 list?** The system also addresses the practical case where no behavioral history exists. Rather than incorrectly presenting generic recommendations as personal, it explicitly labels a popularity fallback as cold start.

The final evaluation selected item-based collaborative filtering as the best personalized method. Its held-out test NDCG@10 was **0.354436**, compared with **0.018441** for global popularity and **0.026511** for the catalog-text content model. A validation-only hybrid search selected a CF weight of 1.00, so the deployed personalized hybrid route intentionally produces CF results. This is an evidence-based decision, not a claim that every hybrid must use all available components.

## 2. Business problem and success criteria

An e-commerce catalog is too large for a shopper to browse efficiently. A recommendation system should reduce that search cost by ranking items that are plausibly relevant to the shopper, while avoiding products they have already interacted with. For reviewability, the project additionally requires:

- reproducible raw-to-processed data preparation;
- a transparent baseline and multiple personalized methods;
- a leakage-safe evaluation design;
- a usable application interface rather than only notebooks or offline scripts;
- honest handling of new users who have no behavioral history;
- API and UI behavior that can be demonstrated and tested.

The project does not claim that an offline metric is a guaranteed production conversion lift. The test results establish comparative ranking quality for this synthetic held-out event population.

## 3. Data scope and governance

The only permitted source is the Amazon Retail Demo Store synthetic e-commerce dataset. The frozen raw files are `interactions.csv`, `items.csv`, and `users.csv`. They contain 675,004 interactions, 2,465 catalog products, and 6,000 users.

The interaction events are `View`, `AddToCart`, `ViewCart`, `StartCheckout`, and `Purchase`. The source includes real human-readable product names, descriptions, two category levels, product gender, price, promotion status, and discount information. The complete field-level contract and validation rules are documented in [DATA_CONTRACT.md](DATA_CONTRACT.md).

Raw files are not edited. The preprocessing pipeline rejects missing required columns, invalid identifiers, invalid event values, invalid timestamps, and cross-file references that would create orphan interactions. It retains non-identical repeated events because repeat behavior is a factual property of the source data. It does not create arbitrary interaction-strength weights during preprocessing.

## 4. System design

```text
Frozen CSV files
     │
     ▼
Validation and reproducible preprocessing
     ├─────────────────────────► Processed CSV files
     │                                  │
     │                                  ├──────► MySQL users / products / interactions
     │                                  │               │
     ▼                                  │               ▼
Offline model training                  │       Flask catalog and activity reads
Popularity · CF · TF-IDF content · hybrid            │
     │                                                │
     ▼                                                ▼
Saved local model artifacts ───────────────► Recommendation service ─────► React UI
                                                   │                         │
                                                   ├─ known user: CF         ├─ model comparison
                                                   └─ new user: popularity   └─ recent activity
```

MySQL stores application data only. Sparse matrices, similarity structures, TF-IDF vectors, and Joblib artifacts remain on disk. This keeps the relational database focused on catalog/user/event queries and avoids storing large ML structures in a transactional application database.

## 5. Recommendation methods

### 5.1 Popularity baseline

The popularity baseline ranks products by the number of distinct training users who interacted with each item. It is intentionally simple, deterministic, and free of invented event weights. It serves two purposes: a benchmark for personalized methods and the fallback for anonymous or unknown users.

### 5.2 Item-based collaborative filtering

The selected personalized model represents a user-item interaction as binary: the user interacted with the item at least once in the training window. It computes cosine similarity between sparse item interaction vectors. At recommendation time, it aggregates each unseen candidate’s similarity to the user’s historical items. Only the top 100 positive neighbors per item are stored, keeping candidate generation bounded.

This model is explainable at the method level: it recommends items because users who interacted with the shopper’s historical items also interacted with those candidates. The application shows the actual recent event history to make the source behavior visible, but it does not falsely claim that one displayed interaction caused one specific recommendation.

### 5.3 Content-based filtering

The content model builds TF-IDF product documents from verified product name, description, category level 1, category level 2, and catalog gender. Category and gender values are field-prefixed so they remain distinguishable from normal description words. A user profile is the normalized sum of vectors for historically interacted products.

Price and promotion were intentionally excluded from this text representation because their recommendation value was not established by an experiment. The content model remains available in the UI for comparison, but its measured ranking performance was weaker than CF.

### 5.4 Hybrid and cold start

The hybrid unions the top 100 CF and content candidates, independently max-normalizes each score source per user, and searches CF weights from 0.00 to 1.00 in 0.05 increments using validation data only. The selected weight was CF 1.00 / content 0.00.

For a user with no usable personalized candidates, the cold-start router returns popularity recommendations with a `popularity_cold_start` route label. That label is surfaced by the API and UI so generic recommendations are never described as personalized.

## 6. Evaluation methodology

The event log is split globally by time, rather than randomly, to prevent future behavior from being used to train a past recommendation. The windows are:

| Window | Events | Timestamp rule |
| --- | ---: | --- |
| Train | 472,504 | `timestamp_unix <= 1767539907` |
| Validation | 101,250 | `1767539907 < timestamp_unix <= 1768500029` |
| Test | 101,250 | `timestamp_unix > 1768500029` |

An eligible evaluation user has history before the holdout period and at least one unseen product interaction in that holdout. Previously seen items are excluded from both candidate recommendations and that user’s holdout relevance set. This matches the product rule that already seen items should not be recommended and avoids penalizing the model for correctly filtering them.

The metrics are Top-N ranking metrics, not conventional binary classification accuracy:

- **Precision@10**: fraction of the ten recommended products that appeared in the user’s later unseen interactions.
- **Recall@10**: fraction of the user’s later unseen relevant products recovered in the Top-10.
- **NDCG@10**: ranking quality that gives greater credit when relevant products appear closer to the top of the list.

The full methodology, metric values, bootstrap confidence intervals, coverage, diversity, and history-slice analysis are in [EVALUATION.md](EVALUATION.md).

## 7. Results and interpretation

| Model | Test Precision@10 | Test Recall@10 | Test NDCG@10 |
| --- | ---: | ---: | ---: |
| Popularity | 0.004352 | 0.041758 | 0.018441 |
| Content-based | 0.003912 | 0.036557 | 0.026511 |
| Collaborative filtering | **0.066110** | **0.549275** | **0.354436** |
| Validation-selected hybrid | **0.066110** | **0.549275** | **0.354436** |

The CF / selected-hybrid NDCG@10 bootstrap 95% interval is **[0.339695, 0.369477]**. The paired NDCG@10 difference between selected hybrid and popularity is **0.335995**, with a 95% bootstrap interval of **[0.322371, 0.349737]**. Since that interval stays above zero in this held-out population, the CF improvement is robust for this test setting.

Precision should not be described as model accuracy. In a Top-10 recommender, a user can have several future relevant products. A model can recover a substantial portion of those products while making only ten recommendations, which is why recall and ranked position are important. The final CF model recovers about 54.9% of eligible users’ later unseen relevant items in their Top-10 lists on average.

## 8. Application behavior

The application supports three reviewer-visible algorithm selections:

1. **Collaborative filtering** — returns the sparse item-based CF results for a known dataset user.
2. **Content-based** — returns TF-IDF catalog-similarity results for a known dataset user.
3. **Hybrid** — returns the validation-selected hybrid, which currently routes to personalized CF for known users.

Selecting a dataset user also loads the latest eight real events from MySQL. Each row displays event type, product, category, and UTC timestamp. A temporary demo user is intentionally not persisted; that flow demonstrates the popularity cold-start route without contaminating the database or re-training artifacts.

All API responses use a structured safe error shape. The API validates algorithm names, user IDs, limits, activity limits, demo-user fields, and search input. Catalog queries are parameterized. Product recommendation IDs are hydrated from the verified MySQL product catalog before being returned to the UI.

## 9. Quality assurance and reproducibility

The project contains unit tests for preprocessing, database loading, popularity, CF, content filtering, hybrid selection, robustness evaluation, cold start, API contracts, and live API integration. The final live integration test uses the actual local MySQL catalog and saved artifacts; it checks health, real users, all three algorithms, product hydration, activity, cold start, and expected invalid-request behavior.

The final verified state is:

| Check | Result |
| --- | --- |
| Python test suite with live integration enabled | 41 passed |
| Source compilation | Passed |
| Flask real API route checks | Passed |
| React production build | Passed |
| `npm audit --omit=dev` | 0 vulnerabilities |
| Fresh-process model/router artifact loading | Passed |

The detailed execution record and known limitations are in [QA_REPORT.md](QA_REPORT.md).

## 10. Limitations and responsible claims

- The dataset is synthetic; offline performance does not prove real-world revenue or conversion uplift.
- The cold-start fallback has no genuine-new-user relevance metric because the frozen data has no later interactions for a newly created user. A proxy metric would be fabricated, so none is reported.
- Content features are limited to verified catalog fields. The model does not invent product attributes or semantic meanings.
- CF depends on interaction history. The popularity route ensures availability for cold start but does not make recommendations personal.
- The UI activity panel shows real recorded behavioral context. It is not a causal explanation for one particular ranked item.

## 11. Review demonstration script

1. Start MySQL, Flask, and the React UI using the commands in [README.md](../README.md).
2. Select a dataset user and point out the visible recent history.
3. Run CF, content, and hybrid sequentially. Explain that hybrid is shown for comparison and selected CF-only based on validation.
4. Point out the personalized route label and product catalog details.
5. Create a new demo user and run recommendations again. Point out the cold-start route label and explain why it uses popularity.
6. Reference the NDCG@10 comparison and bootstrap interval from the evaluation report when discussing model choice.

## 12. Delivery checklist

- [x] Frozen data source and reproducible preprocessing
- [x] Validated MySQL load and catalog integrity checks
- [x] Popularity, CF, content, hybrid, and cold-start implementations
- [x] Leakage-safe temporal evaluation and robustness audit
- [x] Flask API and React reviewer UI
- [x] Real activity visibility and safe error handling
- [x] Unit, contract, live integration, build, audit, and artifact-load verification
- [x] Professional documentation package
