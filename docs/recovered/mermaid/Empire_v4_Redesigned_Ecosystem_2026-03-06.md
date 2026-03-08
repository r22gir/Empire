# ============================================
# EMPIRE v4.0 — REDESIGNED ARCHITECTURE
# MAX = Founder's AI Assistant (Top Layer)
# Everything connects TO MAX, classified by domain
# ============================================


# ============================================
# 1. THE BIG PICTURE — MAX Controls Everything
# ============================================

graph TB
    RG["👑 RG — Founder"]

    RG -->|"Voice · Text · Dashboard · Telegram · Claude"| MAX

    subgraph MAX_LAYER["🤖 MAX — Founder's Personal AI Assistant"]
        MAX["MAX AI<br/>Brain · Memory · 12 Desks"]
        MAX_MEM["Unified Memory<br/>Remembers Everything"]
        MAX_TOOLS["Tools<br/>Search · Quote · Ship · Research"]
    end

    MAX --> WORKROOM
    MAX --> EMPIRE
    MAX --> PERSONAL

    subgraph WORKROOM["🏗️ EMPIRE WORKROOM — RG's Drapery Business"]
        WR_APP["WorkroomForge App<br/>:3001"]
        WR_AI["AI Measurement Tools<br/>Photo Analysis · Mockups"]
        WR_QUOTE["Quote Builder<br/>Auto-Pricing · PDF"]
        WR_CUST["Customer Management<br/>Emily · Sarah · Maria"]
        WR_INV["Inventory<br/>Fabrics · Hardware · Motors"]
        WR_LUXE["LuxeForge<br/>Designer Portal · Camera"]
    end

    subgraph EMPIRE["🚀 EMPIRE PLATFORM — SaaS Ecosystem"]
        EP_APP["Empire App<br/>:3000"]
        EP_MARKET["MarketForge<br/>Multi-Channel Listing"]
        EP_CONTRACTOR["ContractorForge<br/>Multi-Tenant SaaS"]
        EP_SUPPORT["SupportForge<br/>AI Customer Support"]
        EP_SHIP["ShipForge<br/>Shipping Labels"]
        EP_WALLET["Empire Wallet<br/>Crypto Payments"]
        EP_LICENSE["License System<br/>Subscriptions"]
        EP_ONBOARD["Setup Portal<br/>Zero to Hero"]
    end

    subgraph PERSONAL["📋 PERSONAL — RG's Other Projects"]
        P_VET["VeteranForge<br/>VA Telehealth"]
        P_AMP["AMP<br/>Actitud Mental Positiva"]
        P_LLC["LLCFactory<br/>Business Formation"]
        P_RECOVER["RecoveryForge<br/>File Recovery"]
    end

    MAX_MEM --> MAX
    MAX_TOOLS --> MAX


# ============================================
# 2. MAX ASSISTANT — What MAX Actually Does
# ============================================

graph TB
    subgraph MAX_CORE["🤖 MAX — The Brain"]
        direction TB
        BRAIN["Persistent Memory<br/>97+ memories · memory.md<br/>Customers · Decisions · Context"]
        PERSONALITY["Personality<br/>Direct · No Fluff<br/>Matches RG's Energy"]
        CONTEXT["Context Pack<br/>Loads on Every Session<br/>Knows What Happened Last Time"]
    end

    subgraph MAX_CHANNELS["📡 How RG Talks to MAX"]
        CH_DASH["🖥️ Founder Dashboard :3009<br/>Full UI · File Upload · Charts"]
        CH_TG["📱 Telegram<br/>Ultra-Short · Voice Reply<br/>Works While Driving"]
        CH_CLAUDE["💻 Claude.ai<br/>Architecture · Deep Work<br/>Context Bridge Sync"]
        CH_TERM["⌨️ Terminal<br/>Direct Commands"]
    end

    subgraph MAX_DESKS["🗄️ 12 AI DESKS — Each Desk = Specialist"]
        D_MARKETING["📣 Marketing Desk<br/>Social Posts · Content · Ads"]
        D_FINANCE["💰 Finance Desk<br/>Revenue · Costs · Invoicing"]
        D_LEGAL["⚖️ Legal Desk<br/>Contracts · Compliance"]
        D_IT["🔧 IT Desk<br/>Server Health · Deploys · Logs"]
        D_SUPPORT["🎧 Support Desk<br/>Tickets · Customer Issues"]
        D_OPS["📦 Operations Desk<br/>Shipping · Inventory · Orders"]
        D_FORGE["🏗️ Forge Desk<br/>WorkroomForge AI Vision"]
        D_ANALYTICS["📊 Analytics Desk<br/>Metrics · Reports · Trends"]
        D_COMMERCE["🛒 Commerce Desk<br/>Listings · Marketplace · Pricing"]
        D_CONTENT["✍️ Content Desk<br/>Blog · Docs · Presentations"]
        D_RESEARCH["🔬 Research Desk<br/>Web Search · Competitors · Ideas"]
        D_STRATEGY["🎯 Strategy Desk<br/>Roadmap · Priorities · Planning"]
    end

    CH_DASH --> MAX_CORE
    CH_TG --> MAX_CORE
    CH_CLAUDE --> MAX_CORE
    CH_TERM --> MAX_CORE

    MAX_CORE --> MAX_DESKS

    D_FORGE -->|"controls"| WR["WorkroomForge"]
    D_COMMERCE -->|"controls"| MKF["MarketForge"]
    D_SUPPORT -->|"controls"| SF["SupportForge"]
    D_IT -->|"controls"| SERVER["Empire Dell"]
    D_FINANCE -->|"controls"| WALLET["Empire Wallet"]
    D_OPS -->|"controls"| SHIP["ShipForge"]


# ============================================
# 3. EMPIRE WORKROOM — RG's Drapery Business
#    (Currently MISSING pieces marked ❌)
# ============================================

graph TB
    subgraph WR_DOMAIN["🏗️ EMPIRE WORKROOM — Custom Drapery Business"]

        subgraph WR_LIVE["🟢 LIVE"]
            WR_APP2["WorkroomForge :3001<br/>Quote Builder UI"]
            WR_LUXE2["LuxeForge :3002<br/>Designer Portal"]
        end

        subgraph WR_AI_TOOLS["🤖 AI TOOLS — ❌ MOST MISSING"]
            AI_PHOTO["📸 AI Photo Analysis<br/>❌ Upload broken"]
            AI_MEASURE["📏 AI Measurement<br/>❌ Not working"]
            AI_MOCKUP["🎨 AI Mockup Generator<br/>❌ Not working"]
            AI_OUTLINE["📐 AI Outline &amp; Dimensions<br/>❌ Not working"]
            AI_UPHOLSTERY["🛋️ AI Upholstery Analysis<br/>❌ Not working"]
            AI_IMAGINE["✨ AI Imagine / Redesign<br/>❌ Not working"]
        end

        subgraph WR_PRICING["💰 PRICING ENGINE"]
            PRICE_CALC["Auto-Calculator<br/>Base × SqFt + Lining + Hardware + Motor"]
            PRICE_TYPES["Treatment Types<br/>Ripplefold $45 · Pinch Pleat $38<br/>Rod Pocket $28 · Grommet $32<br/>Roman $55 · Roller $42"]
            PRICE_LINING["Linings<br/>Standard $8 · Blackout $15<br/>Thermal $12 · Interlining $18"]
            PRICE_HW["Hardware &amp; Motors<br/>Somfy $285 · Lutron $425<br/>Generic $185"]
        end

        subgraph WR_CUSTOMERS["👥 CUSTOMERS"]
            C_EMILY["Emily Rodriguez<br/>$22,600 VIP Repeat"]
            C_SARAH["Sarah Mitchell<br/>$12,400 VIP"]
            C_MARIA["Maria Gonzalez<br/>$8,900 Designer Referral"]
            C_DAVID["David Chen<br/>$4,200 New"]
            C_JAMES["James Wilson<br/>$3,100 Inactive"]
            C_PIPE["Pipeline: $31,900"]
        end

        subgraph WR_VENDORS["🏭 VENDORS"]
            V1["Rowley Company"]
            V2["Somfy"]
            V3["Lutron"]
            V4["Kirsch"]
        end
    end

    WR_APP2 --> WR_AI_TOOLS
    WR_APP2 --> WR_PRICING
    WR_APP2 --> WR_CUSTOMERS
    WR_LUXE2 --> AI_PHOTO
    WR_LUXE2 --> AI_MEASURE


# ============================================
# 4. EMPIRE PLATFORM — SaaS for Resellers
#    (What Users/Buyers Subscribe To)
# ============================================

graph TB
    subgraph EP_DOMAIN["🚀 EMPIRE PLATFORM — SaaS Ecosystem"]

        subgraph EP_TIERS["📋 SUBSCRIPTION TIERS"]
            T_LITE["LITE $29/mo<br/>1 App · Basic Support · 5 Listings"]
            T_PRO["PRO $79/mo<br/>3 Apps · Priority Support<br/>50 Listings · ShipForge"]
            T_EMPIRE2["EMPIRE $199/mo<br/>All Apps · Dedicated Support<br/>Unlimited · Wallet · White Label"]
        end

        subgraph EP_APPS["📱 USER-FACING APPS"]
            A_PORTAL["Empire App Portal<br/>User's Dashboard"]
            A_MARKET2["MarketForge<br/>List on eBay · Amazon · Poshmark"]
            A_CONTRACT["ContractorForge<br/>Contractor Business Tools"]
            A_SUPPORT2["SupportForge<br/>AI Help Desk"]
            A_SHIP2["ShipForge<br/>Labels · Tracking · Returns"]
            A_CRM2["ForgeCRM<br/>Customer Management"]
            A_WALLET2["Empire Wallet<br/>USDC · SOL · EMPIRE Token"]
            A_SOCIAL2["SocialForge<br/>Auto-Post · Scheduling"]
            A_RELIST["RelistApp<br/>Cross-Platform Relisting"]
        end

        subgraph EP_ONBOARD2["🚀 ZERO TO HERO"]
            ZH1["1. Intake 30min"]
            ZH2["2. LLC Formation"]
            ZH3["3. Stripe Connect"]
            ZH4["4. Social Accounts"]
            ZH5["5. Tools Activation"]
            ZH6["6. Telegram Setup"]
            ZH7["7. HERO — Taking Orders!"]
            ZH1 --> ZH2 --> ZH3 --> ZH4 --> ZH5 --> ZH6 --> ZH7
        end

        subgraph EP_BUNDLES["📦 HARDWARE BUNDLES"]
            B1_2["Budget $349<br/>Xiaomi + Lite 12mo"]
            B2_2["Seeker Pro $599<br/>Solana Seeker + Pro 12mo"]
            B3_2["Full Empire $899<br/>Seeker + Beelink + Empire 12mo"]
        end

        subgraph EP_LIMITS["🔒 USER BOUNDARIES"]
            LIM1["❌ No Founder Dashboard"]
            LIM2["❌ No Server Access"]
            LIM3["❌ No MAX Brain Editing"]
            LIM4["❌ No Other Users' Data"]
            LIM5["⏱️ Rate Limits per Tier"]
            LIM6["📊 Storage Limits per Tier"]
        end
    end

    T_LITE --> A_PORTAL
    T_PRO --> A_PORTAL
    T_EMPIRE2 --> A_PORTAL
    A_PORTAL --> A_MARKET2
    A_PORTAL --> A_SHIP2
    A_PORTAL --> A_SUPPORT2


# ============================================
# 5. INFRASTRUCTURE — What Runs Everything
# ============================================

graph TB
    subgraph INFRA["🖥️ INFRASTRUCTURE"]

        subgraph DELL2["Empire Dell — Primary Server"]
            ALWAYS["Always Running:<br/>:8000 Backend + Telegram Bot<br/>Memory API · Desk Scheduler<br/>MAX Monitor"]
            DEMAND["On Demand (max 3):<br/>:3009 Founder Dashboard<br/>:3000 Empire App<br/>:3001 WorkroomForge<br/>:3002 LuxeForge"]
            DISABLED2["Disabled:<br/>:7878 OpenClaw<br/>:11434 Ollama<br/>Docker 32 containers"]
        end

        subgraph CLOUD2["Cloud APIs"]
            CL_GROK["xAI Grok<br/>Chat + Vision<br/>$$ per query"]
            CL_CLAUDE2["Claude API<br/>Fallback AI<br/>$$ per query"]
            CL_TG2["Telegram API<br/>Free"]
            CL_BRAVE["Brave Search<br/>❌ Key Missing<br/>1000 free/mo"]
            CL_EDGE["edge-tts<br/>✅ Installed<br/>Free TTS"]
        end

        subgraph FUTURE2["Future Hardware"]
            BEELINK2["Beelink Mini PC<br/>Ships with Full Empire Bundle<br/>Runs Light Modules for Users"]
        end

        subgraph BACKUP2["Backups"]
            BK_GH["GitHub r22gir/Empire<br/>All Code"]
            BK_GD["Google Drive<br/>Full Sync"]
            BK_USB["USB 1TB<br/>Backup Only"]
        end
    end

    ALWAYS --> CL_GROK
    ALWAYS -.-> CL_CLAUDE2
    ALWAYS --> CL_TG2


# ============================================
# 6. WHAT'S BROKEN — Fix Priority List
# ============================================

graph TB
    subgraph BROKEN["🔴 WHAT'S BROKEN RIGHT NOW"]
        B_SEARCH["Web Search<br/>DDG Rate Limited<br/>Brave Key Missing"]
        B_AI_TOOLS2["WorkroomForge AI Tools<br/>Photo Upload Broken<br/>Measure · Mockup · Outline<br/>Upholstery · Imagine"]
        B_LAUNCH["start-empire.sh<br/>Doesn't Work Clean"]
        B_DOCKER2["Docker 32 Containers<br/>All Stopped · No Panel"]
        B_OLLAMA2["Ollama<br/>Not Installed on Dell"]
        B_SCHED["MAX Scheduler<br/>Missing apscheduler"]
        B_PYTESS["Files API<br/>Missing pytesseract"]
        B_OPENAI["TTS Voice<br/>edge-tts Installed<br/>But Not Tested"]
    end

    subgraph FIX_ORDER["🟢 FIX PRIORITY"]
        F1["1. start-empire.sh<br/>One-click launch"]
        F2["2. WorkroomForge AI Tools<br/>Photo upload + all analysis"]
        F3["3. Brave Search Key<br/>Reliable web search"]
        F4["4. pip install missing<br/>apscheduler · pytesseract"]
        F5["5. Test TTS voice<br/>edge-tts on Telegram"]
        F6["6. Docker control panel<br/>Start/stop containers"]
    end

    B_LAUNCH --> F1
    B_AI_TOOLS2 --> F2
    B_SEARCH --> F3
    B_SCHED --> F4
    B_PYTESS --> F4
    B_OPENAI --> F5
    B_DOCKER2 --> F6
