#!/bin/bash
# Empire Stop — Full shutdown with confirmation
# Saves sessions, kills all services, optionally reboots

# ── Confirmation dialog ──────────────────────────────────────────────
ACTION=$(zenity --list --radiolist \
    --title="Empire Stop" \
    --text="Shut down all Empire services?" \
    --column="" --column="Action" \
    TRUE "Stop services only" \
    FALSE "Stop services and reboot" \
    --width=350 --height=250 2>/dev/null)

# User cancelled
if [ -z "$ACTION" ]; then
    exit 0
fi

# ── Save ClaudeForge session if active ───────────────────────────────
if [ -f /tmp/claudeforge.lock ]; then
    ~/Empire/products/claudeforge/scripts/end_session.sh 2>/dev/null
fi

# ── Save CopilotForge session if active ──────────────────────────────
if [ -f /tmp/copilotforge.lock ]; then
    ~/Empire/products/copilotforge/scripts/end_session.sh 2>/dev/null
fi

# ── Kill autosave processes ──────────────────────────────────────────
pkill -f "autosave.sh" 2>/dev/null

# ── Kill backend ─────────────────────────────────────────────────────
pkill -f "uvicorn app.main:app" 2>/dev/null

# ── Kill frontend ────────────────────────────────────────────────────
pkill -f "next dev -p 3009" 2>/dev/null
pkill -f "next-server" 2>/dev/null

# ── Clean up lock files ──────────────────────────────────────────────
rm -f /tmp/claudeforge.lock /tmp/copilotforge.lock 2>/dev/null

# ── Notify ───────────────────────────────────────────────────────────
notify-send "Empire Stopped" "All services shut down. Sessions saved." 2>/dev/null

# ── Reboot if requested ──────────────────────────────────────────────
if [ "$ACTION" = "Stop services and reboot" ]; then
    sleep 2
    systemctl reboot
fi
