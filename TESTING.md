# Testing Guide

SPIP uses `pytest` for backend unit and integration testing.

## Backend Testing

### 1. Setup Test Environment
Ensure you have the test dependencies installed:
```bash
cd backend
pip install -r requirements.txt
```

Ensure your `.env` contains a `TEST_DATABASE_URL` if you want a separate test DB, or configure pytest to run in memory (SQLite).

### 2. Run Tests
To run the full suite:
```bash
pytest
```

To run with coverage:
```bash
pytest --cov=app --cov-report=term-missing
```

## End-to-End (E2E) Testing Strategy
For production deployments, the frontend requires E2E validation.
We recommend using **Playwright** or **Cypress** to simulate actual student flows.

### Future Playwright Setup
1. `cd frontend && npm init playwright@latest`
2. Write E2E flows in `tests/` verifying login, dashboard rendering, and AI interview completion.
3. Integrate `npx playwright test` into the `.github/workflows/ci.yml`.

## Frontend Testing
Currently, the frontend relies on ESLint for static analysis and Next.js strict mode.

### 1. Run Linter
```bash
cd frontend
npm run lint
```

### 2. Production Build Test
Always test if the production build completes successfully before merging:
```bash
npm run build
```
