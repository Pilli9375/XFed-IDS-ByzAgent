@echo off
rem Starts the XFed-IDS dashboard: backend, traffic simulator, frontend,
rem then opens it in the default browser. Close the three windows to stop.
cd /d "%~dp0"
set PY=C:\Users\nagaa\anaconda3\envs\xfed\python.exe

start "XFed backend" cmd /k "%PY%" -m uvicorn backend.main:app --port 8000

echo Waiting for the backend (it re-checks the model, about a minute)...
:wait
timeout /t 3 /nobreak >nul
curl -s http://127.0.0.1:8000/health >nul 2>&1 || goto wait

start "XFed simulator" cmd /k "%PY%" -m backend.simulator
start "XFed frontend" cmd /k "cd /d frontend && npm run dev"

timeout /t 5 /nobreak >nul
start "" http://localhost:5173/
