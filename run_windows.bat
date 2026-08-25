@echo off
REM One-click launcher for Windows.
REM Double-click this file (or run it from Command Prompt) to set up
REM and start the whole project: venv, dependencies, backend, and UI.

cd /d "%~dp0"

echo ==============================================
echo  Workflow Automation Tool - Setup and Launch
echo ==============================================

REM --- Secrets now live in a .env file (never committed to git) ---
REM --- instead of being typed into this script - see .env.example ---
if not exist ".env" (
    echo No .env file found - creating one from .env.example.
    copy .env.example .env >nul
    echo.
    echo IMPORTANT: open the new .env file and fill in your GROQ_API_KEY
    echo and CREDENTIAL_ENCRYPTION_KEY. See SETUP_CHECKLIST.md for how to
    echo generate a CREDENTIAL_ENCRYPTION_KEY. The app will still run
    echo without these - the natural-language builder just falls back to
    echo a keyword-based parser, and saved credentials won't survive a
    echo restart - but setting them now avoids re-doing setup later.
    echo.
    pause
)

REM --- Step 1: Create virtual environment if it doesn't exist ---
REM Explicitly targets Python 3.13 rather than plain "py", because
REM letting Windows pick whatever it defaults to can silently select a
REM beta/pre-release Python (e.g. 3.14 betas have known incompatibilities
REM with current fastapi/pydantic - this project needs a stable release).
if not exist "venv\" (
    echo Creating virtual environment using Python 3.13...
    py -3.13 -m venv venv
    if not exist "venv\Scripts\activate.bat" (
        echo.
        echo ERROR: Could not create the virtual environment with Python 3.13.
        echo Run "py -0" to see which Python versions are installed on this
        echo machine, then either install Python 3.13 from
        echo https://www.python.org/downloads/ or edit this line in
        echo run_windows.bat to use a different installed version instead:
        echo     py -3.13 -m venv venv
        echo.
        pause
        exit /b 1
    )
) else (
    echo Virtual environment already exists, skipping creation.
)

REM --- Step 2: Install dependencies into the venv ---
echo Installing dependencies...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo.
    echo ERROR: Could not activate the virtual environment.
    echo Try deleting the "venv" folder and running this script again.
    echo.
    pause
    exit /b 1
)
pip install -r requirements.txt --quiet

REM --- Step 3: Start the FastAPI backend in a new window ---
echo Starting backend (FastAPI)...
start "Backend - FastAPI" cmd /k "call venv\Scripts\activate.bat && uvicorn app.main:app --reload"

REM Give the backend a few seconds to start before seeding/connecting
timeout /t 4 /nobreak >nul

REM --- Step 4: Seed example workflows (safe to run every time) ---
echo Seeding example workflows...
call venv\Scripts\activate.bat
python seed_data.py

REM --- Step 5: Start the Streamlit UI in a new window ---
echo Starting UI (Streamlit)...
start "Frontend - Streamlit" cmd /k "call venv\Scripts\activate.bat && streamlit run streamlit_app.py"

echo.
echo All set. Two new windows should have opened:
echo   1. Backend  (FastAPI)   - keep this running
echo   2. Frontend (Streamlit) - your browser should open automatically
echo.
echo If the browser didn't open, go to http://localhost:8501
pause
