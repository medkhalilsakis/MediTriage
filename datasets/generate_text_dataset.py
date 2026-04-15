"""
generate_text_dataset.py
- Utilise Diseases_Symptoms.csv pour générer des exemples textuels 'symptoms_text' -> disease
- Utile si tu veux fine-tuner un modèle NLP pour texte libre.
- Sortie: text_dataset.csv (columns: text, disease)
"""

import pandas as pd
import os
from prepare_data import normalize  # optional: if in same folder; else re-define
import warnings

INPUT_DS = "Diseases_Symptoms.csv"
OUT = "text_dataset.csv"

if not os.path.exists(INPUT_DS):
    warnings.warn(f"{INPUT_DS} not found. Skipping text dataset generation.")
else:
    d1 = pd.read_csv(INPUT_DS)
    rows = []
    for idx, r in d1.iterrows():
        disease = str(r.get("Name") or r.get("name") or r.get("Disease") or "").strip()
        symptoms = r.get("Symptoms") or ""
        # Create 3 textual variants for augmentation
        base = ", ".join([s.strip() for s in str(symptoms).split(",") if s.strip()])
        if not base:
            continue
        rows.append({"text": base, "disease": disease})
        # variant 1: sentence
        rows.append({"text": f"I have {base}.", "disease": disease})
        # variant 2: question style
        rows.append({"text": f"Symptoms: {base}. What could it be?", "disease": disease})

    df_text = pd.DataFrame(rows).drop_duplicates().reset_index(drop=True)
    df_text.to_csv(OUT, index=False)
    print("Text dataset saved to", OUT, "rows:", len(df_text))