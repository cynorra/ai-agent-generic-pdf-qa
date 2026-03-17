@echo off
echo Starting Generic AI Agent System...

:: Start Backend
start cmd /k "title Backend && venv\Scripts\activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload"

:: Start Frontend
start cmd /k "title Frontend && cd auraflow-intelligence-main && npm run dev"

echo System is starting in separate windows.
echo Backend: http://localhost:5000
echo Frontend: http://localhost:5173
pause
