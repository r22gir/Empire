#!/bin/bash
BUSINESS=${1:-workroom}
echo "Verifying social connections for $BUSINESS..."
for PLATFORM in facebook instagram tiktok linkedin pinterest google_business; do
    RESULT=$(curl -s -X POST "http://localhost:8000/api/v1/socialforge/verify-connection/$BUSINESS/$PLATFORM" 2>/dev/null)
    CONNECTED=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('connected', False))" 2>/dev/null)
    if [ "$CONNECTED" = "True" ]; then
        echo "  ✅ $PLATFORM — connected"
    else
        REASON=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('reason', 'unknown'))" 2>/dev/null)
        echo "  ⏳ $PLATFORM — $REASON"
    fi
done
echo ""
echo "Done. Run Part II to test publishing."
