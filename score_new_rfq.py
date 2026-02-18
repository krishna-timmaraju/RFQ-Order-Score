import pandas as pd
import pickle
import psycopg2
from datetime import datetime

# ============================================
# 1. LOAD MODEL
# ============================================
print("Loading model...")
with open('lead_scoring_model.pkl', 'rb') as f:
    model_package = pickle.load(f)

model = model_package['model']
feature_names = model_package['features']
print(f"Loaded model version: {model_package['version']}")
print(f"Test AUC: {model_package['test_auc']:.3f}")

# ============================================
# 2. CONNECT TO DATABASE
# ============================================
conn = psycopg2.connect(
    host="localhost",
    user="postgres",
    password="postgres",
    dbname="marketplace_db"
)
cursor = conn.cursor()

# ============================================
# 3. GET NEW RFQs TO SCORE
# ============================================
query = """
    SELECT 
        r.rfq_id,
        b.brank AS buyer_brank,
        CASE 
            WHEN r.category = b.primary_category THEN 1.0
            WHEN r.category LIKE CONCAT('%', SUBSTRING(b.primary_category, 1, 5), '%') THEN 0.6
            ELSE 0.2
        END AS category_match,
        (r.budget_min IS NOT NULL AND r.budget_max IS NOT NULL) AS budget_specified
    FROM rfqs r
    JOIN businesses b ON r.buyer_business_id = b.business_id
    LEFT JOIN rfq_lead_scores s ON r.rfq_id = s.rfq_id
    WHERE r.status = 'published'
      AND s.rfq_id IS NULL  -- Not yet scored
    ORDER BY r.created_at DESC
    LIMIT 100
"""

df = pd.read_sql(query, conn)

if len(df) == 0:
    print("No new RFQs to score.")
    conn.close()
    exit()

print(f"\nFound {len(df)} new RFQs to score")

# ============================================
# 4. PREPARE FEATURES
# ============================================
X = df[feature_names].copy()
X['budget_specified'] = X['budget_specified'].astype(int)

# ============================================
# 5. PREDICT
# ============================================
print("Making predictions...")
probabilities = model.predict_proba(X)[:, 1]

df['conversion_probability'] = probabilities
df['lead_score'] = (probabilities * 100).astype(int)

# ============================================
# 6. SAVE PREDICTIONS TO DATABASE
# ============================================
print("\nSaving predictions to database...")

insert_query = """
    INSERT INTO rfq_lead_scores (rfq_id, lead_score, conversion_probability, model_version)
    VALUES (%s, %s, %s, %s)
"""

for _, row in df.iterrows():
    cursor.execute(insert_query, (
        row['rfq_id'],
        int(row['lead_score']),
        float(row['conversion_probability']),
        model_package['version']
    ))

conn.commit()
print(f"✓ Saved {len(df)} predictions")

# ============================================
# 7. SHOW SAMPLE PREDICTIONS
# ============================================
print("\nSample predictions:")
print(df[['rfq_id', 'buyer_brank', 'category_match', 'lead_score']].head(10))

cursor.close()
conn.close()

print("\n✓ Done! Predictions are now in rfq_lead_scores table")
print("Next: Query the table in your API to show scores to sellers")