# Rapport UML - MediTriage

Date: 2026-04-19
Perimetre: plateforme de triage medical intelligent, gestion des rendez-vous, dossier medical, suivi, messagerie et pilotage admin.

## 1) Acteurs metier

- Patient: decrit ses symptomes, consulte le pre-diagnostic, prend et suit ses rendez-vous, accede a son dossier, echange des messages.
- Docteur: prend en charge les rendez-vous, cree consultation/dossier, propose orientation, assure le suivi.
- Admin: gouvernance des comptes, supervision rendez-vous, statistiques globales.
- Chatbot: acteur systeme intelligent qui analyse les symptomes, propose pre-diagnostic/orientation et peut declencher une reservation guidee.

## 2) Cas d'utilisation demandes: acteurs concernes + scenario

| ID | Cas d'utilisation | Patient | Docteur | Admin | Chatbot | Scenario nominal (resume) |
|---|---|---|---|---|---|---|
| UC01 | S'inscrire | X | X | - | X (indirect) | L'utilisateur soumet email, mot de passe, role. Le systeme valide les donnees, cree le compte CustomUser, puis le profil PatientProfile ou DoctorProfile. Retour JWT. |
| UC02 | S'authentifier | X | X | X | - | L'utilisateur envoie email/mot de passe. Le backend valide et retourne access/refresh token + role. Le frontend active les routes protegees. |
| UC03 | Decrire ses symptomes | X | - | - | X | Le patient envoie un message de symptomes (session privee ou endpoint public). Le chatbot extrait symptomes, contexte et niveau de gravite. |
| UC04 | Consulter le pre-diagnostic | X | - | - | X | Le chatbot retourne un pre-diagnostic structure: maladies probables, urgence, departement suggere, precautions, recommandation de rendez-vous. |
| UC05 | Gerer un rendez-vous (patient) | X | X | X | X (option booking) | Le patient cree/annule/reprogramme. Le systeme auto-assigne medecin + slot (30 min, 08:00-16:00, pas dimanche, charge max/heure). Le docteur/admin peut confirmer/ajuster. |
| UC06 | Acceder a son dossier medical | X | X | X | - | L'utilisateur authentifie consulte le dossier selon ses droits: patient=propre dossier, docteur=dossiers lies a ses consultations, admin=tous. |
| UC07 | Initier une conversation avec chatbot | X | - | - | X | Le patient (ou visiteur public) ouvre une session chatbot. Les messages sont historises, l'analyse courante est conservee. |
| UC08 | Recevoir notifications et rappels | X | X | X | - | Le systeme envoie notifications (rendez-vous, suivi, systeme, prescription) et alertes de suivi. L'utilisateur liste puis marque comme lu. |
| UC09 | Proposer une orientation medicale | X (recepteur) | X | X | X | Chatbot suggere un departement. En consultation, docteur/admin peut referer vers collegue (auto selection possible) ou notifier patient de reconsulter une autre specialite. |
| UC10 | Gerer le dossier medical | X (contribution docs) | X | X | - | Docteur/admin cree et met a jour les sections du dossier, demande/revoit des documents, change l'etat (actif, clos, archive). Patient peut deposer documents. |
| UC11 | Assurer le suivi post-consultation | X | X | X | - | Depuis une consultation, creation d'un follow-up + rendez-vous de suivi, puis notifications/alertes. Le statut de suivi evolue (scheduled, in_progress, completed, missed). |
| UC12 | Gerer les comptes utilisateurs | X (self) | X (self) | X | - | Admin desactive/reactive comptes docteurs et archive comptes patients. Chaque role peut gerer son propre profil via /auth/me. |
| UC13 | Gerer les rendez-vous (staff/admin) | X (impacte) | X | X | - | Docteur/admin pilote le cycle: today, accept, complete, delay, reassign. Les workflows auto-postpone, leave redistribution et advance-offers s'appliquent. |
| UC14 | Echanger des messages | X | X | X | - | Utilisateur ouvre conversation selon regles de contact autorisees, envoie/recoit messages directs, presence online via heartbeat. |
| UC15 | Consulter les statistiques | - | - | X | - | Admin consulte les KPIs consolides (volumes, statuts, departements, tendances, taux, charge medecins) via endpoint d'analytics. |

## 3) Diagramme global de cas d'utilisation (PlantUML)

~~~plantuml
@startuml
left to right direction
skinparam packageStyle rectangle

actor Patient
actor Docteur
actor Admin
actor Chatbot

rectangle "MediTriage" {
  usecase "UC01 S'inscrire" as UC01
  usecase "UC02 S'authentifier" as UC02
  usecase "UC03 Decrire symptomes" as UC03
  usecase "UC04 Consulter pre-diagnostic" as UC04
  usecase "UC05 Gerer un rendez-vous" as UC05
  usecase "UC06 Acceder dossier medical" as UC06
  usecase "UC07 Initier conversation chatbot" as UC07
  usecase "UC08 Recevoir notifications/rappels" as UC08
  usecase "UC09 Proposer orientation medicale" as UC09
  usecase "UC10 Gerer dossier medical" as UC10
  usecase "UC11 Assurer suivi post-consultation" as UC11
  usecase "UC12 Gerer comptes utilisateurs" as UC12
  usecase "UC13 Gerer les rendez-vous (staff)" as UC13
  usecase "UC14 Echanger messages" as UC14
  usecase "UC15 Consulter statistiques" as UC15
}

Patient -- UC01
Patient -- UC02
Patient -- UC03
Patient -- UC04
Patient -- UC05
Patient -- UC06
Patient -- UC07
Patient -- UC08
Patient -- UC11
Patient -- UC14

Docteur -- UC01
Docteur -- UC02
Docteur -- UC05
Docteur -- UC06
Docteur -- UC08
Docteur -- UC09
Docteur -- UC10
Docteur -- UC11
Docteur -- UC13
Docteur -- UC14

Admin -- UC02
Admin -- UC05
Admin -- UC06
Admin -- UC08
Admin -- UC09
Admin -- UC10
Admin -- UC11
Admin -- UC12
Admin -- UC13
Admin -- UC14
Admin -- UC15

Chatbot -- UC03
Chatbot -- UC04
Chatbot -- UC07
Chatbot -- UC09

UC04 ..> UC03 : <<include>>
UC05 ..> UC04 : <<extend>>
UC11 ..> UC10 : <<include>>
UC13 ..> UC05 : <<include>>
@enduml
~~~

## 4) Diagramme de classes metier (Mermaid)

~~~mermaid
classDiagram

class CustomUser {
  +id
  +email
  +role
  +is_active
}

class PatientProfile {
  +dob
  +gender
  +blood_group
  +is_account_deleted
}

class DoctorProfile {
  +specialization
  +department
  +license_number
  +years_of_experience
}

class Appointment {
  +scheduled_at
  +status
  +urgency_level
  +department
  +reason
}

class MedicalRecord {
  +status
  +consultation_motive
  +diagnostic_summary
  +follow_up_plan
}

class Consultation {
  +diagnosis
  +chatbot_diagnosis
  +icd10_code
  +redirect_to_colleague
}

class Prescription {
  +created_at
}

class PrescriptionItem {
  +medication
  +dosage
  +frequency
  +duration
}

class ChatbotSession {
  +title
  +awaiting_appointment_confirmation
  +is_closed
}

class ChatbotMessage {
  +sender
  +content
  +metadata
}

class FollowUp {
  +scheduled_at
  +status
}

class FollowUpAlert {
  +alert_type
  +status
  +scheduled_at
}

class Notification {
  +notification_type
  +title
  +is_read
}

class Conversation {
  +participant_low
  +participant_high
  +last_message_at
}

class DirectMessage {
  +content
  +is_read
  +created_at
}

class UserPresence {
  +is_online
  +last_seen
}

CustomUser "1" --> "0..1" PatientProfile
CustomUser "1" --> "0..1" DoctorProfile
CustomUser "1" --> "0..*" Notification
CustomUser "1" --> "0..1" UserPresence

PatientProfile "1" --> "0..*" Appointment
DoctorProfile "1" --> "0..*" Appointment
PatientProfile "1" --> "1" MedicalRecord
MedicalRecord "1" --> "0..*" Consultation
Consultation "0..1" --> "1" Appointment
Consultation "1" --> "1" DoctorProfile
Consultation "1" --> "0..1" Prescription
Prescription "1" --> "1..*" PrescriptionItem

PatientProfile "1" --> "0..*" ChatbotSession
ChatbotSession "1" --> "0..*" ChatbotMessage
ChatbotSession "0..1" --> "1" Appointment : booked_appointment

Consultation "1" --> "0..*" FollowUp
FollowUp "1" --> "0..*" FollowUpAlert

Conversation "1" --> "0..*" DirectMessage
DirectMessage "1" --> "1" CustomUser : sender
DirectMessage "1" --> "1" CustomUser : recipient
~~~

## 5) Diagrammes de sequence cles

### 5.1 Inscription puis authentification

~~~mermaid
sequenceDiagram
  autonumber
  actor U as Utilisateur
  participant FE as Frontend
  participant AUTH as Auth API
  participant DB as DB

  U->>FE: Remplir formulaire inscription
  FE->>AUTH: POST /api/auth/register
  AUTH->>DB: Creer CustomUser + profile (patient/doctor)
  DB-->>AUTH: User cree
  AUTH-->>FE: access + refresh + user

  U->>FE: Login
  FE->>AUTH: POST /api/auth/login
  AUTH->>DB: Verifier identifiants
  DB-->>AUTH: OK
  AUTH-->>FE: access + refresh + role
~~~

### 5.2 Triage chatbot, pre-diagnostic et booking guide

~~~mermaid
sequenceDiagram
  autonumber
  actor P as Patient
  participant FE as Frontend
  participant CB as Chatbot API
  participant AI as AI Service
  participant APP as Appointment Service
  participant DB as DB

  P->>FE: Decrire symptomes
  FE->>CB: POST /api/chatbot/sessions/{id}/message
  CB->>AI: build_health_chat_response(symptomes)
  AI-->>CB: probable_diseases + urgence + departement
  CB-->>FE: Pre-diagnostic + question "book now?"

  P->>FE: Repond "yes"
  FE->>CB: POST /message (yes)
  CB->>APP: assign_doctor_and_slot()
  APP->>DB: Creer Appointment (auto-assign)
  DB-->>APP: Appointment confirme
  CB->>DB: Maj ChatbotSession(booked_appointment, is_closed)
  CB-->>FE: Confirmation rendez-vous
~~~

### 5.3 Consultation, orientation et suivi post-consultation

~~~mermaid
sequenceDiagram
  autonumber
  actor D as Docteur
  participant FE as Frontend Docteur
  participant MR as MedicalRecords API
  participant APP as Appointments API
  participant FU as FollowUp API
  participant N as Notifications API
  participant DB as DB

  D->>FE: Ouvrir appointment du jour
  FE->>MR: POST /consultations/create-from-appointment
  MR->>DB: get/create MedicalRecord + create Consultation
  MR->>APP: set Appointment.status=completed
  MR-->>FE: Consultation creee

  alt Orientation vers collegue
    D->>FE: Demander referral
    FE->>MR: POST /consultations/{id}/refer
    MR->>DB: Creer Appointment de referral
    MR->>N: Notifier patient (+ collegue cible)
    MR-->>FE: Referral confirme
  else Suivi standard
    D->>FE: Planifier follow-up
    FE->>MR: POST /consultations/{id}/schedule-follow-up
    MR->>DB: Creer FollowUp + Appointment
    MR->>N: Notifier patient
    MR-->>FE: Follow-up planifie
  end
~~~

### 5.4 Messagerie securisee entre roles

~~~mermaid
sequenceDiagram
  autonumber
  actor A as Utilisateur A
  actor B as Utilisateur B
  participant MSG as Messaging API
  participant DB as DB

  A->>MSG: GET /api/messaging/contacts
  MSG->>DB: Calcul contacts autorises + presence
  MSG-->>A: Liste contacts

  A->>MSG: POST /api/messaging/conversations (recipient_id)
  MSG->>DB: get_or_create Conversation
  MSG-->>A: Conversation

  A->>MSG: POST /conversations/{id}/messages
  MSG->>DB: Creer DirectMessage
  MSG-->>A: Message envoye

  B->>MSG: GET /conversations/{id}/messages
  MSG->>DB: Lire messages + mark read
  MSG-->>B: Historique messages

  A->>MSG: POST /presence/heartbeat
  B->>MSG: POST /presence/heartbeat
~~~

## 6) Mapping rapide cas d'utilisation -> endpoints backend

- UC01: POST /api/auth/register
- UC02: POST /api/auth/login, POST /api/auth/token/refresh, GET/PATCH/DELETE /api/auth/me
- UC03-UC04-UC07: POST /api/chatbot/public/message, /api/chatbot/sessions, /api/chatbot/sessions/{id}/message
- UC05-UC13: /api/appointments + actions today, accept, complete, delay, reassign, request-reschedule, advance-offers/respond
- UC06-UC10: /api/medical-records/records, /consultations, /requests, /documents + close/archive/reopen
- UC09: /api/medical-records/consultations/{id}/refer + orientation chatbot
- UC11: /api/medical-records/consultations/{id}/schedule-follow-up + /api/follow-up
- UC08: /api/notifications + mark-all-read, /api/follow-up/alerts
- UC12: /api/doctors/profiles/{id}/deactivate|reactivate, /api/patients/{id}/delete-account, /api/auth/me
- UC14: /api/messaging/contacts, /conversations, /messages, /presence/heartbeat, /summary
- UC15: GET /api/admin/stats

## 7) Notes de modelisation

- Le role Chatbot est un acteur systeme (non humain) qui influence UC03, UC04, UC07 et UC09.
- UC05 et UC13 sont separes pour distinguer la vue patient (un rendez-vous personnel) et la vue staff/admin (pilotage global).
- Les regles de planning (30 min, 08:00-16:00, pas dimanche, charge max medecin/heure) doivent etre explicitees dans les contraintes du modele.
- L'orientation medicale existe a deux niveaux: orientation algorithmique (chatbot) et orientation clinique (refer depuis consultation).
