# ============================================
# EMPIRE v4.0 — MEMORY ARCHITECTURE
# ============================================

graph TB
    subgraph CLIENTS["Clients"]
        WEB["🌐 Founder Dashboard"]
        TG["📱 Telegram Bot"]
        API["🔧 External API"]
        CC["💻 Claude.ai<br/>via context-bridge"]
    end

    subgraph MEMAPI["🧠 /api/v1/memory/*"]
        SEARCH["/search"]
        RECENT["/recent"]
        ADD["/add"]
        CTXPK["/context-pack"]
        STATS["/stats"]
        SUMMARY["/conversation-summary"]
        KNOW["/knowledge"]
    end

    subgraph STORE["💾 Storage"]
        MEMDB["memories.db<br/>SQLite — 97 entries"]
        CONVS["conversation_summaries"]
        CUST["customers"]
        TASKS["tasks"]
        KNOWDB["knowledge"]
    end

    subgraph MEMMD["📄 memory.md"]
        BRAIN["MAX Brain v4.0<br/>Hardware, Products,<br/>Customers, Pricing"]
    end

    WEB -->|"GET on startup"| CTXPK
    WEB -->|"POST after chat"| SUMMARY
    TG -->|"auto-save every msg"| ADD
    API --> SEARCH
    CC -.->|"manual push"| ADD

    SEARCH --> MEMDB
    RECENT --> MEMDB
    ADD --> MEMDB
    CTXPK --> MEMDB
    CTXPK --> CONVS
    CTXPK --> TASKS
    SUMMARY --> CONVS
    KNOW --> KNOWDB
    STATS --> MEMDB

    BRAIN -.->|"loaded into<br/>system prompt"| SYSPROMPT["System Prompt"]
