#!/bin/bash
pkill -f "auto_save.sh" 2>/dev/null
nohup ~/Empire/auto_save.sh > /dev/null 2>&1 &
gnome-terminal --title="Empire Backend" -- bash -c "cd ~/Empire/backend && source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000; exec bash" &
gnome-terminal --title="Empire Frontend" -- bash -c "cd ~/Empire/founder_dashboard && npx next dev -p 3009; exec bash" &
gnome-terminal --title="Claude Code" -- bash -c "cd ~/Empire/founder_dashboard && claude; exec bash" &
notify-send "🏰 Empire Launched" "Backend:8000 | Frontend:3009 | Claude Code | Auto-save ON"
