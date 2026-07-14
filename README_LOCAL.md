# SPIP Local Development Guide

This guide explains how to run SPIP in a local environment for development without Docker.

## Prerequisites

- Node.js (v18+)
- Python 3.10+
- PostgreSQL
- Redis
- Qdrant (or Qdrant Cloud)

## Configuration

1. In `backend/`, copy `.env.example` to `.env.local` and configure your credentials.
2. In `frontend/`, copy `.env.example` to `.env.local` and configure your credentials.

> **Note**: Do NOT hardcode credentials into the codebase. Always use the `.env.local` file.

## Running the Application

You can use the provided scripts in the `scripts/` directory to run individual components or the entire stack:

- **Run all components**: `scripts\run_all_local.bat`
- **Run frontend only**: `scripts\start_frontend.bat`
- **Run backend only**: `scripts\start_backend.bat`
- **Run Celery worker**: `scripts\start_worker.bat`
- **Run Celery beat**: `scripts\start_scheduler.bat`

## Architecture

During local development, the application is configured to read from `.env.local` based on the `ENVIRONMENT=local` variable set in the startup scripts.
