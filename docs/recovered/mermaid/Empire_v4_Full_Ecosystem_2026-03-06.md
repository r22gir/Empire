<!--
EMPIREBOX v4.0 — ECOSYSTEM ARCHITECTURE
Two access tiers: Founder (unlimited) vs User/Buyer (subscription)
-->

# ============================================
# 1. MASTER ECOSYSTEM — Who Connects to What
# ============================================

graph TB
    subgraph FOUNDER["👑 FOUNDER — RG (Unlimited Access)"]
        F_DASH["Founder Dashboard<br/>:3009 — MAX Command Center"]
        F_TG["Telegram<br/>@Empire_Max_Bot"]
        F_CLAUDE["Claude.ai<br/>Context Bridge"]
        F_TERM["Terminal / SSH<br/>Direct Server Access"]
    end

    subgraph USER["👤 USER / BUYER (Subscription Tier)"]
        U_APP["Empire App<br/>:3000 — Customer Portal"]
        U_WF["WorkroomForge<br/>:3001 — Get Quotes"]
        U_LF["LuxeForge<br/>:3002 — Designer Portal"]
        U_MF["MarketF<br/>P2P Marketplace"]
        U_TG["Telegram Bot<br/>Support Channel"]
        U_MOBILE["Mobile App<br/>Flutter"]
    end

    subgraph CORE["⚙️ EMPIRE CORE ENGINE"]
        API["FastAPI Backend<br/>:8000"]
        MAX["MAX AI<br/>12 Desks"]
        MEM["Unified Memory<br/>API"]
        AUTH["Auth + License<br/>System"]
        GUARD["Guardrails +<br/>Emergency Stop"]
    end

    subgraph AI["🤖 AI LAYER"]
        GROK["xAI Grok<br/>Primary"]
        CLAUDE_AI["Claude API<br/>Secondary"]
        OLLAMA["Ollama CPU<br/>Emergency"]
    end

    subgraph PRODUCTS["📦 PRODUCT MODULES"]
        subgraph LIVE_P["🟢 LIVE"]
            WF_MOD["WorkroomForge<br/>Drapery Quotes + AI Photo"]
            LF_MOD["LuxeForge<br/>Measurement + Camera"]
            SF_MOD["SupportForge<br/>AI Customer Support"]
        end
        subgraph BUILT_P["🔵 BUILT"]
            MKF_MOD["MarketForge<br/>Multi-Channel Listing"]
            CF_MOD["ContractorForge<br/>Multi-Tenant SaaS"]
            SHIP_MOD["ShipForge<br/>Shipping Labels"]
            WALLET_MOD["Empire Wallet<br/>Crypto Payments"]
            ECON_MOD["Economic Intel<br/>Cost Tracking"]
        end
        subgraph PLANNED_P["⬜ PLANNED"]
            LEAD_MOD["LeadForge"]
            CRM_MOD["ForgeCRM"]
            SOCIAL_MOD["SocialForge"]
            LLC_MOD["LLCFactory"]
            RELIST_MOD["RelistApp"]
        end
    end

    subgraph DATA["💾 DATA LAYER"]
        MEMDB["memories.db"]
        EMPIRE_DB["empire.db<br/>Tasks, Desks, Contacts"]
        CHAT_DB["Chat History"]
        CUST_DB["Customer Profiles"]
    end

    subgraph INFRA["🖥️ EMPIRE DELL"]
        DELL["Precision Tower 5810<br/>Xeon 10c/20t · 32GB · Ubuntu 24"]
    end

    %% Founder connections — UNLIMITED
    F_DASH -->|"Full Admin"| API
    F_TG -->|"Direct to MAX"| MAX
    F_CLAUDE -->|"Context Push"| MEM
    F_TERM -->|"SSH Root"| DELL

    %% User connections — GATED by Auth + License
    U_APP -->|"Auth Required"| AUTH
    U_WF -->|"Auth Required"| AUTH
    U_LF -->|"Auth Required"| AUTH
    U_MF -->|"Auth Required"| AUTH
    U_TG -->|"Rate Limited"| AUTH
    U_MOBILE -->|"Auth Required"| AUTH
    AUTH -->|"License Valid"| API

    %% Core to AI
    MAX --> GROK
    MAX -.-> CLAUDE_AI
    MAX -.-> OLLAMA
    MAX --> GUARD

    %% Core to Products
    API --> PRODUCTS
    API --> MEM
    MEM --> DATA

    %% Infrastructure
    API --> DELL


# ============================================
# 2. FOUNDER ACCESS — Everything RG Touches
# ============================================

graph TB
    subgraph RG["👑 RG — FOUNDER"]
        RG_BRAIN["Thinks / Decides"]
    end

    subgraph TOUCHPOINTS["How RG Interacts"]
        TP_DASH["🖥️ Founder Dashboard :3009<br/>MAX Chat · 12 Desks · Tasks<br/>System Monitor · File Manager"]
        TP_TG["📱 Telegram @Empire_Max_Bot<br/>Voice + Text · Quick Commands<br/>Direct, No Fluff"]
        TP_CLAUDE["💻 Claude.ai + Claude Code<br/>Architecture · Code · Docs<br/>Context Bridge → Memory"]
        TP_TERM["⌨️ Terminal / SSH<br/>start-empire.sh · git · logs<br/>Direct Server Admin"]
        TP_WF["🏗️ WorkroomForge :3001<br/>Quote Builder · AI Photo<br/>Customer Management"]
        TP_BROWSER["🌐 Empire App :3000<br/>Inventory · Finance · Shipping<br/>Unified Dashboard"]
    end

    subgraph FOUNDER_POWERS["Founder-Only Capabilities"]
        FP_ADMIN["System Admin<br/>Start/Stop Services"]
        FP_CONFIG["API Keys &amp; Config<br/>All .env Files"]
        FP_DEPLOY["Deploy &amp; Git Push<br/>Version Control"]
        FP_MEMORY["Edit MAX Brain<br/>memory.md Direct"]
        FP_DESKS["All 12 AI Desks<br/>Marketing · Finance · Legal<br/>IT · Support · Operations<br/>Forge · Analytics · Commerce<br/>Content · Research · Strategy"]
        FP_MONITOR["System Monitor<br/>CPU · RAM · Disk · Logs"]
    end

    RG_BRAIN --> TP_DASH
    RG_BRAIN --> TP_TG
    RG_BRAIN --> TP_CLAUDE
    RG_BRAIN --> TP_TERM
    RG_BRAIN --> TP_WF
    RG_BRAIN --> TP_BROWSER

    TP_DASH --> FP_ADMIN
    TP_DASH --> FP_DESKS
    TP_DASH --> FP_MONITOR
    TP_TERM --> FP_CONFIG
    TP_TERM --> FP_DEPLOY
    TP_CLAUDE --> FP_MEMORY


# ============================================
# 3. USER / BUYER ACCESS — Subscription Gated
# ============================================

graph TB
    subgraph BUYER["👤 USER / BUYER"]
        B_NEW["New User<br/>Signs Up"]
    end

    subgraph TIERS["📋 SUBSCRIPTION TIERS"]
        T_LITE["LITE $29/mo<br/>1 Forge App<br/>Basic Support<br/>5 Listings"]
        T_PRO["PRO $79/mo<br/>3 Forge Apps<br/>Priority Support<br/>50 Listings<br/>ShipForge"]
        T_EMPIRE["EMPIRE $199/mo<br/>All Forge Apps<br/>Dedicated Support<br/>Unlimited Listings<br/>Empire Wallet<br/>White Label"]
    end

    subgraph ONBOARD["🚀 ZERO TO HERO — Onboarding"]
        Z1["OpenClaw Intake<br/>30 min conversation"]
        Z2["LLCFactory<br/>Business Formation"]
        Z3["Stripe Connect<br/>Payment Setup"]
        Z4["SocialForge<br/>Social Accounts"]
        Z5["Tools Activation<br/>Based on Tier"]
        Z6["EmpireAssist<br/>Telegram Bot Setup"]
        Z7["HERO STATUS<br/>Taking Orders!"]
    end

    subgraph USER_APPS["📱 What Users Can Access"]
        UA_PORTAL["Empire App Portal<br/>Their Dashboard"]
        UA_MARKET["MarketForge<br/>List on eBay, Amazon, etc."]
        UA_SHIP["ShipForge<br/>Print Labels, Track"]
        UA_SUPPORT["SupportForge<br/>AI Help Desk"]
        UA_CRM["ForgeCRM<br/>Customer Management"]
        UA_WALLET["Empire Wallet<br/>Crypto Payments"]
        UA_SOCIAL["SocialForge<br/>Auto-Post Content"]
    end

    subgraph USER_LIMITS["🔒 User Limitations"]
        UL_NO["❌ Cannot Access:<br/>Founder Dashboard<br/>System Admin<br/>MAX Brain/Memory<br/>Server Terminal<br/>AI Desk Config<br/>Other Users' Data"]
        UL_RATE["⏱️ Rate Limited:<br/>API Calls per Tier<br/>AI Queries per Day<br/>Storage per Account"]
    end

    B_NEW --> TIERS
    T_LITE --> Z1
    T_PRO --> Z1
    T_EMPIRE --> Z1
    Z1 --> Z2 --> Z3 --> Z4 --> Z5 --> Z6 --> Z7

    Z7 --> UA_PORTAL
    UA_PORTAL --> UA_MARKET
    UA_PORTAL --> UA_SHIP
    UA_PORTAL --> UA_SUPPORT
    UA_PORTAL --> UA_CRM
    UA_PORTAL --> UA_WALLET
    UA_PORTAL --> UA_SOCIAL


# ============================================
# 4. DATA FLOW — How Info Moves
# ============================================

graph LR
    subgraph INPUT["📥 INPUT"]
        I_CHAT["Chat Message"]
        I_PHOTO["Photo Upload"]
        I_VOICE["Voice Note"]
        I_ORDER["Customer Order"]
        I_LISTING["Product Listing"]
    end

    subgraph PROCESS["⚙️ PROCESSING"]
        P_GUARD["Guardrails<br/>Validate Input"]
        P_AUTH["Auth Check<br/>License Valid?"]
        P_ROUTE["AI Router<br/>Grok → Claude → Ollama"]
        P_TOOLS["Tool Executor<br/>Search · Quote · Ship"]
        P_DESK["Desk Router<br/>Which AI Desk?"]
    end

    subgraph STORE["💾 STORE"]
        S_MEM["Memory API<br/>Long-term Brain"]
        S_CHAT["Chat History<br/>Per Conversation"]
        S_CUST["Customer DB<br/>Profiles + Revenue"]
        S_TASK["Task Engine<br/>Desks + Actions"]
    end

    subgraph OUTPUT["📤 OUTPUT"]
        O_TEXT["Text Response"]
        O_VOICE_OUT["TTS Voice Reply"]
        O_PDF["PDF Quote / Report"]
        O_NOTIFY["Notification<br/>Telegram / Email"]
        O_ACTION["Automated Action<br/>Ship · List · Invoice"]
    end

    I_CHAT --> P_GUARD --> P_AUTH --> P_ROUTE
    I_PHOTO --> P_GUARD
    I_VOICE --> P_GUARD
    I_ORDER --> P_AUTH --> P_TOOLS
    I_LISTING --> P_AUTH --> P_TOOLS

    P_ROUTE --> P_DESK
    P_ROUTE --> P_TOOLS
    P_DESK --> S_TASK
    P_TOOLS --> S_MEM
    P_TOOLS --> S_CUST

    S_MEM --> O_TEXT
    S_TASK --> O_ACTION
    O_TEXT --> O_VOICE_OUT
    P_TOOLS --> O_PDF
    S_TASK --> O_NOTIFY


# ============================================
# 5. HARDWARE BUNDLES — What Ships to Users
# ============================================

graph TB
    subgraph BUNDLES["📦 HARDWARE BUNDLES"]
        B1["💰 Budget Mobile $349<br/>Xiaomi Redmi Note 13<br/>+ Lite 12mo Sub"]
        B2["🔥 Seeker Pro $599<br/>Solana Seeker Phone<br/>+ Pro 12mo Sub<br/>MOST POPULAR"]
        B3["👑 Full Empire $899<br/>Solana Seeker<br/>+ Beelink Mini PC<br/>+ Empire 12mo Sub"]
    end

    subgraph PROFIT["💵 REVENUE MODEL"]
        REV1["Hardware: Loss Leader<br/>Sell at/below cost"]
        REV2["Subscriptions: Profit<br/>$29-$199/mo recurring"]
        REV3["MarketF: 8% Transaction Fee"]
        REV4["Empire Wallet: Tx Fees"]
        REV5["Year 3 Target:<br/>$3.4M - $17.2M"]
    end

    B1 --> REV2
    B2 --> REV2
    B3 --> REV2
    B2 --> REV3
    B3 --> REV3
    B3 --> REV4


# ============================================
# 6. SERVICE MAP — What Runs Where
# ============================================

graph TB
    subgraph DELL_SERVER["🖥️ EMPIRE DELL — Always Running"]
        subgraph ALWAYS_ON["Always On"]
            S_BACK[":8000 FastAPI<br/>Backend + API"]
            S_TG[":8000 Telegram Bot<br/>Runs inside Backend"]
            S_MEM_SVC[":8000 Memory API<br/>Brain Access"]
            S_SCHED["Desk Scheduler<br/>Background Tasks"]
            S_MON["MAX Monitor<br/>Health Checks"]
        end

        subgraph ON_DEMAND["Start on Demand (max 3)"]
            S_FD[":3009 Founder Dashboard"]
            S_EA[":3000 Empire App"]
            S_WF[":3001 WorkroomForge"]
            S_LF[":3002 LuxeForge"]
        end

        subgraph DISABLED["Disabled / Future"]
            S_OC[":7878 OpenClaw"]
            S_OL[":11434 Ollama CPU"]
            S_HP[":8080 Homepage"]
            S_DOCKER["Docker: 32 Containers<br/>PostgreSQL · Redis"]
        end
    end

    subgraph CLOUD["☁️ CLOUD SERVICES"]
        C_GROK["xAI Grok API"]
        C_CLAUDE["Claude API"]
        C_TG["Telegram API"]
        C_GH["GitHub r22gir/Empire"]
        C_GD["Google Drive Backup"]
    end

    subgraph FUTURE_HW["🔮 FUTURE"]
        F_BEELINK["Beelink Mini PC<br/>Light Modules<br/>Ships with Full Empire Bundle"]
    end

    S_BACK --> C_GROK
    S_BACK -.-> C_CLAUDE
    S_TG --> C_TG
    DELL_SERVER -.-> C_GH
    DELL_SERVER -.-> C_GD
