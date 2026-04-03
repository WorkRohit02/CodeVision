#!/bin/bash
set -e

echo ""
echo " =========================================="
echo "  CodeVision - AI Code Analysis (Gemini)"
echo " =========================================="
echo ""

cd "$(dirname "$0")"

if ! command -v python3 &>/dev/null; then
    echo " ERROR: Python 3 not found. Install from https://python.org"
    exit 1
fi

cd backend

if [ ! -d "venv" ]; then
    echo " Setting up virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo " Installing dependencies..."
pip install -r requirements.txt -q

if [ ! -f ".env" ]; then
    echo ""
    echo " SETUP REQUIRED:"
    echo " 1. Get your FREE Gemini API key from https://aistudio.google.com/apikey"
    echo " 2. Edit the file:  backend/.env"
    echo " 3. Replace YOUR_KEY_HERE with your real key"
    echo ""
    echo "GEMINI_API_KEY=YOUR_KEY_HERE" > .env
    echo " Created backend/.env — add your key then run again."
    exit 1
fi

if grep -q "YOUR_KEY_HERE" .env; then
    echo ""
    echo " API key not set. Edit backend/.env and replace YOUR_KEY_HERE"
    exit 1
fi

echo ""
echo " Starting CodeVision at http://localhost:8000"
echo " Press Ctrl+C to stop"
echo ""

sleep 1 && (open http://localhost:8000 2>/dev/null || xdg-open http://localhost:8000 2>/dev/null) &

python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
