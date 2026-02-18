import pandas as pd
import numpy as np
import random

random.seed(42)
np.random.seed(42)

def generate_neutral_synthetic_data(n_samples=1000):
    """
    Purpose: Pipeline testing ONLY.
    
    Features are generated independently.
    Outcome is random noise with weak signal.
    
    DO NOT use this to draw conclusions about
    which features matter in real life.
    """

    records = []

    for _ in range(n_samples):

        # Generate features independently
        # No assumptions about which one matters more
        brank = random.choices(
            [1, 2, 3, 4, 5],
            weights=[15, 25, 30, 20, 10]
        )[0]

        category_match = random.choices(
            [1.0, 0.6, 0.2],
            weights=[35, 40, 25]
        )[0]

        # Fix from previous issue: integer not string
        budget_specified = random.choices([1, 0], weights=[45, 55])[0]

        # ── Outcome: Purely random ───────────────────────────────────────
        # No assumptions embedded here at all
        # The model will get a low AUC (expected for random data)
        # That is fine because this is only for pipeline testing
        converted = random.choices([1, 0], weights=[30, 70])[0]

        records.append({
            'buyer_brank': brank,
            'category_match': category_match,
            'budget_specified': budget_specified,
            'converted': converted
        })

    df = pd.DataFrame(records)
    return df


df = generate_neutral_synthetic_data(n_samples=1000)
df.to_csv('training_data_pipeline_test.csv', index=False)

print("IMPORTANT: This data is for pipeline testing only.")
print(f"\nGenerated {len(df)} rows")
print(f"Conversion rate: {df['converted'].mean():.1%}")