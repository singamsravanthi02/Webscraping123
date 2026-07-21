# Deployment

- Build backend, worker, and frontend Docker images from the repo root.
- Set production environment variables in `backend/.env.production` and frontend env files.
- Run Alembic migrations before starting the API.
- Start Redis, Postgres, and Qdrant before Celery workers.

## Release Steps

1. Build images with `docker compose build`.
2. Start the stack with `docker compose up -d`.
3. Verify `/health` and `/metrics`.
4. Confirm Celery is consuming `main-queue`.
5. Confirm knowledge uploads complete on a shared temp volume.

## Environment Variables

- `DATABASE_URL`
- `REDIS_URL`
- `QDRANT_URL`
- `GEMINI_API_KEY`
- `NVIDIA_API_KEY`
- `OLLAMA_BASE_URL`
- `AI_PROVIDER`

## Troubleshooting

- If AI requests fail with quota errors, the gateway should fall back to the next provider.
- If uploads fail, verify the shared knowledge upload mount exists in both backend and worker containers.
- If migrations fail, inspect backend startup logs before restarting the stack.
