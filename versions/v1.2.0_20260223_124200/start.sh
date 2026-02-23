#!/bin/bash
cd ~/Empire

# Load environment variables
export $(grep -v '^#' ~/Empire/backend/.env | xargs)

# Start backend
cd ~/Empire/backend
source ~/Empire/venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 > ~/Empire/logs/backend.log 2>&1 &

# Start frontend
cd ~/Empire/founder_dashboard
npm run dev > ~/Empire/logs/frontend.log 2>&1 &

echo "EmpireBox started!"
echo "Dashboard: http://localhost:3000"
echo "Backend: http://localhost:8000"
