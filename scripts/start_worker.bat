@echo off
echo Starting SPIP Celery Worker (Local Environment)...
cd backend
set ENVIRONMENT=local
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)
    venv\Scripts\celery.exe -A app.worker.celery worker --loglevel=info
