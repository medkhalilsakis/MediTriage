# Django Configuration Files for PostgreSQL Integration

## 📋 Contents
Cette file contient les configurations Django requises pour intégrer PostgreSQL à MediTriage.

---

## 1️⃣ settings.py (DATABASE SECTION)

Replace the DATABASES section in `BackEnd/config/settings.py`:

```python
# =====================================================
# DATABASE CONFIGURATION - PostgreSQL Production
# =====================================================

# OPTION A: Direct Configuration (Development)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'meditriage',
        'USER': 'meditriage_user',
        'PASSWORD': 'your_secure_password',
        'HOST': 'localhost',
        'PORT': '5432',
        'CONN_MAX_AGE': 600,  # Connection pooling (seconds)
        'OPTIONS': {
            'sslmode': 'prefer',  # Use SSL if available
        }
    }
}

# OPTION B: Environment Variables (Recommended for Production)
# Requires: pip install python-decouple
from decouple import config

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='meditriage'),
        'USER': config('DB_USER', default='meditriage_user'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': config('DB_CONN_MAX_AGE', default=600, cast=int),
        'OPTIONS': {
            'sslmode': config('DB_SSL_MODE', default='prefer'),
        }
    }
}

# =====================================================
# DATABASE CONNECTION POOL (Optional, requires psycopg2-pool)
# For high-traffic production environments
# =====================================================

# Uncomment if using django-db-multitenant or connection pooling
# from django.db.backends.postgresql import base
# base.psycopg2_version  # Ensure psycopg2 installed

# Connection timeout settings
DB_CONN_TIMEOUT = config('DB_CONN_TIMEOUT', default=30, cast=int)

# ====================================================
# LOGGING - SQL Queries (Development Only)
# ====================================================

if DEBUG:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            'django.db.backends': {
                'handlers': ['console'],
                'level': 'DEBUG',
            },
        },
    }
```

---

## 2️⃣ .env File (Environment Variables)

Create `BackEnd/.env` file:

```bash
# =====================================================
# DATABASE CONFIGURATION
# =====================================================
DB_NAME=meditriage
DB_USER=meditriage_user
DB_PASSWORD=YOUR_SECURE_PASSWORD_HERE
DB_HOST=localhost
DB_PORT=5432
DB_CONN_MAX_AGE=600
DB_SSL_MODE=prefer

# =====================================================
# DJANGO SETTINGS
# =====================================================
DEBUG=False
SECRET_KEY=your-django-secret-key-here-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# =====================================================
# CORS CONFIGURATION
# =====================================================
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://your-domain.com

# =====================================================
# JWT CONFIGURATION
# =====================================================
JWT_SECRET_KEY=your-jwt-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# =====================================================
# EMAIL CONFIGURATION (for notifications)
# =====================================================
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com  # or your email provider
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@meditriage.com

# =====================================================
# AWS S3 (Optional, for file storage)
# =====================================================
USE_S3=False
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=meditriage-uploads
AWS_S3_REGION_NAME=us-east-1

# =====================================================
# LOGGING & MONITORING
# =====================================================
LOG_LEVEL=INFO
SENTRY_DSN=  # Optional: Sentry error tracking

# =====================================================
# API SETTINGS
# =====================================================
API_PAGE_SIZE=20
API_BASE_URL=http://localhost:8000/api
```

---

## 3️⃣ requirements.txt (Database Dependencies)

Ensure your `BackEnd/requirements.txt` includes:

```txt
# Core
Django==6.0.3
djangorestframework==3.17.1

# Database
psycopg2-binary==2.9.11
# OR (for production use psycopg2 instead of psycopg2-binary)
# psycopg2==2.9.11

# Environment & Configuration
python-decouple==3.8

# Authentication
djangorestframework-simplejwt==5.5.1

# CORS & API
django-cors-headers==4.9.0
drf-spectacular==0.29.0

# Filtering & Pagination
django-filter==25.2

# PDF Generation
reportlab==4.4.10

# Optional: Connection Pooling
# pgbouncer (system-level, better than Django-level)
# django-db-pool==1.3.0  # Lightweight pooling

# Optional: Monitoring & Performance
# django-extensions==3.2.3
# django-debug-toolbar==4.2.0  # Development only

# Optional: Testing
# pytest==7.4.0
# pytest-django==4.5.2
# factory-boy==3.3.0
```

---

## 4️⃣ settings.py (Full Database Section Example)

Complete working example for `BackEnd/config/settings.py`:

```python
import os
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# ========== CRITICAL: CHANGE THESE IN PRODUCTION ==========
SECRET_KEY = config('SECRET_KEY', default='your-secret-key')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')
# ===========================================================

INSTALLED_APPS = [
    'daphne',  # If using async
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    
    # Local apps
    'authentication.apps.AuthenticationConfig',
    'patients.apps.PatientsConfig',
    'doctors.apps.DoctorsConfig',
    'appointments.apps.AppointmentsConfig',
    'medical_records.apps.MedicalRecordsConfig',
    'prescriptions.apps.PrescriptionsConfig',
    'chatbot.apps.ChatbotConfig',
    'follow_up.apps.FollowUpConfig',
    'notifications.apps.NotificationsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ========== DATABASE CONFIGURATION ==========
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='meditriage'),
        'USER': config('DB_USER', default='meditriage_user'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': config('DB_CONN_MAX_AGE', default=600, cast=int),
        'OPTIONS': {
            'sslmode': config('DB_SSL_MODE', default='prefer'),
        },
        'ATOMIC_REQUESTS': True,  # For data consistency
        'AUTOCOMMIT': True,
    }
}

# ========== REST FRAMEWORK ==========
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# ========== JWT SETTINGS ==========
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=config('JWT_EXPIRATION_HOURS', default=24, cast=int)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': config('JWT_SECRET_KEY', default=SECRET_KEY),
}

# ========== CORS SETTINGS ==========
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:5173').split(',')
CORS_ALLOW_CREDENTIALS = True

# ========== STATIC & MEDIA ==========
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ========== LOGGING ==========
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': config('LOG_LEVEL', default='INFO'),
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': config('LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# ========== SECURITY SETTINGS (Production) ==========
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_SECURITY_POLICY = {
        'default-src': ("'self'",),
        'script-src': ("'self'", "'unsafe-inline'"),
    }
```

---

## 5️⃣ Docker Configuration (Optional, for containerization)

### Dockerfile

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=2)"

# Run server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

### docker-compose.yml

```yaml
version: '3.9'

services:
  postgres:
    image: postgres:15-alpine
    container_name: meditriage-db
    environment:
      POSTGRES_DB: ${DB_NAME:-meditriage}
      POSTGRES_USER: ${DB_USER:-meditriage_user}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database_schema.sql:/docker-entrypoint-initdb.d/01-schema.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-meditriage_user}"]
      interval: 10s
      timeout: 5s
      retries: 5

  django:
    build: .
    container_name: meditriage-api
    command: sh -c "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"
    environment:
      - DB_ENGINE=django.db.backends.postgresql
      - DB_NAME=${DB_NAME:-meditriage}
      - DB_USER=${DB_USER:-meditriage_user}
      - DB_PASSWORD=${DB_PASSWORD}
      - DB_HOST=postgres
      - DB_PORT=5432
      - DEBUG=${DEBUG:-False}
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy

  react:
    image: node:18-alpine
    working_dir: /app
    volumes:
      - ../MediFront:/app
    ports:
      - "5173:5173"
    command: npm run dev

volumes:
  postgres_data:
```

### .dockerignore

```
__pycache__
*.pyc
*.pyo
*.egg-info
.git
.gitignore
.env
db.sqlite3
node_modules
dist
build
```

---

## 6️⃣ Production Deployment Checklist

### Before Going Live:

```bash
# 1. Generate new SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# 2. Collect static files
python manage.py collectstatic --noinput

# 3. Run migrations
python manage.py migrate

# 4. Check for issues
python manage.py check --deploy

# 5. Create superuser
python manage.py createsuperuser

# 6. Test admin panel
# Navigate to /admin/

# 7. Test API documentation
# Navigate to /api/docs/swagger/
```

### Environment Variables (Production Server):

```bash
# On your production server, set environment variables:

# Linux/macOS (add to ~/.bashrc or ~/.zshrc):
export DEBUG=False
export SECRET_KEY="your-super-secret-key"
export DB_PASSWORD="production-db-password"
export DB_HOST="db.example.com"
export ALLOWED_HOSTS="api.meditriage.com,www.meditriage.com"

# Windows (PowerShell):
$env:DEBUG="False"
$env:SECRET_KEY="your-super-secret-key"
$env:DB_PASSWORD="production-db-password"
# etc.
```

---

## 7️⃣ Nginx Configuration (Production Reverse Proxy)

### /etc/nginx/sites-available/meditriage

```nginx
upstream django {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.meditriage.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.meditriage.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/api.meditriage.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.meditriage.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # Logging
    access_log /var/log/nginx/meditriage_access.log;
    error_log /var/log/nginx/meditriage_error.log;
    
    # Client upload size
    client_max_body_size 50M;
    
    # Static files
    location /static/ {
        alias /var/www/meditriage/staticfiles/;
        expires 30d;
    }
    
    # Media files
    location /media/ {
        alias /var/www/meditriage/media/;
        expires 7d;
    }
    
    # API proxy
    location /api/ {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
    
    # Health check
    location /health/ {
        access_log off;
        proxy_pass http://django;
    }
    
    # Default
    location / {
        return 404;
    }
}
```

---

## ✅ Validation Checklist

```bash
# Test database connection
python manage.py dbshell
SELECT version();  # Should see PostgreSQL version
\q

# Check migrations
python manage.py showmigrations

# Run system checks
python manage.py check --deploy

# Test admin panel
python manage.py runserver
# Visit: http://localhost:8000/admin/

# Test API
# Visit: http://localhost:8000/api/docs/swagger/

# Test database integrity
psql -U meditriage_user -d meditriage -c "SELECT COUNT(*) FROM authentication_customuser;"
```

---

**Generated**: 28 March 2026  
**For**: MediTriage Project  
**PostgreSQL Version**: 12+  
**Django Version**: 6.0.3
