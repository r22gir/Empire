#!/bin/bash
# Auto-save Claude session context every 3 min (cron) or manually
# Usage: ~/Empire/scripts/save-session.sh ["optional description"]

SESSION_FILE="$HOME/Empire/.claude-session.md"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M')
BRANCH=$(cd ~/Empire && git branch --show-current 2>/dev/null || echo "unknown")
LAST_COMMIT=$(cd ~/Empire && git log --oneline -1 2>/dev/null || echo "unknown")
DIRTY=$(cd ~/Empire && git diff --name-only 2>/dev/null | head -15)
DIRTY_COUNT=$(cd ~/Empire && git diff --name-only 2>/dev/null | wc -l)
UNTRACKED=$(cd ~/Empire && git ls-files --others --exclude-standard 2>/dev/null | head -10)

# Recently modified files (last 5 min, lightweight)
RECENT=$(find ~/Empire -maxdepth 3 \( -name '*.py' -o -name '*.ts' -o -name '*.tsx' -o -name '*.md' \) 2>/dev/null \
    | xargs stat --format='%Y %n' 2>/dev/null \
    | awk -v cutoff="$(date -d '5 minutes ago' +%s)" '$1 > cutoff {print $2}' \
    | head -10)

# Find the most recent Claude plan file (if any)
LATEST_PLAN=""
LATEST_PLAN_PREVIEW=""
if [ -d "$HOME/.claude/plans" ]; then
    LATEST_PLAN=$(ls -t "$HOME/.claude/plans"/*.md 2>/dev/null | head -1)
    if [ -n "$LATEST_PLAN" ]; then
        # Grab first 30 lines, strip code fences that break heredoc
        LATEST_PLAN_PREVIEW=$(head -30 "$LATEST_PLAN" 2>/dev/null | sed 's/```/---code-block---/g')
    fi
fi

# Find most recent Claude conversation transcript
LATEST_SESSION=""
if [ -d "$HOME/.claude/projects/-home-rg-Empire" ]; then
    LATEST_SESSION=$(ls -t "$HOME/.claude/projects/-home-rg-Empire"/*.jsonl 2>/dev/null | head -1)
fi

# Running Empire services (fast port check)
SERVICES=""
for pair in "8000:backend" "3000:empire-app" "3001:workroomforge" "3002:luxeforge" "3009:founder-dashboard" "7878:openclaw" "11434:ollama"; do
    port="${pair%%:*}"
    name="${pair##*:}"
    if ss -tlnp 2>/dev/null | grep -q ":${port} " 2>/dev/null; then
        SERVICES="${SERVICES}\n- ${name} :${port} ONLINE"
    fi
done

# Description: manual arg > auto-detect from recent changes
if [ -n "$1" ]; then
    DESCRIPTION="$1"
elif [ -n "$RECENT" ]; then
    DESCRIPTION="Auto-detected recent edits:\n$(echo "$RECENT" | sed 's|/home/rg/Empire/||g')"
else
    DESCRIPTION="No recent changes detected. Check git log."
fi

cat > "$SESSION_FILE" << ENDOFFILE
# Claude Session State (auto-saved)
## Last Updated: $TIMESTAMP

## What Was Happening
$DESCRIPTION

## Git State
- Branch: $BRANCH
- Last Commit: $LAST_COMMIT
- Modified Files ($DIRTY_COUNT): ${DIRTY:-none}
- Untracked: ${UNTRACKED:-none}

## Active Plan File
${LATEST_PLAN:-No plan file found}

## Plan Preview
${LATEST_PLAN_PREVIEW:-No active plan}

## Previous Session Transcript
${LATEST_SESSION:-No transcript found}

## Running Services
$(echo -e "${SERVICES:-No Empire services detected}")

## System
- RAM: $(free -h | awk '/Mem:/{print $3"/"$2}')
- Disk: $(df -h / | awk 'NR==2{print $3"/"$2}')
ENDOFFILE

# Silent in cron mode, verbose in terminal
[ -t 1 ] && echo "Session saved to $SESSION_FILE at $TIMESTAMP"
exit 0
