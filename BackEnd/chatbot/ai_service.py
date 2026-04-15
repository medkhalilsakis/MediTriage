import csv
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

from django.utils import timezone


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = PROJECT_ROOT / 'datasets' / 'Dataset1'
TRAINING_FILE = DATASET_ROOT / 'Training.csv'
SEVERITY_FILE = DATASET_ROOT / 'symptom_severity.csv'
DESCRIPTION_FILE = DATASET_ROOT / 'disease_description.csv'
PRECAUTION_FILE = DATASET_ROOT / 'disease_precaution.csv'

DEFAULT_SUMMARY = (
    'Preliminary AI triage only. This is not a confirmed diagnosis. '
    'Please consult a licensed clinician, especially if symptoms worsen.'
)

APPOINTMENT_INTENT_TERMS = {
    'appointment',
    'book',
    'book appointment',
    'schedule',
    'schedule appointment',
    'consultation',
    'rendez vous',
    'rendezvous',
    'rdv',
    'prendre rendez vous',
    'cita',
    'agendar',
    'agendar cita',
    'reservar cita',
}

RED_FLAG_SYMPTOMS = {
    'chest_pain',
    'breathlessness',
    'coma',
    'slurred_speech',
    'weakness_of_one_body_side',
    'stomach_bleeding',
}

CRITICAL_HINTS = {
    'loss of consciousness',
    'unconscious',
    'severe chest pain',
    'heavy bleeding',
    'stroke',
    'cannot breathe',
    'difficulty breathing',
    'douleur thoracique intense',
    'perte de connaissance',
}

HIGH_HINTS = {
    'high fever',
    'vomiting blood',
    'severe pain',
    'persistent pain',
    'forte fievre',
    'douleur intense',
}

DEPARTMENT_RULES = [
    {
        'department': 'Cardiology',
        'keywords': ('heart', 'cardiac', 'hypertension', 'palpitation', 'chest pain', 'vascular'),
        'specialization_keywords': ('cardio', 'cardiac', 'heart'),
    },
    {
        'department': 'Pulmonology',
        'keywords': ('asthma', 'pneumonia', 'tuberculosis', 'breath', 'lung', 'respiratory', 'cough'),
        'specialization_keywords': ('pulmo', 'respir', 'lung'),
    },
    {
        'department': 'Gastroenterology',
        'keywords': ('gastro', 'stomach', 'liver', 'hepatitis', 'ulcer', 'abdominal', 'diarrh', 'vomit'),
        'specialization_keywords': ('gastro', 'hepato', 'digest'),
    },
    {
        'department': 'Neurology',
        'keywords': ('migraine', 'vertigo', 'paralysis', 'headache', 'speech', 'brain', 'neuro', 'dizziness'),
        'specialization_keywords': ('neuro', 'brain'),
    },
    {
        'department': 'Dermatology',
        'keywords': ('acne', 'skin', 'rash', 'fungal', 'psoriasis', 'itching', 'eruption'),
        'specialization_keywords': ('derma', 'skin'),
    },
    {
        'department': 'Endocrinology',
        'keywords': ('diabetes', 'thyroid', 'hypoglycemia', 'hormone', 'obesity'),
        'specialization_keywords': ('endo', 'diabet'),
    },
    {
        'department': 'General Medicine',
        'keywords': (),
        'specialization_keywords': ('general', 'internal'),
    },
]

MULTILINGUAL_SYMPTOM_ALIASES = {
    'fever': ('high_fever', 'mild_fever'),
    'fievre': ('high_fever', 'mild_fever'),
    'fiebre': ('high_fever', 'mild_fever'),
    'cough': ('cough',),
    'toux': ('cough',),
    'tos': ('cough',),
    'chest pain': ('chest_pain',),
    'douleur thoracique': ('chest_pain',),
    'dolor de pecho': ('chest_pain',),
    'shortness of breath': ('breathlessness',),
    'difficulty breathing': ('breathlessness',),
    'essoufflement': ('breathlessness',),
    'dificultad para respirar': ('breathlessness',),
    'headache': ('headache',),
    'maux de tete': ('headache',),
    'dolor de cabeza': ('headache',),
    'nausea': ('nausea',),
    'nausee': ('nausea',),
    'nauseas': ('nausea',),
    'vomit': ('vomiting',),
    'vomissement': ('vomiting',),
    'vomitos': ('vomiting',),
    'diarrhea': ('diarrhoea',),
    'diarrhoea': ('diarrhoea',),
    'diarrhee': ('diarrhoea',),
    'fatigue': ('fatigue',),
    'tired': ('fatigue', 'tiredness'),
    'dizziness': ('dizziness',),
    'vertige': ('dizziness', 'spinning_movements'),
    'mareo': ('dizziness',),
    'rash': ('skin_rash',),
    'eruption cutanee': ('skin_rash',),
    'erupcion cutanea': ('skin_rash',),
    'abdominal pain': ('abdominal_pain', 'stomach_pain'),
    'douleur abdominale': ('abdominal_pain', 'stomach_pain'),
    'dolor abdominal': ('abdominal_pain', 'stomach_pain'),
    'joint pain': ('joint_pain',),
    'douleur articulaire': ('joint_pain',),
    'dolor articular': ('joint_pain',),
    'muscle pain': ('muscle_pain',),
    'douleur musculaire': ('muscle_pain',),
    'palpitations': ('palpitations', 'fast_heart_rate'),
    'runny nose': ('runny_nose',),
    'nez qui coule': ('runny_nose',),
    'loss of smell': ('loss_of_smell',),
    'perte de lodorat': ('loss_of_smell',),
    'loss of taste': ('loss_of_taste',),
    'perte du gout': ('loss_of_taste',),
}


def _strip_accents(value):
    normalized = unicodedata.normalize('NFD', value or '')
    return ''.join(char for char in normalized if unicodedata.category(char) != 'Mn')


def _normalize_text(value):
    cleaned = _strip_accents(value).lower()
    cleaned = cleaned.replace('-', ' ').replace('_', ' ')
    cleaned = re.sub(r'[^a-z0-9\s]', ' ', cleaned)
    return re.sub(r'\s+', ' ', cleaned).strip()


def _normalize_symptom(value):
    return _normalize_text(value).replace(' ', '_')


def _normalize_disease_key(value):
    return _normalize_text(value)


def _display_symptom(symptom):
    return symptom.replace('_', ' ')


def _safe_float(raw_value, default=1.0):
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return default


def _is_positive(raw_value):
    return str(raw_value).strip().lower() in {'1', '1.0', 'true', 'yes'}


@lru_cache(maxsize=1)
def _load_knowledge_base():
    severity_map = _load_severity_map()
    disease_descriptions = _load_disease_descriptions()
    disease_precautions = _load_disease_precautions()
    training_profiles, symptoms = _load_training_profiles()
    alias_map = _build_symptom_alias_map(symptoms)

    return {
        'severity_map': severity_map,
        'disease_descriptions': disease_descriptions,
        'disease_precautions': disease_precautions,
        'training_profiles': training_profiles,
        'symptoms': symptoms,
        'alias_map': alias_map,
    }


def _load_training_profiles():
    if not TRAINING_FILE.exists():
        return {}, set()

    disease_counts = Counter()
    symptom_counts_by_disease = defaultdict(Counter)
    symptoms = set()

    with TRAINING_FILE.open('r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        symptom_columns = [
            column
            for column in fieldnames
            if _normalize_symptom(column) not in {'prognosis', 'disease'}
        ]

        for raw_column in symptom_columns:
            normalized_column = _normalize_symptom(raw_column)
            if normalized_column:
                symptoms.add(normalized_column)

        for row in reader:
            disease_name = (row.get('prognosis') or row.get('disease') or '').strip()
            if not disease_name:
                continue

            disease_counts[disease_name] += 1
            for raw_column in symptom_columns:
                normalized_column = _normalize_symptom(raw_column)
                if not normalized_column:
                    continue
                if _is_positive(row.get(raw_column)):
                    symptom_counts_by_disease[disease_name][normalized_column] += 1

    disease_profiles = {}
    for disease_name, counts in symptom_counts_by_disease.items():
        total_rows = max(disease_counts[disease_name], 1)
        disease_profiles[disease_name] = {
            symptom: count / total_rows
            for symptom, count in counts.items()
        }

    return disease_profiles, symptoms


def _load_severity_map():
    if not SEVERITY_FILE.exists():
        return {}

    severity_map = {}
    with SEVERITY_FILE.open('r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            symptom = _normalize_symptom(row.get('Symptom', ''))
            if not symptom:
                continue
            severity_map[symptom] = max(
                severity_map.get(symptom, 0.0),
                _safe_float(row.get('Symptom_severity'), default=1.0),
            )
    return severity_map


def _load_disease_descriptions():
    if not DESCRIPTION_FILE.exists():
        return {}

    disease_descriptions = {}
    with DESCRIPTION_FILE.open('r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            disease = (row.get('Disease') or '').strip()
            description = (row.get('Symptom_Description') or '').strip()
            key = _normalize_disease_key(disease)
            if key and description:
                disease_descriptions[key] = description
    return disease_descriptions


def _load_disease_precautions():
    if not PRECAUTION_FILE.exists():
        return {}

    disease_precautions = {}
    with PRECAUTION_FILE.open('r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            disease = (row.get('Disease') or '').strip()
            key = _normalize_disease_key(disease)
            if not key:
                continue

            precautions = []
            for column in ('Symptom_precaution_0', 'Symptom_precaution_1', 'Symptom_precaution_2', 'Symptom_precaution_3'):
                value = (row.get(column) or '').strip()
                if value and value.lower() != 'null':
                    precautions.append(value)

            if precautions:
                disease_precautions[key] = precautions
    return disease_precautions


def _resolve_first_existing(candidates, known_symptoms):
    for candidate in candidates:
        if candidate in known_symptoms:
            return candidate
    return None


def _build_symptom_alias_map(known_symptoms):
    alias_map = {}

    for symptom in known_symptoms:
        phrase = symptom.replace('_', ' ')
        alias_map[phrase] = symptom

    for alias, candidates in MULTILINGUAL_SYMPTOM_ALIASES.items():
        normalized_alias = _normalize_text(alias)
        target = _resolve_first_existing(candidates, known_symptoms)
        if normalized_alias and target:
            alias_map[normalized_alias] = target

    return alias_map


def _extract_symptoms_from_text(text, alias_map):
    normalized_text = _normalize_text(text)
    if not normalized_text:
        return []

    padded_text = f' {normalized_text} '
    detected = set()
    for alias in sorted(alias_map.keys(), key=len, reverse=True):
        if not alias:
            continue
        token = f' {alias} '
        if token in padded_text:
            detected.add(alias_map[alias])

    return sorted(detected)


def _rank_diseases(detected_symptoms, training_profiles, severity_map, disease_descriptions):
    if not detected_symptoms or not training_profiles:
        return []

    symptom_weights = {
        symptom: 1.0 + (severity_map.get(symptom, 1.0) / 10.0)
        for symptom in detected_symptoms
    }
    max_possible_score = sum(symptom_weights.values()) or 1.0

    ranked = []
    for disease_name, profile in training_profiles.items():
        weighted_overlap = 0.0
        matched = []

        for symptom in detected_symptoms:
            presence_rate = profile.get(symptom, 0.0)
            if presence_rate <= 0:
                continue

            weighted_overlap += presence_rate * symptom_weights[symptom]
            matched.append((symptom, presence_rate))

        if not matched:
            continue

        normalized_overlap = weighted_overlap / max_possible_score
        coverage = len(matched) / max(len(detected_symptoms), 1)
        confidence = (0.65 * normalized_overlap + 0.35 * coverage) * 100
        matched.sort(key=lambda item: item[1], reverse=True)

        disease_description = disease_descriptions.get(_normalize_disease_key(disease_name), '')
        ranked.append(
            {
                'disease': disease_name,
                'score': round(confidence, 2),
                'matched_symptoms': [_display_symptom(symptom) for symptom, _ in matched[:6]],
                'description': disease_description,
            }
        )

    ranked.sort(key=lambda item: item['score'], reverse=True)
    return ranked[:5]


def _detect_appointment_intent(text):
    normalized_text = _normalize_text(text)
    if not normalized_text:
        return False

    return any(term in normalized_text for term in APPOINTMENT_INTENT_TERMS)


def _compute_urgency(detected_symptoms, original_text, severity_map):
    score = sum(severity_map.get(symptom, 1.0) for symptom in detected_symptoms)
    normalized_text = _normalize_text(original_text)

    if any(symptom in RED_FLAG_SYMPTOMS for symptom in detected_symptoms) or any(hint in normalized_text for hint in CRITICAL_HINTS):
        return 'critical', round(score, 2)

    if score >= 16 or any(hint in normalized_text for hint in HIGH_HINTS):
        return 'high', round(score, 2)

    if score >= 8:
        return 'medium', round(score, 2)

    return 'low', round(score, 2)


def _resolve_department(primary_disease, detected_symptoms):
    disease_text = (primary_disease or '').lower()
    symptoms_text = ' '.join(_display_symptom(item) for item in detected_symptoms).lower()

    for rule in DEPARTMENT_RULES:
        keywords = rule['keywords']
        if keywords and any(keyword in disease_text for keyword in keywords):
            return {
                'department': rule['department'],
                'matching_keywords': list(rule['specialization_keywords']),
            }

    for rule in DEPARTMENT_RULES:
        keywords = rule['keywords']
        if keywords and any(keyword in symptoms_text for keyword in keywords):
            return {
                'department': rule['department'],
                'matching_keywords': list(rule['specialization_keywords']),
            }

    return {
        'department': 'General Medicine',
        'matching_keywords': ['general', 'internal'],
    }


def _appointment_window_for_urgency(urgency_level):
    if urgency_level == 'critical':
        return timedelta(hours=4), 'as soon as possible (within 4 hours)'
    if urgency_level == 'high':
        return timedelta(days=1), 'within 24 hours'
    if urgency_level == 'medium':
        return timedelta(days=3), 'within 3 days'
    return timedelta(days=7), 'within 7 days'


def _build_appointment_recommendation(appointment_requested, urgency_level, department):
    if not appointment_requested:
        return {
            'should_schedule': False,
            'message': 'No appointment recommendation requested in this message.',
        }

    delta, window = _appointment_window_for_urgency(urgency_level)
    suggested_datetime = timezone.now() + delta

    return {
        'should_schedule': True,
        'department': department,
        'suggested_window': window,
        'suggested_datetime_iso': suggested_datetime.isoformat(),
        'suggested_datetime_label': suggested_datetime.strftime('%Y-%m-%d %H:%M UTC'),
        'message': f'Based on the urgency, schedule a {department} appointment {window}.',
    }


def analyze_symptoms(text, wants_appointment=False):
    knowledge_base = _load_knowledge_base()
    alias_map = knowledge_base['alias_map']
    severity_map = knowledge_base['severity_map']

    detected_symptoms = _extract_symptoms_from_text(text, alias_map)
    appointment_requested = bool(wants_appointment or _detect_appointment_intent(text))

    if not detected_symptoms:
        recommendation = _build_appointment_recommendation(
            appointment_requested=appointment_requested,
            urgency_level='low',
            department='General Medicine',
        )
        return {
            'probable_diseases': [],
            'urgency_level': 'low',
            'severity_score': 0.0,
            'detected_symptoms': [],
            'department': 'General Medicine',
            'department_matching_keywords': ['general', 'internal'],
            'appointment_requested': appointment_requested,
            'recommended_appointment': recommendation,
            'precautions': [],
            'summary': (
                'I could not confidently map your text to known symptom patterns. '
                'Please provide specific symptoms (for example: fever, cough, chest pain, nausea). '
                + DEFAULT_SUMMARY
            ),
        }

    probable_diseases = _rank_diseases(
        detected_symptoms=detected_symptoms,
        training_profiles=knowledge_base['training_profiles'],
        severity_map=severity_map,
        disease_descriptions=knowledge_base['disease_descriptions'],
    )

    urgency_level, severity_score = _compute_urgency(detected_symptoms, text, severity_map)
    primary_disease = probable_diseases[0]['disease'] if probable_diseases else 'Undetermined condition'
    department_info = _resolve_department(primary_disease, detected_symptoms)
    recommendation = _build_appointment_recommendation(
        appointment_requested=appointment_requested,
        urgency_level=urgency_level,
        department=department_info['department'],
    )

    precautions = knowledge_base['disease_precautions'].get(_normalize_disease_key(primary_disease), [])
    summary = (
        f'Most likely condition from current symptom patterns: {primary_disease}. '
        f'Urgency level appears {urgency_level}. '
        'This is a screening support output and not a confirmed diagnosis. '
        'Please follow up with a clinician for definitive evaluation.'
    )

    return {
        'probable_diseases': probable_diseases,
        'urgency_level': urgency_level,
        'severity_score': severity_score,
        'detected_symptoms': [_display_symptom(symptom) for symptom in detected_symptoms],
        'department': department_info['department'],
        'department_matching_keywords': department_info['matching_keywords'],
        'appointment_requested': appointment_requested,
        'recommended_appointment': recommendation,
        'precautions': precautions,
        'summary': summary,
    }
