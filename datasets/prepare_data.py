"""
prepare_data.py
- Charge les CSV fournis (les noms attendus sont listés ci-dessous).
- Normalise les noms de symptômes (lowercase, underscore).
- Construit un vocabulaire maître (master_symptoms).
- Convertit chaque dataset en une table binaire (one-hot symptoms) + colonne `disease`.
- Calcule un score d'urgency et un label urgency basé sur symptom_severity + red_flags.
- Sauvegarde:
    - unified_data.csv
    - master_symptoms.json
"""

import pandas as pd
import json
import os
import warnings

# --------- CONFIG ----------
INPUT_FILES = {
    "diseases_symptoms": "Diseases_Symptoms.csv",   # text Symptoms list + Treatments
    "training_data": "training_data.csv",
    "testing": "Testing.csv",
    "training2": "Training.csv",
    "dataset3": "dataset.csv",
    "symptom_severity": "symptom_severity.csv",
    # optional:
    "disease_description": "disease_description.csv",
    "disease_precaution": "disease_precaution.csv"
}
OUTPUT_UNIFIED = "unified_data.csv"
OUTPUT_MASTER = "master_symptoms.json"
# thresholds for urgency (adjust later with clinician)
URGENT_THRESHOLD = 15
MODERATE_THRESHOLD = 8

# --------- HELPERS ----------
def normalize(col):
    if not isinstance(col, str):
        return col
    s = col.strip().lower()
    s = s.replace(" ", "_").replace("-", "_").replace(".", "_").replace("(", "").replace(")", "")
    s = s.replace("__", "_")
    return s

def safe_read_csv(path):
    if not os.path.exists(path):
        warnings.warn(f"File not found: {path}")
        return None
    return pd.read_csv(path)

# --------- LOAD ----------
print("Loading files...")
d1 = safe_read_csv(INPUT_FILES["diseases_symptoms"])
tr = safe_read_csv(INPUT_FILES["training_data"])
tst = safe_read_csv(INPUT_FILES["testing"])
tr2 = safe_read_csv(INPUT_FILES["training2"])
d3 = safe_read_csv(INPUT_FILES["dataset3"])
symsev = safe_read_csv(INPUT_FILES["symptom_severity"])

# Some optional files
desc = safe_read_csv(INPUT_FILES.get("disease_description"))
prec = safe_read_csv(INPUT_FILES.get("disease_precaution"))

# --------- BUILD MASTER SYMPTOMS ----------
print("Building master symptom list...")
dfs_for_cols = [df for df in (tr, tst, tr2, d3) if df is not None]
cols = set()
for df in dfs_for_cols:
    for c in df.columns:
        cn = normalize(c)
        # ignore likely label columns
        if cn in ("prognosis", "disease", "name", "code", "treatments", "symptom_description"):
            continue
        cols.add(cn)
# also include symptom names that appear inside Diseases_Symptoms.csv 'Symptoms' column
if d1 is not None and "Symptoms" in d1.columns:
    # split the comma separated lists
    for cell in d1["Symptoms"].dropna().astype(str):
        for s in cell.split(","):
            cols.add(normalize(s))

master_symptoms = sorted(cols)
print(f"Master symptom count: {len(master_symptoms)}")

# helper to map df to master
def df_to_master(df, master_symptoms):
    df = df.copy()
    # normalize column names
    df.columns = [normalize(c) for c in df.columns]
    out = pd.DataFrame(0, index=df.index, columns=master_symptoms)
    # find which columns are symptom columns (binary 0/1)
    for c in df.columns:
        if c in master_symptoms:
            # try convert to int
            try:
                out[c] = df[c].fillna(0).astype(int)
            except Exception:
                # if not numeric, try infer presence by text not null or not zero
                out[c] = df[c].fillna('').apply(lambda x: 0 if str(x).strip() in ("", "0", "0.0", "nan") else 1)
    # detect disease label
    label_col = None
    for candidate in ("prognosis", "disease"):
        if candidate in df.columns:
            label_col = candidate
            break
    if label_col is None:
        # fallback: last column might be label (common in some provided files)
        label_col = df.columns[-1]
    out["disease"] = df[label_col].astype(str)
    return out

# convert dataset3 (which lists symptom names per row) to binary via symptom names
def dataset3_to_master(df, master_symptoms):
    df = df.copy()
    out = pd.DataFrame(0, index=df.index, columns=master_symptoms)
    # disease column exists as 'Disease'
    if 'Disease' in df.columns:
        out['disease'] = df['Disease'].astype(str)
    else:
        # try lowercase 'disease'
        if 'disease' in df.columns:
            out['disease'] = df['disease'].astype(str)
    # parse Symptom_0..Symptom_16
    for idx, row in df.iterrows():
        for c in df.columns:
            if c.lower().startswith("symptom"):
                val = row[c]
                if pd.isna(val):
                    continue
                s = normalize(str(val))
                if s in master_symptoms:
                    out.at[idx, s] = 1
    return out

# Convert diseases_symptoms.csv (text lists) into rows
def diseases_symptoms_to_master(d1, master_symptoms):
    rows = []
    for idx, row in d1.iterrows():
        disease = str(row.get("Name") or row.get("name") or row.get("Disease") or "")
        symptoms_text = row.get("Symptoms") or row.get("symptoms") or ""
        row_dict = {k: 0 for k in master_symptoms}
        for s in str(symptoms_text).split(","):
            s2 = normalize(s)
            if s2 in master_symptoms:
                row_dict[s2] = 1
        row_dict["disease"] = disease
        rows.append(row_dict)
    if rows:
        return pd.DataFrame(rows)
    return pd.DataFrame(columns=master_symptoms + ["disease"])

# --------- BUILD UNIFIED DATAFRAME ----------
parts = []
for df in dfs_for_cols:
    try:
        parts.append(df_to_master(df, master_symptoms))
    except Exception as e:
        print("skip df:", e)

if d3 is not None:
    try:
        parts.append(dataset3_to_master(d3, master_symptoms))
    except Exception as e:
        print("skip dataset3:", e)

if d1 is not None:
    try:
        parts.append(diseases_symptoms_to_master(d1, master_symptoms))
    except Exception as e:
        print("skip diseases_symptoms:", e)

if not parts:
    raise SystemExit("No datasets loaded. Put your CSV files in the working directory.")

all_data = pd.concat(parts, ignore_index=True, sort=False).fillna(0)
# ensure symptom columns are ints
for c in master_symptoms:
    all_data[c] = all_data[c].astype(int)

# clean disease labels (strip)
all_data['disease'] = all_data['disease'].astype(str).str.strip()

# drop empty rows or rows without disease
all_data = all_data[all_data['disease'].str.len() > 0].reset_index(drop=True)

print("Unified shape:", all_data.shape)
print("Sample diseases:", all_data['disease'].unique()[:10])

# --------- URGENCY via symptom_severity + red_flags ----------
print("Computing urgency labels...")
sev_map = {}
if symsev is not None:
    # symsev likely has columns Symptom, Symptom_severity
    symsev.columns = [normalize(c) for c in symsev.columns]
    if 'symptom' in symsev.columns and 'symptom_severity' in symsev.columns:
        for idx, r in symsev.iterrows():
            sev_map[normalize(r['symptom'])] = float(r['symptom_severity'])
    else:
        # fallback if csv has different headers
        for idx, r in symsev.iterrows():
            k = list(r)[0]
            v = list(r)[1]
            sev_map[normalize(k)] = float(v)
else:
    print("symptom_severity.csv not found, default severity 1 for all symptoms.")

# red flags list (normalize). Adjust with clinician.
red_flags = set(normalize(x) for x in [
    "chest_pain", "loss_of_consciousness", "breathlessness", "severe_bleeding",
    "coma", "palpitations", "unconscious", "sudden_weakness", "paralysis"
])

def compute_urgency_label(row):
    present = [c for c in master_symptoms if int(row[c]) == 1]
    score = sum(sev_map.get(c, 1.0) for c in present)
    if any(flag in present for flag in red_flags):
        return "URGENT", score
    if score >= URGENT_THRESHOLD:
        return "URGENT", score
    if score >= MODERATE_THRESHOLD:
        return "MODERATE", score
    return "SIMPLE", score

urgency_res = all_data.apply(lambda r: compute_urgency_label(r), axis=1, result_type="expand")
all_data["urgency"] = urgency_res[0]
all_data["urgency_score"] = urgency_res[1].astype(float)

print(all_data.urgency.value_counts())

# --------- SAVE OUTPUTS ----------
print("Saving outputs...")
all_data.to_csv(OUTPUT_UNIFIED, index=False)
with open(OUTPUT_MASTER, "w", encoding="utf-8") as f:
    json.dump(master_symptoms, f, ensure_ascii=False, indent=2)

print("Done. Files created:", OUTPUT_UNIFIED, OUTPUT_MASTER)