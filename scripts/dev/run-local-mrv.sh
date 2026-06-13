#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "============================================="
echo "VeriField Nexus - Local MRV Startup Script"
echo "============================================="

# Ensure we are at the root directory
cd "$(dirname "$0")/../.."

# 1. Install dependencies
echo "[1/3] Installing workspace dependencies..."
npm install

# 2. Check backend virtual environment
echo "[2/3] Checking backend virtual environment..."
if [ ! -d "backend/venv" ]; then
    echo "Creating python virtual environment in backend/venv..."
    python3 -m venv backend/venv
    backend/venv/bin/pip install --upgrade pip
fi

echo "Installing backend python dependencies..."
backend/venv/bin/pip install -r backend/requirements.txt

# 3. Start Backend & Dashboard concurrently
echo "[3/3] Starting backend (port 8000) and dashboard (port 3000)..."

# 3.1. Detect Local IP & configure environment
LOCAL_IP=$(ipconfig getifaddr en0 || ipconfig getifaddr en1 || ifconfig | grep "inet " | grep -v 127.0.0.1 | head -n 1 | awk '{print $2}')
if [ -z "$LOCAL_IP" ]; then
    LOCAL_IP="127.0.0.1"
fi
echo "Detected Local IP: $LOCAL_IP"

# Update dashboard/.env.local
ENV_FILE="dashboard/.env.local"
if [ -f "$ENV_FILE" ]; then
    if grep -q "NEXT_PUBLIC_API_URL=" "$ENV_FILE"; then
        sed -i '' "s|NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=|g" "$ENV_FILE"
    else
        echo "NEXT_PUBLIC_API_URL=" >> "$ENV_FILE"
    fi
else
    echo "NEXT_PUBLIC_API_URL=" > "$ENV_FILE"
    echo "NEXT_IGNORE_INCORRECT_LOCKFILE=true" >> "$ENV_FILE"
fi
echo "Updated $ENV_FILE: NEXT_PUBLIC_API_URL= (using Next.js rewrites proxy)"

# Kill existing uvicorn instances on port 8000 to avoid conflicts
if lsof -t -i:8000 >/dev/null; then
    echo "Freeing port 8000..."
    kill -9 $(lsof -t -i:8000) || true
fi

# Kill existing Next.js instances on port 3000
if lsof -t -i:3000 >/dev/null; then
    echo "Freeing port 3000..."
    kill -9 $(lsof -t -i:3000) || true
fi

# Start FastAPI backend in the background (bind to 0.0.0.0)
echo "Starting FastAPI Backend..."
cd backend
venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Start Next.js Dashboard in the background (bind to 0.0.0.0)
echo "Starting Next.js Dashboard..."
npm run dev --prefix dashboard -- -H 0.0.0.0 > dashboard.log 2>&1 &
DASHBOARD_PID=$!

# Trap signals to cleanly kill background processes on exit
cleanup() {
    echo ""
    echo "Shutting down local services..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $DASHBOARD_PID 2>/dev/null || true
    echo "Cleanup complete."
}
trap cleanup EXIT INT TERM

echo ""
echo "============================================="
echo "Local MRV services are running!"
echo "- FastAPI API:              http://$LOCAL_IP:8000"
echo "- Dashboard (Admin Panel):  http://$LOCAL_IP:3000"
echo "- standalone Capture PWA:    http://$LOCAL_IP:3000/capture"
echo ""
echo "📱 OPEN ON IPHONE:"
echo "http://$LOCAL_IP:3000/capture"
echo ""
echo "- Backend log:  tail -f backend.log"
echo "- Frontend log: tail -f dashboard.log"
echo "============================================="
echo "Press [Ctrl+C] to stop all services."
echo ""

# Keep script running to show logs/status
while true; do
    sleep 1
done
