# Developer Guide

- Use Python 3.11+ for the backend and Node 20+ for the frontend.
- Run `pytest` in `backend/` and `npm run lint && npm run build` in `frontend/`.
- Prefer the centralized AI gateway over direct model calls.
- Keep feature changes aligned with the existing domain folders.

## Workflow

1. Make the smallest change that fixes the root cause.
2. Run backend tests or the relevant smoke check.
3. Verify frontend lint/build if the UI changed.
4. Re-run the live path when the change affects runtime behavior.

## Environment

- Copy `backend/.env.example` to `backend/.env`.
- Keep secrets out of git.
- Document new variables in the appropriate env file before using them in code.
