# Demo Platform Scenario

Ce scenario fournit un jeu de donnees complet pour la plateforme:
- 1 admin
- 5 docteurs
- 10 patients
- 10 rendez-vous
- consultations, prescriptions, suivi, notifications, demande de documents

## 1) Charger les donnees demo

Depuis le dossier `BackEnd`:

```bash
python manage.py seed_demo_platform --reset
```

Options utiles:

```bash
python manage.py seed_demo_platform --password "DemoPass123!"
python manage.py seed_demo_platform
```

- `--reset` supprime d abord les comptes demo `*@demo.meditriage.local`.
- Sans `--reset`, la commande est idempotente et met a jour les enregistrements existants.

## 2) Comptes de connexion

Mot de passe par defaut pour tous les comptes:

```text
DemoPass123!
```

### Admin
- email: `admin@demo.meditriage.local`

### Docteurs (5)
- `dr_amina@demo.meditriage.local` (general medicine)
- `dr_yacine@demo.meditriage.local` (cardiology)
- `dr_samira@demo.meditriage.local` (respiratory)
- `dr_karim@demo.meditriage.local` (neurology)
- `dr_lyna@demo.meditriage.local` (dermatology)

### Patients (10)
- `patient01@demo.meditriage.local`
- `patient02@demo.meditriage.local`
- `patient03@demo.meditriage.local`
- `patient04@demo.meditriage.local`
- `patient05@demo.meditriage.local`
- `patient06@demo.meditriage.local`
- `patient07@demo.meditriage.local`
- `patient08@demo.meditriage.local`
- `patient09@demo.meditriage.local`
- `patient10@demo.meditriage.local`

## 3) Donnees generees

La commande cree/met a jour:
- 5 profils docteurs avec disponibilite Lundi-Vendredi 08:00-16:00
- 10 profils patients
- 10 rendez-vous avec statuts varies (`completed`, `confirmed`, `pending`, `cancelled`, `no_show`)
- 3 consultations reliees a des rendez-vous completes
- 2 prescriptions avec items medicamenteux
- 2 suivis post-consultation + alertes
- 1 demande de documents medicaux
- notifications systeme/rendez-vous/suivi
- 1 demande de conge en attente pour un docteur

## 4) Scenario complet de demonstration (parcours metier)

### Etape A - Pilotage admin
1. Se connecter avec `admin@demo.meditriage.local`.
2. Ouvrir le dashboard admin:
   - verifier les KPI utilisateurs, rendez-vous et urgences.
   - verifier la section conges en attente.
3. Aller dans Users:
   - visualiser la separation patients/docteurs.
   - tester activation/desactivation docteur.

### Etape B - Parcours patient
1. Se connecter avec `patient06@demo.meditriage.local`.
2. Ouvrir le dashboard patient:
   - verifier RDV a venir et notifications.
   - observer l historique medical deja present pour certains patients.
3. Effectuer une demande de RDV directe (optionnelle) pour tester le routing auto.

### Etape C - Parcours docteur (operations quotidiennes)
1. Se connecter avec `dr_amina@demo.meditriage.local`.
2. Ouvrir Doctor Dashboard:
   - verifier calendrier mensuel, patients du jour et historique.
3. Sur un RDV `pending`, utiliser action `Accept` puis `Complete`.
4. Ouvrir le dossier medical depuis `Open medical dossier`.

### Etape D - Consultation et continuite de soins
1. Sur consultation creee:
   - renseigner diagnostic, examen, plan de traitement.
2. Verifier dans l historique docteur que la consultation est visible.
3. Verifier prescription associee sur les cas deja completes.

### Etape E - Suivi et documents
1. Verifier les suivis planifies (follow-up) et les alertes.
2. Verifier la demande de documents medicaux en attente.
3. Cote patient, verifier centre notifications et section documents.

### Etape F - Validation transversale
1. Verifier anonymisation/retention historique si suppression compte patient (si vous testez ce flux).
2. Verifier coherence entre:
   - dashboard admin (volume global)
   - dashboard docteur (charge et historique)
   - dashboard patient (parcours individuel)

## 5) Recommandation de demo en reunion

Ordre conseille (15-20 min):
1. Admin dashboard (vue globale)
2. Users governance (patients/docteurs)
3. Patient dashboard (demande RDV + notifications)
4. Doctor dashboard (accept/complete + dossier)
5. Follow-up + document request + prescription

Ce flux couvre le cycle complet: triage -> RDV -> consultation -> prescription -> suivi -> gouvernance admin.
