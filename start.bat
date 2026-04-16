@echo off
echo ========================================
echo   ZhangFang V1 Starting...
echo ========================================
echo.

cd /d "%~dp0"

if not exist "backend\venv\Scripts\python.exe" (
    echo [ERROR] venv not found. Please run setup.bat first.
    pause
    exit /b 1
)

cd backend
venv\Scripts\python.exe main.py
pause
