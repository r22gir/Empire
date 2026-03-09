#!/bin/bash
# Empire Command Center — Launch on port 3009
cd "$(dirname "$0")"
echo "Stopping any existing process on port 3009..."
fuser -k 3009/tcp 2>/dev/null
sleep 1
echo "Starting Command Center..."
PORT=3009 npm run dev &
sleep 4
echo "Opening browser..."
xdg-open http://localhost:3009 2>/dev/null || echo "Open http://localhost:3009 in your browser"
echo "Command Center running on http://localhost:3009"
