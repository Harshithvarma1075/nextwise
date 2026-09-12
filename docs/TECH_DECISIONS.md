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
