@echo off
echo ========================================
echo   ZhangFang Setup
echo ========================================
echo.

cd /d "%~dp0"

set PYTHON_CMD=
for %%p in (
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "python"
) do (
    if exist %%p (
        set "PYTHON_CMD=%%~p"
        goto :found
    )
)

echo [ERROR] Python 3.11+ not found. Please install Python first.
pause
exit /b 1

:found
echo Found Python: %PYTHON_CMD%

if not exist "backend\venv\Scripts\python.exe" (
    echo Creating venv...
    %PYTHON_CMD% -m venv backend\venv
    echo venv created.
)

echo Installing backend dependencies...
backend\venv\Scripts\pip.exe install -r backend\requirements.txt

if exist "frontend\package.json" (
    echo.
    echo Building frontend...
    cd frontend
    call npm install
    call npx vite build
    cd ..\
    echo Frontend build done.
)

echo.
echo ========================================
echo   Setup complete! Run start.bat to launch.
echo ========================================
pause
