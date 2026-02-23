#!/bin/bash
EMPIRE_DIR="$HOME/Empire"
LOG_DIR="$EMPIRE_DIR/logs"
mkdir -p "$LOG_DIR"

if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    cd "$EMPIRE_DIR/backend"
    source venv/bin/activate
    nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$LOG_DIR/backend.log" 2>&1 &
    sleep 3
fi

if ! curl -s http://localhost:3000 > /dev/null 2>&1; then
    cd "$EMPIRE_DIR/founder_dashboard"
    nohup npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
    sleep 5
fi

xdg-open http://localhost:3000
xdg-open http://localhost:3000
