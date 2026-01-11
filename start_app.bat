@echo off
echo Starting Backend...
start "Backend" cmd /k "cd backend && python run_backend.py"

echo Starting Frontend...
start "Frontend" cmd /k "cd frontend && npm run dev"

echo Done. Check the windows.
