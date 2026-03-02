#!/bin/bash
# CoPilotForge v2 — Context Generator
# Builds a fresh context.md from memory, last session, git activity, and system status

OUTPUT=~/Empire/products/copilotforge/data/context.md
ARCHIVE=~/Empire/docs/CHAT_ARCHIVE
BRAIN=~/Empire/max/memory.md

# ── Start with MAX brain memory ──────────────────────────────────────
if [ -f "$BRAIN" ]; then
    cat "$BRAIN" > "$OUTPUT"
else
    echo "# MAX Memory" > "$OUTPUT"
    echo "(no memory.md found)" >> "$OUTPUT"
fi

# ── System status ────────────────────────────────────────────────────
{
    echo ""
    echo "---"
    echo "## LIVE SYSTEM STATUS"
    echo "Generated: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    echo "### Memory"
    free -h | head -2
    echo ""
    echo "### Disk"
    df -h / | tail -1
    echo ""
    echo "### Running Servers"
    ss -tlnp 2>/dev/null | grep -E ":[0-9]{4} " | awk '{print $4}' | sort -u
} >> "$OUTPUT"

# ── Recent git activity ──────────────────────────────────────────────
{
    echo ""
    echo "---"
    echo "## RECENT GIT ACTIVITY"
    echo ""
    echo "### Branch"
    cd ~/Empire && git branch --show-current 2>/dev/null
    echo ""
    echo "### Last 15 Commits"
    echo '```'
    git log --oneline -15 2>/dev/null
    echo '```'
    echo ""
    echo "### Uncommitted Changes"
    CHANGES=$(git status --short 2>/dev/null)
    if [ -n "$CHANGES" ]; then
        echo '```'
        echo "$CHANGES"
        echo '```'
    else
        echo "Working tree clean."
    fi
} >> "$OUTPUT"

# ── Last session summary ─────────────────────────────────────────────
{
    echo ""
    echo "---"
    echo "## LAST SESSION SUMMARY"
    LATEST=$(ls -t "$ARCHIVE"/*.md 2>/dev/null | head -1)
    if [ -n "$LATEST" ]; then
        echo "Source: $(basename "$LATEST")"
        echo ""
        cat "$LATEST"
    else
        echo "No session archives found."
    fi
} >> "$OUTPUT"

# ── Previous session (abbreviated) ───────────────────────────────────
SECOND=$(ls -t "$ARCHIVE"/*.md 2>/dev/null | sed -n '2p')
if [ -n "$SECOND" ]; then
    {
        echo ""
        echo "---"
        echo "## PREVIOUS SESSION (abbreviated)"
        echo "Source: $(basename "$SECOND")"
        echo ""
        head -30 "$SECOND"
        echo ""
        echo "..."
    } >> "$OUTPUT"
fi

# ── Instructions for Copilot ─────────────────────────────────────────
{
    echo ""
    echo "---"
    echo "## INSTRUCTIONS"
    echo "You are MAX, the AI for Empire. Read everything above."
    echo "Say: **Empire Ready.** Then state the last task from the session summary."
    echo "Ask what we are building today."
} >> "$OUTPUT"

LINES=$(wc -l < "$OUTPUT")
echo "Context generated: $OUTPUT ($LINES lines)"
