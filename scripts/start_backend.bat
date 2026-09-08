@echo off
title Landslide Backend Launcher
set "BK=%~dp0..\backend"
echo Opening backend server in its own window on http://localhost:8000 ...
start "Landslide Backend (8000) - close to stop" /D "%BK%" cmd /k ""%BK%\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo Backend started. Close its window to stop.
exit /b 0