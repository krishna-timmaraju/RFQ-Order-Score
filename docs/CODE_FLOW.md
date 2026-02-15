# RFQ-Order-Score — Code Flow Diagram

## Source file summaries (4–5 words)

| File | Summary |
|------|--------|
| `config.py` | Loads env; DB & API config |
| `app.py` | Flask app, CORS, /ui and /api |
| `api/routes/rfqs.py` | RFQ API: scored list, stats, health |
| `static/index.html` | UI: table of RFQs and scores |
| `train_model.py` | Train GBM, save lead-scoring model |
| `score_new_rfq.py` | Score new RFQs, write to DB |

---

## Code flow diagram

```mermaid
flowchart TB
    subgraph env["Environment"]
        dotenv[".env"]
    end

    subgraph config["Configuration"]
        config_py["config.py\nLoads env; DB & API config"]
    end

    subgraph web["Web layer"]
        app_py["app.py\nFlask app, CORS, /ui and /api"]
        rfqs_py["api/routes/rfqs.py\nRFQ API: scored list, stats, health"]
        index_html["static/index.html\nUI: table of RFQs and scores"]
    end

    subgraph batch["Batch / offline"]
        train["train_model.py\nTrain GBM, save lead-scoring model"]
        score_new["score_new_rfq.py\nScore new RFQs, write to DB"]
    end

    subgraph data["Data"]
        csv["training_data.csv"]
        pkl["lead_scoring_model.pkl"]
        db[(PostgreSQL\nrfqs, rfq_lead_scores)]
    end

    dotenv --> config_py
    config_py --> app_py
    config_py --> rfqs_py
    config_py --> score_new

    app_py --> rfqs_py
    app_py --> index_html

    index_html -->|"GET /api/rfqs/scored\nGET /api/rfqs/stats"| rfqs_py
    rfqs_py --> db

    csv --> train
    train --> pkl
    pkl --> score_new
    score_new --> db
```

---

## Request flow (runtime)

```mermaid
sequenceDiagram
    participant Browser
    participant app as app.py
    participant rfqs as api/routes/rfqs.py
    participant config as config.py
    participant DB as PostgreSQL

    Browser->>app: GET /ui
    app->>Browser: index.html

    Browser->>app: GET /api/rfqs/scored?limit=10
    app->>rfqs: get_scored_rfqs()
    rfqs->>config: get_db_config()
    rfqs->>DB: SELECT rfqs + lead_scores
    DB-->>rfqs: rows
    rfqs-->>app: JSON { rfqs, count }
    app-->>Browser: JSON

    Browser->>app: GET /api/rfqs/stats
    app->>rfqs: get_rfq_stats()
    rfqs->>DB: aggregate query
    DB-->>rfqs: stats
    rfqs-->>Browser: JSON { stats }
```

---

## Batch flow (model training & scoring)

```mermaid
flowchart LR
    A["training_data.csv"] --> B["train_model.py"]
    B --> C["lead_scoring_model.pkl"]
    C --> D["score_new_rfq.py"]
    D --> E[(PostgreSQL\nrfq_lead_scores)]
```

- **train_model.py**: Reads CSV → trains GradientBoostingClassifier → saves model + metadata to `.pkl`.
- **score_new_rfq.py**: Loads `.pkl` → queries DB for unscored RFQs → predicts conversion probability → inserts into `rfq_lead_scores`.
