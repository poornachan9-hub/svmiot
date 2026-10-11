import pandas as pd
import numpy as np
from scipy import stats
from sklearn.feature_selection import mutual_info_classif
from sklearn.preprocessing import LabelEncoder

df = pd.read_csv("datasets/RT_IOT2022_official.csv", low_memory=False)
y = df["Attack_type"]
X = df.drop(columns=["Attack_type", "Unnamed: 0", "id.orig_p", "bwd_URG_flag_count"])

print(f"Genuine dataset: {len(X)} rows, {len(X.columns)} features, target: Attack_type ({y.nunique()} classes)")

# Sample 10k rows for fast statistical test
sample_idx = df.groupby("Attack_type", group_keys=False).apply(
    lambda x: x.sample(min(len(x), 1000), random_state=42)
).index
X_sample = X.loc[sample_idx]
y_sample = y.loc[sample_idx]

num_cols = X_sample.select_dtypes(include=[np.number]).columns

print("\n--- TOP 15 FEATURES BY ANOVA F-STATISTIC ---")
f_scores = []
for col in num_cols:
    groups = [group[col].values for _, group in X_sample.groupby(y_sample) if len(group) > 1]
    if len(groups) > 1:
        f_val, p_val = stats.f_oneway(*groups)
        if not np.isnan(f_val):
            f_scores.append((col, f_val, p_val))

f_scores.sort(key=lambda x: -x[1])
for col, f_val, p_val in f_scores[:15]:
    print(f"  {col:30s} | F={f_val:10.2f} | p={p_val:.2e}")

print("\n--- LEAST INFORMATIVE NUMERIC FEATURES ---")
for col, f_val, p_val in f_scores[-5:]:
    print(f"  {col:30s} | F={f_val:10.2f} | p={p_val:.2e}")
