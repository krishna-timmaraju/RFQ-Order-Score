# RFQ Scoring Engine

A machine-learning-powered RFQ scoring Engine for RFQs (Request for Quotation) in a B2B marketplace. Given a published RFQ and the buyer's profile, the model predicts the probability that the RFQ will convert to an order and exposes those scores through a REST API and a lightweight web dashboard.

---

## How it works

1. **Train** — `train_model.py` reads historical RFQ conversion data from `training_data.csv`, trains a Gradient Boosting classifier on three buyer/RFQ signals, and saves the model to `lead_scoring_model.pkl`.
2. **Score** — `score_new_rfq.py` loads the saved model, fetches unscored published RFQs from PostgreSQL, predicts a conversion probability for each one, and writes the scores back to the `rfq_lead_scores` table.
3. **Serve** — `app.py` starts a Flask REST API that reads from the database and returns scored RFQs to consumers.
4. **View** — The web UI at `/ui` displays a sortable table of scored RFQs and allows new RFQs to be created.

### Feature set

| Feature | Description |
|---|---|
| `buyer_brank` | Buyer's business rank on the platform (1 = highest, 5 = lowest) |
| `category_match` | Similarity between the RFQ category and the buyer's primary category (`1.0` / `0.6` / `0.2`) |
| `budget_specified` | Whether the RFQ includes a budget range (`1` = yes, `0` = no) |

---

## Project structure

```
RFQ-Order-Score/
├── app.py                        # Flask application entry point
├── config.py                     # DB & API configuration (reads from .env)
├── train_model.py                # Model training script
├── score_new_rfq.py              # Batch scoring script (writes to DB)
├── generate_training_data.py     # Synthetic data generator (pipeline testing only)
├── training_data.csv             # Historical RFQ conversion data (training input)
├── training_data_pipeline_test.csv  # Synthetic data for pipeline checks
├── requirements.txt
├── api/
│   └── routes/
│       └── rfqs.py               # REST API route handlers
├── static/
│   └── index.html                # Web dashboard (single-page)
└── docs/
    └── CODE_FLOW.md              # Architecture & sequence diagrams
```

---

## Prerequisites

- Python 3.10+
- PostgreSQL with a `marketplace_db` database containing `rfqs`, `businesses`, and `rfq_lead_scores` tables

---

## Setup

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/<your-org>/RFQ-Order-Score.git
cd RFQ-Order-Score
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

Create a `.env` file in the project root (never commit this file):

```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=marketplace_db

API_HOST=0.0.0.0
API_PORT=5555
DEBUG=True
```

### 3. Train the model

Place your historical conversion data in `training_data.csv` with columns:

```
buyer_brank, category_match, budget_specified, converted
```

Then run:

```bash
python train_model.py
```

This produces `lead_scoring_model.pkl` and prints AUC scores and feature importances to the console.

> **Pipeline testing only** — If you don't have real training data yet, `generate_training_data.py` creates a synthetic dataset with random outcomes. The resulting model will have low predictive power and should not be used for production scoring.

### 4. Score new RFQs

```bash
python score_new_rfq.py
```

This fetches up to 100 unscored published RFQs from the database, scores them, and writes results to `rfq_lead_scores`.

### 5. Start the API server

```bash
python app.py
```

The server starts on `http://localhost:5555` by default.

---

## API reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Database connectivity check |
| `GET` | `/api/rfqs/scored` | List scored RFQs, sorted by score (supports `?limit=N`) |
| `GET` | `/api/rfqs/stats` | Aggregate stats (total RFQs, total scored) |
| `GET` | `/api/rfqs/score-distribution` | Score distribution across all RFQs |
| `GET` | `/api/rfqs/<rfq_id>` | Full details and score for a single RFQ |
| `POST` | `/api/rfqs` | Create a new RFQ |

### Example response — `GET /api/rfqs/scored?limit=3`

```json
{
  "success": true,
  "count": 3,
  "rfqs": [
    {
      "rfq_id": "RFQ-001",
      "title": "Office Supplies Procurement",
      "category": "Supplies",
      "buyer_name": "Acme Corp",
      "buyer_id": "BIZ001",
      "conversion_probability": 0.821,
      "status": "published"
    }
  ]
}
```

---

## Web dashboard

Open `http://localhost:5555/ui` in your browser.

- **View RFQs tab** — Paginated table of scored RFQs with predicted conversion probability. Click any RFQ ID to open a detail modal.
- **Create RFQ tab** — Form to submit a new RFQ directly to the API.

---

## Tech stack

| Layer | Technology |
|---|---|
| ML model | scikit-learn `GradientBoostingClassifier` |
| Data handling | pandas |
| API server | Flask + Flask-CORS |
| Database | PostgreSQL (psycopg2) |
| Frontend | Vanilla HTML / CSS / JavaScript |
| Config | python-dotenv |

---
