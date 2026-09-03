@echo off
cd /d "%~dp0"

echo ==============================================
echo  Workflow Automation Tool - Setup and Launch
echo ==============================================

REM --- Secrets live in .env (gitignored) - see .env.example ---
if not exist ".env" (
    echo No .env file found - creating one from .env.example.
    copy .env.example .env >nul
    echo.
    echo IMPORTANT: open .env and fill in GROQ_API_KEY and
    echo CREDENTIAL_ENCRYPTION_KEY. The app still runs without these.
    echo.
    pause
)

REM --- Step 1: Python venv (explicitly 3.13 - avoids picking a beta build) ---
if not exist "venv\" (
    echo Creating virtual environment using Python 3.13...
    py -3.13 -m venv venv
    if not exist "venv\Scripts\activate.bat" (
        echo.
        echo ERROR: Could not create the virtual environment with Python 3.13.
        echo Run "py -0" to see installed versions, then edit this line to match:
        echo     py -3.13 -m venv venv
        echo.
        pause
        exit /b 1
    )
) else (
    echo Virtual environment already exists, skipping creation.
)

echo Installing backend dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet

REM --- Step 2: Start the backend ---
echo Starting backend (FastAPI)...
start "Backend - FastAPI" cmd /k "call venv\Scripts\activate.bat && uvicorn app.main:app --reload"

timeout /t 4 /nobreak >nul

echo Seeding example workflows...
call venv\Scripts\activate.bat
python seed_data.py

REM --- Step 3: Install and start the React frontend ---
echo Installing frontend dependencies (this may take a minute the first time)...
cd frontend
if not exist "node_modules\" (
    call npm install
)
echo Starting frontend (React/Vite)...
start "Frontend - React" cmd /k "npm run dev"
cd ..

echo.
echo All set. Two new windows should have opened:
echo   1. Backend  (FastAPI)  - keep this running
echo   2. Frontend (React)    - your browser should open automatically
echo.
echo If the browser didn't open, go to http://localhost:5173
pause
