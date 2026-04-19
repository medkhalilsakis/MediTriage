import csv
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

from django.utils import timezone


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASET1_ROOT = PROJECT_ROOT / 'datasets' / 'Dataset1'
DATASET2_ROOT = PROJECT_ROOT / 'datasets' / 'Dataset2'
DATASET3_ROOT = PROJECT_ROOT / 'datasets' / 'Dataset3'

TRAINING_FILES = [
    DATASET1_ROOT / 'Training.csv',
    DATASET2_ROOT / 'Training.csv',
    DATASET3_ROOT / 'training_data.csv',
]

SEVERITY_FILE = DATASET1_ROOT / 'symptom_severity.csv'
DESCRIPTION_FILE = DATASET1_ROOT / 'disease_description.csv'
PRECAUTION_FILE = DATASET1_ROOT / 'disease_precaution.csv'
DISEASE_SYMPTOMS_FILE = DATASET3_ROOT / 'Diseases_Symptoms.csv'

DEFAULT_SUMMARY = (
    'Preliminary AI triage only. This is not a confirmed diagnosis. '
    'Please consult a licensed clinician, especially if symptoms worsen.'
)

OUT_OF_SCOPE_REPLY = (
    'I am a healthcare triage chatbot and can only help with health-related symptoms, '
    'medical orientation, and basic care guidance. Please keep your question within this medical scope.'
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
    'reserve',
    'reservation',
}

GREETING_TERMS = {
    'hello',
    'hi',
    'hey',
    'good morning',
    'good afternoon',
    'good evening',
    'bonjour',
    'salut',
    'hola',
    'buenas',
}

THANKS_TERMS = {
    'thanks',
    'thank you',
    'thx',
    'merci',
    'gracias',
}

HEALTH_DOMAIN_HINTS = {
    'symptom',
    'symptoms',
    'health',
    'medical',
    'doctor',
    'hospital',
    'diagnosis',
    'disease',
    'pain',
    'fever',
    'cough',
    'nausea',
    'vomit',
    'breathing',
    'chest',
    'headache',
    'rash',
    'infection',
    'blood pressure',
    'diabetes',
    'urgence',
    'medicale',
    'sante',
    'symptome',
    'douleur',
    'fievre',
    'toux',
    'hopital',
    'consulta',
    'salud',
    'sintoma',
    'dolor',
    'fiebre',
    'tos',
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


def _split_csv_values(raw_value):
    if not raw_value:
        return []
    values = [part.strip() for part in re.split(r'[,;|]', str(raw_value))]
    return [value for value in values if value and value.lower() != 'null']


def _contains_any_term(normalized_text, terms):
    if not normalized_text:
        return False
    padded_text = f' {normalized_text} '
    for term in terms:
        normalized_term = _normalize_text(term)
        if not normalized_term:
            continue
        if f' {normalized_term} ' in padded_text:
            return True
    return False


@lru_cache(maxsize=1)
def _load_knowledge_base():
    severity_map = _load_severity_map()
    disease_descriptions = _load_disease_descriptions()
    disease_precautions = _load_disease_precautions()
    training_profiles, symptoms = _load_training_profiles()
    disease_catalog = _load_dataset3_disease_catalog()
    alias_map = _build_symptom_alias_map(symptoms, disease_catalog)
    known_disease_terms = _collect_known_disease_terms(
        training_profiles=training_profiles,
        disease_descriptions=disease_descriptions,
        disease_catalog=disease_catalog,
    )

    return {
        'severity_map': severity_map,
        'disease_descriptions': disease_descriptions,
        'disease_precautions': disease_precautions,
        'training_profiles': training_profiles,
        'symptoms': symptoms,
        'alias_map': alias_map,
        'disease_catalog': disease_catalog,
        'known_disease_terms': known_disease_terms,
    }


def _load_training_profiles():
    disease_counts = Counter()
    symptom_counts_by_disease = defaultdict(Counter)
    symptoms = set()

    for training_file in TRAINING_FILES:
        if not training_file.exists():
            continue

        with training_file.open('r', encoding='utf-8', newline='') as handle:
            reader = csv.DictReader(handle)
            fieldnames = [column for column in (reader.fieldnames or []) if column]
            symptom_columns = []
            disease_columns = []

            for column in fieldnames:
                normalized_column = _normalize_symptom(column)
                if normalized_column in {'prognosis', 'disease'}:
                    disease_columns.append(column)
                    continue
                if not normalized_column:
                    continue
                symptom_columns.append(column)
                symptoms.add(normalized_column)

            for row in reader:
                disease_name = ''
                for disease_column in disease_columns:
                    disease_name = (row.get(disease_column) or '').strip().strip(',')
                    if disease_name:
                        break
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
            for column in (
                'Symptom_precaution_0',
                'Symptom_precaution_1',
                'Symptom_precaution_2',
                'Symptom_precaution_3',
            ):
                value = (row.get(column) or '').strip()
                if value and value.lower() != 'null':
                    precautions.append(value)

            if precautions:
                disease_precautions[key] = precautions
    return disease_precautions


def _load_dataset3_disease_catalog():
    if not DISEASE_SYMPTOMS_FILE.exists():
        return {}

    catalog = {}
    with DISEASE_SYMPTOMS_FILE.open('r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            disease_name = (row.get('Name') or row.get('Disease') or '').strip()
            disease_key = _normalize_disease_key(disease_name)
            if not disease_key:
                continue

            symptoms = _split_csv_values(row.get('Symptoms', ''))
            treatments = _split_csv_values(row.get('Treatments', ''))
            code = (row.get('Code') or '').strip()

            catalog[disease_key] = {
                'name': disease_name,
                'symptoms': symptoms,
                'treatments': treatments,
                'code': code,
            }

    return catalog


def _collect_known_disease_terms(training_profiles, disease_descriptions, disease_catalog):
    terms = {}

    for disease_name in training_profiles.keys():
        key = _normalize_disease_key(disease_name)
        if key:
            terms[key] = disease_name

    for disease_key in disease_descriptions.keys():
        if disease_key and disease_key not in terms:
            terms[disease_key] = disease_key.replace('_', ' ').title()

    for disease_key, payload in disease_catalog.items():
        if disease_key:
            terms[disease_key] = payload.get('name') or terms.get(disease_key) or disease_key.replace('_', ' ').title()

    return terms


def _resolve_first_existing(candidates, known_symptoms):
    for candidate in candidates:
        if candidate in known_symptoms:
            return candidate
    return None


def _best_known_symptom_for_phrase(phrase, known_symptoms):
    phrase_tokens = set(_normalize_text(phrase).split())
    if not phrase_tokens:
        return None

    best_symptom = None
    best_score = 0.0
    for symptom in known_symptoms:
        symptom_tokens = set(symptom.replace('_', ' ').split())
        if not symptom_tokens:
            continue
        overlap = len(phrase_tokens & symptom_tokens)
        union = len(phrase_tokens | symptom_tokens)
        if union == 0:
            continue
        score = overlap / union
        if score > best_score:
            best_score = score
            best_symptom = symptom

    if best_score >= 0.5:
        return best_symptom
    return None


def _build_symptom_alias_map(known_symptoms, disease_catalog):
    alias_map = {}

    for symptom in known_symptoms:
        phrase = symptom.replace('_', ' ')
        alias_map[phrase] = symptom

    for alias, candidates in MULTILINGUAL_SYMPTOM_ALIASES.items():
        normalized_alias = _normalize_text(alias)
        target = _resolve_first_existing(candidates, known_symptoms)
        if normalized_alias and target:
            alias_map[normalized_alias] = target

    for payload in disease_catalog.values():
        for symptom_phrase in payload.get('symptoms', []):
            normalized_alias = _normalize_text(symptom_phrase)
            if not normalized_alias or normalized_alias in alias_map:
                continue

            direct_symptom = _normalize_symptom(symptom_phrase)
            if direct_symptom in known_symptoms:
                alias_map[normalized_alias] = direct_symptom
                continue

            candidate = _best_known_symptom_for_phrase(symptom_phrase, known_symptoms)
            if candidate:
                alias_map[normalized_alias] = candidate

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


def _find_condition_mentions(normalized_text, known_disease_terms, max_items=2):
    if not normalized_text:
        return []

    padded_text = f' {normalized_text} '
    mentions = []
    for disease_key in sorted(known_disease_terms.keys(), key=len, reverse=True):
        if len(disease_key) < 4:
            continue
        token = f' {disease_key} '
        if token in padded_text:
            mentions.append(disease_key)
        if len(mentions) >= max_items:
            break

    return mentions


def _build_condition_information_reply(mentioned_terms, knowledge_base):
    if not mentioned_terms:
        return (
            'I can explain health conditions and run symptom triage. '
            'Please provide either a condition name or your symptoms.'
        )

    disease_key = mentioned_terms[0]
    known_terms = knowledge_base['known_disease_terms']
    catalog = knowledge_base['disease_catalog']
    descriptions = knowledge_base['disease_descriptions']
    precautions = knowledge_base['disease_precautions']

    display_name = catalog.get(disease_key, {}).get('name') or known_terms.get(disease_key) or disease_key.title()
    description = descriptions.get(disease_key) or 'I do not have a full clinical description for this condition in my local dataset.'
    treatments = catalog.get(disease_key, {}).get('treatments', [])[:4]
    safety = precautions.get(disease_key, [])[:3]

    parts = [
        f'Condition overview: {display_name}.',
        f'Description: {description}',
    ]

    if treatments:
        parts.append(f'Common management options in the dataset: {", ".join(treatments)}.')
    if safety:
        parts.append(f'Precaution tips: {", ".join(safety)}.')

    parts.append('If you share your current symptoms, I can perform a triage estimate with urgency and department guidance.')
    return ' '.join(parts)


def _is_greeting_only(normalized_text):
    if not normalized_text:
        return False
    if _contains_any_term(normalized_text, GREETING_TERMS) and len(normalized_text.split()) <= 8:
        return not _contains_any_term(normalized_text, HEALTH_DOMAIN_HINTS)
    return False


def _is_thanks_message(normalized_text):
    if not normalized_text:
        return False
    return _contains_any_term(normalized_text, THANKS_TERMS) and len(normalized_text.split()) <= 8


def _is_health_related_query(normalized_text, detected_symptoms, appointment_requested, known_disease_terms):
    if detected_symptoms:
        return True
    if appointment_requested:
        return True
    if _contains_any_term(normalized_text, HEALTH_DOMAIN_HINTS):
        return True
    if _find_condition_mentions(normalized_text, known_disease_terms, max_items=1):
        return True
    return False


def analyze_symptoms(text, wants_appointment=False):
    knowledge_base = _load_knowledge_base()
    alias_map = knowledge_base['alias_map']
    severity_map = knowledge_base['severity_map']
    disease_catalog = knowledge_base['disease_catalog']

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
            'treatment_suggestions': [],
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

    for item in probable_diseases:
        disease_key = _normalize_disease_key(item['disease'])
        item['treatment_options'] = disease_catalog.get(disease_key, {}).get('treatments', [])[:4]

    urgency_level, severity_score = _compute_urgency(detected_symptoms, text, severity_map)
    primary_disease = probable_diseases[0]['disease'] if probable_diseases else 'Undetermined condition'
    department_info = _resolve_department(primary_disease, detected_symptoms)
    recommendation = _build_appointment_recommendation(
        appointment_requested=appointment_requested,
        urgency_level=urgency_level,
        department=department_info['department'],
    )

    primary_key = _normalize_disease_key(primary_disease)
    precautions = knowledge_base['disease_precautions'].get(primary_key, [])
    treatment_suggestions = disease_catalog.get(primary_key, {}).get('treatments', [])[:4]

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
        'treatment_suggestions': treatment_suggestions,
        'summary': summary,
    }


def _build_triage_reply(analysis, booking_auth_required=False):
    probable = analysis.get('probable_diseases', [])
    urgency = analysis.get('urgency_level', 'low')
    department = analysis.get('department', 'General Medicine')
    detected_symptoms = analysis.get('detected_symptoms', [])[:6]
    precautions = analysis.get('precautions', [])[:3]
    treatments = analysis.get('treatment_suggestions', [])[:4]
    summary = analysis.get('summary', DEFAULT_SUMMARY)

    if not probable:
        lines = [
            'Triage summary',
            '- I need clearer medical symptoms to generate a reliable triage result.',
            '- Please include symptom type, duration, intensity, and progression.',
        ]
        if booking_auth_required and analysis.get('appointment_requested'):
            lines.append('- To book an appointment, please log in or sign up first.')
        lines.append(f'Safety note: {summary}')
        return '\n'.join(lines)

    lines = [
        'Triage summary',
        'Most likely conditions:',
    ]
    for index, item in enumerate(probable[:3], start=1):
        lines.append(f"{index}. {item.get('disease', 'Unknown')} ({item.get('score', 0)}% confidence)")

    lines.extend(
        [
            f'Urgency level: {urgency}',
            f'Recommended department: {department}',
        ]
    )

    if detected_symptoms:
        lines.append(f'Detected symptoms: {", ".join(detected_symptoms)}')

    if treatments:
        lines.append('Common care options (dataset-based):')
        lines.extend(f'- {treatment}' for treatment in treatments)

    if precautions:
        lines.append('Precautions:')
        lines.extend(f'- {precaution}' for precaution in precautions)

    if analysis.get('appointment_requested'):
        if booking_auth_required:
            lines.append('Booking: To reserve an appointment, please log in or sign up first.')
        else:
            recommendation = analysis.get('recommended_appointment', {})
            if recommendation.get('should_schedule'):
                lines.append(
                    'Booking suggestion: '
                    f"{recommendation.get('suggested_window')} "
                    f"(suggested time: {recommendation.get('suggested_datetime_label')})."
                )

    lines.append(f'Safety note: {summary}')
    return '\n'.join(line for line in lines if line)


def build_health_chat_response(text, wants_appointment=False, require_auth_for_booking=False):
    normalized_text = _normalize_text(text)
    if not normalized_text:
        return {
            'response_type': 'empty',
            'reply': (
                'Please share your health question or symptoms. '
                'For example: "I have fever, cough, and chest discomfort for 2 days."'
            ),
            'analysis': None,
            'booking_auth_required': False,
        }

    if _is_thanks_message(normalized_text):
        return {
            'response_type': 'gratitude',
            'reply': 'You are welcome. If you have more health symptoms to review, I am ready to help.',
            'analysis': None,
            'booking_auth_required': False,
        }

    if _is_greeting_only(normalized_text):
        return {
            'response_type': 'greeting',
            'reply': (
                'Hello. I am your local healthcare triage assistant. '
                'Describe your symptoms and I will provide urgency, probable conditions, and department guidance.'
            ),
            'analysis': None,
            'booking_auth_required': False,
        }

    knowledge_base = _load_knowledge_base()
    appointment_requested = bool(wants_appointment or _detect_appointment_intent(text))
    detected_symptoms = _extract_symptoms_from_text(text, knowledge_base['alias_map'])

    if not _is_health_related_query(
        normalized_text=normalized_text,
        detected_symptoms=detected_symptoms,
        appointment_requested=appointment_requested,
        known_disease_terms=knowledge_base['known_disease_terms'],
    ):
        return {
            'response_type': 'out_of_scope',
            'reply': OUT_OF_SCOPE_REPLY,
            'analysis': None,
            'booking_auth_required': False,
        }

    condition_mentions = _find_condition_mentions(
        normalized_text=normalized_text,
        known_disease_terms=knowledge_base['known_disease_terms'],
        max_items=2,
    )

    if not detected_symptoms and condition_mentions:
        booking_auth_required = bool(require_auth_for_booking and appointment_requested)
        reply = _build_condition_information_reply(condition_mentions, knowledge_base)
        if booking_auth_required:
            reply = f'{reply} To reserve an appointment, please log in or sign up first.'

        return {
            'response_type': 'condition_info',
            'reply': reply,
            'analysis': None,
            'booking_auth_required': booking_auth_required,
        }

    analysis = analyze_symptoms(text, wants_appointment=appointment_requested)
    booking_auth_required = bool(require_auth_for_booking and analysis.get('appointment_requested'))
    reply = _build_triage_reply(analysis, booking_auth_required=booking_auth_required)

    return {
        'response_type': 'triage',
        'reply': reply,
        'analysis': analysis,
        'booking_auth_required': booking_auth_required,
    }