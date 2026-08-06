@echo off
echo Starting Codebook Monitoring Tool...

start "Backend" cmd /k "cd /d %~dp0backend && python -m venv venv 2>nul && call venv\Scripts\activate && pip install -r requirements.txt -q && uvicorn app.main:app --reload --port 8000"

timeout /t 3 /nobreak >nul

start "Frontend" cmd /k "cd /d %~dp0frontend && npm install && npm run dev"

echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8000/docs
