#!/bin/bash
# EMPIRE SWITCHBOARD v2.0

BK='\033[0m'; BD='\033[1m'; DM='\033[2m'
GD='\033[38;2;212;175;55m'; PR='\033[38;2;139;92;246m'
CY='\033[38;2;34;211;238m'; GN='\033[38;2;34;197;94m'
RD='\033[38;2;239;68;68m'; WH='\033[38;2;255;255;255m'
GY='\033[38;2;100;100;120m'; OG='\033[38;2;251;146;60m'
TL='\xe2\x95\x94'; TR='\xe2\x95\x97'; BL='\xe2\x95\x9a'; BR='\xe2\x95\x9d'
HZ='\xe2\x95\x90'; VT='\xe2\x95\x91'; LT='\xe2\x95\xa0'; RT='\xe2\x95\xa3'

MAX_NEXTJS=3; RAM_WARN=70; RAM_CRIT=85; INTERVAL=30; W=62
LOG="$HOME/Empire/logs/switchboard.log"
PIDFILE="/tmp/empire-switchboard.pid"
mkdir -p "$HOME/Empire/logs"

PRODUCTS=(
    "3001|WorkroomForge|$HOME/Empire/workroomforge|nextjs|forge|Drapery workroom"
    "3002|LuxeForge|$HOME/Empire/luxeforge_web|nextjs|forge|Customer portal"
    "3009|Command Center|$HOME/Empire/founder_dashboard|nextjs|core|MAX dashboard"
    "8000|FastAPI Backend|$HOME/Empire/backend|fastapi|core|API 104+ endpoints"
    "8080|Homepage|$HOME/Empire/homepage|nextjs|core|Landing page"
)

FUTURE=(
    "MarketForge|Backend built 28 endpoints"
    "ContractorForge|PR 11 conflicts"
    "SupportForge|PR 15/16 dupes"
    "MarketF|8pct marketplace"
    "RecoveryForge|AI file recovery"
    "ForgeCRM|Customer mgmt"
    "VeteranForge|VA telehealth"
    "SocialForge|Social media"
    "LLCFactory|Business formation"
    "ShipForge|EasyPost shipping"
    "LeadForge|AI lead gen"
)

ram_pct()    { free | awk '/Mem:/ {printf "%.0f", ($3/$2)*100}'; }
ram_free()   { free -h | awk '/Mem:/ {print $7}'; }
ram_used()   { free -h | awk '/Mem:/ {print $3}'; }
ram_total()  { free -h | awk '/Mem:/ {print $2}'; }
swap_pct()   { free | awk '/Swap:/ {if($2>0) printf "%.0f", ($3/$2)*100; else print "0"}'; }
cpu_load()   { awk '{printf "%.1f", $1}' /proc/loadavg; }
disk_pct()   { df -h /home 2>/dev/null | awk 'NR==2 {gsub(/%/,""); print $5}'; }
disk_free()  { df -h /home 2>/dev/null | awk 'NR==2 {print $4}'; }
njs_count()  { ps aux | grep "next-server" | grep -v grep | wc -l; }
sys_uptime() { uptime -p 2>/dev/null | sed 's/up //' || echo "?"; }
port_active(){ lsof -ti:$1 >/dev/null 2>&1; }
port_pid()   { lsof -ti:$1 2>/dev/null | head -1; }
pid_mem()    { [ -n "$1" ] && ps -p "$1" -o %mem= 2>/dev/null | awk '{printf "%.1f",$1}' || echo "0"; }
docker_count(){ docker ps -q 2>/dev/null | wc -l; }
docker_total(){ docker ps -aq 2>/dev/null | wc -l; }
log_it() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"; }
alert()  { notify-send -u "$1" "$2" "$3" 2>/dev/null; log_it "[$1] $2: $3"; }

svc_mode() {
    local pid=$(port_pid $1)
    [ -z "$pid" ] && echo "off" && return
    local c=$(ps -p "$pid" -o args= 2>/dev/null)
    echo "$c" | grep -q "next dev" && echo "dev" && return
    echo "$c" | grep -q "next start" && echo "prod" && return
    echo "$c" | grep -q "uvicorn" && echo "api" && return
    echo "run"
}

hdr() { printf "${GD}"; printf '=%.0s' $(seq 1 $((W-1))); printf "${TR}${BK}\n"; }
ftr() { printf "${GD}"; printf '=%.0s' $(seq 1 $((W-1))); printf "${BR}${BK}\n"; }
sep() { printf "${GD}"; printf '=%.0s' $(seq 1 $((W-1))); printf "${RT}${BK}\n"; }
row() { printf "${GD}${VT}${BK} %-$((W-3))b ${GD}${VT}${BK}\n" "$1"; }
erow(){ printf "${GD}${VT}${BK}%-$((W-1))s${GD}${VT}${BK}\n" ""; }

bar() {
    local pct=$1 w=${2:-28} warn=${3:-70} crit=${4:-85}
    local filled=$((pct * w / 100)); [ $filled -gt $w ] && filled=$w
    local empty=$((w - filled))
    local c=$GN; [ "$pct" -ge "$warn" ] && c=$OG; [ "$pct" -ge "$crit" ] && c=$RD
    printf "["; for ((i=0;i<filled;i++)); do printf "${c}#${BK}"; done
    for ((i=0;i<empty;i++)); do printf "${GY}.${BK}"; done
    printf "] ${c}${pct}%%${BK}"
}

svc_stop() {
    local port=$1 name=$2 pid=$(port_pid $1)
    if [ -n "$pid" ]; then
        kill $pid 2>/dev/null; sleep 1
        kill -0 $pid 2>/dev/null && kill -9 $pid 2>/dev/null
        printf "  ${RD}stop${BK} ${WH}${name}${BK} (PID $pid)\n"
        log_it "STOP $name :$port"
    else
        printf "  ${GY}${name} already stopped${BK}\n"
    fi
}

svc_start() {
    local port=$1 name=$2 dir=$3 type=$4 mode=${5:-dev}
    port_active $port && { printf "  ${OG}${name} already on :${port}${BK}\n"; return 1; }
    [ ! -d "$dir" ] && { printf "  ${RD}Dir missing: ${dir}${BK}\n"; return 1; }
    local rp=$(ram_pct) nj=$(njs_count)
    if [ "$rp" -ge "$RAM_CRIT" ]; then
        printf "  ${RD}BLOCKED${BK} RAM ${rp}%%\n"
        alert "critical" "BLOCKED" "$name RAM ${rp}%"
        return 1
    fi
    if [ "$type" = "nextjs" ] && [ "$nj" -ge "$MAX_NEXTJS" ]; then
        printf "  ${RD}BLOCKED${BK} ${nj}/${MAX_NEXTJS} Next.js running\n"
        printf "  ${OG}Kill one first:${BK}\n"
        for p in "${PRODUCTS[@]}"; do
            IFS='|' read -r pp pn pd pt pg pdesc <<< "$p"
            [ "$pt" = "nextjs" ] && port_active $pp && printf "    ${CY}:${pp}${BK} ${pn}\n"
        done
        alert "critical" "BLOCKED" "$name $nj/$MAX_NEXTJS Next.js"
        return 1
    fi
    [ "$rp" -ge "$RAM_WARN" ] && printf "  ${OG}RAM ${rp}%%${BK}\n"
    printf "  Starting ${WH}${name}${BK} (${mode})..."
    case $type in
        nextjs)
            if [ "$mode" = "prod" ]; then
                (cd "$dir" && npm run build >/dev/null 2>&1 && npx next start -p $port >/dev/null 2>&1) &
            else
                (cd "$dir" && npm run dev -- -p $port >/dev/null 2>&1) &
            fi ;;
        fastapi)
            (cd "$dir" && source venv/bin/activate 2>/dev/null; uvicorn app.main:app --host 0.0.0.0 --port $port --reload >/dev/null 2>&1) &
            ;;
    esac
    disown 2>/dev/null
    for i in $(seq 1 12); do
        sleep 1
        if port_active $port; then
            printf "\r  ${GN}ON${BK} ${WH}${name}${BK} :${port} (${mode})   \n"
            log_it "START $name :$port $mode"
            return 0
        fi; printf "."
    done
    printf "\r  ${RD}FAIL ${name}${BK}                    \n"; return 1
}

svc_toggle() {
    local i=$(($1-1)); [ $i -lt 0 ] || [ $i -ge ${#PRODUCTS[@]} ] && return
    IFS='|' read -r pt pn pd pp pg pdesc <<< "${PRODUCTS[$i]}"
    port_active $pt && svc_stop $pt "$pn" || svc_start $pt "$pn" "$pd" "$pp" "dev"
}

svc_mode_start() {
    local i=$(($1-1)) m=$2; [ $i -lt 0 ] || [ $i -ge ${#PRODUCTS[@]} ] && return
    IFS='|' read -r pt pn pd pp pg pdesc <<< "${PRODUCTS[$i]}"
    port_active $pt && { svc_stop $pt "$pn"; sleep 1; }
    svc_start $pt "$pn" "$pd" "$pp" "$m"
}

svc_restart() {
    local i=$(($1-1)); [ $i -lt 0 ] || [ $i -ge ${#PRODUCTS[@]} ] && return
    IFS='|' read -r pt pn pd pp pg pdesc <<< "${PRODUCTS[$i]}"
    local mm=$(svc_mode $pt); [ "$mm" = "off" ] && mm="dev"
    svc_stop $pt "$pn"; sleep 1; svc_start $pt "$pn" "$pd" "$pp" "$mm"
}

open_browser() {
    local i=$(($1-1)); [ $i -lt 0 ] || [ $i -ge ${#PRODUCTS[@]} ] && return
    IFS='|' read -r pt pn pd pp pg pdesc <<< "${PRODUCTS[$i]}"
    port_active $pt && { xdg-open "http://localhost:$pt" 2>/dev/null & disown; printf "  ${CY}Opening ${pn}${BK}\n"; } || printf "  ${RD}${pn} off${BK}\n"
}

bulk_up() {
    local mode=${1:-dev} nj=0; echo ""
    for p in "${PRODUCTS[@]}"; do
        IFS='|' read -r pt pn pd pp pg pdesc <<< "$p"
        port_active $pt && { printf "  ${GY}${pn} running${BK}\n"; [ "$pp" = "nextjs" ] && nj=$((nj+1)); continue; }
        [ "$pp" = "nextjs" ] && { nj=$((nj+1)); [ $nj -gt $MAX_NEXTJS ] && { printf "  ${OG}SKIP ${pn}${BK}\n"; continue; }; }
        svc_start $pt "$pn" "$pd" "$pp" "$mode"; sleep 2
    done
}

bulk_down() {
    echo ""
    for p in "${PRODUCTS[@]}"; do
        IFS='|' read -r pt pn pd pp pg pdesc <<< "$p"
        svc_stop $pt "$pn"; sleep 0.5
    done
}

bg_monitor() {
    echo $$ > "$PIDFILE"
    alert "normal" "Empire Switchboard" "Monitor active"
    while true; do
        local rp=$(ram_pct) nj=$(njs_count) sp=$(swap_pct)
        [ "$nj" -gt "$MAX_NEXTJS" ] && alert "critical" "TOO MANY SERVERS" "$nj running max $MAX_NEXTJS"
        [ "$rp" -ge "$RAM_CRIT" ] && alert "critical" "RAM ${rp}%%" "$(ram_free) free"
        [ "$sp" -ge 50 ] && alert "critical" "SWAP ${sp}%%" "Crash imminent"
        sleep $INTERVAL
    done
}

monitor_start() {
    [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null && { printf "  ${OG}Already running${BK}\n"; return; }
    $0 --bg & disown 2>/dev/null; sleep 1
    printf "  ${GN}Monitor ON${BK} PID $(cat $PIDFILE)\n"
}

monitor_stop() {
    [ -f "$PIDFILE" ] && { kill $(cat "$PIDFILE") 2>/dev/null; rm -f "$PIDFILE"; printf "  ${GN}Monitor OFF${BK}\n"; } || printf "  ${GY}Not running${BK}\n"
}

display() {
    clear
    local rp=$(ram_pct) sp=$(swap_pct) dp=$(disk_pct) cl=$(cpu_load)
    local nj=$(njs_count) dr=$(docker_count) dt=$(docker_total)
    echo ""
    printf "  ${GD}========================================${BK}\n"
    printf "  ${WH}${BD}  EMPIRE SWITCHBOARD${BK}            ${GD}v2.0${BK}\n"
    printf "  ${GY}  Master Control Panel   $(date '+%I:%M %p')${BK}\n"
    printf "  ${GD}========================================${BK}\n"
    echo ""
    printf "  ${WH}RAM ${BK} "; bar $rp 25 $RAM_WARN $RAM_CRIT; printf " ${GY}$(ram_used)/$(ram_total)${BK}\n"
    printf "  ${WH}SWAP${BK} "; bar $sp 25 40 70; printf "\n"
    printf "  ${WH}DISK${BK} "; bar ${dp:-0} 25 70 90; printf " ${GY}$(disk_free) free${BK}\n"
    printf "  ${WH}CPU ${BK} Load: ${cl}  Up: ${GY}$(sys_uptime)${BK}\n"
    echo ""
    local njc=$GN; [ "$nj" -ge "$MAX_NEXTJS" ] && njc=$OG; [ "$nj" -gt "$MAX_NEXTJS" ] && njc=$RD
    printf "  ${WH}NEXT.JS${BK} ${njc}${nj}/${MAX_NEXTJS}${BK}  ${GY}|${BK}  ${WH}DOCKER${BK} ${GY}${dr}/${dt}${BK}\n"
    printf "  ${GD}----------------------------------------${BK}\n"
    printf "  ${WH}${BD}#  SERVICE              STATUS   MODE${BK}\n"
    printf "  ${GD}----------------------------------------${BK}\n"
    local n=1
    for p in "${PRODUCTS[@]}"; do
        IFS='|' read -r port name dir type group desc <<< "$p"
        if port_active $port; then
            local pid=$(port_pid $port) mode=$(svc_mode $port) mem=$(pid_mem $(port_pid $port))
            local mc=$PR; [ "$mode" = "prod" ] && mc=$GN; [ "$mode" = "api" ] && mc=$CY
            printf "  ${WH}${n}${BK}  ${GN}*${BK} %-18s ${GN}LIVE${BK}     ${mc}${mode}${BK} ${GY}${mem}%%${BK}\n" "$name"
            printf "     ${GY}:${port} PID ${pid} ${desc}${BK}\n"
        else
            printf "  ${WH}${n}${BK}  ${RD}o${BK} ${GY}%-18s off${BK}\n" "$name"
            printf "     ${GY}:${port} ${desc}${BK}\n"
        fi
        n=$((n+1))
    done
    printf "  ${GD}----------------------------------------${BK}\n"
    printf "  ${GY}COMING SOON:${BK}\n"
    for ff in "${FUTURE[@]}"; do
        IFS='|' read -r fn fd <<< "$ff"
        printf "     ${GY}%-18s ${fd}${BK}\n" "$fn"
    done
    echo ""
    if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
        printf "  ${GN}*${BK} Monitor ${GN}ACTIVE${BK} PID $(cat $PIDFILE)\n"
    else
        printf "  ${RD}o${BK} ${GY}Monitor off (type m)${BK}\n"
    fi
    printf "  ${GD}========================================${BK}\n"
    printf "  ${CY}1-5${BK} toggle  ${CY}d1-5${BK} dev  ${CY}p1-5${BK} prod\n"
    printf "  ${CY}r1-5${BK} restart ${CY}o1-5${BK} browser\n"
    printf "  ${CY}up${BK} start all  ${CY}down${BK} stop all  ${CY}prod${BK} all prod\n"
    printf "  ${CY}m${BK} monitor on  ${CY}mx${BK} off  ${CY}w${BK} watch\n"
    printf "  ${CY}dk${BK} docker  ${CY}cr${BK} crashes  ${CY}L${BK} launch  ${CY}log${BK} log\n"
    printf "  ${CY}q${BK} quit\n"
    printf "  ${GD}========================================${BK}\n"
}

crash_history() {
    echo ""
    printf "  ${WH}${BD}CRASH HISTORY${BK}\n"
    printf "  ${RD}Feb23${BK} Ollama OOM      ${GN}Removed Ollama${BK}\n"
    printf "  ${RD}Feb24${BK} pkill -f broad   ${GN}Port kills only${BK}\n"
    printf "  ${RD}Feb25${BK} 5+ Next.js       ${GN}Max 3 limit${BK}\n"
    printf "  ${RD}Feb26${BK} Soft freeze      ${GN}Switchboard${BK}\n"
    printf "  ${WH}BANNED:${BK} ${RD}sensors-detect pkill-node ollama${BK}\n"
}

quick_launch() {
    echo ""
    printf "  ${CY}claude${BK} ClaudeForge  ${CY}github${BK} repo  ${CY}files${BK} filemanager  ${CY}back${BK}\n"
    while true; do
        printf "${PR}launch>${BK} "; read -r lc
        case $lc in
            claude) xdg-open "https://claude.ai/new" 2>/dev/null & break;;
            github) xdg-open "https://github.com/r22gir/Empire" 2>/dev/null & break;;
            files)  xdg-open "$HOME/Empire" 2>/dev/null & break;;
            back|q) break;; *) printf "  ${GY}?${BK}\n";;
        esac
    done
}

docker_menu() {
    printf "\n  ${CY}dc up${BK} | ${CY}dc down${BK} | ${CY}dc ps${BK} | ${CY}back${BK}\n"
    while true; do
        printf "${PR}docker>${BK} "; read -r dc
        case $dc in
            "dc up")   cd ~/Empire && docker compose up -d 2>&1|tail -5; break;;
            "dc down") cd ~/Empire && docker compose down 2>&1|tail -5; break;;
            "dc ps")   docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null|head -15;;
            back|q)    break;; *) printf "  ${GY}?${BK}\n";;
        esac
    done
}

watch_mode() {
    trap 'return' INT
    while true; do display; printf "\n${GY}  Auto ${INTERVAL}s Ctrl+C stop${BK}\n"; sleep $INTERVAL; done
    trap - INT
}

case "$1" in
    --bg)   bg_monitor; exit 0;;
    -s)     display; exit 0;;
    -c)     echo "RAM:$(ram_pct)% NEXT:$(njs_count)/$MAX_NEXTJS FREE:$(ram_free)"
            for p in "${PRODUCTS[@]}"; do IFS='|' read -r pt pn pd pp pg pdesc <<< "$p"; port_active $pt && echo "  * :$pt $pn ($(svc_mode $pt))" || echo "  o :$pt $pn"; done; exit 0;;
    -m)     monitor_start; exit 0;;
    -x)     monitor_stop; exit 0;;
    --up)   bulk_up dev; exit 0;;
    --down) bulk_down; exit 0;;
esac

display
while true; do
    printf "\n${GD}empire>${BK} "
    read -r cmd
    case $cmd in
        [1-5])      svc_toggle $cmd; sleep 1; display;;
        d[1-5])     svc_mode_start ${cmd:1} dev; sleep 1; display;;
        p[1-5])     svc_mode_start ${cmd:1} prod; sleep 1; display;;
        r[1-5])     svc_restart ${cmd:1}; sleep 1; display;;
        o[1-5])     open_browser ${cmd:1};;
        up)         bulk_up dev; sleep 2; display;;
        down)       bulk_down; sleep 1; display;;
        prod)       bulk_up prod; sleep 2; display;;
        m)          monitor_start;;
        mx)         monitor_stop;;
        w)          watch_mode; display;;
        dk|docker)  docker_menu; display;;
        L|launch)   quick_launch; display;;
        cr|crash)   crash_history;;
        log)        [ -f "$LOG" ] && tail -20 "$LOG" || echo "  No log";;
        s|"")       display;;
        q|quit|exit) printf "${GD}  Empire out.${BK}\n"; exit 0;;
        *)          printf "  ${GY}?${BK}\n";;
    esac
done
