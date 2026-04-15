# 📑 INDEX - Base de Données PostgreSQL MediTriage

## 🎯 Accès Rapide par Besoin

### Je veux...

#### ✅ **Démarrer immédiatement**
1. Lire: [SQL_DATABASE_README.md](SQL_DATABASE_README.md) (5 min)
2. Exécuter: `psql -f database_schema.sql` (2 min)
3. Configurer: [DJANGO_POSTGRESQL_CONFIG.md](DJANGO_POSTGRESQL_CONFIG.md) (5 min)
4. Tester: `python manage.py check` (1 min)

**Temps total**: ~15 minutes ⏱️

---

#### 📖 **Comprendre la structure**
→ [DATABASE_DOCUMENTATION.md](DATABASE_DOCUMENTATION.md)
- Schéma des 14 tables
- Relations one-to-one/many
- Indexes & constraints
- Vues SQL
- Performance tips

---

#### 🔧 **Installer PostgreSQL**
→ [POSTGRESQL_SETUP_GUIDE.md](POSTGRESQL_SETUP_GUIDE.md)
- Étapes 1-10 détaillées
- Alternatives (pgAdmin, CLI)
- Troubleshooting
- Backups automatisés
- Sécurité/SSL

---

#### 💾 **Obtenir le code SQL brut**
→ [database_schema.sql](database_schema.sql)
- 1200+ lignes SQL PostgreSQL prêt à utiliser
- Copier-coller dans pgAdmin ou psql
- Toutes tables, indexes, vues, constraints

---

#### 🧪 **Exécuter des requêtes**
→ [USEFUL_SQL_QUERIES.sql](USEFUL_SQL_QUERIES.sql)
**12 catégories**:
1. Statistiques générales
2. Requêtes patients
3. Requêtes médecins
4. Rendez-vous
5. Dossiers médicaux
6. Ordonnances
7. Sessions chatbot
8. Suivi post-consultation
9. Notifications
10. Rapports & analytics
11. Nettoyage & maintenance
12. Intégrité & validation

---

#### ⚙️ **Configurer Django pour PostgreSQL**
→ [DJANGO_POSTGRESQL_CONFIG.md](DJANGO_POSTGRESQL_CONFIG.md)
- settings.py (Database section)
- .env file template
- requirements.txt (updated)
- Docker configuration (optional)
- Nginx setup (production)
- SSL/TLS setup

---

## 📊 Table Matrice (Quelle Table Pour Quel Besoin)

| Besoin | Table | Fichier |
|--------|-------|---------|
| Lister patients | `patients_patientprofile` | [DATABASE_DOCUMENTATION.md](DATABASE_DOCUMENTATION.md#2-patientspatientprofile-10-colonnes) |
| Lister médecins | `doctors_doctorprofile` | [DATABASE_DOCUMENTATION.md](DATABASE_DOCUMENTATION.md#3-doctorsdoctorprofile-9-colonnes) |
| Voir RDV | `appointments_appointment` | [DATABASE_DOCUMENTATION.md](DATABASE_DOCUMENTATION.md#5-appointmentsappointment-10-colonnes) |
| Créer consultation | `medical_records_consultation` | [DATABASE_DOCUMENTATION.md](DATABASE_DOCUMENTATION.md#7-medical_recordsconsultation-10-colonnes) |
| Prescrire | `prescriptions_prescription` | [DATABASE_DOCUMENTATION.md](DATABASE_DOCUMENTATION.md#8-prescriptionsprescription-7-colonnes) |
| Chat IA | `chatbot_chebotsession` | [DATABASE_DOCUMENTATION.md](DATABASE_DOCUMENTATION.md#10-chatbotchebotsession-6-colonnes) |
| Notifier | `notifications_notification` | [DATABASE_DOCUMENTATION.md](DATABASE_DOCUMENTATION.md#14-notificationsnotification-7-colonnes) |

---

## 🚀 Workflow par Cas d'Usage

### Cas 1: Nouvelle Installation (Production)

```
1. POSTGRESQL_SETUP_GUIDE.md → Étapes 1-5 (Installer & créer BD)
2. database_schema.sql → Charger schema
3. DJANGO_POSTGRESQL_CONFIG.md → Configurer Django
4. POSTGRESQL_SETUP_GUIDE.md → Étapes 6-10 (Backups, sécurité)
✅ Prêt!
```

**Temps**: ~1 heure

---

### Cas 2: Migration SQLite → PostgreSQL

```
1. POSTGRESQL_SETUP_GUIDE.md → Étape 2 (Créer BD)
2. database_schema.sql → Charger schema
3. POSTGRESQL_SETUP_GUIDE.md → Étape 6 (Charger données)
4. DJANGO_POSTGRESQL_CONFIG.md → Changer settings.py
5. Exécuter: python manage.py migrate
✅ Migré!
```

**Temps**: ~30 minutes

---

### Cas 3: Analyser/Requêter Données

```
1. USEFUL_SQL_QUERIES.sql → Choisir requête
2. Adapter paramètres
3. Exécuter via:
   - psql (CLI)
   - pgAdmin (GUI)
   - Django shell
✅ Résultats!
```

**Temps**: ~5 minutes/requête

---

### Cas 4: Optimiser Performance

```
1. DATABASE_DOCUMENTATION.md → Section Performance
2. USEFUL_SQL_QUERIES.sql → Requêtes analytics
3. POSTGRESQL_SETUP_GUIDE.md → Étape 8 (Monitoring)
4. Exécuter: VACUUM ANALYZE;
✅ Optimisé!
```

**Temps**: ~20 minutes

---

## 📋 Fichiers Détail

### File 1: `database_schema.sql` (1200+ lines)
**Type**: SQL brut PostgreSQL  
**Pour**: Déployer la BD
**Format**: .sql (copy-paste ready)  
**Contient**:
- [ ] 14 tables
- [ ] M2M tables (groups, permissions)  
- [ ] 9 vues SQL
- [ ] 45+ indexes
- [ ] Constraints complets

**Usage**:
```bash
psql -U meditriage_user -d meditriage -f database_schema.sql
```

---

### File 2: `DATABASE_DOCUMENTATION.md` (400+ lines)
**Type**: Markdown documentation  
**Pour**: Comprendre structure
**Format**: .md (lire dans éditeur)  
**Contient**:
- [ ] Architecture modulaire
- [ ] Description 14 tables
- [ ] Cardinalités relations
- [ ] Constraints & intégrité
- [ ] Vues SQL
- [ ] Conseils performance

**Usage**:
```
Lire section "Tableau des Tables" pour schema complet
```

---

### File 3: `POSTGRESQL_SETUP_GUIDE.md` (500+ lines)
**Type**: Step-by-step guide  
**Pour**: Installer & configurer PostgreSQL
**Format**: .md (copy-paste commands)  
**Contient**:
- [ ] 10 étapes détaillées
- [ ] Commandes exactes
- [ ] Alternatives (pgAdmin, GUI)
- [ ] Troubleshooting
- [ ] Backups/restore
- [ ] Sécurité SSL/TLS

**Usage**:
```
Suivre Étape 1 → Étape 10 séquentiellement
```

---

### File 4: `USEFUL_SQL_QUERIES.sql` (800+ lines)
**Type**: SQL queries collection  
**Pour**: Requêter les données
**Format**: .sql (copy-paste queries)  
**Contient**:
- [ ] 100+ requêtes prêtes
- [ ] 12 catégories
- [ ] Exemples pratiques
- [ ] Statistiques
- [ ] Analytics
- [ ] Maintenance

**Usage**:
```bash
# Load all
psql -U meditriage_user -d meditriage -f USEFUL_SQL_QUERIES.sql

# Or copy individual queries
```

---

### File 5: `SQL_DATABASE_README.md` (300+ lines)
**Type**: Overview & index  
**Pour**: Navigation & démarrage rapide
**Format**: .md (lire dans éditeur)  
**Contient**:
- [ ] Vue d'ensemble
- [ ] 5 minutes démarrage rapide
- [ ] 4 cas d'usage complets
- [ ] Workflow recommandé
- [ ] Checklist production
- [ ] Troubleshooting rapide

**Usage**:
```
Lire d'abord pour comprendre quelle file utiliser!
```

---

### File 6: `DJANGO_POSTGRESQL_CONFIG.md` (400+ lines)
**Type**: Configuration templates  
**Pour**: Intégrer Django/PostgreSQL
**Format**: .md (code blocks)
**Contient**:
- [ ] settings.py (Database section)
- [ ] .env file template
- [ ] requirements.txt updated
- [ ] Docker configuration
- [ ] Nginx reverse proxy
- [ ] SSL/TLS setup
- [ ] Production checklist

**Usage**:
```
Copy settings.py section → replace in BackEnd/config/settings.py
Copy .env template → create BackEnd/.env
Update requirements.txt if needed
```

---

## 🎯 Navigation par Rôle

### Je suis un **Développeur** 👨‍💻

**Votre workflow**:
1. [SQL_DATABASE_README.md](SQL_DATABASE_README.md) - 5 min overview
2. [POSTGRESQL_SETUP_GUIDE.md](POSTGRESQL_SETUP_GUIDE.md) - Install locally
3. [DJANGO_POSTGRESQL_CONFIG.md](DJANGO_POSTGRESQL_CONFIG.md) - Configure
4. [USEFUL_SQL_QUERIES.sql](USEFUL_SQL_QUERIES.sql) - Write queries
5. [DATABASE_DOCUMENTATION.md](DATABASE_DOCUMENTATION.md) - Understand schema

**Temps**: ~2-3 heures setup + development

---

### Je suis un **DevOps/SRE** 🔧

**Votre workflow**:
1. [POSTGRESQL_SETUP_GUIDE.md](POSTGRESQL_SETUP_GUIDE.md) - Full setup (Étapes 1-10)
2. [DJANGO_POSTGRESQL_CONFIG.md](DJANGO_POSTGRESQL_CONFIG.md) - Security & production
3. [USEFUL_SQL_QUERIES.sql](USEFUL_SQL_QUERIES.sql) - Monitoring queries
4. [database_schema.sql](database_schema.sql) - Backup & restore

**Temps**: ~4-5 heures setup + operations + monitoring

---

### Je suis un **DBA** 🗄️

**Votre workflow**:
1. [DATABASE_DOCUMENTATION.md](DATABASE_DOCUMENTATION.md) - Complete schema review
2. [database_schema.sql](database_schema.sql) - Implementation check
3. [USEFUL_SQL_QUERIES.sql](USEFUL_SQL_QUERIES.sql) - Analytics & tuning
4. [POSTGRESQL_SETUP_GUIDE.md](POSTGRESQL_SETUP_GUIDE.md) - Performance, backups

**Temps**: ~1-2 heures optimization + tuning

---

### Je suis un **Data Analyst** 📊

**Votre workflow**:
1. [DATABASE_DOCUMENTATION.md](DATABASE_DOCUMENTATION.md) - Understand tables
2. [USEFUL_SQL_QUERIES.sql](USEFUL_SQL_QUERIES.sql) - Ready-to-run analytics
3. Create custom queries based on examples

**Temps**: ~30 min learning + queries

---

## 🔗 Cross-References

### Si vous avez une question sur...

**...comment installer PostgreSQL?**  
→ [POSTGRESQL_SETUP_GUIDE.md](POSTGRESQL_SETUP_GUIDE.md) Étapes 1-2

**...comment charger le schema?**  
→ [POSTGRESQL_SETUP_GUIDE.md](POSTGRESQL_SETUP_GUIDE.md) Étape 3  
**OU** [SQL_DATABASE_README.md](SQL_DATABASE_README.md) Démarrage Rapide

**...comment configurer Django?**  
→ [DJANGO_POSTGRESQL_CONFIG.md](DJANGO_POSTGRESQL_CONFIG.md) Section 1-2  
**OU** [POSTGRESQL_SETUP_GUIDE.md](POSTGRESQL_SETUP_GUIDE.md) Étape 4

**...structure des tables?**  
→ [DATABASE_DOCUMENTATION.md](DATABASE_DOCUMENTATION.md) Section "Tableau des Tables"

**...requêtes SQL prêtes?**  
→ [USEFUL_SQL_QUERIES.sql](USEFUL_SQL_QUERIES.sql) Catégories 1-12

**...backups & restore?**  
→ [POSTGRESQL_SETUP_GUIDE.md](POSTGRESQL_SETUP_GUIDE.md) Étape 7

**...production deployment?**  
→ [DJANGO_POSTGRESQL_CONFIG.md](DJANGO_POSTGRESQL_CONFIG.md) Section 6-7

**...optimisation performance?**  
→ [DATABASE_DOCUMENTATION.md](DATABASE_DOCUMENTATION.md) Conseils Performance  
**OU** [POSTGRESQL_SETUP_GUIDE.md](POSTGRESQL_SETUP_GUIDE.md) Étape 8

**...monitoring & alertes?**  
→ [POSTGRESQL_SETUP_GUIDE.md](POSTGRESQL_SETUP_GUIDE.md) Étape 8

**...erreurs/troubleshooting?**  
→ [POSTGRESQL_SETUP_GUIDE.md](POSTGRESQL_SETUP_GUIDE.md) Troubleshooting Rapide

---

## ✅ Validation Checklist

### Avant utilisation, vérifiez:

- [ ] PostgreSQL 12+ installé
- [ ] tous les 6 fichiers présents:
  - [ ] `database_schema.sql`
  - [ ] `DATABASE_DOCUMENTATION.md`
  - [ ] `POSTGRESQL_SETUP_GUIDE.md`
  - [ ] `USEFUL_SQL_QUERIES.sql`
  - [ ] `SQL_DATABASE_README.md`
  - [ ] `DJANGO_POSTGRESQL_CONFIG.md`
- [ ] Espace disque disponible (~500 MB minimum)
- [ ] Accès PostgreSQL (user+password)

### Après utilisation, vérifiez:

- [ ] `\dt` affiche 14+ tables
- [ ] `python manage.py check` = 0 issues
- [ ] `python manage.py migrate` = OK
- [ ] Backups configurés
- [ ] Monitoring en place

---

## 📞 FAQ Rapide

**Q: Par où commencer?**  
A: [SQL_DATABASE_README.md](SQL_DATABASE_README.md) Démarrage Rapide (5 min)

**Q: Je n'ai pas PostgreSQL, comment l'installer?**  
A: [POSTGRESQL_SETUP_GUIDE.md](POSTGRESQL_SETUP_GUIDE.md) Étapes 1-2

**Q: Comment charger le schema?**  
A: [POSTGRESQL_SETUP_GUIDE.md](POSTGRESQL_SETUP_GUIDE.md) Étape 3 OU [SQL_DATABASE_README.md](SQL_DATABASE_README.md) section "Charger les Tables"

**Q: Comment écrire une requête?**  
A: Cherchez un exemple similaire dans [USEFUL_SQL_QUERIES.sql](USEFUL_SQL_QUERIES.sql) et adaptez

**Q: Quelles tables existent?**  
A: [DATABASE_DOCUMENTATION.md](DATABASE_DOCUMENTATION.md) "Tableau des Tables"

**Q: Comment faire un backup?**  
A: [POSTGRESQL_SETUP_GUIDE.md](POSTGRESQL_SETUP_GUIDE.md) Étape 7

**Q: J'ai une erreur, comment la résoudre?**  
A: [POSTGRESQL_SETUP_GUIDE.md](POSTGRESQL_SETUP_GUIDE.md) "Troubleshooting"

**Q: Prêt pour production?**  
A: [DJANGO_POSTGRESQL_CONFIG.md](DJANGO_POSTGRESQL_CONFIG.md) Sections 6-7 + checklist

---

## 📈 Estimated Times

| Tâche | Temps | Fichier |
|-------|-------|---------|
| Lire overview | 10 min | SQL_DATABASE_README.md |
| Installer PostgreSQL | 30 min | POSTGRESQL_SETUP_GUIDE.md |
| Charger schema | 2 min | database_schema.sql |
| Configurer Django | 10 min | DJANGO_POSTGRESQL_CONFIG.md |
| Setup backups | 15 min | POSTGRESQL_SETUP_GUIDE.md |
| **TOTAL → Production Ready** | **~1.5 hours** | - |

---

## 🎓 Learning Path

**Beginner** (Just need to use it):
1. Deploy → [SQL_DATABASE_README.md](SQL_DATABASE_README.md) Démarrage Rapide
2. Write queries → [USEFUL_SQL_QUERIES.sql](USEFUL_SQL_QUERIES.sql)

**Intermediate** (Need to understand it):
1. [DATABASE_DOCUMENTATION.md](DATABASE_DOCUMENTATION.md) - Complete schema
2. [POSTGRESQL_SETUP_GUIDE.md](POSTGRESQL_SETUP_GUIDE.md) - Full installation
3. [USEFUL_SQL_QUERIES.sql](USEFUL_SQL_QUERIES.sql) - Practice queries

**Advanced** (Need to optimize it):
1. [DATABASE_DOCUMENTATION.md](DATABASE_DOCUMENTATION.md) - Performance section
2. [POSTGRESQL_SETUP_GUIDE.md](POSTGRESQL_SETUP_GUIDE.md) - Monitoring (Étape 8)
3. [USEFUL_SQL_QUERIES.sql](USEFUL_SQL_QUERIES.sql) - Analytics queries

---

## 📝 File Statistics

| Fichier | Type | Lignes | Sections |
|---------|------|--------|----------|
| database_schema.sql | SQL | 1200+ | 9 modules |
| DATABASE_DOCUMENTATION.md | Markdown | 400+ | 14 tables |
| POSTGRESQL_SETUP_GUIDE.md | Markdown | 500+ | 10 étapes |
| USEFUL_SQL_QUERIES.sql | SQL | 800+ | 12 catégories |
| SQL_DATABASE_README.md | Markdown | 300+ | 10 sections |
| DJANGO_POSTGRESQL_CONFIG.md | Markdown | 400+ | 7 sections |
| **TOTAL** | - | **3600+** | - |

---

**Created**: 28 March 2026  
**For**: MediTriage Project  
**Version**: 1.0  
**Status**: ✅ Complete & Ready

---

## 🚀 Quick Start Command

```bash
# Copy into your terminal:
psql -U postgres && CREATE USER meditriage_user WITH PASSWORD 'password'; CREATE DATABASE meditriage OWNER meditriage_user; \q && psql -U meditriage_user -d meditriage -f database_schema.sql && echo "✅ Database ready!"
```

**Then**: Configure Django (see [DJANGO_POSTGRESQL_CONFIG.md](DJANGO_POSTGRESQL_CONFIG.md)) & run `python manage.py migrate`

✨ **All set!**
