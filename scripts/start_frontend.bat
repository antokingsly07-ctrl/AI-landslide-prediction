@echo off
title Landslide Frontend Launcher
set "FRONT=%~dp0..\frontend"
if not exist "%FRONT%\node_modules\vite\package.json" (
  echo Installing frontend dependencies, first run only. This can take a few minutes.
  pushd "%FRONT%"
  call npm install --no-audit --no-fund
  popd
)
echo Opening Vite dev server in its own window on http://localhost:5173
start "Vite Dev Server 5173 - close to stop" /D "%FRONT%" cmd /k "npm run dev"
echo Vite started. Close its window to stop.
exit /b 0