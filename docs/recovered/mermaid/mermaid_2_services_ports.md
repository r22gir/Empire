# ============================================
# EMPIRE v4.0 — SERVICES & PORTS
# ============================================

graph LR
    subgraph PORTS["Empire Dell — Active Ports"]
        direction TB
        P8000["🟢 :8000<br/>FastAPI Backend"]
        P3009["🟢 :3009<br/>Founder Dashboard"]
        P3000["🟢 :3000<br/>Empire App"]
        P3001["🟢 :3001<br/>WorkroomForge"]
        P3002["🟡 :3002<br/>LuxeForge"]
        P8080["⬜ :8080<br/>Homepage"]
        P7878["🔴 :7878<br/>OpenClaw"]
        P11434["🔴 :11434<br/>Ollama"]
    end

    subgraph DOCKER["🐳 Docker — ALL STOPPED"]
        PG["PostgreSQL"]
        REDIS["Redis"]
        CONTAINERS["32 Containers"]
    end

    P8000 -->|"API calls"| P3009
    P8000 -->|"API calls"| P3000
    P8000 -->|"API calls"| P3001
    P8000 -->|"API calls"| P3002
