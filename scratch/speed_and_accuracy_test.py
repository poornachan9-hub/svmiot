import time
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

df = pd.read_csv("datasets/RT_IOT2022_official.csv", low_memory=False)
y_raw = df["Attack_type"]
X_raw = df.drop(columns=["Attack_type", "Unnamed: 0", "id.orig_p", "bwd_URG_flag_count"])

# Handle string categoricals (proto, service) with LabelEncoder or OneHot
for col in ["proto", "service"]:
    if col in X_raw.columns:
        X_raw[col] = LabelEncoder().fit_transform(X_raw[col].astype(str))

y = LabelEncoder().fit_transform(y_raw)
X_train, X_test, y_train, y_test = train_test_split(X_raw, y, test_size=0.2, random_state=42, stratify=y)
scaler = StandardScaler()
X_tr_scaled = scaler.fit_transform(X_train)
X_te_scaled = scaler.transform(X_test)

print(f"Dataset split: Train={len(X_train)}, Test={len(X_test)}")

for name, model in [
    ("DecisionTree", DecisionTreeClassifier(max_depth=15, random_state=42)),
    ("RandomForest", RandomForestClassifier(n_estimators=50, max_depth=15, random_state=42, n_jobs=-1)),
    ("LogisticRegression", LogisticRegression(max_iter=500, random_state=42)),
    ("GradientBoosting", GradientBoostingClassifier(n_estimators=30, max_depth=4, random_state=42)),
]:
    t0 = time.time()
    model.fit(X_tr_scaled, y_train)
    t = time.time() - t0
    preds = model.predict(X_te_scaled)
    acc = accuracy_score(y_test, preds)
    f1 = f1_score(y_test, preds, average="macro", zero_division=0)
    print(f"{name:20s}: Fit={t:5.2f}s | Acc={acc:6.4f} | F1={f1:6.4f}")

# Test SVM with max_iter
t0 = time.time()
svm = SVC(kernel="rbf", max_iter=2000, random_state=42).fit(X_tr_scaled, y_train)
t = time.time() - t0
preds = svm.predict(X_te_scaled)
acc = accuracy_score(y_test, preds)
f1 = f1_score(y_test, preds, average="macro", zero_division=0)
print(f"{'SVM (max_iter=2000)':20s}: Fit={t:5.2f}s | Acc={acc:6.4f} | F1={f1:6.4f}")
