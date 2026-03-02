#!/bin/bash
# CoPilotForge - Search Past Chats

CHATS_DIR=~/Empire/products/copilotforge/data/chats

echo ""
echo "🔍 CoPilotForge - Search Chats"
echo "═══════════════════════════════════════"
echo ""

read -p "Search term: " TERM

if [ -z "$TERM" ]; then
  echo "No search term provided"
  exit 1
fi

echo ""
echo "Results for: '$TERM'"
echo "───────────────────────────────────────"

grep -r -l -i "$TERM" "$CHATS_DIR" 2>/dev/null | while read file; do
  echo ""
  echo "📄 $file"
  echo "   Context:"
  grep -i -B1 -A1 "$TERM" "$file" | head -6
done

echo ""
echo "═══════════════════════════════════════"
