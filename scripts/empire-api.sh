#!/bin/bash
# Empire Switchboard API - lightweight HTTP server for service control
# Called by Command Center UI buttons

PORT=9090

while true; do
  REQUEST=$(echo -e "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nAccess-Control-Allow-Methods: GET,POST\r\n\r\n" | nc -l -p $PORT -q 1 2>/dev/null | head -1)

  PATH_REQ=$(echo "$REQUEST" | awk '{print $2}')

  case "$PATH_REQ" in
    /status)
      RAM=$(free | awk '/Mem:/ {printf "%.0f", ($3/$2)*100}')
      NJS=$(ps aux | grep next-server | grep -v grep | wc -l)
      SVCS=""
      for p in 3001 3002 3009 8000 8080; do
        NAME=""; case $p in 3001) NAME="WorkroomForge";; 3002) NAME="LuxeForge";; 3009) NAME="CommandCenter";; 8000) NAME="FastAPI";; 8080) NAME="Homepage";; esac
        PID=$(lsof -ti:$p 2>/dev/null | head -1)
        [ -n "$PID" ] && SVCS="$SVCS{\"port\":$p,\"name\":\"$NAME\",\"status\":\"live\",\"pid\":$PID}," || SVCS="$SVCS{\"port\":$p,\"name\":\"$NAME\",\"status\":\"off\",\"pid\":0},"
      done
      SVCS="${SVCS%,}"
      echo "{\"ram\":$RAM,\"nextjs\":$NJS,\"maxNextjs\":3,\"services\":[$SVCS]}"
      ;;
    /start/3001) cd ~/Empire/workroomforge && npm run dev -- -p 3001 >/dev/null 2>&1 & echo '{"ok":true,"msg":"WorkroomForge starting"}' ;;
    /start/3002) cd ~/Empire/luxeforge_web && npm run dev -- -p 3002 >/dev/null 2>&1 & echo '{"ok":true,"msg":"LuxeForge starting"}' ;;
    /start/3009) cd ~/Empire/founder_dashboard && npm run dev -- -p 3009 >/dev/null 2>&1 & echo '{"ok":true,"msg":"CommandCenter starting"}' ;;
    /start/8000) cd ~/Empire/backend && source venv/bin/activate 2>/dev/null; uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload >/dev/null 2>&1 & echo '{"ok":true,"msg":"FastAPI starting"}' ;;
    /start/8080) cd ~/Empire/homepage && npm run dev -- -p 8080 >/dev/null 2>&1 & echo '{"ok":true,"msg":"Homepage starting"}' ;;
    /stop/*) P=$(echo "$PATH_REQ" | grep -oP '\d+'); PID=$(lsof -ti:$P 2>/dev/null); [ -n "$PID" ] && kill $PID 2>/dev/null && echo "{\"ok\":true,\"msg\":\"Stopped port $P\"}" || echo "{\"ok\":false,\"msg\":\"Not running\"}" ;;
    *) echo '{"error":"unknown"}' ;;
  esac
done
