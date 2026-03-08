# ============================================
# EMPIRE v4.0 — FULL SYSTEM ARCHITECTURE
# Paste into Eraser.io as-is
# ============================================

graph TB
    subgraph HW["🖥️ EMPIRE DELL — Precision Tower 5810"]
        CPU["Xeon E5-2650 v3<br/>10c/20t"]
        RAM["32GB RAM"]
        GPU["Quadro K600<br/>Dedicated"]
        DISK["92GB SSD"]
        OS["Ubuntu 24.04 LTS<br/>Kernel 6.17"]
    end

    subgraph EXT["☁️ EXTERNAL"]
        XAI["xAI Grok<br/>Primary AI + Vision"]
        CLAUDE["Claude API<br/>Secondary AI"]
        TGAPI["Telegram API"]
        GH["GitHub"]
        GD["Google Drive"]
    end

    subgraph BACK["⚙️ BACKEND :8000"]
        FAST["FastAPI + Uvicorn"]
        MAXR["/max/* — AI Chat"]
        MEMR["/memory/* — Brain API"]
        CHATR["/chats/* — History"]
        SYSR["/system/* — Monitor"]
        TGBOT["Telegram Bot"]
    end

    subgraph FRONT["🖼️ FRONTENDS"]
        FD["Founder Dashboard<br/>:3009"]
        EA["Empire App<br/>:3000"]
        WF["WorkroomForge<br/>:3001"]
        LF["LuxeForge<br/>:3002"]
    end

    subgraph MEM["🧠 MEMORY"]
        MEMDB["memories.db<br/>97 entries"]
        MEMMD["memory.md<br/>v4.0 Brain"]
        CTXPK["context-pack<br/>Session Startup"]
    end

    subgraph AGENT["🤖 AGENTS"]
        SAFE["Safeguards"]
        ESTOP["Emergency Stop"]
        DESKS["12 AI Desks"]
        SCHED["Desk Scheduler"]
    end

    FRONT -->|"REST + SSE"| BACK
    TGAPI --> TGBOT
    TGBOT --> MAXR
    MAXR --> XAI
    MAXR -.->|"fallback"| CLAUDE
    MAXR --> MEMR
    MEMR --> MEMDB
    MEMR --> MEMMD
    FD -->|"on startup"| CTXPK
    CTXPK --> MEMDB
    MAXR --> AGENT
    DESKS --> SCHED
    BACK --> HW
    GH -.-> HW
    GD -.-> HW
