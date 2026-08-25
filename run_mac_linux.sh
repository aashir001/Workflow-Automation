#!/bin/bash
# One-click launcher for Mac/Linux.
# Run with: ./run_mac_linux.sh
# (First time only, you may need: chmod +x run_mac_linux.sh)

cd "$(dirname "$0")"

echo "=============================================="
echo " Workflow Automation Tool - Setup and Launch"
echo "=============================================="

# --- Secrets now live in a .env file (never committed to git) ---
# --- instead of being typed into this script - see .env.example ---
if [ ! -f ".env" ]; then
    echo "No .env file found - creating one from .env.example."
    cp .env.example .env
    echo ""
    echo "IMPORTANT: open the new .env file and fill in your GROQ_API_KEY"
    echo "and CREDENTIAL_ENCRYPTION_KEY. See SETUP_CHECKLIST.md for how to"
    echo "generate a CREDENTIAL_ENCRYPTION_KEY. The app will still run"
    echo "without these - the natural-language builder just falls back to"
    echo "a keyword-based parser, and saved credentials won't survive a"
    echo "restart - but setting them now avoids re-doing setup later."
    echo ""
    read -p "Press Enter to continue..."
fi

# --- Step 1: Create virtual environment if it doesn't exist ---
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists, skipping creation."
fi

# --- Step 2: Install dependencies into the venv ---
echo "Installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt --quiet

# --- Step 3: Start the FastAPI backend in the background ---
echo "Starting backend (FastAPI)..."
uvicorn app.main:app --reload > backend.log 2>&1 &
BACKEND_PID=$!

# Give the backend a few seconds to start
sleep 4

# --- Step 4: Seed example workflows (safe to run every time) ---
echo "Seeding example workflows..."
python seed_data.py

# --- Step 5: Start the Streamlit UI (this opens in your browser) ---
echo "Starting UI (Streamlit)..."
echo ""
echo "Backend running in background (PID $BACKEND_PID, logs in backend.log)"
echo "Press Ctrl+C to stop the UI. Run 'kill $BACKEND_PID' to stop the backend after."
echo ""
streamlit run streamlit_app.py
