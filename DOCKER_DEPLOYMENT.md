# Docker Deployment Guide (MediSmart)

## 1. Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine + Compose Plugin (Linux)
- Open ports: `80` (frontend), optional `443` if you add TLS reverse proxy later

## 2. Configure environment variables

From project root, create `.env` from the template:

```bash
cp .env.docker.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.docker.example .env
```

Then edit `.env` and set at least:

- `POSTGRES_PASSWORD`
- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS` (add your server domain/IP)

## 3. Build and start containers

From project root:

```bash
docker compose up -d --build
```

This starts:

- `db` (PostgreSQL)
- `backend` (Django + Gunicorn)
- `frontend` (Nginx serving React build + reverse proxy `/api` to backend)

## 4. Access the application

- Frontend: `http://<server-ip-or-domain>/`
- API docs (through Nginx): `http://<server-ip-or-domain>/api/docs/swagger/`
- Django admin: `http://<server-ip-or-domain>/admin/`

## 5. Create admin user (first deploy)

```bash
docker compose exec backend python manage.py createsuperuser
```

## 6. Useful operations

- Check logs:

```bash
docker compose logs -f
```

- Check one service logs:

```bash
docker compose logs -f backend
```

- Restart services:

```bash
docker compose restart
```

- Stop services:

```bash
docker compose down
```

- Stop and remove volumes (danger: deletes DB/media/static data):

```bash
docker compose down -v
```

## 7. Production recommendations

- Set `DJANGO_DEBUG=False`
- Use a strong `DJANGO_SECRET_KEY`
- Restrict `DJANGO_ALLOWED_HOSTS` to your real domain(s)
- Keep `CORS_ALLOW_ALL=False` for same-origin deployment
- Put TLS/HTTPS in front (Cloudflare, Nginx Proxy Manager, Traefik, or cloud LB)
- Add scheduled DB backups

## 8. Notes about static/media

- Backend runs migrations + collectstatic at container startup
- Nginx serves frontend and static/media files from shared Docker volumes
- Uploaded media persists in `media_data` volume
