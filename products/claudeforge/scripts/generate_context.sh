#!/bin/bash
# ClaudeForge - Context Generator v2
OUTPUT=~/Empire/products/claudeforge/data/context.md
ARCHIVE=~/Empire/docs/CHAT_ARCHIVE
BRAIN=~/Empire/max/memory.md

# Start with brain
cat "$BRAIN" > "$OUTPUT"

# Add system status
echo "" >> "$OUTPUT"
echo "## LIVE SYSTEM STATUS (auto-generated)" >> "$OUTPUT"
echo "Generated: $(date '+%Y-%m-%d %H:%M:%S')" >> "$OUTPUT"
echo "### Memory" >> "$OUTPUT"
free -h | head -2 >> "$OUTPUT"
echo "" >> "$OUTPUT"
echo "### Running Servers" >> "$OUTPUT"
ss -tlnp 2>/dev/null | grep -E "300[0-9]|8000|8080" | awk '{print $4}' >> "$OUTPUT" 2>/dev/null
echo "" >> "$OUTPUT"
echo "### Disk" >> "$OUTPUT"
df -h / | tail -1 >> "$OUTPUT"

# Add LATEST session summary from archive
echo "" >> "$OUTPUT"
echo "## LAST SESSION SUMMARY" >> "$OUTPUT"
LATEST=$(ls -t "$ARCHIVE"/*.md 2>/dev/null | head -1)
if [ -n "$LATEST" ]; then
  echo "Source: $LATEST" >> "$OUTPUT"
  echo "" >> "$OUTPUT"
  cat "$LATEST" >> "$OUTPUT"
else
  echo "No session archives found." >> "$OUTPUT"
fi

# Add second latest for extra context
SECOND=$(ls -t "$ARCHIVE"/*.md 2>/dev/null | sed -n '2p')
if [ -n "$SECOND" ]; then
  echo "" >> "$OUTPUT"
  echo "## PREVIOUS SESSION" >> "$OUTPUT"
  echo "Source: $SECOND" >> "$OUTPUT"
  echo "" >> "$OUTPUT"
  head -30 "$SECOND" >> "$OUTPUT"
  echo "..." >> "$OUTPUT"
fi

echo "" >> "$OUTPUT"
echo "## INSTRUCTIONS" >> "$OUTPUT"
echo "You are MAX, the AI for EmpireBox. Read everything above." >> "$OUTPUT"
echo "Say: Empire Ready. Then state the last task from the session summary." >> "$OUTPUT"
echo "Ask what we are building today." >> "$OUTPUT"

echo "Context generated: $OUTPUT ($(wc -l < "$OUTPUT") lines)"
