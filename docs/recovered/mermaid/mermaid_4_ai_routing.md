# ============================================
# EMPIRE v4.0 — AI ROUTING & TOOL EXECUTION
# ============================================

graph TB
    MSG["User Message"] --> GUARD["Guardrails<br/>Input Validation"]
    GUARD --> ROUTER["AI Router"]

    ROUTER -->|"Priority 1"| GROK["xAI Grok<br/>☁️ Primary"]
    ROUTER -.->|"Priority 2"| CLAUDE["Claude API<br/>☁️ Secondary"]
    ROUTER -.->|"Priority 3<br/>Emergency Only"| OLLAMA["Ollama CPU<br/>🖥️ Fallback"]

    GROK --> RESP["Response"]
    RESP --> PARSE["Parse Tool Blocks"]

    PARSE -->|"```tool```"| TOOLS["Tool Executor"]
    PARSE -->|"no tools"| DELIVER["Deliver Response"]

    TOOLS --> WS["🔍 Web Search<br/>DDG HTML → Brave"]
    TOOLS --> QQ["💰 Quick Quote"]
    TOOLS --> QR["📊 Quote Report"]
    TOOLS --> PRES["📑 Presentation"]
    TOOLS --> IMG["🖼️ Image Search"]

    TOOLS --> FEEDBACK["Feed results back"]
    FEEDBACK --> GROK

    DELIVER -->|"web"| WEBUI["Dashboard UI"]
    DELIVER -->|"telegram"| TGUI["Telegram<br/>+ TTS voice"]

    subgraph CHANNEL["Channel Directives"]
        WEBDIR["Web: detailed OK"]
        TGDIR["Telegram: ultra-short<br/>plain text, no fluff"]
    end

    ROUTER --> CHANNEL
