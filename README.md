# Amazon Retail Demo Store hybrid recommender

An end-to-end, explainable product recommendation system for the NxtWise hiring assessment. The system will combine item-based collaborative filtering with TF-IDF content similarity using the frozen Amazon Retail Demo Store synthetic e-commerce dataset.

## Status

**Phase 10 complete — Flask API and React UI.** The application serves saved CF, content, and hybrid model results through a validated API, hydrates results from MySQL, and provides a simple interactive demonstration including cold start.

## Frozen dataset

`data/raw/amazon_retail_demo/` contains:

- `interactions.csv`
- `items.csv`
- `users.csv`

This is the only permitted dataset. Raw files are Git-ignored and must never be edited.

## Planned stack

Python, Flask, MySQL, Pandas, NumPy, SciPy, scikit-learn, Joblib, Pytest, React, and Vite.

## Target architecture

```text
Raw CSVs → validation/preprocessing → processed users, items, interactions
                                   ├→ sparse item-based CF
                                   └→ TF-IDF content model
                                         ↓
                            normalized hybrid ranker → Top-N

React → Flask REST API → recommendation service → MySQL + model artifacts
```

## Layout

```text
backend/    Flask application, MySQL repository, API service, and backend tests
src/        Offline preprocessing, models, training, evaluation, and cold-start routing
data/       Git-ignored raw and generated data
docs/       Project source of truth
frontend/   React/Vite recommendation demonstration UI
models/     Git-ignored generated model artifacts
```

## Next phase

## Run locally

1. Ensure MySQL is running and `.env` contains the already configured database credentials.
2. Start the API from the project root:

   ```powershell
   C:\Users\Harshith Varma\AppData\Local\Python\pythoncore-3.14-64\python.exe -m flask --app backend.run run --host 127.0.0.1 --port 5000
   ```

3. In a second terminal, start the UI:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

Open `http://127.0.0.1:5173`. Select a dataset user and choose CF, content, or hybrid to compare outputs. “Create new demo user” is intentionally not saved to MySQL; it demonstrates the popularity cold-start route without modifying the evaluation dataset.

## Next phase

The next development phase is Phase 11: strengthen API/UI integration tests and operational robustness.

## Disclosure

This project uses the Amazon Retail Demo Store synthetic e-commerce dataset and AI coding assistance. Final documentation will disclose all libraries and external resources used.
