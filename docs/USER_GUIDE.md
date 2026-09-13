# Reviewer and User Guide

## Purpose of the interface

The NxtWise Recommendation Studio interface is a reviewer-facing demonstration of the implemented recommender system. It is not a mockup: user selection, event activity, product details, and recommendations are requested from the Flask API. Products shown in recommendation cards come from the local MySQL catalog; rankings come from saved offline model artifacts.

The UI helps answer three questions during a demonstration:

1. What real behavior does this selected user have?
2. How do CF, content-based, and hybrid paths differ?
3. What happens when there is no behavioral history?

## Before you start

1. Ensure the MySQL service is running and the project-root `.env` has valid database credentials.
2. Start the Flask API at `http://127.0.0.1:5000`.
3. Start the Vite UI at `http://127.0.0.1:5173`.
4. Open the UI in a browser.

Exact commands are maintained in [README.md](../README.md).

## Screen layout

| Area | What it shows | Why it matters |
| --- | --- | --- |
| Choose a shopper | Searchable list of real dataset users | Lets the reviewer choose an actual behavioral profile. |
| Model selector | CF, content-based, hybrid | Supports transparent side-by-side method comparison. |
| Active shopper | User ID, age, gender, or the demo-user state | Makes the current context explicit. |
| Recent activity | Latest eight real events, products, categories, and UTC times | Provides observable history context without claiming causality. |
| Route label | `PERSONALIZED` or `COLD START` | Distinguishes behavior-driven recommendations from fallback output. |
| Product cards | Rank, name, category, description, price, gender, promotion state | Displays verified catalog information from MySQL. |

## Demonstrating a known dataset user

1. Select one user from the list, or type a numeric ID prefix and select **Find**.
2. Wait for the **Recent activity** panel to load. It displays newest events first.
3. Read the event labels literally. For example, `View` is a view; it is not a purchase. `AddToCart`, `ViewCart`, `StartCheckout`, and `Purchase` preserve their exact dataset meanings.
4. Select **Collaborative filtering** and press **Get recommendations**.
5. Confirm the green `PERSONALIZED` label and the `collaborative filter` route.
6. Switch to **Content-based** and repeat to show that it uses catalog similarity, not shared-user behavior.
7. Switch to **Hybrid (selected)** and repeat. Explain that validation selected CF-only because content did not improve NDCG@10 in this experiment.

### Suggested explanation

> “The activity panel shows the real event history supplied to the behavioral models. Our collaborative filter treats each validated interaction type as a binary signal, then recommends products associated with the user’s interacted items across similar users. The product cards are real catalog records, not generated descriptions.”

## Demonstrating cold start

1. Select **Create new demo user**.
2. Confirm that the active shopper reads **New demo user** and the activity panel states that no history exists.
3. Select any algorithm and press **Get recommendations**.
4. Confirm the orange `COLD START` and `popularity cold start` labels.

### Important note

The demo user is temporary. It is not inserted into MySQL, does not create interactions, and does not change the model. This is intentional: creating fake history to force personalized output would make the demonstration misleading.

## Interpreting route labels

| Route | Meaning |
| --- | --- |
| `collaborative_filter` | The CF model returned personalized candidates. |
| `content_based` | The TF-IDF content model returned personalized candidates. |
| `personalized_cf` | The selected hybrid route; validation chose CF weight 1.00. |
| `popularity_cold_start` | No usable personalized profile/candidates existed, so global popularity was returned. |

## Error states and recovery

| UI or API message | Likely cause | What to check |
| --- | --- | --- |
| “Cannot reach the API” | Flask is not running, wrong API address, or blocked local connection | Start Flask on port 5000 and open UI at `127.0.0.1:5173`. |
| “Catalog data is temporarily unavailable” | MySQL is not running or `.env` is invalid | Check MySQL service, database name, account, password, and loaded tables. |
| “Recommendation model is temporarily unavailable” | Required Joblib/JSON artifact is absent or incompatible | Regenerate the relevant saved model artifact from its module; do not create placeholder files. |
| “No dataset user exists” | Search/query used an ID not present in the database | Choose an ID from the user list or use the demo-user cold-start flow. |
| Empty personalized list | No candidates remain after filtering | The router falls back to popularity for the hybrid/cold-start route. |

## What not to claim

- Do not call Precision@10, Recall@10, or NDCG@10 “accuracy.”
- Do not say every displayed activity event directly caused every recommendation.
- Do not say cold-start popularity results are personalized.
- Do not say the hybrid outperformed CF; validation selected CF-only.
- Do not say the synthetic-dataset metrics guarantee production business impact.
