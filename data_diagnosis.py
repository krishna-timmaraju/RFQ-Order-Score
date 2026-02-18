import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier

# Load your training data
df = pd.read_csv('training_data.csv')
#df = pd.read_csv('training_data_pipeline_test.csv')

df['converted'] = df['converted'].astype(str).str.strip().str.lower().map({'t': 1, 'true': 1, '1': 1, 'y': 1, 'yes': 1, 'f': 0, 'false': 0, '0': 0, 'n': 0, 'no': 0}).astype(int)

print("=" * 60)
print("DIAGNOSIS REPORT")
print("=" * 60)

# CHECK 1: Conversion rate by budget_specified
print("\n[CHECK 1] Conversion rate by budget_specified:")
print(df.groupby('budget_specified')['converted'].agg(['mean', 'count']))
print("\nExpected: Some variation but NOT 0% vs 100%")

# CHECK 2: Conversion rate by buyer_brank
print("\n[CHECK 2] Conversion rate by buyer_brank:")
print(df.groupby('buyer_brank')['converted'].agg(['mean', 'count']))
print("\nExpected: Clear downward trend SS-1 > SS-2 > SS-3 > SS-4 > SS-5")

# CHECK 3: Conversion rate by category_match
print("\n[CHECK 3] Conversion rate by category_match:")
print(df.groupby('category_match')['converted'].agg(['mean', 'count']))
print("\nExpected: 1.0 > 0.6 > 0.2 conversion rates")

# CHECK 4: Feature distributions
print("\n[CHECK 4] Feature distributions:")
for col in ['buyer_brank', 'category_match', 'budget_specified']:
    print(f"\n  {col}:")
    print(f"  {df[col].value_counts().sort_index()}")

# CHECK 5: Correlation with converted
print("\n[CHECK 5] Raw correlation with converted:")
df['converted'] = df['converted'].astype(str).str.strip().str.lower().map({'t': 1, 'true': 1, '1': 1, 'y': 1, 'yes': 1, 'f': 0, 'false': 0, '0': 0, 'n': 0, 'no': 0}).astype(int)
for col in ['buyer_brank', 'category_match', 'budget_specified']:
    df[col] = pd.to_numeric(df[col], errors='coerce')
for col in ['buyer_brank', 'category_match', 'budget_specified']:
    corr = df[col].corr(df['converted'])
    print(f"  {col}: {corr:.3f}")

# CHECK 6: Overall conversion rate
print(f"\n[CHECK 6] Overall conversion rate: {df['converted'].mean():.1%}")
print(f"  Total samples: {len(df)}")
print(f"  Converted: {df['converted'].sum()}")
print(f"  Not converted: {(df['converted']==0).sum()}")