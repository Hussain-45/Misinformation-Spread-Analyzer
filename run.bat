@echo off
echo ===================================================
echo Veritas // Misinformation Spread Analyser Launcher
echo ===================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your system PATH.
    echo Please install Python 3.8+ and try again.
    pause
    exit /b 1
)

:: Set up virtual environment if it doesn't exist
if not exist .venv (
    echo [SETUP] Creating Python virtual environment in .venv...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: Install/Upgrade dependencies
echo [SETUP] Installing/Updating required packages...
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Package installation failed.
    pause
    exit /b 1
)

echo.
echo ===================================================
echo [SUCCESS] Setup complete! Starting Veritas...
echo Access the dashboard in your browser:
echo --^> http://127.0.0.1:8000
echo ===================================================
echo.

:: Launch FastAPI server
.venv\Scripts\python main.py

pause
