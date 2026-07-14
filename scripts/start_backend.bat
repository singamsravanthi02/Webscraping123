@echo off
echo Starting SPIP Backend (Local Environment)...
cd backend
set ENVIRONMENT=local
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)
uvicorn app.main:app --reload --port 8000
