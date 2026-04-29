@echo off
chcp 65001 >nul 2>nul
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

REM Kill any existing process on port 8000
echo Checking port 8000...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000.*LISTENING"') do (
    echo Killing existing process PID %%a on port 8000...
    taskkill /F /PID %%a >nul 2>nul
    timeout /t 1 /nobreak >nul
)

cd backend

REM Clear Python bytecode cache to prevent stale routes
echo Clearing __pycache__...
for /d /r %%d in (__pycache__) do (
    if exist "%%d" rd /s /q "%%d" 2>nul
)

venv\Scripts\python.exe main.py
pause
