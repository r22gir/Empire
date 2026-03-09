#!/bin/bash
#══════════════════════════════════════════════════════════════
# EMPIRE LAUNCHER — EmpireDell
# One-click start: Backend + Command Center + Browser
#══════════════════════════════════════════════════════════════

echo ""
echo "════════════════════════════════════════════════════════"
echo "   E M P I R E  —  Starting all services..."
echo "════════════════════════════════════════════════════════"
echo ""

# Safely stop existing services on our ports
echo "Stopping any existing services..."
for port in 8000 3009; do
  pid=$(lsof -ti :$port 2>/dev/null)
  if [ -n "$pid" ]; then
    echo "  Stopping PID $pid on port $port"
    kill $pid 2>/dev/null
    sleep 1
  fi
done

# Start Backend API
echo "Starting Backend API (port 8000)..."
cd ~/empire-repo/backend
source ~/empire-repo/backend/venv/bin/activate
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/empire-backend.log 2>&1 &
BACKEND_PID=$!
sleep 3

# Start Command Center (port 3009)
echo "Starting Command Center (port 3009)..."
cd ~/empire-repo/empire-command-center
nohup npm run dev -- -p 3009 > /tmp/empire-cc.log 2>&1 &
CC_PID=$!
sleep 5

# Verify services
echo ""
echo "Checking services..."
BACKEND_OK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs 2>/dev/null)
CC_OK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3009 2>/dev/null)

[ "$BACKEND_OK" = "200" ] && echo "  Backend API:       LIVE (port 8000)" || echo "  Backend API:       STARTING..."
[ "$CC_OK" = "200" ] && echo "  Command Center:    LIVE (port 3009)" || echo "  Command Center:    STARTING..."

echo ""
echo "════════════════════════════════════════════════════════"
echo "   EMPIRE IS LIVE!"
echo "════════════════════════════════════════════════════════"
echo ""
echo "  Command Center:   http://localhost:3009"
echo "  LuxeForge Intake: http://localhost:3009/intake"
echo "  AMP:              http://localhost:3009/amp"
echo "  Backend API:      http://localhost:8000/docs"
echo ""
echo "  Logs: /tmp/empire-backend.log"
echo "        /tmp/empire-cc.log"
echo ""
echo "════════════════════════════════════════════════════════"

# Open browser
export DISPLAY=:0
sleep 1
xdg-open http://localhost:3009 2>/dev/null || firefox http://localhost:3009 2>/dev/null &

# Send desktop notification
notify-send "Empire Launched" "Command Center: localhost:3009 | API: localhost:8000" 2>/dev/null

# Keep running
wait
