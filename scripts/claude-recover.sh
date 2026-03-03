#!/bin/bash
# Claude Code Crash Recovery — builds context from last session, copies to clipboard
# Usage: double-click from desktop or run from terminal

CLAUDE_EMPIRE="$HOME/.claude/projects/-home-rg-Empire"
CLAUDE_HOME="$HOME/.claude"
MEMORY_DIR="$HOME/.claude/projects/-home-rg/memory"

echo "============================================"
echo "  CLAUDE CRASH RECOVERY"
echo "============================================"
echo ""

# --- 1. Find latest session transcript ---
LATEST_SESSION=$(ls -t "$CLAUDE_EMPIRE"/*.jsonl 2>/dev/null | head -1)
LAST_MESSAGES=""
if [ -n "$LATEST_SESSION" ]; then
    SESSION_ID=$(basename "$LATEST_SESSION" .jsonl)
    echo "Latest session: $SESSION_ID"
    echo "  Modified: $(date -r "$LATEST_SESSION" '+%Y-%m-%d %H:%M:%S')"

    # Extract last ~20 user/assistant text messages from JSONL
    # Format: {type: "user"|"assistant", message: {content: ...}}
    LAST_MESSAGES=$(python3 -c "
import json, sys
msgs = []
with open('$LATEST_SESSION') as f:
    for line in f:
        try:
            obj = json.loads(line.strip())
            tp = obj.get('type','')
            if tp not in ('user','assistant'): continue
            msg = obj.get('message',{})
            content = msg.get('content','')
            texts = []
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get('type') == 'text':
                        t = c['text'].strip()
                        if t and not t.startswith('<system'):
                            texts.append(t[:400])
            elif isinstance(content, str):
                t = content.strip()
                if t and not t.startswith('<system'):
                    texts.append(t[:400])
            for t in texts:
                msgs.append(f'{tp.upper()}: {t}')
        except: pass
for m in msgs[-20:]:
    print(m)
" 2>/dev/null)
fi

# --- 2. Find latest plan file ---
LATEST_PLAN=$(ls -t "$CLAUDE_HOME"/plans/*.md 2>/dev/null | head -1)
PLAN_CONTENT=""
if [ -n "$LATEST_PLAN" ]; then
    PLAN_NAME=$(basename "$LATEST_PLAN")
    echo "Latest plan:   $PLAN_NAME"
    echo "  Modified: $(date -r "$LATEST_PLAN" '+%Y-%m-%d %H:%M:%S')"
    PLAN_CONTENT=$(cat "$LATEST_PLAN")
fi

# --- 3. Read memory files ---
MEMORY_CONTENT=""
if [ -d "$MEMORY_DIR" ]; then
    echo "Memory dir:    $MEMORY_DIR"
    for f in "$MEMORY_DIR"/*.md; do
        [ -f "$f" ] && MEMORY_CONTENT+="
--- $(basename "$f") ---
$(cat "$f")
"
    done
fi

# --- 4. Check for .claude-session.md (old format) ---
OLD_SESSION="$HOME/Empire/.claude-session.md"
OLD_SESSION_CONTENT=""
if [ -f "$OLD_SESSION" ]; then
    echo "Session file:  $OLD_SESSION"
    OLD_SESSION_CONTENT=$(cat "$OLD_SESSION")
fi

echo ""

# --- 5. Build recovery prompt ---
RECOVERY=$(cat <<'HEADER'
Computer crashed. Resume where we left off. Here's the full context from the last session:

HEADER
)

if [ -n "$PLAN_CONTENT" ]; then
    RECOVERY+="
## Active Plan
$PLAN_CONTENT
"
fi

if [ -n "$LAST_MESSAGES" ]; then
    RECOVERY+="
## Last Conversation Messages
$LAST_MESSAGES
"
fi

if [ -n "$OLD_SESSION_CONTENT" ]; then
    RECOVERY+="
## Session State
$OLD_SESSION_CONTENT
"
fi

RECOVERY+="
After reading, tell me:
1. What we were working on
2. How far we got (what's done vs not done)
3. What the next step is

Then continue the work."

# --- 6. Copy to clipboard ---
echo "$RECOVERY" | xclip -selection clipboard

LINES=$(echo "$RECOVERY" | wc -l)
echo "============================================"
echo "  COPIED TO CLIPBOARD ($LINES lines)"
echo "  Paste into Claude Code and go!"
echo "============================================"
echo ""
echo "Tip: open a terminal, run 'cd ~/Empire && claude'"
echo "     then paste (Ctrl+V) and press Enter"
