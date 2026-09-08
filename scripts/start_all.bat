@echo off
title Landslide EWS - Start All
echo ===============================================
echo  AI Landslide Early Warning & Monitoring
echo ===============================================
echo.
echo Opening backend (8000) and frontend (5173)...
echo Each server opens in its own window. Keep them open.
echo.
start "Landslide Backend Launcher" cmd /c "%~dp0start_backend.bat"
timeout /t 2 /nobreak >nul
start "Landslide Frontend Launcher" cmd /c "%~dp0start_frontend.bat"
echo.
echo Done. Open http://localhost:5173 in your browser.
echo Login: super_admin@landslide.demo / admin123
echo.
exit /b 0