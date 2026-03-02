# EmpireBox Session Log - 2026-02-24

## Crash Recovery Session

### What Caused the Crash
- Running `launch-all.sh` — the `pkill -f` commands (lines 7-9) killed services too aggressively and crashed the system
- `pkill -f uvicorn`, `pkill -f "next dev"`, `pkill -f "python3 -m http.server"` fired simultaneously
- Combined with kernel 6.17.0-14-generic instability on this hardware

### Fix Applied
- Replaced `pkill -f` commands in `launch-all.sh` with safe port-based kills
- Now only kills processes on specific ports: 8000, 8080, 3000, 3001, 3002
- Kills one at a time with 1-second pause between each

### System Health Check (22:14)
- **Memory**: 27Gi total, 2.1Gi used, 25Gi available — GOOD
- **Swap**: 8Gi total, 0B used — GOOD
- **Disk**: 457G total, 82G used (19%) — GOOD
- **Uptime**: 7 min (fresh boot after crash)
- **Load**: 0.77 — GOOD
- **Ports 8000/8080/3000/3001/3002**: All clear

### Docker Status (22:16)
- **32 containers** — ALL exited/stopped, none running
- Key containers: postgres, redis, ollama, nginx, portainer, open-webui
- 13 forge microservices (marketforge, contractorforge, leadforge, etc.)
- OpenClaw AI, voice service, control center, API gateway
- Most exited cleanly (exit 0), a few exited with errors (exit 255, 137, 2)

### Top Processes (22:16)
- CPU 93.8% idle — system is calm
- Only notable process: `claude` at 45% CPU / 2.5GB RAM
- No zombie processes, 0 stopped

### TODO
- [ ] Launch EmpireBox ecosystem (launch-all.sh)
- [ ] Verify all 5 services come up healthy
- [ ] Fix `/licenses/generate` 500 error on FastAPI backend
- [ ] Decide: restart Docker containers or keep using direct launch?

### WARNINGS
- DO NOT run `sensors-detect` — crashes this hardware
- DO NOT use `pkill -f` for broad patterns — caused today's crash
