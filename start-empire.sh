#!/bin/bash
# Empire Box - One Click Launcher

echo "🏰 Starting Empire Box..."

# Start backend
cd ~/Empire/backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start frontend
cd ~/Empire/founder_dashboard
npm run dev &
FRONTEND_PID=$!

# Wait for servers to start
echo "⏳ Waiting for servers..."
sleep 5

# Open browser
firefox http://localhost:3000 &

echo "✅ Empire Box is running!"
echo "   Backend PID: $BACKEND_PID"
echo "   Frontend PID: $FRONTEND_PID"
echo ""
echo "Press Ctrl+C to stop all servers"

# Wait and cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
