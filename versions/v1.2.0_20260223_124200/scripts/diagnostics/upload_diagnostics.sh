#!/bin/bash
# Upload diagnostics archive to a shared location or print instructions
# for manual sharing when debugging EmpireBox crashes.

OUTPUT="/tmp/empirebox_diagnostics.txt"
ARCHIVE="/tmp/empirebox_diagnostics_$(date '+%Y%m%d_%H%M%S').tar.gz"

# Ensure diagnostics have been collected
if [ ! -f "$OUTPUT" ]; then
    echo "Diagnostics file not found. Running collect_system_info.sh first..."
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    bash "$SCRIPT_DIR/collect_system_info.sh"
fi

# Include relevant logs if accessible
FILES_TO_ARCHIVE=("$OUTPUT")
[ -f /var/log/empirebox/health.log ]    && FILES_TO_ARCHIVE+=("/var/log/empirebox/health.log")
[ -f /var/log/empirebox/resources.log ] && FILES_TO_ARCHIVE+=("/var/log/empirebox/resources.log")

tar -czf "$ARCHIVE" "${FILES_TO_ARCHIVE[@]}" 2>/dev/null

echo "=== EmpireBox Diagnostics Archive ==="
echo "Archive: $ARCHIVE"
echo ""
echo "To share diagnostics, use one of the following methods:"
echo ""
echo "  1. GitHub Issue attachment:"
echo "     - Open https://github.com/r22gir/Empire/issues/new"
echo "     - Attach $ARCHIVE to the issue"
echo ""
echo "  2. Paste text content:"
echo "     cat $OUTPUT"
echo ""
echo "  3. Transfer via scp (replace USER and HOST):"
echo "     scp $ARCHIVE USER@HOST:~/empirebox_diagnostics/"
echo ""
echo "Archive size: $(du -sh "$ARCHIVE" | cut -f1)"
