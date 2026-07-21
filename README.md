# Webscraping123

AI Placement OS with FastAPI backend, Next.js frontend, Celery workers, Redis, and Qdrant.

## Run Locally

```bash
docker compose up --build
```

## Components

- `backend/` FastAPI + Celery + AI gateway
- `frontend/` Next.js app
- `docker-compose.yml` local orchestration for app, Redis, Qdrant, and Postgres

## Notes

- Copy `backend/.env.example` to `backend/.env` and fill in real values locally.
- Do not commit secrets.
