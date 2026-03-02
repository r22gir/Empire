#!/bin/bash

# Find latest save (auto-saves or manual)
LATEST=$(ls -t ~/Empire/saves/EMPIRE_SAVE_*.md ~/Downloads/EMPIRE_SESSION_SAVE* 2>/dev/null | head -1)

# Copy its contents + instructions to clipboard
{
  echo "Resuming Empire build. Auto-save contents below. EmpireBox is online."
  echo ""
  echo "Standing rules:"
  echo "- Save checkpoint every 10 minutes automatically"
  echo "- Every few sessions consolidate saves into one master, delete old ones"
  echo "- Always give copy-paste commands, never expect me to type"
  echo ""
  cat "$LATEST"
} | xclip -selection clipboard

# Open Claude
firefox --new-window https://claude.ai/new &

notify-send "🏰 Empire" "Latest save copied to clipboard: $(basename $LATEST)"
