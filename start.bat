@echo off
chcp 65001 >nul 2>nul
echo ========================================
echo   ZhangFang Starting...
echo ========================================
echo.

cd /d "%~dp0"

if not exist "backend\venv\Scripts\python.exe" (
    echo [ERROR] venv not found. Please run setup.bat first.
    pause
    exit /b 1
)

REM Kill any existing process on port 8000
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000.*LISTENING"') do (
    echo Killing existing process PID %%a on port 8000...
    taskkill /F /PID %%a >nul 2>nul
)
timeout /t 2 /nobreak >nul

REM Build frontend if needed
if not exist "frontend\dist\index.html" (
    echo Building frontend...
    cd frontend
    call npx vite build
    cd ..
)

REM Start backend (serves frontend from dist on port 8000)
echo Starting on http://127.0.0.1:8000 ...
cd backend

REM Clear Python bytecode cache
for /d /r %%d in (__pycache__) do (
    if exist "%%d" rd /s /q "%%d" 2>nul
)

venv\Scripts\python.exe main.py
pause
