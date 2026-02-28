#!/bin/bash
#############################################
# EMPIRE BOX® MASTER INSTALLER v1.0
# Created by RG22
# Full Suite - All Products Unlocked
#############################################

set -e

PURPLE='\033[0;35m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
WHITE='\033[1;37m'
DIM='\033[2m'
NC='\033[0m'

clear
echo ""
echo ""
echo -e "${PURPLE}"
cat << 'EMPIRE'


    ███████╗███╗   ███╗██████╗ ██╗██████╗ ███████╗
    ██╔════╝████╗ ████║██╔══██╗██║██╔══██╗██╔════╝
    █████╗  ██╔████╔██║██████╔╝██║██████╔╝█████╗  
    ██╔══╝  ██║╚██╔╝██║██╔═══╝ ██║██╔══██╗██╔══╝  
    ███████╗██║ ╚═╝ ██║██║     ██║██║  ██║███████╗
    ╚══════╝╚═╝     ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝

EMPIRE
echo -e "${NC}"
echo -e "${CYAN}                          ██████╗  ██████╗ ██╗  ██╗   ${WHITE}®${NC}"
echo -e "${CYAN}                          ██╔══██╗██╔═══██╗╚██╗██╔╝${NC}"
echo -e "${CYAN}                          ██████╔╝██║   ██║ ╚███╔╝${NC}"
echo -e "${CYAN}                          ██╔══██╗██║   ██║ ██╔██╗${NC}"
echo -e "${CYAN}                          ██████╔╝╚██████╔╝██╔╝ ██╗${NC}"
echo -e "${CYAN}                          ╚═════╝  ╚═════╝ ╚═╝  ╚═╝${NC}"
echo ""
echo -e "${WHITE}                ╔════════════════════════════════════════╗${NC}"
echo -e "${WHITE}                ║      ${PURPLE}BUSINESS COMMAND CENTER${WHITE}          ║${NC}"
echo -e "${WHITE}                ║         ${CYAN}MASTER INSTALLATION${WHITE}             ║${NC}"
echo -e "${WHITE}                ╚════════════════════════════════════════╝${NC}"
echo ""
echo ""
echo -e "${WHITE}═══════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${DIM}                                              by RG22${NC}"
echo ""
echo -e "${WHITE}═══════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo ""

INSTALL_DIR="$HOME/Empire"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$HOME/empirebox_install.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"; echo -e "$1"; }

check_license() {
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                                    LICENSE VERIFICATION                                           ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    
    if [ -f "$HOME/.empirebox_master" ]; then
        echo -e "${GREEN}✓ MASTER LICENSE DETECTED${NC}"
        echo -e "${GREEN}  All products unlocked - Full Access${NC}"
        export LICENSE_TYPE="MASTER"
        return 0
    fi
    
    if [ -f "$SCRIPT_DIR/license.key" ]; then
        LICENSE_KEY=$(cat "$SCRIPT_DIR/license.key")
        echo -e "${GREEN}✓ License found on installation media${NC}"
    elif [ -f "$HOME/.empirebox_license" ]; then
        LICENSE_KEY=$(cat "$HOME/.empirebox_license")
        echo -e "${GREEN}✓ Existing license found${NC}"
    else
        echo ""
        echo -e "${YELLOW}Enter License Key:${NC}"
        echo -e "  ${DIM}EB-XXXX-XXXX-XXXX (Standard)${NC}"
        echo -e "  ${DIM}EM-XXXX-XXXX-XXXX (Master)${NC}"
        echo ""
        read -p "License Key: " LICENSE_KEY
    fi
    
    if [[ "$LICENSE_KEY" =~ ^EM-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$ ]]; then
        echo -e "${GREEN}✓ MASTER LICENSE VALIDATED${NC}"
        echo -e "${PURPLE}  Welcome, Founder!${NC}"
        echo "$LICENSE_KEY" > "$HOME/.empirebox_master"
        export LICENSE_TYPE="MASTER"
    elif [[ "$LICENSE_KEY" =~ ^EB-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$ ]]; then
        echo -e "${GREEN}✓ Standard license validated${NC}"
        echo "$LICENSE_KEY" > "$HOME/.empirebox_license"
        export LICENSE_TYPE="STANDARD"
    else
        echo -e "${RED}Invalid license${NC}"
        exit 1
    fi
}

check_system() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                                    SYSTEM REQUIREMENTS                                            ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    
    [ -f /etc/os-release ] && . /etc/os-release && echo -e "  OS:      ${GREEN}$NAME $VERSION_ID${NC}"
    echo -e "  CPU:     ${GREEN}$(nproc) cores${NC}"
    echo -e "  RAM:     ${GREEN}$(free -g | awk '/^Mem:/{print $2}')GB${NC}"
    echo -e "  Disk:    ${GREEN}$(df -BG "$HOME" | awk 'NR==2 {print $4}') free${NC}"
    ping -c 1 google.com &>/dev/null && echo -e "  Network: ${GREEN}Connected${NC}" || echo -e "  Network: ${YELLOW}Offline${NC}"
}

install_dependencies() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                                   INSTALLING DEPENDENCIES                                         ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    
    sudo apt-get update -qq
    sudo apt-get install -y -qq python3 python3-pip python3-venv nodejs npm postgresql redis-server git curl wget build-essential >> "$LOG_FILE" 2>&1
    echo -e "${GREEN}✓ System packages installed${NC}"
}

create_structure() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                                   CREATING EMPIRE STRUCTURE                                       ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    
    mkdir -p "$INSTALL_DIR"/{backend,frontend,products,data,logs,backups,uploads}
    mkdir -p "$INSTALL_DIR"/products/{workroom_forge,luxe_forge,market_forge,support_forge,lead_forge,empire_wallet,content_forge,open_claw}
    
    echo -e "${GREEN}✓ Directory structure created${NC}"
    echo ""
    echo -e "  ${PURPLE}$INSTALL_DIR/${NC}"
    echo -e "  ├── backend/           ${DIM}(MAX AI Engine)${NC}"
    echo -e "  ├── frontend/          ${DIM}(Founder Dashboard)${NC}"
    echo -e "  └── products/"
    echo -e "      ├── ${CYAN}workroom_forge/${NC}  ${DIM}Production${NC}"
    echo -e "      ├── ${CYAN}luxe_forge/${NC}      ${DIM}Marketplace${NC}"
    echo -e "      ├── ${CYAN}market_forge/${NC}    ${DIM}eBay/Amazon${NC}"
    echo -e "      ├── ${CYAN}support_forge/${NC}   ${DIM}Support${NC}"
    echo -e "      ├── ${CYAN}lead_forge/${NC}      ${DIM}CRM${NC}"
    echo -e "      ├── ${CYAN}empire_wallet/${NC}   ${DIM}Payments${NC}"
    echo -e "      ├── ${CYAN}content_forge/${NC}   ${DIM}AI Content${NC}"
    echo -e "      └── ${CYAN}open_claw/${NC}       ${DIM}Legal${NC}"
}

setup_backend() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                                     SETTING UP BACKEND                                            ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    
    cd "$INSTALL_DIR"
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip -q
    pip install -q fastapi uvicorn anthropic openai httpx aiofiles python-multipart pydantic sqlalchemy redis python-dotenv
    [ -d "$HOME/Empire/backend" ] && cp -r "$HOME/Empire/backend"/* "$INSTALL_DIR/backend/" 2>/dev/null
    echo -e "${GREEN}✓ Backend ready${NC}"
}

setup_frontend() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                                     SETTING UP FRONTEND                                           ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    
    if [ -d "$HOME/Empire/founder_dashboard" ]; then
        cp -r "$HOME/Empire/founder_dashboard" "$INSTALL_DIR/frontend/dashboard"
        cd "$INSTALL_DIR/frontend/dashboard"
        npm install --silent 2>/dev/null || true
    fi
    echo -e "${GREEN}✓ Frontend ready${NC}"
}

create_env() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                                  ENVIRONMENT CONFIGURATION                                        ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    
    cat > "$INSTALL_DIR/.env" << ENVFILE
# EMPIRE BOX® - by RG22
# Generated: $(date)
# License: $LICENSE_TYPE

ANTHROPIC_API_KEY=your-key-here
OPENAI_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# All Products Enabled
WORKROOM_FORGE=true
LUXE_FORGE=true
MARKET_FORGE=true
SUPPORT_FORGE=true
LEAD_FORGE=true
EMPIRE_WALLET=true
CONTENT_FORGE=true
OPEN_CLAW=true
ENVFILE
    chmod 600 "$INSTALL_DIR/.env"
    echo -e "${GREEN}✓ Environment configured${NC}"
}

create_launcher() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                                     CREATING LAUNCHERS                                            ${NC}"
    echo -e "${CYAN}══════════��════════════════════════════════════════════════════════════════════════════════════════${NC}"
    
    cat > "$INSTALL_DIR/start-empire.sh" << 'STARTER'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 &
cd ../frontend/dashboard && npm run dev &
echo "Empire Box® Running - http://localhost:3000"
wait
STARTER
    chmod +x "$INSTALL_DIR/start-empire.sh"
    
    cat > "$HOME/Desktop/EmpireBox.desktop" << DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=Empire Box®
Comment=Business Command Center by RG22
Exec=gnome-terminal -- bash -c "cd $INSTALL_DIR && ./start-empire.sh; exec bash"
Terminal=false
Categories=Office;Business;
DESKTOP
    chmod +x "$HOME/Desktop/EmpireBox.desktop"
    echo -e "${GREEN}✓ Desktop launcher created${NC}"
}

show_complete() {
    clear
    echo ""
    echo -e "${PURPLE}"
cat << 'LOGO'
    ███████╗███╗   ███╗██████╗ ██╗██████╗ ███████╗
    ██╔════╝████╗ ████║██╔══██╗██║██╔══██╗██╔════╝
    █████╗  ██╔████╔██║██████╔╝██║██████╔╝█████╗  
    ██╔══╝  ██║╚██╔╝██║██╔═══╝ ██║██╔══██╗██╔══╝  
    ███████╗██║ ╚═╝ ██║██║     ██║██║  ██║███████╗
    ╚══════╝╚═╝     ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝
LOGO
    echo -e "${NC}"
    echo -e "${CYAN}                          ██████╗  ██████╗ ██╗  ██╗   ${WHITE}®${NC}"
    echo -e "${CYAN}                          ██████╔╝██║   ██║ ╚███╔╝${NC}"
    echo -e "${CYAN}                          ██████╔╝╚██████╔╝██╔╝ ██╗${NC}"
    echo -e "${CYAN}                          ╚═════╝  ╚═════╝ ╚═╝  ╚═╝${NC}"
    echo ""
    echo -e "${GREEN}    ╔═══════════════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}    ║                         INSTALLATION COMPLETE! ✓                                     ║${NC}"
    echo -e "${GREEN}    ╚═══════════════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "    License: ${PURPLE}$LICENSE_TYPE${NC}"
    echo -e "    Location: ${WHITE}$INSTALL_DIR${NC}"
    echo ""
    echo -e "    ${YELLOW}NEXT STEPS:${NC}"
    echo -e "    1. Edit API keys: ${DIM}nano $INSTALL_DIR/.env${NC}"
    echo -e "    2. Start Empire:  ${DIM}cd $INSTALL_DIR && ./start-empire.sh${NC}"
    echo -e "    3. Open Dashboard: ${CYAN}http://localhost:3000${NC}"
    echo ""
    echo -e "    ${DIM}Or double-click 'Empire Box' on your desktop!${NC}"
    echo ""
    echo -e "${WHITE}═══════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${DIM}                                              by RG22${NC}"
    echo -e "${WHITE}═══════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

main() {
    echo "" > "$LOG_FILE"
    check_license
    check_system
    
    echo ""
    read -p "Install Empire Box®? (Y/n) " -n 1 -r
    echo ""
    [[ $REPLY =~ ^[Nn]$ ]] && exit 0
    
    install_dependencies
    create_structure
    setup_backend
    setup_frontend
    create_env
    create_launcher
    show_complete
}

main "$@"
