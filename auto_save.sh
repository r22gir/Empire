#!/bin/bash
# Empire Auto-Save — runs every 10 minutes
# Saves git status, system state, and timestamps

while true; do
  TIMESTAMP=$(date +"%Y-%m-%d_%I%M%p")
  SAVE_DIR=~/Empire/saves
  mkdir -p "$SAVE_DIR"
  
  # Get latest git log
  LAST_COMMIT=$(cd ~/Empire && git log --oneline -1 2>/dev/null || echo "unknown")
  
  # Get system stats
  RAM=$(free -h | awk '/Mem:/{print $3"/"$2}')
  DISK=$(df -h /home | awk 'NR==2{print $3"/"$2}')
  
  # Check services
  BACKEND=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs 2>/dev/null || echo "down")
  FRONTEND=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3009 2>/dev/null || echo "down")
  
  # Get uncommitted changes
  CHANGES=$(cd ~/Empire && git status --short 2>/dev/null)
  
  # Get recent commits since last save
  RECENT=$(cd ~/Empire && git log --oneline -5 2>/dev/null)

  # Write save file
  cat > "$SAVE_DIR/EMPIRE_SAVE_${TIMESTAMP}.md" << EOF
# EMPIRE AUTO-SAVE — $(date +"%B %d, %Y %I:%M %p")

## System
- RAM: $RAM
- Disk: $DISK
- Backend (8000): $BACKEND
- Frontend (3009): $FRONTEND

## Latest Commit
$LAST_COMMIT

## Recent Commits (last 5)
$RECENT

## Uncommitted Changes
$CHANGES

## Services Running
$(ps aux | grep -E "uvicorn|next|claude" | grep -v grep | awk '{print $11, $12, $13}')

## Pending Tasks
1. AMP real content — Cali Colombia, 4 team members, 9 services
2. Whisper transcribe audio file
3. Verify Telegram bot
4. CRM database
5. SocialForge app
6. Multi-method measurement
7. Telegram voice response (TTS back)
8. Sync 13 desks with Telegram (shows 8)
EOF

  # Keep only last 6 saves (1 hour worth)
  ls -t "$SAVE_DIR"/EMPIRE_SAVE_*.md 2>/dev/null | tail -n +7 | xargs rm -f 2>/dev/null
  
  # Notify
  notify-send "🏰 Empire Saved" "$TIMESTAMP — $LAST_COMMIT"
  
  sleep 600
done
