import sys
from pathlib import Path

import pandas as pd
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score, classification_report

# ============================================
# 1. LOAD DATA
# ============================================
DATA_FILE = Path('training_data.csv')
if not DATA_FILE.exists():
    print("Error: training_data.csv not found.")
    print(f"Please add '{DATA_FILE.resolve()}' and run again.")
    sys.exit(1)

print("Loading training data...")
df = pd.read_csv(DATA_FILE)

# Ensure boolean-like columns are numeric (handle t/f, True/False, 0/1)
def to_binary(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip().str.lower()
    return s.isin(('t', 'true', '1', 'yes', 'y')).astype(int)

for col in ('budget_specified', 'converted'):
    if col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            df[col] = to_binary(df[col])
        else:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

print(f"Total samples: {len(df)}")
print(f"Conversion rate: {df['converted'].mean():.1%}")
print(f"\nFeature distributions:")
print(df.describe())

# ============================================
# 2. PREPARE FEATURES
# ============================================
X = df[['buyer_brank', 'category_match', 'budget_specified']]
y = df['converted']

# Convert boolean to int:
X['budget_specified'] = X['budget_specified'].astype(int)

# Split data:
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\nTrain set: {len(X_train)} samples")
print(f"Test set: {len(X_test)} samples")

# ============================================
# 3. TRAIN MODEL
# ============================================
print("\nTraining model...")
model = GradientBoostingClassifier(
    n_estimators=100,
    learning_rate=0.1,
    max_depth=3,
    random_state=42
)

model.fit(X_train, y_train)

# ============================================
# 4. EVALUATE MODEL
# ============================================
print("\n" + "="*50)
print("MODEL PERFORMANCE")
print("="*50)

# Predictions:
y_train_pred_proba = model.predict_proba(X_train)[:, 1]
y_test_pred_proba = model.predict_proba(X_test)[:, 1]

# AUC scores:
train_auc = roc_auc_score(y_train, y_train_pred_proba)
test_auc = roc_auc_score(y_test, y_test_pred_proba)

print(f"Train AUC: {train_auc:.3f}")
print(f"Test AUC: {test_auc:.3f}")
print(f"Gap: {train_auc - test_auc:.3f}")

if test_auc < 0.70:
    print("\n⚠️  WARNING: Test AUC < 0.70. Model may not be ready for production.")
elif test_auc < 0.80:
    print("\n✓ Test AUC is fair. Consider shipping as PoC with monitoring.")
else:
    print("\n✓ Test AUC is good. Ready for production!")

# Feature importance:
print("\n" + "="*50)
print("FEATURE IMPORTANCE")
print("="*50)
feature_names = ['buyer_brank', 'category_match', 'budget_specified']
for name, importance in zip(feature_names, model.feature_importances_):
    print(f"{name:20s}: {importance:.3f}")

# Classification report:
y_test_pred = (y_test_pred_proba > 0.5).astype(int)
print("\n" + "="*50)
print("CLASSIFICATION REPORT (Threshold = 0.5)")
print("="*50)
print(classification_report(y_test, y_test_pred, 
                          target_names=['Not Converted', 'Converted']))

# Top-K analysis:
print("\n" + "="*50)
print("TOP-K LIFT ANALYSIS")
print("="*50)

test_results = pd.DataFrame({
    'actual': y_test.values,
    'predicted_prob': y_test_pred_proba
}).sort_values('predicted_prob', ascending=False)

overall_conversion = y_test.mean()

for k in [10, 20, 30]:
    top_k_count = int(k/100 * len(test_results))
    top_k_conversion = test_results.head(top_k_count)['actual'].mean()
    lift = top_k_conversion / overall_conversion
    
    print(f"Top {k:2d}%: {top_k_conversion:5.1%} conversion (Lift: {lift:.1f}x)")

# ============================================
# 5. SAVE MODEL
# ============================================
model_package = {
    'model': model,
    'features': feature_names,
    'train_auc': train_auc,
    'test_auc': test_auc,
    'version': 'v1.0'
}

with open('lead_scoring_model.pkl', 'wb') as f:
    pickle.dump(model_package, f)

print("\n✓ Model saved as 'lead_scoring_model.pkl'")