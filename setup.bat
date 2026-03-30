@echo off
REM ──────────────────────────────────────────────────────────────
REM Basketbol Anomali Tespit Sistemi — Windows Kurulum Scripti
REM ──────────────────────────────────────────────────────────────

set PROJ_DIR=%~dp0
set VENV_DIR=%PROJ_DIR%venv

echo Sanal ortam olusturuluyor...
python -m venv "%VENV_DIR%"

echo Sanal ortam aktif ediliyor...
call "%VENV_DIR%\Scripts\activate.bat"

echo pip guncelleniyor...
pip install --upgrade pip

echo Backend bagimliliklar yukleniyor...
pip install -r "%PROJ_DIR%backend\requirements.txt"

echo Frontend bagimliliklar yukleniyor...
cd "%PROJ_DIR%frontend" && npm install

cd "%PROJ_DIR%"
echo.
echo Kurulum tamamlandi!
echo.
echo Kullanim:
echo   venv\Scripts\activate
echo   cd backend
echo   uvicorn main:app --reload --host 0.0.0.0 --port 8000
