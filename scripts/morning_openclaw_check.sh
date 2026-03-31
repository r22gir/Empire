#!/bin/bash
# Morning OpenClaw Health Check — runs at 7:30 AM EST via cron
# Sends email + Telegram with full system status

BACKEND_UP=false
CC_UP=false
OPENCLAW_UP=false
OLLAMA_UP=false

curl -s localhost:8000/health > /dev/null 2>&1 && BACKEND_UP=true
curl -s -o /dev/null -w "%{http_code}" localhost:3005 2>/dev/null | grep -q 200 && CC_UP=true
curl -s localhost:7878/health > /dev/null 2>&1 && OPENCLAW_UP=true
curl -s localhost:11434/api/tags > /dev/null 2>&1 && OLLAMA_UP=true

# Get task stats
TASK_STATS=$(curl -s http://localhost:8000/api/v1/openclaw/tasks/stats 2>/dev/null || echo '{"error":"unavailable"}')

# Get disk and memory
DISK=$(df -h /home | tail -1 | awk '{print $5 " used of " $2}')
RAM=$(free -h | awk '/Mem/{print $3 " used of " $2}')
UPTIME=$(uptime -p 2>/dev/null || echo "unknown")

# Build status
if [ "$OPENCLAW_UP" = true ] && [ "$BACKEND_UP" = true ]; then
    SUBJECT="Empire Morning Report — All Systems Go"
    EMOJI="☀️"
else
    SUBJECT="ALERT: Empire Services Down"
    EMOJI="🚨"
fi

BE_ICON=$( [ "$BACKEND_UP" = true ] && echo '✅' || echo '❌' )
CC_ICON=$( [ "$CC_UP" = true ] && echo '✅' || echo '❌' )
OC_ICON=$( [ "$OPENCLAW_UP" = true ] && echo '✅' || echo '❌' )
OL_ICON=$( [ "$OLLAMA_UP" = true ] && echo '✅' || echo '❌' )

MSG="${EMOJI} Good Morning! Empire Status ($(date '+%Y-%m-%d %H:%M %Z'))

Services:
  ${BE_ICON} Backend :8000
  ${CC_ICON} Command Center :3005
  ${OC_ICON} OpenClaw :7878
  ${OL_ICON} Ollama :11434

Resources: Disk ${DISK} | RAM ${RAM}
Uptime: ${UPTIME}

Tasks: ${TASK_STATS}
Dashboard: studio.empirebox.store/openclaw"

# Send Telegram
curl -s -X POST http://localhost:8000/api/v1/max/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\":$(echo "$MSG" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))'),\"channel\":\"telegram\"}" > /dev/null 2>&1

# Send Email
curl -s -X POST http://localhost:8000/api/v1/max/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"Send an email to the founder with subject: ${SUBJECT} and body: $(echo "$MSG" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')\",\"channel\":\"system\"}" > /dev/null 2>&1

echo "$(date): Morning check sent. OC=$OPENCLAW_UP BE=$BACKEND_UP" >> ~/empire-repo/logs/morning_checks.log
