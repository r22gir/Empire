#!/usr/bin/env bash
# ============================================================
#  Claude Context System v2 — FULLY AUTOMATED
#  
#  START: Opens Claude Code with context injected automatically
#  END:   Claude Code summarizes session, saves to context file
#  
#  No clipboard. No pasting. Just click and go.
# ============================================================
set -euo pipefail

CONTEXT_DIR="$HOME/.claude-context"
SESSIONS_DIR="$CONTEXT_DIR/sessions"
MASTER_CONTEXT="$CONTEXT_DIR/master_context.md"
PROJECT_BRIEF="$CONTEXT_DIR/project_brief.md"
SESSION_NOTES="$CONTEXT_DIR/session_notes.md"
LAST_SUMMARY="$CONTEXT_DIR/last_chat_summary.md"
BIN_DIR="$HOME/.local/bin"
ICON_DIR="$HOME/.local/share/icons/claude-context"
CLAUDE_FOLDER="$HOME/Desktop/Claude"
COMMANDS_DIR="$HOME/.claude/commands"

echo ""
echo "Installing Claude Context System v2 (Fully Automated)..."
echo ""

# ── Create directories ──────────────────────────────────────
mkdir -p "$CONTEXT_DIR/sessions"
mkdir -p "$BIN_DIR"
mkdir -p "$ICON_DIR"
mkdir -p "$CLAUDE_FOLDER"
mkdir -p "$COMMANDS_DIR"

# ── Create project brief if it doesn't exist ────────────────
if [ ! -f "$PROJECT_BRIEF" ]; then
cat > "$PROJECT_BRIEF" << 'BRIEF'
# Empire Box Ecosystem — Project Brief

## Current Machine
EmpireDell (Intel Xeon E5-2650 v3, 32GB RAM, 20 cores)

## Key Reference Docs
- Full audit: ~/Empire/data/beelink_operations_audit.md
- Architecture diagram: ~/Empire/data/architecture_diagram.mmd
- Architecture detail: ~/Empire/data/architecture_map.md

## Current Focus
- Empire Box development on EmpireDell
- MAX AI assistant (Telegram + Web UI)
- WorkroomForge quote system (drapery/upholstery)

## Tech Stack
- Backend: FastAPI (Python) at :8000
- Frontend: Next.js apps (Founder Dashboard :3009, Empire App :3000, WorkroomForge :3001)
- AI: xAI Grok (primary) → Claude (fallback) → Ollama (local)
- Database: SQLite (memories.db, token_usage.db, empire.db)
- Telegram Bot: python-telegram-bot
- Brain: SQLite memory store + conversation tracker

## Key Decisions
- xAI Grok is primary AI provider
- Edge-TTS for voice (free, replaced OpenAI TTS)
- 13 AI desks but only 4 actively used (Forge, Support, Marketing, Sales)
- Data consolidated from Beelink on Mar 6 (198 files)
BRIEF
echo "  ✅ Created project_brief.md"
fi

if [ ! -f "$SESSION_NOTES" ]; then
cat > "$SESSION_NOTES" << 'NOTES'
# Session Notes
NOTES
fi

if [ ! -f "$LAST_SUMMARY" ]; then
echo "_No previous session yet._" > "$LAST_SUMMARY"
fi

# ── Build master context (assembled before each launch) ─────
build_master_context() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M')
    
    cat > "$MASTER_CONTEXT" << HEADER
# Empire Box — Session Context (Updated: $timestamp)

You are resuming work on the Empire Box ecosystem. Read the context below before responding.

---

HEADER

    if [ -f "$PROJECT_BRIEF" ]; then
        cat "$PROJECT_BRIEF" >> "$MASTER_CONTEXT"
        echo -e "\n---\n" >> "$MASTER_CONTEXT"
    fi

    if [ -f "$LAST_SUMMARY" ]; then
        echo "## Last Session Summary" >> "$MASTER_CONTEXT"
        echo "" >> "$MASTER_CONTEXT"
        cat "$LAST_SUMMARY" >> "$MASTER_CONTEXT"
        echo -e "\n---\n" >> "$MASTER_CONTEXT"
    fi

    if [ -f "$SESSION_NOTES" ]; then
        local line_count
        line_count=$(wc -l < "$SESSION_NOTES")
        if [ "$line_count" -gt 2 ]; then
            echo "## Running Notes" >> "$MASTER_CONTEXT"
            echo "" >> "$MASTER_CONTEXT"
            tail -20 "$SESSION_NOTES" >> "$MASTER_CONTEXT"
            echo -e "\n---\n" >> "$MASTER_CONTEXT"
        fi
    fi

    cat >> "$MASTER_CONTEXT" << 'FOOTER'
## Instructions
- Acknowledge you've read this context
- Brief 1-2 sentence recap of where we left off
- Ask what to work on next
FOOTER
}

# ── Create START script ─────────────────────────────────────
cat > "$BIN_DIR/claude-start" << 'START_SCRIPT'
#!/usr/bin/env bash
set -euo pipefail

CONTEXT_DIR="$HOME/.claude-context"
MASTER_CONTEXT="$CONTEXT_DIR/master_context.md"
PROJECT_BRIEF="$CONTEXT_DIR/project_brief.md"
SESSION_NOTES="$CONTEXT_DIR/session_notes.md"
LAST_SUMMARY="$CONTEXT_DIR/last_chat_summary.md"

# Build fresh master context
timestamp=$(date '+%Y-%m-%d %H:%M')

cat > "$MASTER_CONTEXT" << HEADER
# Empire Box — Session Context (Updated: $timestamp)

You are resuming work on the Empire Box ecosystem. Read the context below before responding.

---

HEADER

if [ -f "$PROJECT_BRIEF" ]; then
    cat "$PROJECT_BRIEF" >> "$MASTER_CONTEXT"
    printf "\n---\n\n" >> "$MASTER_CONTEXT"
fi

if [ -f "$LAST_SUMMARY" ]; then
    echo "## Last Session Summary" >> "$MASTER_CONTEXT"
    echo "" >> "$MASTER_CONTEXT"
    cat "$LAST_SUMMARY" >> "$MASTER_CONTEXT"
    printf "\n---\n\n" >> "$MASTER_CONTEXT"
fi

if [ -f "$SESSION_NOTES" ]; then
    line_count=$(wc -l < "$SESSION_NOTES")
    if [ "$line_count" -gt 2 ]; then
        echo "## Running Notes" >> "$MASTER_CONTEXT"
        echo "" >> "$MASTER_CONTEXT"
        tail -20 "$SESSION_NOTES" >> "$MASTER_CONTEXT"
        printf "\n---\n\n" >> "$MASTER_CONTEXT"
    fi
fi

cat >> "$MASTER_CONTEXT" << 'FOOTER'
## Instructions
- Acknowledge you've read this context
- Brief 1-2 sentence recap of where we left off
- Ask what to work on next
FOOTER

echo "Context built: $(wc -w < "$MASTER_CONTEXT") words"
echo "Launching Claude Code with context..."
echo ""

# Launch Claude Code with context file injected
claude --append-system-prompt-file "$MASTER_CONTEXT"
START_SCRIPT

chmod +x "$BIN_DIR/claude-start"
echo "  ✅ Installed claude-start"

# ── Create END script ───────────────────────────────────────
cat > "$BIN_DIR/claude-end" << 'END_SCRIPT'
#!/usr/bin/env bash
set -euo pipefail

CONTEXT_DIR="$HOME/.claude-context"
SESSIONS_DIR="$CONTEXT_DIR/sessions"
LAST_SUMMARY="$CONTEXT_DIR/last_chat_summary.md"
SESSION_NOTES="$CONTEXT_DIR/session_notes.md"

mkdir -p "$SESSIONS_DIR"

TIMESTAMP=$(date '+%Y-%m-%d %H:%M')
SESSION_FILE="$SESSIONS_DIR/session_$(date '+%Y%m%d_%H%M%S').md"

echo ""
echo "Saving session context..."
echo ""

# Use Claude Code in print mode to generate a session summary
# It reads its own conversation history via -c (continue last session)
SUMMARY=$(claude -c -p "Summarize this entire session for context continuity. Include: what we worked on, key outcomes, decisions made, files changed, and what should be done next. Be concise but complete. Output ONLY the summary, no preamble." 2>/dev/null || echo "Could not auto-generate summary.")

if [ "$SUMMARY" = "Could not auto-generate summary." ] || [ -z "$SUMMARY" ]; then
    echo "Auto-summary failed. Paste your summary then press Ctrl+D:"
    SUMMARY=$(cat)
fi

# Save session file
{
    echo "# Session — $TIMESTAMP"
    echo ""
    echo "$SUMMARY"
} > "$SESSION_FILE"

# Update last summary (used by next START)
cp "$SESSION_FILE" "$LAST_SUMMARY"

# Append to running notes
echo "- [$TIMESTAMP] Session ended" >> "$SESSION_NOTES"

echo ""
echo "✅ Session saved: $SESSION_FILE"
echo "   Next claude-start will include this context automatically."
echo ""
END_SCRIPT

chmod +x "$BIN_DIR/claude-end"
echo "  ✅ Installed claude-end"

# ── Create Claude Code slash command for manual save ────────
cat > "$COMMANDS_DIR/save-context.md" << 'SLASH_CMD'
Summarize this entire session for context continuity. Write the summary to ~/.claude-context/last_chat_summary.md

Include:
- What we worked on
- Key outcomes and decisions
- Files created or changed
- What should be done next

Be concise but complete. Write ONLY to the file, confirm when done.
SLASH_CMD
echo "  ✅ Created /save-context slash command"

# ── Create Claude Code slash command to read context ────────
cat > "$COMMANDS_DIR/load-context.md" << 'SLASH_CMD2'
Read and acknowledge the context from these files:
1. ~/.claude-context/master_context.md
2. ~/.claude-context/project_brief.md
3. ~/.claude-context/last_chat_summary.md

Summarize what you understand about the current project state and ask what to work on next.
SLASH_CMD2
echo "  ✅ Created /load-context slash command"

# ── Create desktop shortcuts ───────────────────────────────

# START shortcut
cat > "$CLAUDE_FOLDER/Claude START.desktop" << EOF
[Desktop Entry]
Name=Claude START
Comment=Launch Claude Code with full session context
Exec=$BIN_DIR/claude-start
Icon=utilities-terminal
Terminal=true
Type=Application
Categories=Development;
EOF
chmod +x "$CLAUDE_FOLDER/Claude START.desktop"

# END shortcut
cat > "$CLAUDE_FOLDER/Claude END.desktop" << EOF
[Desktop Entry]
Name=Claude END
Comment=Save session and end
Exec=$BIN_DIR/claude-end
Icon=process-stop
Terminal=true
Type=Application
Categories=Development;
EOF
chmod +x "$CLAUDE_FOLDER/Claude END.desktop"

# BRIEF shortcut (edit project brief)
cat > "$CLAUDE_FOLDER/Claude BRIEF.desktop" << EOF
[Desktop Entry]
Name=Claude BRIEF
Comment=Edit project brief
Exec=bash -c '${EDITOR:-nano} $CONTEXT_DIR/project_brief.md'
Icon=accessories-text-editor
Terminal=true
Type=Application
Categories=Development;
EOF
chmod +x "$CLAUDE_FOLDER/Claude BRIEF.desktop"

# Mark as trusted (GNOME)
if command -v gio &>/dev/null; then
    for f in "$CLAUDE_FOLDER"/*.desktop; do
        gio set "$f" metadata::trusted true 2>/dev/null || true
    done
fi

echo "  ✅ Desktop shortcuts created in ~/Desktop/Claude/"

# ── Clean up old shortcuts ──────────────────────────────────
rm -f "$HOME/Desktop/claude-context.desktop" 2>/dev/null || true
rm -f "$HOME/Desktop/claude-context-end.desktop" 2>/dev/null || true

# ── Summary ─────────────────────────────────────────────────
echo ""
echo "============================================"
echo "  Claude Context System v2 — Installed!"
echo "============================================"
echo ""
echo "  ~/Desktop/Claude/"
echo "    🟢 Claude START  — Opens Claude Code with context auto-injected"
echo "    🔴 Claude END    — Auto-summarizes session and saves for next time"
echo "    📋 Claude BRIEF  — Edit your project brief"
echo ""
echo "  Inside Claude Code you can also use:"
echo "    /save-context  — Manually save context mid-session"
echo "    /load-context  — Reload context if needed"
echo ""
echo "  Flow:"
echo "    1. Click Claude START → Claude Code opens with full context"
echo "    2. Work normally"
echo "    3. Click Claude END → Session auto-summarized and saved"
echo "    4. Next Claude START has updated context"
echo ""
echo "  All sessions saved to: ~/.claude-context/sessions/"
echo "  Master context at:     ~/.claude-context/master_context.md"
echo ""
