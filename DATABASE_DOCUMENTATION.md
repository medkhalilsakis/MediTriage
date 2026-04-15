# MEDITRIAGE - Documentation Schéma PostgreSQL

## 📋 Vue d'ensemble

Ce document décrit le schéma de base de données PostgreSQL complet pour le projet **MediTriage** - une plateforme de triage médical assistée par IA.

**Version**: 1.0  
**Base de données**: PostgreSQL 12+  
**Générée depuis**: Django ORM Models  
**Date**: 2026-03-28

---

## 🏗️ Architecture de la Base de Données

### Structure par Modules (9 applications)

```
authentication_customuser            ← Utilisateurs centralisés
├─ authentication_customuser_groups
├─ authentication_customuser_user_permissions
│
├── patients_patientprofile           ← Profils patients
├── doctors_doctorprofile             ← Profils médecins
│   └─ doctors_doctoravailabilityslot
├── appointments_appointment          ← Rendez-vous
├── medical_records_
│   ├─ medical_records_medicalrecord ← Historique médical
│   └─ medical_records_consultation   ← Consultations
├── prescriptions_
│   ├─ prescriptions_prescription     ← Ordonnances
│   └─ prescriptions_prescriptionitem ← Médicaments
├── chatbot_
│   ├─ chatbot_chebotsession          ← Sessions IA
│   └─ chatbot_chatbotmessage         ← Messages IA
├── follow_up_
│   ├─ follow_up_followup             ← Suivi patient
│   └─ follow_up_followupalert        ← Alertes
└── notifications_notification        ← Notifications
```

---

## 📊 Tableau des Tables Principales

### 1. **authentication_customuser** (18 colonnes)
Utilisateur central avec rôle (patient/doctor/admin)

| Colonne | Type | Constraints | Description |
|---------|------|-----------|-------------|
| id | BIGSERIAL | PK | Identifiant unique |
| email | VARCHAR(254) | UNIQUE, NOT NULL | Email utilisateur |
| username | VARCHAR(150) | UNIQUE, NOT NULL | Pseudo |
| password | VARCHAR(128) | NOT NULL | Hash bcrypt/pbkdf2 |
| role | VARCHAR(20) | CHECK, DEFAULT 'patient' | patient \| doctor \| admin |
| first_name | VARCHAR(150) | NOT NULL | Prénom |
| last_name | VARCHAR(150) | NOT NULL | Nom |
| is_active | BOOLEAN | DEFAULT TRUE | Activé/désactivé |
| is_staff | BOOLEAN | DEFAULT FALSE | Accès panel admin |
| is_superuser | BOOLEAN | DEFAULT FALSE | Super-admin |
| is_verified | BOOLEAN | DEFAULT FALSE | Email vérifié |
| phone_number | VARCHAR(20) | | Numéro téléphone |
| date_joined | TIMESTAMP | DEFAULT NOW() | Inscription |
| last_login | TIMESTAMP | NULL | Dernière connexion |
| created_at | TIMESTAMP | DEFAULT NOW() | Créé le |
| updated_at | TIMESTAMP | DEFAULT NOW() | Modifié le |

**Indexes**: email, username, role

---

### 2. **patients_patientprofile** (10 colonnes)
Profil détaillé patient lié 1:1 à un utilisateur

| Colonne | Type | Constraints | Description |
|---------|------|-----------|-------------|
| id | BIGSERIAL | PK | |
| user_id | BIGINT | FK, UNIQUE | Référence CustomUser |
| dob | DATE | | Date de naissance |
| gender | VARCHAR(10) | CHECK (male\|female\|other) | Genre |
| blood_group | VARCHAR(3) | CHECK (A+, A-, ..., O-) | Groupe sanguin |
| allergies | TEXT | | Allergies |
| emergency_contact_name | VARCHAR(120) | | Contact urgence |
| emergency_contact_phone | VARCHAR(20) | | Téléphone urgence |
| address | TEXT | | Adresse |
| created_at, updated_at | TIMESTAMP | | |

---

### 3. **doctors_doctorprofile** (9 colonnes)
Profil médecin avec spécialité et licence

| Colonne | Type | Constraints | Description |
|---------|------|-----------|-------------|
| id | BIGSERIAL | PK | |
| user_id | BIGINT | FK, UNIQUE | Référence CustomUser |
| specialization | VARCHAR(120) | NOT NULL | Cardiologie, Neurologie, etc. |
| license_number | VARCHAR(80) | UNIQUE, NOT NULL | Numéro de licence |
| years_of_experience | INTEGER | DEFAULT 0, CHECK >= 0 | Années expérience |
| consultation_fee | NUMERIC(10,2) | DEFAULT 0, CHECK >= 0 | Tarif consultation |
| bio | TEXT | | Biographie |
| created_at, updated_at | TIMESTAMP | | |

---

### 4. **doctors_doctoravailabilityslot** (6 colonnes)
Créneaux disponibilité hebdomadaire

| Colonne | Type | Constraints | Description |
|---------|------|-----------|-------------|
| id | BIGSERIAL | PK | |
| doctor_id | BIGINT | FK | Référence DoctorProfile |
| weekday | INTEGER | CHECK (0-6) | 0=Lun, ..., 6=Dim |
| start_time | TIME | NOT NULL | Heure début |
| end_time | TIME | NOT NULL | Heure fin |
| is_active | BOOLEAN | DEFAULT TRUE | Actif |
| created_at | TIMESTAMP | DEFAULT NOW() | |
| **UNIQUE** | (doctor_id, weekday, start_time, end_time) | | Pas de doublons |

---

### 5. **appointments_appointment** (10 colonnes)
Rendez-vous patient-médecin

| Colonne | Type | Constraints | Description |
|---------|------|-----------|-------------|
| id | BIGSERIAL | PK | |
| patient_id | BIGINT | FK | Patient |
| doctor_id | BIGINT | FK | Médecin |
| scheduled_at | TIMESTAMP | NOT NULL | Date/heure RDV |
| status | VARCHAR(20) | CHECK (pending\|confirmed\|completed\|cancelled\|no_show) | État |
| urgency_level | VARCHAR(20) | CHECK (low\|medium\|high\|critical) | Urgence |
| reason | TEXT | | Motif consultation |
| notes | TEXT | | Notes supplémentaires |
| created_at, updated_at | TIMESTAMP | | |

---

### 6. **medical_records_medicalrecord** (8 colonnes)
Historique médical du patient (1:1)

| Colonne | Type | Constraints | Description |
|---------|------|-----------|-------------|
| id | BIGSERIAL | PK | |
| patient_id | BIGINT | FK, UNIQUE | Patient (1:1) |
| chronic_conditions | TEXT | | Maladies chroniques |
| surgeries_history | TEXT | | Historique chirurgies |
| family_history | TEXT | | Antécédents familiaux |
| immunizations | TEXT | | Vaccinations |
| created_at, updated_at | TIMESTAMP | | |

---

### 7. **medical_records_consultation** (10 colonnes)
Détails consultation (diagnostic, vitaux, plan traitement)

| Colonne | Type | Constraints | Description |
|---------|------|-----------|-------------|
| id | BIGSERIAL | PK | |
| medical_record_id | BIGINT | FK | Historique patient |
| doctor_id | BIGINT | FK | Médecin effectuant |
| appointment_id | BIGINT | FK, UNIQUE, NULL | RDV associé |
| diagnosis | TEXT | NOT NULL | Diagnostic |
| anamnesis | TEXT | | Anamnèse (histoire) |
| vitals | JSONB | | {temperature, bp, hr} |
| icd10_code | VARCHAR(20) | | Code diagnostic ICD-10 |
| treatment_plan | TEXT | | Plan de traitement |
| created_at, updated_at | TIMESTAMP | | |

---

### 8. **prescriptions_prescription** (7 colonnes)
Ordonnance médicale

| Colonne | Type | Constraints | Description |
|---------|------|-----------|-------------|
| id | BIGSERIAL | PK | |
| consultation_id | BIGINT | FK, UNIQUE | Consultation liée |
| doctor_id | BIGINT | FK | Médecin prescripteur |
| patient_id | BIGINT | FK | Patient receveur |
| notes | TEXT | | Notes prescripteur |
| created_at, updated_at | TIMESTAMP | | |

---

### 9. **prescriptions_prescriptionitem** (6 colonnes)
Ligne d'ordonnance (médicament spécifique)

| Colonne | Type | Constraints | Description |
|---------|------|-----------|-------------|
| id | BIGSERIAL | PK | |
| prescription_id | BIGINT | FK | Ordonnance |
| medication | VARCHAR(150) | NOT NULL | Nom médicament |
| dosage | VARCHAR(80) | NOT NULL | Dosage (ex: 500mg) |
| frequency | VARCHAR(80) | NOT NULL | Fréquence (ex: 2x/jour) |
| duration | VARCHAR(80) | NOT NULL | Durée (ex: 7 jours) |
| instructions | TEXT | | Instructions supplémentaires |

---

### 10. **chatbot_chebotsession** (6 colonnes)
Session de chat IA pour triage symptômes

| Colonne | Type | Constraints | Description |
|---------|------|-----------|-------------|
| id | BIGSERIAL | PK | |
| patient_id | BIGINT | FK | Patient |
| title | VARCHAR(120) | | Titre session |
| is_closed | BOOLEAN | DEFAULT FALSE | Session fermée |
| created_at, updated_at | TIMESTAMP | | |

---

### 11. **chatbot_chatbotmessage** (5 colonnes)
Message dans session chat

| Colonne | Type | Constraints | Description |
|---------|------|-----------|-------------|
| id | BIGSERIAL | PK | |
| session_id | BIGINT | FK | Session chat |
| sender | VARCHAR(10) | CHECK (patient\|bot) | Qui envoie |
| content | TEXT | NOT NULL | Contenu message |
| metadata | JSONB | | Analyse IA {urgent, diseases} |
| created_at | TIMESTAMP | DEFAULT NOW() | |

---

### 12. **follow_up_followup** (9 colonnes)
Rendez-vous de suivi post-consultation

| Colonne | Type | Constraints | Description |
|---------|------|-----------|-------------|
| id | BIGSERIAL | PK | |
| patient_id | BIGINT | FK | Patient |
| doctor_id | BIGINT | FK | Médecin suivi |
| consultation_id | BIGINT | FK, NULL | Consultation initiale |
| scheduled_at | TIMESTAMP | NOT NULL | Date suivi |
| status | VARCHAR(20) | CHECK (scheduled\|in_progress\|completed\|missed) | État |
| notes | TEXT | | Notes suivi |
| created_at, updated_at | TIMESTAMP | | |

---

### 13. **follow_up_followupalert** (7 colonnes)
Alertes rappel pour rendez-vous suivi

| Colonne | Type | Constraints | Description |
|---------|------|-----------|-------------|
| id | BIGSERIAL | PK | |
| follow_up_id | BIGINT | FK | Suivi associé |
| alert_type | VARCHAR(10) | CHECK (sms\|email\|push) | Moyen alerte |
| scheduled_at | TIMESTAMP | NOT NULL | Date envoi alerte |
| status | VARCHAR(10) | CHECK (pending\|sent\|failed) | État envoi |
| message | TEXT | | Corps message |
| created_at | TIMESTAMP | DEFAULT NOW() | |

---

### 14. **notifications_notification** (7 colonnes)
Système notifications tableau de bord

| Colonne | Type | Constraints | Description |
|---------|------|-----------|-------------|
| id | BIGSERIAL | PK | |
| recipient_id | BIGINT | FK | Utilisateur destinataire |
| notification_type | VARCHAR(20) | CHECK (system\|appointment\|prescription\|follow_up\|chatbot) | Type |
| title | VARCHAR(120) | NOT NULL | Titre |
| message | TEXT | NOT NULL | Corps |
| is_read | BOOLEAN | DEFAULT FALSE | Lue/non-lue |
| created_at | TIMESTAMP | DEFAULT NOW() | |

---

## 🔗 Relations et Cardinalités

### OneToOne Relations
- `CustomUser` ↔ `PatientProfile` (parent role=patient)
- `CustomUser` ↔ `DoctorProfile` (parent role=doctor)
- `PatientProfile` ↔ `MedicalRecord` (historique patient)
- `Appointment` ↔ `Consultation` (optionnelle)
- `Consultation` ↔ `Prescription` (optionnelle)

### OneToMany Relations
- `PatientProfile` → `Appointment` (patient a plusieurs RDV)
- `PatientProfile` → `Prescription` (patient reçoit plusieurs ordonnances)
- `PatientProfile` → `ChatbotSession` (patient crée plusieurs sessions chat)
- `PatientProfile` → `FollowUp` (patient a plusieurs suivis)
- `DoctorProfile` → `Appointment` (médecin effectue plusieurs RDV)
- `DoctorProfile` → `Consultation` (médecin effectue plusieurs consultations)
- `DoctorProfile` → `Prescription` (médecin prescrit plusieurs ordonnances)
- `DoctorProfile` → `FollowUp` (médecin assure plusieurs suivis)
- `DoctorProfile` → `DoctorAvailabilitySlot` (médecin a plusieurs créneaux)
- `MedicalRecord` → `Consultation` (dossier a plusieurs consultations)
- `Prescription` → `PrescriptionItem` (ordonnance a plusieurs médicaments)
- `ChatbotSession` → `ChatbotMessage` (session a plusieurs messages)
- `FollowUp` → `FollowUpAlert` (suivi a plusieurs alertes)
- `CustomUser` → `Notification` (utilisateur reçoit plusieurs notifications)

---

## 📈 Vues SQL

### `v_active_doctors`
Liste des médecins actifs avec spécialités

```sql
SELECT email, specialization, years_of_experience 
FROM v_active_doctors 
WHERE years_of_experience > 5;
```

### `v_unread_notifications`
Notifications non lues par utilisateur

```sql
SELECT recipient, title, created_at 
FROM v_unread_notifications 
ORDER BY created_at DESC LIMIT 10;
```

### `v_upcoming_appointments`
Rendez-vous à venir

```sql
SELECT patient_email, doctor_email, scheduled_at, urgency_level 
FROM v_upcoming_appointments;
```

### `v_patient_statistics`
Statistiques patient (rendez-vous, consultations, ordonnances)

---

## 🔐 Contraintes d'Intégrité

### CHECK Constraints
- `role` ∈ {patient, doctor, admin}
- `status` (appointments) ∈ {pending, confirmed, completed, cancelled, no_show}
- `urgency_level` ∈ {low, medium, high, critical}
- `blood_group` ∈ {A+, A-, B+, B-, AB+, AB-, O+, O-}
- `gender` ∈ {male, female, other}
- `weekday` ∈ [0, 6]
- `years_of_experience` ≥ 0
- `consultation_fee` ≥ 0

### UNIQUE Constraints
- `email` (global)
- `username` (global)
- `license_number` (médecins)
- `user_id` (PatientProfile, DoctorProfile)
- (doctor_id, weekday, start_time, end_time) - DoctorAvailabilitySlot
- `appointment_id` (Consultation - optionnelle)
- `consultation_id` (Prescription - optionnelle)
- `patient_id` (MedicalRecord)

### FOREIGN KEY CASCADE
Suppression d'un utilisateur → Supprime tout (profil, RDV, consultations, etc.)

---

## 📊 Indexation Stratégique

### Index Primaires (BY PRIMARY BUSINESS QUERIES)

**Recherche Patients**:
- `idx_patients_patientprofile_blood_group`
- `idx_patients_patientprofile_gender`

**Recherche Médecins**:
- `idx_doctors_doctorprofile_specialization`
- `idx_doctors_doctorprofile_license_number`

**Filtrage RDV**:
- `idx_appointments_appointment_status`
- `idx_appointments_appointment_urgency_level`
- `idx_appointments_appointment_scheduled_at`

**Timeline Temporelles**:
- `idx_medical_records_consultation_created_at`
- `idx_notifications_notification_created_at`
- `idx_follow_up_followup_scheduled_at`

**Filtrage État**:
- `idx_notifications_notification_is_read`
- `idx_follow_up_followup_status`

---

## 🚀 Performance & Conseils

### Hypartition (Future)
```sql
CREATE TABLE appointments_appointment_2026_01 
PARTITION OF appointments_appointment
FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
```

### Materialized Views (Future)
```sql
CREATE MATERIALIZED VIEW v_monthly_stats AS
SELECT DATE_TRUNC('month', scheduled_at) as month, 
       COUNT(*) as appointments
FROM appointments_appointment
GROUP BY DATE_TRUNC('month', scheduled_at);
```

### Vacuum & Analyze (Maintenance)
```sql
VACUUM ANALYZE;
```

### Query Optimization
```sql
EXPLAIN ANALYZE
SELECT * FROM appointments_appointment 
WHERE status = 'confirmed' 
AND scheduled_at > NOW();
```

---

## 🔄 Migration depuis SQLite

Pour passer de SQLite (développement) à PostgreSQL (production):

```bash
# 1. Export SQLite
python manage.py dumpdata > data.json

# 2. Configurer PostgreSQL dans settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'meditriage',
        'USER': 'pg_user',
        'PASSWORD': 'secure_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# 3. Créer BD PostgreSQL
createdb meditriage

# 4. Lancer migrations Django
python manage.py migrate

# 5. Charger données
python manage.py loaddata data.json
```

---

## 📋 Checklist Mise en Production

- [ ] Configurer certificats SSL PostgreSQL
- [ ] Sauvegardes automatiques (pg_dump script)
- [ ] Monitoring performance (pg_stat_statements)
- [ ] Logs de transactions (pgaudit extension)
- [ ] Fail-over/Replication (Streaming Replication)
- [ ] Rate limiting API (Django-ratelimit)
- [ ] Data anonymization RGPD (compliant)

---

## 📞 Support

Pour questions sur le schéma, consultez:
- [Django ORM Documentation](https://docs.djangoproject.com/en/6.0/topics/db/models/)
- [PostgreSQL Manual](https://www.postgresql.org/docs/)
- Code source: `BackEnd/*/models.py`

---

**Génération**: 28 mars 2026  
**Version Schéma**: 1.0 (Base initiale, 14 tables, 9 vues, 45+ indexes)
