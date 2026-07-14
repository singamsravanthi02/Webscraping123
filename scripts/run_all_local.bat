@echo off
echo Starting all SPIP components locally...

start "SPIP Backend" cmd /c "call scripts\start_backend.bat"
start "SPIP Frontend" cmd /c "call scripts\start_frontend.bat"
start "SPIP Worker" cmd /c "call scripts\start_worker.bat"
start "SPIP Scheduler" cmd /c "call scripts\start_scheduler.bat"

echo All components started in separate windows.
