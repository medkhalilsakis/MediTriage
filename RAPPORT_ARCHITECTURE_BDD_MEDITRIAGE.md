# Architecture de la Base de Donnees - MediTriage

Date: 2026-04-19
Source de verite: modeles Django dans BackEnd/*/models.py
SGBD cible: PostgreSQL (avec compatibilite SQLite pour dev)

## 1) Vision d'architecture

La base de donnees MediTriage est organisee en 5 couches metier:

1. Identite et acces
- authentication_customuser
- tables techniques de permissions/groupes Django

2. Noyau parcours de soin
- patients_patientprofile
- doctors_doctorprofile
- doctors_doctoravailabilityslot
- doctors_doctorleave
- appointments_appointment
- appointments_appointmentadvanceoffer

3. Dossier clinique et actes
- medical_records_medicalrecord
- medical_records_consultation
- medical_records_doctoroperation
- medical_records_medicaldocumentrequest
- medical_records_medicaldocument
- prescriptions_prescription
- prescriptions_prescriptionitem
- follow_up_followup
- follow_up_followupalert

4. IA, communication et engagement
- chatbot_chatbotsession
- chatbot_chatbotmessage
- messaging_conversation
- messaging_directmessage
- messaging_userpresence
- notifications_notification

5. Tables techniques framework
- django_migrations, django_content_type, django_session, etc.

## 2) Modele logique (tables applicatives)

### 2.1 Identite

authentication_customuser
- PK: id
- Champs cles: email (unique), username, role (patient|doctor|admin), is_active, is_verified
- Role: identite centrale et controle d'acces

patients_patientprofile
- PK: id
- FK: user_id -> authentication_customuser (OneToOne)
- Champs cles: dob, gender, blood_group, allergies
- Gouvernance suppression: is_account_deleted, account_deleted_at, deleted_by

doctors_doctorprofile
- PK: id
- FK: user_id -> authentication_customuser (OneToOne)
- Champs cles: specialization, department, license_number (unique), consultation_fee

### 2.2 Planification des soins

doctors_doctoravailabilityslot
- PK: id
- FK: doctor_id -> doctors_doctorprofile (ManyToOne)
- Contrainte: unique (doctor, weekday, start_time, end_time)
- Role: fenetres de disponibilite hebdomadaire

doctors_doctorleave
- PK: id
- FK: doctor_id -> doctors_doctorprofile
- FK: created_by, reviewed_by -> authentication_customuser
- Champs cles: status (pending|approved|rejected|cancelled), is_active, start_date, end_date
- Contrainte: end_date >= start_date

appointments_appointment
- PK: id
- FK: patient_id -> patients_patientprofile
- FK: doctor_id -> doctors_doctorprofile
- Champs cles: scheduled_at, status, urgency_level, department, reason
- Suivi staff: last_staff_action_at

appointments_appointmentadvanceoffer
- PK: id
- FK: appointment_id -> appointments_appointment
- FK: offered_doctor_id -> doctors_doctorprofile
- FK: requested_by_id -> authentication_customuser
- Champs cles: offered_slot, status, expires_at
- Contrainte: une seule offre pending par appointment

### 2.3 Dossier medical

medical_records_medicalrecord
- PK: id
- FK: patient_id -> patients_patientprofile (OneToOne)
- Etat: status (active|closed|archived), closed_at, archived_at, archived_by
- Champs cliniques structures: diagnostic_summary, treatment_management, follow_up_plan
- Extension analytique: specialty_assessments (JSON), longitudinal_metrics (JSON)

medical_records_consultation
- PK: id
- FK: medical_record_id -> medical_records_medicalrecord
- FK: doctor_id -> doctors_doctorprofile
- FK: appointment_id -> appointments_appointment (OneToOne optionnel)
- Champs cles: diagnosis, chatbot_diagnosis, vitals (JSON), icd10_code
- Orientation: out_of_specialty_confirmed, redirect_to_colleague, redirected_to_doctor, redirected_appointment

medical_records_doctoroperation
- PK: id
- FK: medical_record_id -> medical_records_medicalrecord
- FK: consultation_id -> medical_records_consultation (optionnel)
- FK: doctor_id -> doctors_doctorprofile
- FK: finished_by_id -> authentication_customuser
- Champs cles: scheduled_start, expected_duration_minutes, expected_end_at, release_at
- Regles: calcul automatique expected_end_at et release_at

medical_records_medicaldocumentrequest
- PK: id
- FK: medical_record_id -> medical_records_medicalrecord
- FK: doctor_id -> doctors_doctorprofile
- Champs cles: request_type, status, requested_items (JSON), due_date

medical_records_medicaldocument
- PK: id
- FK: medical_record_id -> medical_records_medicalrecord
- FK: request_id -> medical_records_medicaldocumentrequest (optionnel)
- FK: uploaded_by_patient_id -> patients_patientprofile (optionnel)
- FK: uploaded_by_doctor_id -> doctors_doctorprofile (optionnel)
- FK: reviewed_by_id -> doctors_doctorprofile (optionnel)
- Champs cles: document_type, file, review_status

prescriptions_prescription
- PK: id
- FK: consultation_id -> medical_records_consultation (OneToOne)
- FK: doctor_id -> doctors_doctorprofile
- FK: patient_id -> patients_patientprofile

prescriptions_prescriptionitem
- PK: id
- FK: prescription_id -> prescriptions_prescription
- Champs cles: medication, dosage, frequency, duration

follow_up_followup
- PK: id
- FK: patient_id -> patients_patientprofile
- FK: doctor_id -> doctors_doctorprofile
- FK: consultation_id -> medical_records_consultation (optionnel)
- Champs cles: scheduled_at, status

follow_up_followupalert
- PK: id
- FK: follow_up_id -> follow_up_followup
- Champs cles: alert_type (sms|email|push), status (pending|sent|failed), scheduled_at

### 2.4 IA et communication

chatbot_chatbotsession
- PK: id
- FK: patient_id -> patients_patientprofile
- FK: booked_appointment_id -> appointments_appointment (OneToOne optionnel)
- Champs cles: awaiting_appointment_confirmation, latest_analysis (JSON), is_closed

chatbot_chatbotmessage
- PK: id
- FK: session_id -> chatbot_chatbotsession
- Champs cles: sender (patient|bot), content, metadata (JSON)

messaging_conversation
- PK: id
- FK: participant_low_id -> authentication_customuser
- FK: participant_high_id -> authentication_customuser
- FK: created_by_id -> authentication_customuser (optionnel)
- Contraintes:
  - unique(participant_low, participant_high)
  - participants distincts

messaging_directmessage
- PK: id
- FK: conversation_id -> messaging_conversation
- FK: sender_id -> authentication_customuser
- FK: recipient_id -> authentication_customuser
- Champs cles: content, is_read, created_at

messaging_userpresence
- PK: id
- FK: user_id -> authentication_customuser (OneToOne)
- Champs cles: is_online, last_seen

notifications_notification
- PK: id
- FK: recipient_id -> authentication_customuser
- Champs cles: notification_type, title, is_read, created_at

## 3) Cardinalites critiques

- CustomUser 1 - 0..1 PatientProfile
- CustomUser 1 - 0..1 DoctorProfile
- PatientProfile 1 - 0..* Appointment
- DoctorProfile 1 - 0..* Appointment
- PatientProfile 1 - 1 MedicalRecord
- MedicalRecord 1 - 0..* Consultation
- Appointment 1 - 0..1 Consultation
- Consultation 1 - 0..1 Prescription
- Prescription 1 - 1..* PrescriptionItem
- PatientProfile 1 - 0..* ChatbotSession
- ChatbotSession 1 - 0..* ChatbotMessage
- Consultation 1 - 0..* FollowUp
- FollowUp 1 - 0..* FollowUpAlert
- Conversation 1 - 0..* DirectMessage
- CustomUser 1 - 0..* Notification

## 4) Contraintes d'integrite metier

- Unicite identite
- email unique (CustomUser)
- license_number unique (DoctorProfile)

- Integrite temporelle
- DoctorLeave: end_date >= start_date
- Appointment/FollowUp/Referral: validation metier sur slots 30 minutes, fenetre 08:00-16:00, pas dimanche

- Integrite de parcours
- Un dossier medical par patient (OneToOne)
- Une consultation par rendez-vous (OneToOne optionnel)
- Une ordonnance par consultation (OneToOne)
- Une conversation par paire d'utilisateurs (messaging)

- Archivage et retention
- Suppression patient: anonymisation + archivage des historiques, conservation des liens cliniques

## 5) Indexation et performance (existante)

Index explicites observes dans les modeles:
- messaging_directmessage(conversation, created_at)
- messaging_directmessage(recipient, is_read)
- medical_records_doctoroperation(doctor, scheduled_start)
- medical_records_doctoroperation(doctor, release_at)

Indexes implicites Django:
- toutes les FK principales (appointments, consultations, prescriptions, follow-up, notifications, messages)

Contraintes structurantes:
- unique_pending_offer_per_appointment (AppointmentAdvanceOffer)
- messaging_unique_participant_pair
- messaging_distinct_participants

## 6) Diagramme ER (Mermaid)

~~~mermaid
erDiagram
  authentication_customuser ||--o| patients_patientprofile : has
  authentication_customuser ||--o| doctors_doctorprofile : has
  authentication_customuser ||--o{ notifications_notification : receives

  doctors_doctorprofile ||--o{ doctors_doctoravailabilityslot : owns
  doctors_doctorprofile ||--o{ doctors_doctorleave : requests

  patients_patientprofile ||--o{ appointments_appointment : books
  doctors_doctorprofile ||--o{ appointments_appointment : attends
  appointments_appointment ||--o{ appointments_appointmentadvanceoffer : has

  patients_patientprofile ||--|| medical_records_medicalrecord : owns
  medical_records_medicalrecord ||--o{ medical_records_consultation : contains
  appointments_appointment o|--|| medical_records_consultation : linked_to
  doctors_doctorprofile ||--o{ medical_records_consultation : writes

  medical_records_consultation ||--o| prescriptions_prescription : generates
  prescriptions_prescription ||--|{ prescriptions_prescriptionitem : contains

  medical_records_medicalrecord ||--o{ medical_records_medicaldocumentrequest : asks
  medical_records_medicalrecord ||--o{ medical_records_medicaldocument : stores
  medical_records_medicaldocumentrequest o|--o{ medical_records_medicaldocument : fulfilled_by

  medical_records_consultation ||--o{ follow_up_followup : triggers
  follow_up_followup ||--o{ follow_up_followupalert : alerts

  patients_patientprofile ||--o{ chatbot_chatbotsession : opens
  chatbot_chatbotsession ||--o{ chatbot_chatbotmessage : contains
  chatbot_chatbotsession o|--o| appointments_appointment : booked_appointment

  authentication_customuser ||--o{ messaging_directmessage : sends
  authentication_customuser ||--o{ messaging_directmessage : receives
  messaging_conversation ||--o{ messaging_directmessage : has
  authentication_customuser ||--o| messaging_userpresence : presence
~~~

## 7) Flux de donnees principaux

- Flux triage IA -> rendez-vous
PatientProfile -> ChatbotSession -> ChatbotMessage(metadata) -> Appointment -> Consultation -> MedicalRecord

- Flux consultation -> ordonnance
Appointment -> Consultation -> Prescription -> PrescriptionItem

- Flux suivi
Consultation -> FollowUp -> FollowUpAlert -> Notification

- Flux orientation hors specialite
Consultation(refer) -> Appointment(autre docteur) -> Notification(patient + docteur cible)

## 8) Recommandations d'evolution schema

1. Ajouter un index compose sur appointments_appointment(doctor_id, scheduled_at, status) pour accelerer les ecrans planning.
2. Ajouter un index partiel notifications_notification(recipient_id) WHERE is_read=false pour la boite de notification.
3. Ajouter un index GIN sur chatbot_chatbotmessage.metadata si usage analytique fort des JSON.
4. En production PostgreSQL, activer des migrations SQL versionnees et eviter les scripts statiques divergents.

## 9) Fichiers de reference

- BackEnd/authentication/models.py
- BackEnd/patients/models.py
- BackEnd/doctors/models.py
- BackEnd/appointments/models.py
- BackEnd/medical_records/models.py
- BackEnd/prescriptions/models.py
- BackEnd/chatbot/models.py
- BackEnd/follow_up/models.py
- BackEnd/notifications/models.py
- BackEnd/messaging/models.py
