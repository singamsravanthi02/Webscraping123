@echo off
echo Starting SPIP Celery Scheduler (Local Environment)...
cd backend
set ENVIRONMENT=local
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)
celery -A app.worker.celery beat --loglevel=info
