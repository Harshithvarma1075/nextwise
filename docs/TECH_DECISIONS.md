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
