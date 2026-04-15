"""
train_model.py
- Charge unified_data.csv (produit par prepare_data.py)
- Entraîne un RandomForest pour prédire 'disease' à partir des colonnes master_symptoms
- Sauvegarde model.joblib et label_encoder.joblib
- Génère metrics.json
"""

import pandas as pd
import joblib
import json
import os
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_predict
from sklearn.metrics import classification_report, balanced_accuracy_score, accuracy_score
import numpy as np

INPUT = "unified_data.csv"
MASTER_JSON = "master_symptoms.json"
OUT_MODEL = "model.joblib"
OUT_LE = "label_encoder.joblib"
OUT_METRICS = "metrics.json"

if not os.path.exists(INPUT):
    raise SystemExit(f"{INPUT} not found. Run prepare_data.py first.")

print("Loading unified dataset...")
df = pd.read_csv(INPUT)
with open(MASTER_JSON, "r", encoding="utf-8") as f:
    master_symptoms = json.load(f)

# ensure columns exist
for c in master_symptoms:
    if c not in df.columns:
        df[c] = 0

X = df[master_symptoms].values
y_raw = df['disease'].astype(str).values
le = LabelEncoder()
y = le.fit_transform(y_raw)

# train/test split with stratify
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, stratify=y, random_state=42)

print("Training RandomForest...")
clf = RandomForestClassifier(n_estimators=300, class_weight='balanced', random_state=42, n_jobs=-1)
clf.fit(X_train, y_train)

print("Evaluating...")
y_pred = clf.predict(X_test)
y_proba = clf.predict_proba(X_test)
report = classification_report(y_test, y_pred, target_names=le.classes_, output_dict=True)

metrics = {
    "accuracy": accuracy_score(y_test, y_pred).item(),
    "balanced_accuracy": balanced_accuracy_score(y_test, y_pred).item(),
    "classification_report": report
}

print("Saving model and label encoder...")
joblib.dump(clf, OUT_MODEL)
joblib.dump(le, OUT_LE)
with open(OUT_METRICS, "w", encoding="utf-8") as f:
    json.dump(metrics, f, indent=2, ensure_ascii=False)

print("Saved:", OUT_MODEL, OUT_LE, OUT_METRICS)
print("Top classes:", list(le.classes_)[:20])