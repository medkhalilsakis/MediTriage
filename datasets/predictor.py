"""
predictor.py
- Module utilitaire pour charger model.joblib, label encoder, master_symptoms.json
- Fournit:
    - extract_symptoms_from_text(text): méthode naive qui repère des tokens correspondant au master_symptoms
    - predict_from_text(text): réalise la vectorisation binaire puis prédit top3 maladies + probs + urgency via rule-based
"""

import joblib
import json
import re
import numpy as np
from collections import OrderedDict

MODEL_FILE = "model.joblib"
LE_FILE = "label_encoder.joblib"
MASTER_FILE = "master_symptoms.json"
UNIFIED = "unified_data.csv"

# load artifacts
clf = None
le = None
master_symptoms = None
try:
    clf = joblib.load(MODEL_FILE)
    le = joblib.load(LE_FILE)
    with open(MASTER_FILE, "r", encoding="utf-8") as f:
        master_symptoms = json.load(f)
except Exception as e:
    print("Warning: predictor artifacts not found or failed to load:", e)

# naive symptom extractor: for each master_symptom token, check if its words are present in text
def normalize_token(tok):
    return tok.strip().lower().replace("_", " ")

def extract_symptoms_from_text(text):
    if not text:
        return []
    text_low = text.lower()
    found = []
    for s in master_symptoms:
        token = normalize_token(s)
        # basic word boundary search
        pattern = r"\b" + re.escape(token) + r"\b"
        if re.search(pattern, text_low):
            found.append(s)
    return found

# urgency rule reuse (a simple mirror of prepare_data)
def compute_urgency_from_symptoms(symptoms_list, sev_map=None):
    # default severity 1 if none
    if sev_map is None:
        sev_map = {}
    score = sum(sev_map.get(s, 1.0) for s in symptoms_list)
    red_flags = set(["chest_pain","loss_of_consciousness","breathlessness","severe_bleeding","coma","palpitations"])
    if any(r in symptoms_list for r in red_flags):
        return "URGENT", score
    if score >= 15:
        return "URGENT", score
    if score >= 8:
        return "MODERATE", score
    return "SIMPLE", score

def predict_from_text(text, top_k=3, sev_map=None):
    if clf is None or le is None or master_symptoms is None:
        raise SystemExit("Model artifacts not loaded. Run training first.")
    found = extract_symptoms_from_text(text)
    x = np.zeros(len(master_symptoms), dtype=int)
    for s in found:
        try:
            idx = master_symptoms.index(s)
            x[idx] = 1
        except ValueError:
            pass
    proba = clf.predict_proba([x])[0]
    # topk
    top_idx = np.argsort(proba)[::-1][:top_k]
    results = []
    for i in top_idx:
        results.append({"disease": le.inverse_transform([i])[0], "prob": float(proba[i])})
    urgency_label, urgency_score = compute_urgency_from_symptoms(found, sev_map)
    return {
        "symptoms_detected": found,
        "predictions": results,
        "urgency": urgency_label,
        "urgency_score": urgency_score
    }

if __name__ == "__main__":
    # quick demo
    sample = "I have chest pain and breathlessness and palpitations"
    print(predict_from_text(sample))