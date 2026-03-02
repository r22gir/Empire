#!/bin/bash
clear
echo "🚀 LAUNCHING EMPIREBOX ECOSYSTEM..."
echo ""

# Kill any existing processes
pkill -f uvicorn 2>/dev/null
pkill -f "next dev" 2>/dev/null
pkill -f "python3 -m http.server" 2>/dev/null
sleep 2

# Start Backend API
echo "🐍 Starting Backend API..."
cd ~/Empire/backend
source venv/bin/activate
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
sleep 3

# Start Homepage
echo "🏠 Starting Homepage..."
cd ~/Empire/homepage
python3 -m http.server 8080 &
sleep 1

# Start Founder Dashboard
echo "📊 Starting Founder Dashboard..."
cd ~/Empire/founder_dashboard
npm run dev &
sleep 2

# Start WorkroomForge
echo "🏭 Starting WorkroomForge..."
cd ~/Empire/workroomforge
npm run dev &
sleep 2

# Start LuxeForge
echo "✨ Starting LuxeForge..."
cd ~/Empire/luxeforge_web
npm run dev &
sleep 2

echo ""
echo "══════════════════════════════════════════════"
echo "✅ EMPIREBOX ECOSYSTEM RUNNING"
echo "══════════════════════════════════════════════"
echo ""
echo "🏠 Homepage:           http://localhost:8080"
echo "🧠 Agent Command:      http://localhost:8080/agent-command-center.html"
echo "📊 Founder Dashboard:  http://localhost:3000"
echo "🏭 WorkroomForge:      http://localhost:3001"
echo "✨ LuxeForge Portal:   http://localhost:3002/portal"
echo "🔌 Backend API:        http://localhost:8000/docs"
echo ""
echo "══════════════════════════════════════════════"
echo "Press Ctrl+C to stop all services"
echo "══════════════════════════════════════════════"

# Keep script running
wait
