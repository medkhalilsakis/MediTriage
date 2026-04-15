# Guide d'Installation et d'Utilisation - Base de Données PostgreSQL

## 🎯 Objectif

Ce guide vous explique comment utiliser le fichier SQL complet `database_schema.sql` pour créer la base de données MediTriage sur PostgreSQL.

---

## 📋 Prérequis

- **PostgreSQL** 12 ou supérieur installé
- **psql** (CLI PostgreSQL) disponible dans le PATH
- Compte superuser PostgreSQL (ou droits de création de BD)
- **Django** configuré pour PostgreSQL (voir section configuration)

---

## 🚀 Étape 1: Installer PostgreSQL

### Windows (via pgAdmin ou CommandLine)
```bash
# Vérifier installation
psql --version

# Se connecter en tant que postgres
psql -U postgres
```

### macOS (via Homebrew)
```bash
brew install postgresql@15
brew services start postgresql
```

### Linux (Debian/Ubuntu)
```bash
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

---

## 🔑 Étape 2: Créer Utilisateur et Base de Données

### Option A: Via psql (Ligne de Commande)

```bash
# Se connecter comme postgres
psql -U postgres

# Créer utilisateur (remplacer VOTRE_MOT_DE_PASSE)
CREATE USER meditriage_user WITH PASSWORD 'VOTRE_MOT_DE_PASSE';

# Créer base de données
CREATE DATABASE meditriage OWNER meditriage_user;

# Accorder privilèges
GRANT ALL PRIVILEGES ON DATABASE meditriage TO meditriage_user;
ALTER ROLE meditriage_user CREATEDB;

# Quitter
\q
```

### Option B: Via pgAdmin (GUI)
1. Ouvrir pgAdmin
2. Clic droit sur "Databases" → "Create" → "Database"
3. Nom: `meditriage`
4. Clic droit sur "Login/Group Roles" → "Create" → "Login/Group Role"
5. Nom: `meditriage_user`
6. Onglet "Definition": définir mot de passe
7. Onglet "Privileges": cocher "Can create databases"
8. Sauvegarder

---

## 📁 Étape 3: Créer les Tables

### Option A: Utiliser le fichier SQL

```bash
# Depuis le répertoire du projet
cd d:\MediTriage\MediTriage

# Créer les tables (Windows)
psql -h localhost -U meditriage_user -d meditriage -f database_schema.sql

# Vous serez invité à entrer le mot de passe

# Vérifier création
psql -h localhost -U meditriage_user -d meditriage
# Dann:
\dt
# Pour voir toutes les tables...
```

### Option B: Copier-Coller dans pgAdmin

1. Ouvrir pgAdmin
2. Connecté à `meditriage` avec `meditriage_user`
3. Onglet "Query Tool"
4. Copier tout le contenu de `database_schema.sql`
5. Coller dans l'éditeur
6. Appuyer sur ▶ (Execute)
7. Vérifier les résultats

### Option C: Via Django

```bash
# Configuration préalable (voir Étape 4)
cd BackEnd

# Si vous utilisez Django, les migrations s'en chargeront:
python manage.py migrate

# Mais vous pouvez aussi charger le SQL brut:
psql -U meditriage_user -d meditriage < ../database_schema.sql
```

---

## ⚙️ Étape 4: Configurer Django pour PostgreSQL

### Modifier `BackEnd/config/settings.py`

```python
# Avant (SQLite pour développement):
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Après (PostgreSQL pour production):
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'meditriage',
        'USER': 'meditriage_user',
        'PASSWORD': 'VOTRE_MOT_DE_PASSE',  # Ou utiliser .env
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Meilleure Pratique: Utiliser Variables d'Environnement

```python
# Dans settings.py:
from decouple import config

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='meditriage'),
        'USER': config('DB_USER', default='meditriage_user'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}
```

### Créer `.env` à la racine `BackEnd/`

```
DB_NAME=meditriage
DB_USER=meditriage_user
DB_PASSWORD=VOTRE_MOT_DE_PASSE_SECURE
DB_HOST=localhost
DB_PORT=5432
SECRET_KEY=your-secret-key-here
DEBUG=False
```

### Installer psycopg2

```bash
# Déjà dans requirements.txt, mais au besoin:
pip install psycopg2-binary==2.9.11
```

---

## ✅ Étape 5: Valider la Configuration

### Test 1: Connexion psql

```bash
psql -h localhost -U meditriage_user -d meditriage -c "SELECT NOW();"

# Attendu:
# now
# ---
# 2026-03-28 19:30:45.123456+00:00
```

### Test 2: Vérifier tables Django

```bash
psql -U meditriage_user -d meditriage

# Lister tables:
\dt

# Attendu (45+ tables):
# authentication_customuser
# patients_patientprofile
# doctors_doctorprofile
# appointments_appointment
# ... (et toutes les autres)
```

### Test 3: Django Check

```bash
cd BackEnd
python manage.py check

# Attendu:
# System check identified no issues (0 silenced).
```

### Test 4: Django Shell

```bash
python manage.py shell

# Tester une requête:
>>> from authentication.models import CustomUser
>>> CustomUser.objects.count()
0  # (Vide pour démarrage)

# Exit:
>>> exit()
```

---

## 🔄 Étape 6: Charger Données Initiales (Optionnel)

### Créer Utilisateurs de Test

```bash
python manage.py createsuperuser
# Entrez:
# Email: admin@meditriage.com
# Username: admin
# Password: SecureAdmin123!
```

### Ou via Shell Django

```bash
python manage.py shell

>>> from authentication.models import CustomUser
>>> from patients.models import PatientProfile
>>> from doctors.models import DoctorProfile

>>> # Créer admin
>>> admin = CustomUser.objects.create_superuser(
...     username='admin',
...     email='admin@meditriage.com',
...     password='SecureAdmin123!',
...     role='admin'
... )

>>> # Créer patient test
>>> patient_user = CustomUser.objects.create_user(
...     username='john_doe',
...     email='john@example.com',
...     password='Patient123!',
...     first_name='John',
...     last_name='Doe',
...     role='patient'
... )
>>> patient_profile = PatientProfile.objects.create(
...     user=patient_user,
...     blood_group='O+',
...     gender='male',
...     allergies='Pénicilline'
... )

>>> # Créer médecin test
>>> doctor_user = CustomUser.objects.create_user(
...     username='dr_smith',
...     email='dr.smith@meditriage.com',
...     password='Doctor123!',
...     first_name='Alice',
...     last_name='Smith',
...     role='doctor'
... )
>>> doctor_profile = DoctorProfile.objects.create(
...     user=doctor_user,
...     specialization='Cardiologie',
...     license_number='CAR-2024-001',
...     years_of_experience=10,
...     consultation_fee=50.00
... )

>>> # Vérifier
>>> CustomUser.objects.count()
3
>>> exit()
```

---

## 🛡️ Étape 7: Sauvegardes (Backup)

### Backup Manuel

```bash
# Dump complet de la BD
pg_dump -h localhost -U meditriage_user -d meditriage > meditriage_backup.sql

# Avec compression
pg_dump -h localhost -U meditriage_user -d meditriage | gzip > meditriage_backup.sql.gz

# Dump spécifique (ex: table appointments)
pg_dump -h localhost -U meditriage_user -d meditriage -t appointments_appointment > appointments_backup.sql
```

### Restaurer depuis Backup

```bash
# Restaurer depuis SQL
psql -h localhost -U meditriage_user -d meditriage < meditriage_backup.sql

# Depuis .gz
gunzip < meditriage_backup.sql.gz | psql -h localhost -U meditriage_user -d meditriage
```

### Backup Automatisé (Cron - Linux/macOS)

```bash
# Créer script backup.sh
#!/bin/bash
BACKUP_DIR="/backups/meditriage"
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -h localhost -U meditriage_user -d meditriage | gzip > ${BACKUP_DIR}/meditriage_${DATE}.sql.gz

# Rendre exécutable
chmod +x backup.sh

# Ajouter au crontab (tous les jours à 2h du matin)
0 2 * * * /path/to/backup.sh

# Vérifier crontab
crontab -l
```

### Backup Automatisé (Task Scheduler - Windows)

1. Créer `backup.bat`:
```batch
@echo off
cd "C:\Program Files\PostgreSQL\15\bin"
set BACKUP_DIR=C:\backups\meditriage
set DATETIME=%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
pg_dump -h localhost -U meditriage_user -d meditriage | gzip > %BACKUP_DIR%\meditriage_%DATETIME%.sql.gz
```

2. Planifier via Task Scheduler
   - New Task
   - Trigger: Daily à 2:00 AM
   - Action: Run script `backup.bat`

---

## 📊 Étape 8: Monitoring & Maintenance

### Vérifier Performance

```bash
psql -U meditriage_user -d meditriage

# Taille BD:
SELECT pg_size_pretty(pg_database_size('meditriage'));

# Taille tables:
SELECT schemaname, tablename, pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) 
FROM pg_tables 
ORDER BY pg_relation_size(schemaname||'.'||tablename) DESC;

# Vitesse requêtes (si extension pgbench installée):
SELECT * FROM pg_stat_statements 
ORDER BY total_time DESC LIMIT 10;
```

### Nettoyer (VACUUM)

```bash
# Interactive:
VACUUM ANALYZE;

# Ou depuis bash:
vacuumdb -U meditriage_user -d meditriage -v
```

### Vérifier Intégrité

```bash
# Depuis Django:
python manage.py check

# Depuis psql:
REINDEX DATABASE meditriage;
```

---

## 🔐 Étape 9: Sécurité

### Changer Mot de Passe Admin

```bash
psql -U postgres

ALTER USER meditriage_user WITH PASSWORD 'NEW_SECURE_PASSWORD';
```

### Restreindre Accès (pg_hba.conf)

**Fichier**: `/etc/postgresql/15/main/pg_hba.conf` (Linux)  
Ou**: `C:\Program Files\PostgreSQL\15\data\pg_hba.conf` (Windows)

```
# Authoriser seulement localhost (socket local)
local   meditriage    meditriage_user    trust

# Ou avec MD5 (meilleur):
local   meditriage    meditriage_user    md5
host    meditriage    meditriage_user    127.0.0.1/32    md5
host    meditriage    meditriage_user    ::1/128         md5

# Puis restart:
sudo systemctl restart postgresql
```

### SSL/TLS (Production)

```bash
# Générer certificats
openssl req -x509 -newkey rsa:2048 -keyout server.key -out server.crt -days 365 -nodes

# Placer dans /var/lib/postgresql/15/main/
# Puis configurer postgresql.conf:
ssl = on
ssl_cert_file = '/var/lib/postgresql/15/main/server.crt'
ssl_key_file = '/var/lib/postgresql/15/main/server.key'
```

---

## 🔗 Étape 10: Intégration avec Application Django

### Démarrer Backend

```bash
cd BackEnd

# Si you use un venv:
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate  # Windows

# Installer dépendances (si pas déjà fait):
pip install -r requirements.txt

# Lancer serveur:
python manage.py runserver
# Accès: http://127.0.0.1:8000
```

### Tester API

```bash
# Ouvrir navigateur:
http://127.0.0.1:8000/api/docs/swagger/

# Ou via curl:
curl -X GET http://127.0.0.1:8000/api/doctors/

# Avec authentification JWT:
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -X GET http://127.0.0.1:8000/api/appointments/
```

---

## 🚨 Troubleshooting

### Erreur: "psql: error: could not connect to server"

**Cause**: PostgreSQL n'est pas en cours d'exécution

**Solution**:
```bash
# Linux:
sudo systemctl start postgresql

# macOS:
brew services start postgresql@15

# Windows:
Net Start PostgreSQL15
```

### Erreur: "FATAL: password authentication failed"

**Cause**: Mot de passe incorrect

**Solution**:
```bash
# Réinitialiser mot de passe postgres:
sudo -u postgres psql
ALTER USER postgres WITH PASSWORD 'new_password';
```

### Erreur: "role does not exist"

**Cause**: Utilisateur n'existe pas

**Solution**:
```bash
psql -U postgres
CREATE USER meditriage_user WITH PASSWORD 'password';
CREATE DATABASE meditriage OWNER meditriage_user;
```

### Erreur Django: "could not connect to server"

**Cause**: Paramètres DB incorrects dans settings.py

**Solution**:
```bash
# Vérifier settings.py:
python manage.py dbshell
# Si ça ouvre psql, alors connexion OK

# Sinon, tester directement:
psql -h localhost -U meditriage_user -d meditriage
```

---

## 📈 Étape Bonus: Migration depuis SQLite

Si vous avez une BD SQLite existante:

```bash
# 1. Exporter de SQLite
python manage.py dumpdata > data.json --indent 2

# 2. Configurer PostgreSQL (voir Étape 4)

# 3. Créer BD PostgreSQL (voir Étape 2)

# 4. Lancer migrations
python manage.py migrate

# 5. Charger données
python manage.py loaddata data.json

# 6. Vérifier
python manage.py dbshell
SELECT COUNT(*) FROM authentication_customuser;
```

---

## ✨ Résumé Commandes Clés

```bash
# Démarrer PostgreSQL
psql -U meditriage_user -d meditriage

# Voir tables
\dt

# Voir colonnes d'une table
\d appointments_appointment

# Exécuter requête SQL
SELECT * FROM patients_patientprofile;

# Quitter
\q

# Backup
pg_dump -U meditriage_user -d meditriage > backup.sql

# Restaurer
psql -U meditriage_user -d meditriage < backup.sql

# Vérifier Django
python manage.py check

# Shell Django
python manage.py shell
```

---

## 📞 Documentation Additionnelle

- **PostgreSQL Documentation**: https://www.postgresql.org/docs/
- **Django Database API**: https://docs.djangoproject.com/en/6.0/topics/db/
- **pgAdmin Docs**: https://www.pgadmin.org/docs/
- **SQL Tutorial**: https://www.w3schools.com/sql/

---

**Dernière mise à jour**: 28 mars 2026  
**Auteur**: MediTriage Development Team
