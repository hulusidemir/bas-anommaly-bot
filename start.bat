@echo off
REM ──────────────────────────────────────────────────────────────
REM Basketbol Anomali Tespit Sistemi — Tek Komutla Başlatma
REM Backend (FastAPI) + Frontend (Vite) aynı anda çalışır.
REM ──────────────────────────────────────────────────────────────

set PROJ_DIR=%~dp0
set VENV_DIR=%PROJ_DIR%venv

REM venv varsa aktive et
if exist "%VENV_DIR%\Scripts\activate.bat" (
    call "%VENV_DIR%\Scripts\activate.bat"
)

echo Backend baslatiliyor (port 8000)...
start "backend" cmd /c "cd /d %PROJ_DIR%backend && uvicorn main:app --host 0.0.0.0 --port 8000"

echo Frontend baslatiliyor (port 5173)...
start "frontend" cmd /c "cd /d %PROJ_DIR%frontend && npm run dev -- --host"

echo.
echo ===================================================
echo   Dashboard  -  http://localhost:5173
echo   API        -  http://localhost:8000/api/health
echo   WebSocket  -  ws://localhost:8000/ws
echo ===================================================
echo.
echo Durdurmak icin terminal pencerelerini kapatin.
pause
