#!/bin/bash
# Empire Launch — Start all core services

pgrep -f 'uvicorn app.main:app' >/dev/null || (cd ~/Empire/backend && source ~/Empire/venv/bin/activate && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &)
sleep 2
pgrep -f 'next.*3009' >/dev/null || (cd ~/Empire/founder_dashboard && npm run dev &)
pgrep -f 'next.*3001' >/dev/null || (cd ~/Empire/workroomforge && npm run dev &)
pgrep -x ollama >/dev/null || systemctl is-active --quiet ollama.service 2>/dev/null || sudo systemctl start ollama.service 2>/dev/null
sleep 6
xdg-open http://localhost:3009
notify-send 'Empire Launched' 'Backend :8000 | Dashboard :3009 | WorkroomForge :3001 | Ollama :11434'
