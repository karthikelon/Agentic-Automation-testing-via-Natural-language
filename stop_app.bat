@echo off
echo ========================================
echo   FORCE STOPPING ANTIGRAVITY SERVICES
echo ========================================

echo.
echo Stopping Backend (Port 8000)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a
)

echo.
echo Stopping Frontend (Port 5173)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING') do (
    taskkill /F /PID %%a
)

echo.
echo Cleaning up lingering browser processes...
taskkill /F /IM chrome.exe /T >nul 2>&1
taskkill /F /IM msedgewebview2.exe /T >nul 2>&1

echo.
echo [DONE] All services have been forcefully shut down.
pause
