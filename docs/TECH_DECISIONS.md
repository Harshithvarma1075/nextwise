# Technical decisions

| Topic | Decision | Status / rationale |
| --- | --- | --- |
| Dataset | H&M Personalized Fashion Recommendations | Required project reset; inspect before use. |
| Working size | Evidence-based reproducible subset if needed | Must be chosen after Phase 1 file and feasibility inspection. |
| Interaction signal | Purchase transactions | Exact aggregation and duplicate policy pending data inspection. |
| Collaborative filtering | Item-based CF using sparse matrices | Transparent, practical candidate generation. |
| Content filtering | TF-IDF + cosine similarity over verified product metadata | Final fields pending actual article schema. |
| Hybrid | Normalized weighted CF/content scores | Validate multiple weights; never tune on test data. |
| Evaluation | Temporal train/validation/test split | Prevents future leakage; precise eligibility rules pending data. |
| Cold start | Popularity fallback; metadata preference path if supported | Pending verified metadata/API design. |
| Images | Optional presentation enhancement | Use only if local mapping to article IDs is verified. |

No data-dependent values, schemas, model weights, or evaluation results have been selected.
