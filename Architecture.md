# Architecture

- `backend/` is a FastAPI service with SQLAlchemy, Alembic, Celery, Redis, and Qdrant.
- `frontend/` is a Next.js app that consumes the backend API.
- AI requests go through the centralized gateway in `backend/app/domain/ai_orchestration/gateway.py`.
- Background jobs live under `backend/app/worker/`.

## Runtime Flow

1. Frontend calls the FastAPI API.
2. API stores core data in Postgres.
3. AI features call the shared gateway, which routes to Gemini, NVIDIA, or Ollama.
4. Celery handles background work such as document ingestion, embeddings, and recommendations.
5. Qdrant stores vector data for retrieval and learning workflows.

## Deployment Shape

- Docker Compose runs backend, worker, beat, frontend, Postgres, Redis, Qdrant, Prometheus, and Grafana.
- Knowledge uploads use a shared mounted temp directory so the API and worker see the same file.
- Migrations run automatically on backend startup.
