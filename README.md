# MediSmart

AI-powered smart health platform with 4 actors:
- Patient
- Doctor
- Admin
- AI Chatbot

The project contains:
- Backend: Django REST Framework API with JWT auth
- Frontend: React + Vite dashboard app

## Repository Structure

- BackEnd: Django REST Framework backend
- MediFront: React frontend
- datasets: optional ML datasets/scripts

## Backend Setup (Django)

1. Move to backend folder:

```bash
cd BackEnd
```

2. Create and activate virtual environment:

```bash
python -m venv venv
# Windows
venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create environment variables in BackEnd/.env:

```env
SECRET_KEY=change-me
DEBUG=True
ALLOWED_HOSTS=*
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=
CORS_ALLOW_ALL=True
```

5. Run migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

6. (Optional) Create admin account:

```bash
python manage.py createsuperuser
```

7. Start backend server:

```bash
python manage.py runserver
```

Backend base URL:
- http://127.0.0.1:8000/api/

API docs:
- Swagger: http://127.0.0.1:8000/api/docs/swagger/
- ReDoc: http://127.0.0.1:8000/api/docs/redoc/

## Frontend Setup (React)

1. Move to frontend folder:

```bash
cd MediFront
```

2. Install dependencies:

```bash
npm install
```

3. Create environment variables in MediFront/.env:

```env
VITE_API_URL=http://127.0.0.1:8000/api
```

4. Start frontend:

```bash
npm run dev
```

Frontend URL:
- http://127.0.0.1:5173/

## Core API Endpoints

- POST /api/auth/register/
- POST /api/auth/login/
- POST /api/auth/token/refresh/
- GET /api/appointments/today/
- POST /api/chatbot/sessions/
- POST /api/chatbot/sessions/{id}/message/
- GET /api/prescriptions/{id}/pdf/
- GET /api/admin/stats/

## Implemented Backend Apps

- authentication
- patients
- doctors
- appointments
- medical_records
- prescriptions
- chatbot
- follow_up
- notifications

## Tech Stack

Backend packages:
- djangorestframework
- djangorestframework-simplejwt
- django-cors-headers
- django-filter
- drf-spectacular
- psycopg2-binary
- reportlab
- python-decouple

Frontend packages:
- react-router-dom
- axios
- @tanstack/react-query
- zustand
- react-hook-form
- zod
- tailwindcss
- recharts
- react-hot-toast

## Notes

- JWT is used for all protected routes.
- Axios interceptor auto-attaches Bearer token and refreshes token on 401.
- Role-aware sidebar and route guards are implemented in the frontend.
- Backend default pagination is 20 items/page with filter/search/ordering enabled.
