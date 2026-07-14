# API Documentation

The SPIP Backend is built with FastAPI, which automatically generates OpenAPI standard documentation.

## Accessing the Docs

Once the backend is running locally, navigate to:
- **Swagger UI**: `http://localhost:8000/docs` (Interactive testing)
- **ReDoc**: `http://localhost:8000/redoc` (Read-only reference)

## Authentication

All protected routes require a JWT Bearer token.
1. Authenticate via `POST /api/v1/auth/login/access-token` with `username` (email) and `password`.
2. Retrieve the `access_token` from the JSON response.
3. Pass it in the Authorization header: `Authorization: Bearer <token>`.

## Core Modules

- **Auth** (`/auth/*`): Login, password recovery, token generation.
- **Users** (`/users/*`): CRUD operations for students, faculty, and admins.
- **Jobs** (`/jobs/*`): Job postings, applications, and ATS parsing.
- **Assessments** (`/assessments/*`): Question banks, mock tests, proctoring streams.
- **Interviews** (`/interviews/*`): AI Voice/Text interview generation, evaluation.
- **Learning** (`/learning/*`): Vector DB RAG endpoints for chatting with faculty materials.
- **Notifications** (`/notifications/*`): Trigger and queue system emails and push alerts.

## Rate Limiting

The API uses standard rate limiting via Redis. Excessive requests will return HTTP 429 Too Many Requests.
