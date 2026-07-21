# Database

- Postgres stores application state.
- Alembic manages schema changes under `backend/alembic/`.
- Redis backs caching, rate limiting, and Celery.
- Qdrant stores vector data for learning and AI retrieval.

## Schema Notes

- Users, jobs, assessments, interviews, learning, and knowledge each have dedicated tables.
- AI telemetry and recommendation logs are persisted for dashboard visibility.
- Knowledge documents are chunked and indexed for RAG retrieval.

## Operations

- Run `alembic upgrade head` for fresh deployments.
- Keep Redis and Qdrant available before background jobs start.
- The app expects a working Postgres connection at startup.
