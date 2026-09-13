# Delivery Checklist

## Submission state

NxtWise Recommendation Studio is ready for local review. The submitted version includes the frozen Amazon Retail Demo Store dataset pipeline, trained saved artifacts, MySQL-backed Flask API, React demonstration UI, activity visibility, cold-start behavior, test evidence, and professional documentation.

## What to show a reviewer

| Step | Demonstrate | Evidence to point to |
| --- | --- | --- |
| 1 | Open the React UI after starting MySQL, Flask, and Vite. | [README setup](../README.md#setup) |
| 2 | Select a real dataset user and show their latest recorded activity. | [Reviewer guide](USER_GUIDE.md#demonstrating-a-known-dataset-user) |
| 3 | Run CF, then content, then hybrid for the same user. | Route labels and product cards in the UI; [API contract](API_CONTRACT.md) |
| 4 | Explain that hybrid is intentionally CF-only because validation chose CF weight 1.00. | [Evaluation](EVALUATION.md) and [technical decisions](TECH_DECISIONS.md) |
| 5 | Create a demo user and show the labeled popularity cold-start result. | [Reviewer guide](USER_GUIDE.md#demonstrating-cold-start) |
| 6 | Run the automated verification commands if time permits. | [QA report](QA_REPORT.md) |

## Required local prerequisites

- Python 3.14 environment with the dependencies in `requirements.txt`.
- Node.js/npm for the React/Vite UI.
- Running MySQL server with the project database populated from the processed data.
- A valid project-root `.env` with non-placeholder `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, `MYSQL_USER`, and `MYSQL_PASSWORD` values.
- Saved artifacts in `models/`; do not substitute empty or hand-created artifact files.

## Final verification evidence

The final verification was executed with `RUN_LIVE_API_TESTS=1` and produced **41 passed** backend tests. It included a real, non-mocked Flask/MySQL/artifact integration test. Backend compilation passed; the Vite production build passed; `npm audit --omit=dev` reported zero vulnerabilities; fresh-process artifact loading passed; and `git diff --check` passed.

The live test intentionally validates health, real user lookup, recent activity, all three algorithm options, hydrated product records, cold start, invalid inputs, and missing-user responses. It is opt-in because it requires the reviewer’s own configured local MySQL service and saved model files.

## Important claims to make accurately

- The selected personalized model is item-based collaborative filtering. The UI’s selected hybrid route uses the same CF output because validation chose a CF weight of 1.00.
- Held-out test NDCG@10 is **0.354436** for CF, versus **0.018441** for popularity and **0.026511** for content. These are ranking metrics, not percentage accuracy.
- Product/activity records are from the synthetic dataset; descriptions and event types are not invented by the application.
- The activity panel provides visible behavioral context. It does not prove one event was the direct cause of one recommended product.
- Cold-start recommendations are global popularity results and are labeled non-personalized.

## Do not do before submission

- Do not retune model weights, neighbors, feature fields, or temporal split boundaries on the held-out test results.
- Do not change the raw data or replace the frozen dataset.
- Do not insert fake demo users or interaction history into MySQL.
- Do not call NDCG, precision, or recall “accuracy.”
- Do not suppress the recorded NumPy/Joblib compatibility warning without first testing a dependency upgrade and regenerated artifacts.

## Reference documents

- [README](../README.md): installation, startup, usage, and commands.
- [Final Project Report](FINAL_PROJECT_REPORT.md): problem, design, models, results, and limitations.
- [Reviewer and User Guide](USER_GUIDE.md): a concise demonstration script and error recovery.
- [Quality Assurance Report](QA_REPORT.md): executed checks, defects found, and warning status.
- [Evaluation Report](EVALUATION.md): temporal split, metrics, robustness analysis, and model selection evidence.
