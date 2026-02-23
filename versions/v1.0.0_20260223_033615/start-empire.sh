#!/bin/bash
#══════════════════════════════════════════════════════════════
# 🏰 EMPIRE LAUNCHER
#══════════════════════════════════════════════════════════════

cd ~/Empire
VERSION=$(cat VERSION 2>/dev/null || echo "1.0.0")

echo ""
echo "🏰════════════════════════════════════════════════════════🏰"
echo "   EMPIRE SYSTEM v${VERSION}"
echo "🏰════════════════════════════════════════════════════════🏰"
echo ""

# Kill existing processes
echo "🔄 Stopping existing services..."
pkill -f "next dev" 2>/dev/null
pkill -f "uvicorn" 2>/dev/null
sleep 2

# Start Backend
echo "⚙️  Starting Backend API (port 8000)..."
cd ~/Empire/backend
source ~/Empire/venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
sleep 3

# Start Empire Control Center
echo "🏰 Starting Empire Control Center (port 3000)..."
cd ~/Empire/empire-control
npm run dev &
sleep 3

# Start WorkroomForge
echo "🏭 Starting WorkroomForge (port 3001)..."
cd ~/Empire/workroomforge
npm run dev &
sleep 2

# Start MAX Interface
echo "🤖 Starting MAX Interface (port 3009)..."
cd ~/Empire/founder_dashboard
npm run dev &
sleep 2

echo ""
echo "🏰════════════════════════════════════════════════════════🏰"
echo "   EMPIRE v${VERSION} IS LIVE!"
echo "🏰════════════════════════════════════════════════════════🏰"
echo ""
echo "📍 URLs:"
echo "   🏰 Control Center:  http://localhost:3000"
echo "   🏭 WorkroomForge:   http://localhost:3001"
echo "   🤖 MAX Interface:   http://localhost:3009"
echo "   ⚙️  Backend API:     http://localhost:8000"
echo ""
echo "💾 Version Commands:"
echo "   ./save-version        - Save new version"
echo "   ./restore-version     - Restore old version"
echo "   ./version             - Check current version"
echo ""

# Open browser
sleep 2
xdg-open http://localhost:3000 2>/dev/null || open http://localhost:3000 2>/dev/null &

# Keep running
wait
