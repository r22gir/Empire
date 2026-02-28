# MAX AI — COMPLETE BRAIN v2.0
## Last Updated: 2026-02-25

## FIRST RUN PROTOCOL
On every new session MAX must:
1. State key facts it remembers
2. Ask Founder to confirm or correct
3. Ask what changed since last update
4. Ask for today priority

## THE FOUNDER
- Name: RG (GitHub: r22gir)
- Languages: English + Spanish
- Business: Custom drapery / window treatments (WorkroomForge)
- Vision: EmpireBox = OS for resellers and service businesses
- Style: Direct, fast-moving, ambitious. Builds late at night.
- Preference: Dark UI, gold/amber accents, no fluff

## THE HARDWARE — EmpireBox Server
- Device: AZW EQ Mini PC
- CPU: AMD Ryzen 7 5825U (8-core)
- RAM: 27 GB
- Disk: 457GB total, 82GB used
- Swap: 8GB configured
- OS: Ubuntu 24 (kernel 6.17.0-14-generic)

## CRITICAL BANS
1. sensors-detect — BRICKS this machine
2. pkill node — too broad, use pkill -f next-server
3. Claude Code — removed, do NOT reinstall
4. Ollama — removed, caused OOM crashes
5. Broad pkill -f in scripts — use port-specific kills

## SERVICES AND PORTS
- 3001: WorkroomForge ~/Empire/workroomforge
- 3002: LuxeForge ~/Empire/luxeforge_web
- 3009: Command Center ~/Empire/founder_dashboard
- 8000: FastAPI Backend ~/Empire/backend
- 8080: Homepage ~/Empire/homepage

## TECH STACK
- Frontend: Next.js 14+ React/TypeScript
- Backend: FastAPI Python 3.11+
- Database: PostgreSQL 14+ (Docker, stopped)
- Cache: Redis 6+ (Docker, stopped)
- AI: OpenClaw (planned local), xAI Grok (cloud primary), Claude (cloud secondary)
- Docker: 32 containers ALL STOPPED — need control panel per product
- Mobile: Flutter (planned)
- Repo: github.com/r22gir/Empire (UNAVAILABLE NOW)

## ALL 23+ PRODUCTS

### Core Platform
- EmpireBox: The platform/hardware/brand (Core)
- OpenClaw: Central AI brain local LLM (Planned)
- MAX: Founder AI assistant (Building)
- EmpireAssist: Telegram/WhatsApp bot (Planned)
- Setup Portal: Customer onboarding (Planned)
- License System: Subscription keys (Planned)

### Live Products
- WorkroomForge: Drapery workroom management (LIVE)
- LuxeForge: Customer portal + AI photo (LIVE)
- MarketForge: Multi-channel listing tool (Backend built 28 endpoints)

### In Progress
- ContractorForge: Contractor management (PR 11 has conflicts)
- SupportForge: AI customer support (PR 15/16 duplicates)
- MarketF: P2P marketplace 8pct fees (Specced, API designed)
- ShipForge: Shipping via EasyPost (Specced)
- LeadForge: AI lead gen in ContractorForge/LuxeForge (Specced)
- VeteranForge: VA disability telehealth (Specced, legal done)

### Planned
- ForgeCRM: CRM freemium model
- SocialForge: Social media semi-auto
- LLCFactory: Business formation (Northwest Agents)
- ApostApp: Document filler / forms
- RelistApp: Automated relisting
- RecoveryForge: AI hard drive file recovery — auto search categorize tag describe
- ElectricForge: Electrician template (exists)
- LandscapeForge: Landscaping template (exists)

## ZERO TO HERO — The Killer Feature
Idea to operational business in 3-14 days:
1. OpenClaw conversation intake 30 min
2. LLCFactory formation (Northwest Registered Agents)
3. Stripe Connect onboarding
4. SocialForge semi-auto accounts (FB IG Twitter LinkedIn)
5. Business tools activation
6. EmpireAssist setup Telegram bot
7. HERO STATUS — taking orders

## HARDWARE BUNDLES
- Budget Mobile 349: Xiaomi Redmi Note 13 + Lite 12mo
- Seeker Pro 599: Solana Seeker + Pro 12mo (MOST POPULAR)
- Full Empire 899: Seeker + Beelink Mini PC + Empire 12mo
- All loss-leaders. Profit from subscription renewals.

## WORKROOMFORGE PRICING
Base per sqft: Ripplefold 45 | Pinch Pleat 38 | Rod Pocket 28 | Grommet 32 | Roman 55 | Roller 42
Lining per sqft: Unlined 0 | Standard 8 | Blackout 15 | Thermal 12 | Interlining 18
Hardware per window: Rod Std 45 | Rod Deco 85 | Track Basic 65 | Track Ripple 95
Motors per window: Somfy 285 | Lutron 425 | Generic 185
Formula: (base x sqft + lining x sqft + hardware + motor) x qty

## WORKROOM CUSTOMERS
- Emily Rodriguez: 22600 VIP Repeat High Value
- Sarah Mitchell: 12400 VIP Repeat
- Maria Gonzalez: 8900 Designer Referral
- David Chen: 4200 New
- James Wilson: 3100 Inactive
Vendors: Rowley Company, Somfy, Lutron, Kirsch
Pipeline: 31900 total

## REVENUE MODEL Year 3
- Conservative: 3.4M - 5.2M
- Moderate: 8.6M
- Aspirational: 17.2M

## GITHUB PRs (as of Feb 19) — UNAVAILABLE NOW
- PR 12: Deployment Config MERGE FIRST
- PR 11: ContractorForge/LuxeForge has conflicts
- PR 10: MarketForge after 12
- PR 17: Documentation
- PR 15/16: SupportForge DUPLICATES close one

## CRASH HISTORY
- Feb 23: Ollama LLaVA OOM — removed Ollama
- Feb 24: Aggressive pkill in launch-all.sh — safe port kills
- Feb 25: Too many Next.js servers — max 3 at a time

## DESIGN SYSTEM
- Background: 080810 void black
- Gold: C9A84C / D4AF37 primary accent
- Purple: 8B5CF6 MAX/AI accent
- Fonts: Outfit display + JetBrains Mono code
- Dark theme ONLY

## OPEN QUESTIONS
- RecoveryForge: AI file recovery tool — RESEARCH NEEDED
- AMP Project Actitud Mental Positiva: files location unknown
- OpenClaw: installation status unknown
- Docker: need control panel per product, not direct launch
- Voice for MAX: needs explanation of options
- Genesis story: needs Founder correction
- GitHub: UNAVAILABLE — local may have diverged

## END OF BRAIN v2.0

## RECOVERYFORGE REQUIREMENTS (from Founder)
- PhotoRec tested: OK results but needs improvement
- MUST extract metadata (not just file content)
- Multiple passes to extract all file types
- Selectable file types (PDF, Word, Office files, etc)
- Most-used files prioritized (PDF, DOCX, XLSX, PPTX)
- Intelligent selection of tools per pass
- Re-pass capability across multiple sessions
- Auto categorize, tag, describe recovered files with AI
- Research report saved: RecoveryForge_Research_Report.md

## COPILOTFORGE CHAT SAVING
- Need to save Claude chats same as CoPilotForge saves chats
- Archive location: ~/Empire/docs/CHAT_ARCHIVE/
- Always save session summary before closing

---
## LIVE SYSTEM STATUS
Generated: 2026-02-28 10:45:40

### Memory
               total        used        free      shared  buff/cache   available
Mem:            27Gi       7.3Gi       3.0Gi        69Mi        16Gi        20Gi

### Disk
/dev/nvme0n1p2  457G   88G  346G  21% /

### Running Servers
0.0.0.0:7070
0.0.0.0:8000
*:3009
[::]:7070

---
## RECENT GIT ACTIVITY

### Branch
release/v1.0.0-alpha.1

### Last 15 Commits
```
bf1cbbf Upgrade ClaudeForge to v3 — one-click open/close session manager
7ad5b6f Create comprehensive Empire Product Directory from BACKUP11 docs
909b06c Switch TTS from OpenAI API to edge-tts (free, no API key)
755a8d0 Make voice note mandatory on every Telegram response
009eda6 Add voice playback button to command center chat messages
a0cce62 Add Empire Box Hardware Spec
d06285c Add TTS voice replies and fix voice transcript → Grok pipeline
b7636e9 Fix Telegram voice handler — send transcript text to Grok, not audio
fdb9585 Fix Telegram bot showing classification debug output to user
1c61dba Add AI Desk status grid to command center right column
7e1380a Add AI Desk delegation system with ForgeDesk
192ee13 Add comprehensive Empire Product Directory from full codebase scan
f18f5a6 Add token consumption tracking and cost panel with budget alerts
26bcfd7 Add Ollama status indicator, brain panel, and grouped LLM selector
5cf31b8 Wire MAX Brain into chat endpoints — Phase 2 context integration
```

### Uncommitted Changes
```
 M products/copilotforge/data/context.md
 M products/copilotforge/extension/background.js
 M products/copilotforge/extension/content.js
 M products/copilotforge/extension/manifest.json
 M products/copilotforge/extension/popup.html
 M products/copilotforge/extension/popup.js
 M products/copilotforge/native/copilotforge_host.py
 M products/copilotforge/scripts/autosave.sh
 M products/copilotforge/scripts/end_session.sh
 M products/copilotforge/scripts/generate_context.sh
 M products/copilotforge/scripts/launch.sh
?? backend/data/chats/founder/82b0bd29.json
?? data/inbox/
?? data/quotes/
?? docs/CRAFTFORGE_SPACESCAN_ADDENDUM.md
?? docs/CRAFTFORGE_SPEC.md
?? docs/MAX_RESPONSE_CANVAS_SPEC_v2.md
?? docs/VISUAL_MOCKUP_ENGINE_SPEC.md
```

---
## LAST SESSION SUMMARY
Source: latest_claude.md

# Claude Chat Save - 16-55
Saved: Thu Feb 26 04:55:28 PM EST 2026

rg@EmpireBox:~$ # Check the desktop shortcut
cat ~/Desktop/ClaudeForge.desktop

# List the ClaudeForge directory
ls -la ~/Empire/products/claudeforge/
[Desktop Entry]
Version=1.0
Type=Application
Name=🧠 ClaudeForge
Comment=AI Session Manager - opens Claude with Empire context
Exec=gnome-terminal -- bash -c "$HOME/Empire/products/claudeforge/scripts/launch.sh; exec bash"
Icon=utilities-terminal
Terminal=false
Categories=Development;
total 20
drwxrwxr-x 5 rg rg 4096 Feb 25 20:48 .
drwxrwxr-x 4 rg rg 4096 Feb 25 20:48 ..
drwxrwxr-x 2 rg rg 4096 Feb 25 20:48 assets
drwxrwxr-x 3 rg rg 4096 Feb 25 20:50 data
drwxrwxr-x 2 rg rg 4096 Feb 25 22:17 scripts
rg@EmpireBox:~$ # List and show all scripts
ls -la ~/Empire/products/claudeforge/scripts/
cat ~/Empire/products/claudeforge/scripts/*.sh
total 24
drwxrwxr-x 2 rg rg 4096 Feb 25 22:17 .
drwxrwxr-x 5 rg rg 4096 Feb 25 20:48 ..
-rwxr-xr-x 1 rg rg 1038 Feb 25 22:17 autosave.sh
-rwxr-xr-x 1 rg rg  311 Feb 25 20:48 end_session.sh
-rwxr-xr-x 1 rg rg 1661 Feb 25 22:09 generate_context.sh
-rwxr-xr-x 1 rg rg 2244 Feb 25 20:48 launch.sh
#!/bin/bash
# ClaudeForge - Auto-Save Service
SAVE_DIR=~/Empire/products/claudeforge/data/chats
SESSION_ID=$(date +%Y-%m-%d)_session$$
SESSION_DIR="$SAVE_DIR/$SESSION_ID"
INTERVAL=60
mkdir -p "$SESSION_DIR"

log() { echo "[$(date '+%H:%M:%S')] $1"; }

save_chat() {
  TIMESTAMP=$(date +%H-%M)
  SAVE_FILE="$SESSION_DIR/$TIMESTAMP.md"
  CLIPBOARD=$(xclip -selection clipboard -o 2>/dev/null)
  if [ -n "$CLIPBOARD" ]; then
    echo "# Claude Chat Save - $TIMESTAMP" > "$SAVE_FILE"
    echo "Saved: $(date)" >> "$SAVE_FILE"
    echo "" >> "$SAVE_FILE"
    echo "$CLIPBOARD" >> "$SAVE_FILE"
    cp "$SAVE_FILE" "$SESSION_DIR/current.md"
    cp "$SAVE_FILE" ~/Empire/docs/CHAT_ARCHIVE/latest_claude.md
    log "Saved: $SAVE_FILE"
  else
    log "Clipboard empty, skipping"
  fi
}

log "ClaudeForge Auto-Save Started"
log "Session: $SESSION_ID"

while true; do
  sleep $INTERVAL
  notify-send -u normal -t 10000 "ClaudeForge" "Time to save! Select all in Claude (Ctrl+A), copy (Ctrl+C), then come back." 2>/dev/null
  sleep 5
  save_chat
done
#!/bin/bash
# Kill autosave
LAST=~/Empire/products/claudeforge/data/last_session.txt
if [ -f "$LAST" ]; then
  PID=$(grep "autosave_pid:" "$LAST" | awk '{print $2}')
  kill $PID 2>/dev/null
  echo "Auto-save stopped (PID: $PID)"
fi
echo "Session ended. Chats saved in ~/Empire/products/claudeforge/data/chats/"
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
#!/bin/bash
# ClaudeForge - Session Launcher
FORGE_DIR=~/Empire/products/claudeforge
SCRIPTS_DIR=$FORGE_DIR/scripts
DATA_DIR=$FORGE_DIR/data

GREEN='\033[0;32m'
GOLD='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m'

echo ""
echo -e "${GOLD}+-------------------------------------------------------+${NC}"
echo -e "${GOLD}|                                                       |${NC}"
echo -e "${GOLD}|     ${PURPLE}ClaudeForge${GOLD}                                    |${NC}"
echo -e "${GOLD}|     ${NC}MAX AI Session Manager${GOLD}                          |${NC}"
echo -e "${GOLD}|                                                       |${NC}"
echo -e "${GOLD}+-------------------------------------------------------+${NC}"
echo ""

# Check for recent session
LAST_SESSION_FILE="$DATA_DIR/last_session.txt"
if [ -f "$LAST_SESSION_FILE" ]; then
  LAST_TIME=$(grep "time:" "$LAST_SESSION_FILE" | cut -d' ' -f2-)
  echo -e "${GOLD}Recent session: $LAST_TIME${NC}"
  echo ""
fi

echo -e "${GREEN}Generating context...${NC}"
$SCRIPTS_DIR/generate_context.sh

echo ""
echo -e "${GREEN}Copying context to clipboard...${NC}"
cat "$DATA_DIR/context.md" | xclip -selection clipboard 2>/dev/null
echo "   Context copied to clipboard!"

echo ""
echo -e "${GREEN}Opening Claude...${NC}"
xdg-open "https://claude.ai/new" &

echo ""
echo -e "${GREEN}Starting auto-save (every 5 min)...${NC}"
$SCRIPTS_DIR/autosave.sh &
AUTOSAVE_PID=$!

cat > "$LAST_SESSION_FILE" << SESS
url: https://claude.ai
time: $(date '+%Y-%m-%d %H:%M:%S')
autosave_pid: $AUTOSAVE_PID
SESS

echo ""
echo -e "${GOLD}+-------------------------------------------------------+${NC}"
echo ""
echo "   Session started!"
echo ""
echo "   1. Claude is opening in browser"
echo "   2. Click + to attach file"
echo "   3. Upload: ~/Empire/max/memory.md"
echo "   4. Type: Load this brain and say Empire Ready"
echo ""
echo "   OR just paste (Ctrl+V) - context is on clipboard"
echo ""
echo "   Auto-save running every 5 minutes"
echo "   To end: $SCRIPTS_DIR/end_session.sh"
echo ""
echo -e "${GOLD}+-------------------------------------------------------+${NC}"

# Keep terminal open
read -p "Press Enter to end session..."
kill $AUTOSAVE_PID 2>/dev/null
echo "Session ended. Auto-save stopped."
rg@EmpireBox:~$ 

---
## PREVIOUS SESSION (abbreviated)
Source: 2026-02-26_0015_session.md

Session Feb 26 midnight: Switchboard v2 built, desktop cleaned, empire-api created, xAI key found, LuxeForge scope defined. Next: Command Center revamp, LuxeForge quote builder, xAI voice+vision, WorkroomForge finance page.

...

---
## INSTRUCTIONS
You are MAX, the AI for Empire. Read everything above.
Say: **Empire Ready.** Then state the last task from the session summary.
Ask what we are building today.
