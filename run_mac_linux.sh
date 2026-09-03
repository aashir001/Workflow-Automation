#!/bin/bash
cd "$(dirname "$0")"

echo "=============================================="
echo " Workflow Automation Tool - Setup and Launch"
echo "=============================================="

if [ ! -f ".env" ]; then
    echo "No .env file found - creating one from .env.example."
    cp .env.example .env
    echo ""
    echo "IMPORTANT: open .env and fill in GROQ_API_KEY and"
    echo "CREDENTIAL_ENCRYPTION_KEY. The app still runs without these."
    echo ""
    read -p "Press Enter to continue..."
fi

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists, skipping creation."
fi

echo "Installing backend dependencies..."
source venv/bin/activate
pip install -r requirements.txt --quiet

echo "Starting backend (FastAPI)..."
uvicorn app.main:app --reload > backend.log 2>&1 &
BACKEND_PID=$!
sleep 4

echo "Seeding example workflows..."
python seed_data.py

echo "Installing frontend dependencies (first run only)..."
cd frontend
if [ ! -d "node_modules" ]; then
    npm install
fi

echo ""
echo "Backend running in background (PID $BACKEND_PID, logs in backend.log)"
echo "Starting frontend - press Ctrl+C to stop it."
echo "Run 'kill $BACKEND_PID' afterward to stop the backend too."
echo ""
npm run dev
