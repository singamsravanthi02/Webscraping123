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

## Environment

- Copy `backend/.env.example` to `backend/.env`.
- Required services: Postgres, Redis, Qdrant, Gemini, NVIDIA, Ollama.
- AI provider selection is controlled by `AI_PROVIDER`.

## Architecture

- All AI features go through the centralized gateway in `backend/app/domain/ai_orchestration/`.
- Background work runs through Celery on `main-queue`.
- Document uploads use the shared `/tmp/spip_knowledge_uploads` volume.

## Known Limitations

- Gemini free-tier quota can trigger provider fallback during heavy AI usage.
- `pip-audit` and `npm audit` report known advisories that are documented, not silently ignored.
- AI generation latency depends on the active provider and live network conditions.

## Troubleshooting

- If uploads fail, check that the backend and worker both have access to `/tmp/spip_knowledge_uploads`.
- If AI generation stalls, inspect provider health at `/api/v1/ai/providers`.
- If migrations fail, run `alembic upgrade head` from the backend container.
