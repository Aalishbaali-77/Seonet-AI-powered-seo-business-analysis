@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
  echo Missing .venv at "%~dp0.venv"
  pause
  exit /b 1
)

start "Seonet Backend" cmd /k "call .venv\Scripts\activate.bat && cd backend && python manage.py runserver"
start "Seonet Frontend" cmd /k "cd frontend && npm start"
