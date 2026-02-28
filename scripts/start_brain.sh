#!/bin/bash
# MAX Brain Startup Script
# Starts Ollama with models on the external drive (BACKUP11)

BRAIN_DRIVE="/media/rg/BACKUP11"

# Check if drive is mounted
if [ ! -d "$BRAIN_DRIVE/ollama" ]; then
    echo "ERROR: Brain drive not mounted at $BRAIN_DRIVE"
    echo "Mount the external drive and try again."
    exit 1
fi

# Set Ollama to use external drive
export OLLAMA_MODELS="$BRAIN_DRIVE/ollama/models"
export MAX_BRAIN_PATH="$BRAIN_DRIVE/ollama/brain"

# Start Ollama if not running
if ! pgrep -x "ollama" > /dev/null; then
    OLLAMA_MODELS="$BRAIN_DRIVE/ollama/models" ollama serve &
    sleep 3
    echo "✓ Ollama server started"
else
    echo "✓ Ollama already running"
fi

# Verify models are available
echo "Checking models..."
ollama list | grep -q "nomic-embed-text" && echo "✓ nomic-embed-text ready" || echo "✗ nomic-embed-text missing — run: ollama pull nomic-embed-text"
ollama list | grep -q "mistral" && echo "✓ mistral ready" || echo "✗ mistral missing — run: ollama pull mistral:7b"

# Report brain status
MEMORIES=$(find "$BRAIN_DRIVE/ollama/brain" -name "*.json" -o -name "*.db" 2>/dev/null | wc -l)
echo ""
echo "═══════════════════════════════════"
echo "  MAX Brain Online"
echo "  Models: $BRAIN_DRIVE/ollama/models"
echo "  Brain:  $BRAIN_DRIVE/ollama/brain"
echo "  Memory files: $MEMORIES"
echo "═══════════════════════════════════"
