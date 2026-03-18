"""
Empire Ecosystem Catalog — Auto-generated from full codebase scan.
MAX uses this to answer questions about any Empire product, service, or feature.
Last updated: 2026-03-18 (v5.1 — post tool-fix + knowledge build)
Source: Full codebase audit (422+ commits, 44 screens, 37 tools, 18 desks, 7 databases)
"""

from datetime import datetime

EMPIRE_CATALOG = {
    "company": {
        "name": "Empire Box / EmpireBox",
        "tagline": "Founder's Command Center",
        "vision": "AI-powered business automation platform — run multiple businesses from one command center",
        "founder": "RG",
        "server": "EmpireDell — Dell PowerEdge, Intel Xeon E5-2650 v3, 32GB RAM, 20 cores, Quadro K600 (nouveau), Ubuntu 24.04",
        "domains": {
            "main": "empirebox.store",
            "studio": "studio.empirebox.store",
            "api": "api.empirebox.store",
        },
        "emails": {
            "workroom": "workroom@empirebox.store",
            "woodcraft": "woodcraft@empirebox.store",
            "info": "info@empirebox.store",
            "support": "support@empirebox.store",
        },
        "repo": "github.com/r22gir/Empire (private, main branch)",
        "origin": "Inspired by Alex Finn (AI YouTuber) — OpenClaw + Ollama + Claude API on Mac Mini. Adapted by RG starting on Beelink EQR5.",
    },

    "businesses": {
        "empire_workroom": {
            "name": "Empire Workroom",
            "industry": "Custom drapery & upholstery",
            "description": "RG's drapery & upholstery business — window treatments, drapes, shades, cornices, valances, bedding, upholstery",
            "status": "active",
            "tax_rate": 0.06,
            "labor_rate": 50.0,
            "install_rate": 85.0,
            "fabric_markup": 2.0,
            "customers_count": 113,
            "pipeline_value": 31900,
            "top_customers": ["Emily $22.6K", "Sarah $12.4K", "Maria $8.9K"],
        },
        "woodcraft": {
            "name": "WoodCraft",
            "industry": "Woodwork & CNC",
            "description": "RG's woodwork & CNC business — cross-sell brand, mirrors WorkroomForge structure",
            "status": "planned",
            "software_module": "CraftForge",
            "note": "Full spec exists (CRAFTFORGE_SPEC.md), 15 backend endpoints, ZERO frontend built",
        },
        "empire_platform": {
            "name": "Empire Platform (SaaS)",
            "description": "SaaS ecosystem — all Forge products are dual-use: RG dogfoods first, then sells to subscribers",
            "status": "in_development",
            "tiers": {
                "lite": {"price": 29, "tokens": "50K"},
                "pro": {"price": 79, "tokens": "200K"},
                "empire": {"price": 199, "tokens": "1M"},
                "founder": {"price": 0, "tokens": "unlimited"},
            },
        },
    },

    "products": {
        "command_center": {
            "name": "Command Center",
            "description": "Unified Next.js dashboard — replaces 4 legacy apps. 4 tabs: MAX (gold), Workroom (green), CraftForge (yellow), Platform (blue). 44 screen components.",
            "status": "active",
            "port": 3005,
            "url": "studio.empirebox.store",
            "cc_screen": "DashboardScreen.tsx",
            "tech": "Next.js 14, React 18, TypeScript, Tailwind CSS",
            "systemd": "empire-cc",
            "features": ["MAX AI chat", "Workroom dashboard", "CraftForge dashboard", "Desks management", "Tasks", "Documents", "Inbox", "System report", "Cost tracker", "Quote builder", "Vision analysis"],
            "desk": None,
            "target_user": "Founder (RG)",
        },
        "workroom_forge": {
            "name": "WorkroomForge",
            "description": "Quote builder + workshop operations for Empire Workroom (drapery/upholstery). QB replacement with 43 endpoints, 7 DB tables, 15 components.",
            "status": "active",
            "port": 3001,
            "cc_screen": "WorkroomPage.tsx",
            "features": ["Quote generation (3-option proposals)", "Finance dashboard (P&L)", "Invoice creation", "Payment tracking", "Expense management", "CRM", "Inventory management", "Job tracking", "Photo-to-quote AI pipeline"],
            "desk": "forge",
            "target_user": "Founder + future SaaS subscribers",
        },
        "craft_forge": {
            "name": "CraftForge",
            "description": "Mirror of WorkroomForge for WoodCraft (woodwork/CNC business). 15 backend endpoints exist, zero frontend.",
            "status": "dev",
            "port": None,
            "cc_screen": "CraftForgePage.tsx",
            "features": ["Quote builder", "Inventory", "CRM", "Finance", "Jobs"],
            "desk": None,
            "target_user": "WoodCraft business",
        },
        "luxe_forge": {
            "name": "LuxeForge",
            "description": "Client/designer intake portal. Free = dumb intake form ($0 cost), Paid = designer tools. Full auth flow with signup/login/dashboard.",
            "status": "active",
            "port": 3002,
            "url": "studio.empirebox.store/intake",
            "cc_screen": "LuxeForgePage.tsx",
            "features": ["Client signup/login", "Project submission", "Room/window details", "Photo upload", "Measurement upload", "Quote review", "Message history"],
            "desk": "intake",
            "target_user": "Clients and interior designers",
        },
        "market_forge": {
            "name": "MarketForge",
            "description": "Multi-marketplace listing & inventory management — eBay, Facebook Marketplace, and more.",
            "status": "dev",
            "port": None,
            "cc_screen": "MarketForgePage.tsx",
            "desk": "market",
            "target_user": "Sellers on multiple platforms",
        },
        "social_forge": {
            "name": "SocialForge",
            "description": "Social media management — content creation, post scheduling, campaign management. Instagram and Facebook APIs wired with real tokens.",
            "status": "active",
            "port": None,
            "cc_screen": "SocialForgePage.tsx",
            "desk": "marketing",
            "target_user": "Small business owners",
            "endpoints": ["/api/v1/socialforge/post/instagram", "/api/v1/socialforge/post/facebook", "/api/v1/socialforge/accounts"],
            "integrations": ["Instagram Graph API", "Facebook Pages API"],
        },
        "support_forge": {
            "name": "SupportForge",
            "description": "Customer support & ticketing system — ticket triage, auto-responses, knowledge base.",
            "status": "dev",
            "port": None,
            "cc_screen": "SupportForgePage.tsx",
            "desk": "support",
            "target_user": "Support teams",
        },
        "ship_forge": {
            "name": "ShipForge",
            "description": "Shipping management and tracking — label creation, order fulfillment.",
            "status": "dev",
            "port": None,
            "cc_screen": "ShipForgePage.tsx",
            "desk": None,
            "target_user": "E-commerce businesses",
        },
        "lead_forge": {
            "name": "LeadForge",
            "description": "Lead generation & nurturing — capture, qualification, scoring, follow-ups.",
            "status": "dev",
            "port": None,
            "cc_screen": "LeadForgePage.tsx",
            "desk": "sales",
            "target_user": "Sales teams",
        },
        "contractor_forge": {
            "name": "ContractorForge",
            "description": "Universal SaaS for service businesses — 3 templates: LuxeForge, ElectricForge, LandscapeForge.",
            "status": "dev",
            "port": None,
            "cc_screen": "ContractorForgePage.tsx",
            "desk": "contractors",
            "target_user": "Service business contractors",
        },
        "forge_crm": {
            "name": "ForgeCRM",
            "description": "Customer relationship management — integrated with quotes, invoices, and jobs.",
            "status": "active",
            "port": None,
            "cc_screen": "ForgeCRMPage.tsx",
            "desk": "clients",
            "target_user": "Business owners",
        },
        "llc_factory": {
            "name": "LLCFactory",
            "description": "Business formation & compliance — LLC filing, EIN, registered agent services. Nationwide state requirements documented.",
            "status": "dev",
            "port": None,
            "cc_screen": "LLCFactoryPage.tsx",
            "desk": "legal",
            "target_user": "Entrepreneurs forming LLCs",
        },
        "apost_app": {
            "name": "ApostApp",
            "description": "Document apostille services — authentication for international use.",
            "status": "dev",
            "port": None,
            "cc_screen": "ApostAppPage.tsx",
            "desk": None,
            "target_user": "People needing document apostilles",
        },
        "empire_assist": {
            "name": "EmpireAssist",
            "description": "AI assistant for all Empire products.",
            "status": "dev",
            "port": None,
            "cc_screen": "EmpireAssistPage.tsx",
            "desk": None,
            "target_user": "All Empire users",
        },
        "empire_pay": {
            "name": "EmpirePay",
            "description": "Crypto payments & EMPIRE token integration.",
            "status": "dev",
            "port": None,
            "cc_screen": "EmpirePayPage.tsx",
            "desk": None,
            "target_user": "Crypto-savvy customers",
        },
        "relist_app": {
            "name": "RelistApp",
            "description": "Cross-platform relisting tool — smart lister panel for multi-marketplace posting.",
            "status": "dev",
            "port": 3007,
            "cc_screen": "RelistAppScreen.tsx",
            "desk": None,
            "target_user": "Online sellers",
        },
        "recovery_forge": {
            "name": "RecoveryForge",
            "description": "File recovery tool with AI-powered image classification (Layer 3). Classifies recovered files using LLaVA on Ollama. 18,472 images in current batch.",
            "status": "active",
            "port": 3077,
            "cc_screen": "RecoveryForgeScreen.tsx",
            "desk": None,
            "target_user": "Data recovery users",
        },
        "amp": {
            "name": "AMP (Actitud Mental Positiva)",
            "description": "Portal de la Alegria — Spanish personal development platform. 3 pillars: Mentalidad, Bienestar, Liderazgo. Hybrid Mindvalley + PuraMente + John Maxwell.",
            "status": "dev",
            "port": 3003,
            "url": "studio.empirebox.store/amp",
            "cc_screen": None,
            "features": ["User signup/login", "Mood tracking", "Journal", "Progress tracking"],
            "desk": None,
            "target_user": "Spanish-speaking personal development seekers",
        },
        "vet_forge": {
            "name": "VetForge",
            "description": "Veterinary practice management module.",
            "status": "placeholder",
            "port": None,
            "cc_screen": "VetForgePage.tsx",
            "desk": None,
            "target_user": "Veterinary practices",
        },
        "pet_forge": {
            "name": "PetForge",
            "description": "Pet services management module.",
            "status": "placeholder",
            "port": None,
            "cc_screen": "PetForgePage.tsx",
            "desk": None,
            "target_user": "Pet service businesses",
        },
        "vision_analysis": {
            "name": "Vision Analysis",
            "description": "AI-powered image analysis — measurement estimation, design mockups, fabric analysis using Grok Vision.",
            "status": "active",
            "port": None,
            "cc_screen": "VisionAnalysisPage.tsx",
            "desk": "forge",
            "target_user": "Workroom staff",
        },
        "smart_lister": {
            "name": "Smart Lister",
            "description": "AI-assisted product listing creation panel.",
            "status": "dev",
            "port": None,
            "cc_screen": "SmartListerPanel.tsx",
            "desk": "market",
            "target_user": "Online sellers",
        },
    },

    "desks": {
        "forge": {
            "name": "ForgeDesk (WorkroomForge)",
            "agent_name": "Kai",
            "role": "WorkroomForge operations — quotes, customer follow-up, scheduling, measurements, fabric lookup, pricing",
            "personality": "Professional, detail-oriented, knows drapery/upholstery industry",
            "tools": ["quote_generation", "customer_followup", "scheduling", "measurement_tracking", "fabric_lookup", "pricing_analysis"],
            "preferred_model": None,
            "auto_escalates": "quotes >$5K, new customers, complaints",
        },
        "market": {
            "name": "MarketDesk",
            "agent_name": "Sofia",
            "role": "Marketplace operations — eBay, Facebook listings, inventory sync, pricing, shipping",
            "personality": "Data-driven, detail-oriented, multi-channel expertise",
            "tools": ["listing_creation", "listing_optimization", "inventory_sync", "pricing_analysis", "competitor_watch", "shipping_coordination"],
            "preferred_model": None,
        },
        "marketing": {
            "name": "MarketingDesk",
            "agent_name": "Nova",
            "role": "Social media content creation, post scheduling, campaign management",
            "personality": "Creative, trend-aware, social media savvy",
            "tools": ["content_creation", "post_scheduling", "campaign_management", "hashtag_strategy", "engagement_tracking"],
            "preferred_model": None,
            "platforms": ["Instagram", "Facebook", "Pinterest", "LinkedIn", "Google Business"],
        },
        "support": {
            "name": "SupportDesk",
            "agent_name": "Luna",
            "role": "Customer support — ticket triage, auto-responses, issue resolution, escalation",
            "personality": "Professional, empathetic, solution-oriented",
            "tools": ["ticket_triage", "auto_response", "warranty_claims", "complaint_resolution"],
            "preferred_model": None,
        },
        "sales": {
            "name": "SalesDesk",
            "agent_name": "Aria",
            "role": "Sales pipeline — lead capture, qualification, follow-ups, conversion tracking",
            "personality": "Persuasive, bilingual (English/Spanish), relationship-builder",
            "tools": ["lead_capture", "lead_scoring", "follow_up_automation", "proposal_generation"],
            "preferred_model": None,
        },
        "finance": {
            "name": "FinanceDesk",
            "agent_name": "Sage",
            "role": "Invoices, payment tracking, expense management, P&L reporting",
            "personality": "Precise, analytical, conservative with estimates",
            "tools": ["invoice_creation", "payment_tracking", "expense_logging", "profitability_analysis"],
            "preferred_model": None,
        },
        "clients": {
            "name": "ClientsDesk",
            "agent_name": "Elena",
            "role": "Client relationships — records, addresses, past orders, preferences",
            "personality": "Warm, personable, remembers details",
            "tools": ["client_search", "client_creation", "history_lookup", "preference_tracking"],
            "preferred_model": None,
        },
        "contractors": {
            "name": "ContractorsDesk",
            "agent_name": "Marcus",
            "role": "Contractor/installer relationships — scheduling, pay rates, assignments",
            "personality": "Organized, fair, clear communicator",
            "tools": ["availability_check", "installer_assignment", "pay_rate_tracking", "reliability_scoring"],
            "preferred_model": None,
        },
        "it": {
            "name": "ITDesk",
            "agent_name": "Orion",
            "role": "Systems admin — service health, monitoring, deployment, technical tasks",
            "personality": "Methodical, reliable, security-conscious",
            "tools": ["service_manager", "package_manager", "test_runner", "health_checks", "port_scanning"],
            "preferred_model": None,
        },
        "codeforge": {
            "name": "CodeForge",
            "agent_name": "Atlas",
            "role": "Development operations — code creation, editing, testing, version control",
            "personality": "Precise, methodical — reads before writing, tests after changing",
            "tools": ["file_read", "file_write", "file_edit", "file_append", "git_ops", "test_runner", "project_scaffold"],
            "preferred_model": "claude-opus-4-6",
        },
        "website": {
            "name": "WebsiteDesk",
            "agent_name": "Zara",
            "role": "Website management, SEO, portfolio, online presence",
            "personality": "Brand-aware, content-focused, SEO-savvy",
            "tools": ["content_updates", "seo_optimization", "portfolio_management", "google_business"],
            "preferred_model": None,
        },
        "intake": {
            "name": "Intake Desk",
            "agent_name": "Zara",
            "role": "LuxeForge intake submissions — classifies project type, routes to correct business",
            "personality": "Welcoming, efficient, detail-oriented",
            "tools": ["classify_project", "route_to_business", "send_auto_response", "create_customer_record"],
            "preferred_model": None,
        },
        "legal": {
            "name": "LegalDesk",
            "agent_name": "Raven",
            "role": "Contracts, compliance, insurance, legal documents",
            "personality": "Thorough, cautious, always recommends professional review",
            "tools": ["contract_drafting", "terms_review", "compliance_tracking"],
            "preferred_model": None,
        },
        "analytics": {
            "name": "Analytics Desk",
            "agent_name": "Raven",
            "role": "Business intelligence — daily metrics, weekly reports, revenue forecasting, pipeline analysis",
            "personality": "Data-driven, insightful, trend-spotter",
            "tools": ["daily_metrics", "weekly_report", "revenue_forecast", "pipeline_analysis", "cost_analysis"],
            "preferred_model": "claude-sonnet-4-6",
        },
        "quality": {
            "name": "Quality Desk",
            "agent_name": "Phoenix",
            "role": "AI quality monitoring — accuracy tracking, quality digests, performance alerts",
            "personality": "Critical eye, fair evaluator, improvement-focused",
            "tools": ["quality_check", "accuracy_report", "weekly_digest", "escalate_issues"],
            "preferred_model": "claude-sonnet-4-6",
        },
        "lab": {
            "name": "LabDesk",
            "agent_name": "Phoenix",
            "role": "R&D Lab — testing new AI capabilities, prototyping, experimenting",
            "personality": "Creative, exploratory, nothing affects production",
            "tools": ["experiment_tracking", "prototype_management", "feature_testing"],
            "preferred_model": None,
        },
        "innovation": {
            "name": "InnovationDesk",
            "agent_name": "Spark",
            "role": "Market scanning, competitor monitoring, trend analysis, monetization suggestions",
            "personality": "Proactive, creative, business-minded",
            "tools": ["market_scanning", "competitor_monitoring", "trend_analysis", "monetization_suggestions"],
            "preferred_model": None,
        },
        "costs": {
            "name": "CostTrackerDesk",
            "agent_name": "CostTracker",
            "role": "AI cost monitoring — token usage, per-provider budgets, spending trends",
            "personality": "Budget-conscious, data-driven",
            "tools": ["cost_tracking", "budget_monitoring", "usage_analysis"],
            "preferred_model": None,
        },
    },

    "tools": {
        "search_quotes": {"description": "Search quotes by customer or status", "access_level": 1, "category": "data"},
        "get_quote": {"description": "Get full quote details by ID", "access_level": 1, "category": "data"},
        "search_contacts": {"description": "Search customers, contractors, vendors", "access_level": 1, "category": "data"},
        "create_contact": {"description": "Add a new contact", "access_level": 1, "category": "data"},
        "get_tasks": {"description": "Get real tasks (filter by desk or status)", "access_level": 1, "category": "data"},
        "get_desk_status": {"description": "Get task counts across all desks", "access_level": 1, "category": "data"},
        "create_quick_quote": {"description": "Create quick quote with 3 stacked proposals (Essential/Designer/Premium)", "access_level": 1, "category": "action"},
        "select_proposal": {"description": "Select a design proposal (A/B/C) to finalize a quote", "access_level": 1, "category": "action"},
        "open_quote_builder": {"description": "Open QuoteBuilder inline in dashboard", "access_level": 1, "category": "action"},
        "create_task": {"description": "Create a new task for any desk", "access_level": 1, "category": "action"},
        "run_desk_task": {"description": "Delegate a task to the AI desk system for autonomous handling", "access_level": 1, "category": "action"},
        "send_telegram": {"description": "Send a text message to founder via Telegram", "access_level": 1, "category": "communication"},
        "send_quote_telegram": {"description": "Generate quote PDF and send via Telegram", "access_level": 1, "category": "communication"},
        "send_email": {"description": "Send email with optional attachments", "access_level": 1, "category": "communication"},
        "send_quote_email": {"description": "Generate quote PDF and email to recipient", "access_level": 1, "category": "communication"},
        "web_search": {"description": "Search the web via DuckDuckGo", "access_level": 1, "category": "research"},
        "web_read": {"description": "Fetch and read a web page", "access_level": 1, "category": "research"},
        "search_images": {"description": "Search Unsplash for relevant images", "access_level": 1, "category": "research"},
        "photo_to_quote": {"description": "Create quote from photo analysis + send PDF via Telegram", "access_level": 1, "category": "research"},
        "get_system_stats": {"description": "Real CPU, RAM, disk, temperature", "access_level": 1, "category": "system"},
        "get_weather": {"description": "Live weather data (no API key needed)", "access_level": 1, "category": "system"},
        "get_services_health": {"description": "Check which Empire services are running", "access_level": 1, "category": "system"},
        "present": {"description": "Generate professional presentation/report PDF and send via Telegram", "access_level": 1, "category": "presentation"},
        "shell_execute": {"description": "Execute safe allowlisted shell command", "access_level": 3, "category": "system"},
        "dispatch_to_openclaw": {"description": "Send task to OpenClaw for autonomous execution", "access_level": 3, "category": "autonomous"},
        "file_read": {"description": "Read a file with optional line range", "access_level": 1, "category": "dev"},
        "file_write": {"description": "Write content to a file (with truncation protection)", "access_level": 2, "category": "dev"},
        "file_edit": {"description": "Replace string in file, or append with __APPEND__", "access_level": 2, "category": "dev"},
        "file_append": {"description": "Append content to file (never truncates)", "access_level": 2, "category": "dev"},
        "git_ops": {"description": "Git operations (status, diff, add, commit, push, log)", "access_level": 2, "category": "dev"},
        "service_manager": {"description": "Manage Empire services via systemd (status/restart/logs/start/stop)", "access_level": 1, "category": "dev"},
        "package_manager": {"description": "Install packages or build (pip/npm)", "access_level": 2, "category": "dev"},
        "test_runner": {"description": "Run tests and health checks", "access_level": 1, "category": "dev"},
        "project_scaffold": {"description": "Create new files from templates (router/component/desk/page)", "access_level": 2, "category": "dev"},
    },

    "services": {
        "backend": {"name": "Backend API (FastAPI)", "port": 8000, "systemd": "empire-backend", "type": "systemd", "health_url": "/api/v1/system/stats"},
        "cc": {"name": "Command Center (Next.js)", "port": 3005, "systemd": "empire-cc", "type": "systemd", "health_url": "/"},
        "openclaw": {"name": "OpenClaw AI", "port": 7878, "systemd": "empire-openclaw", "type": "systemd", "health_url": "/health"},
        "ollama": {"name": "Ollama LLM Server", "port": 11434, "systemd": "ollama", "type": "systemd", "health_url": "/api/tags"},
        "recoveryforge": {"name": "RecoveryForge", "port": 3077, "systemd": None, "type": "standalone"},
        "relistapp": {"name": "RelistApp", "port": 3007, "systemd": None, "type": "standalone"},
        "amp": {"name": "AMP (via CC)", "port": 3003, "systemd": None, "type": "standalone"},
        "cloudflare_tunnel": {"name": "Cloudflare Tunnel", "port": None, "systemd": "cloudflared", "type": "systemd", "routes": {"studio.empirebox.store": "localhost:3005", "api.empirebox.store": "localhost:8000"}},
        "telegram_bot": {"name": "Telegram Bot (@Empire_Max_Bot)", "port": None, "systemd": None, "type": "embedded", "note": "Runs inside backend process"},
    },

    "integrations": {
        "xai_grok": {"name": "xAI Grok", "env_var": "XAI_API_KEY", "configured": True, "purpose": "Primary AI provider — chat, vision, TTS (Rex voice)", "model": "grok-3-fast"},
        "anthropic_claude": {"name": "Anthropic Claude", "env_var": "ANTHROPIC_API_KEY", "configured": True, "purpose": "Secondary AI — Sonnet for general, Opus for Atlas coding", "models": ["claude-sonnet-4-6", "claude-opus-4-6"]},
        "groq": {"name": "Groq", "env_var": "GROQ_API_KEY", "configured": True, "purpose": "Fast inference — Llama 3.3 70B + Whisper STT", "model": "llama-3.3-70b-versatile"},
        "telegram": {"name": "Telegram Bot", "env_var": "TELEGRAM_BOT_TOKEN", "configured": True, "purpose": "Founder notifications, quote PDFs, voice messages"},
        "stability_ai": {"name": "Stability AI", "env_var": "STABILITY_API_KEY", "configured": True, "purpose": "Image inpainting for design mockups"},
        "stripe": {"name": "Stripe", "env_var": "STRIPE_SECRET_KEY", "configured": True, "purpose": "Payment processing — test keys active, 3 price tiers configured"},
        "instagram": {"name": "Instagram API", "env_var": "INSTAGRAM_API_TOKEN", "configured": True, "purpose": "Social media posting via Graph API — SocialForge wired"},
        "facebook": {"name": "Facebook Pages", "env_var": "FACEBOOK_PAGE_TOKEN", "configured": True, "purpose": "Social media posting via Graph API — SocialForge wired"},
        "sendgrid": {"name": "SendGrid", "env_var": "SENDGRID_API_KEY", "configured": False, "purpose": "Email sending from workroom@empirebox.store (pending API key)"},
        "brave_search": {"name": "Brave Search", "env_var": "BRAVE_API_KEY", "configured": True, "purpose": "Web search fallback"},
        "openclaw_local": {"name": "OpenClaw", "env_var": "OPENCLAW_GATEWAY_TOKEN", "configured": True, "purpose": "Skills-augmented local AI — autonomous task execution"},
        "ollama_local": {"name": "Ollama", "env_var": None, "configured": True, "purpose": "Local LLM server — LLaVA for image classification"},
        "openai": {"name": "OpenAI", "env_var": "OPENAI_API_KEY", "configured": False, "purpose": "Not used (was for TTS, replaced by Grok TTS)"},
    },

    "databases": {
        "empire.db": {
            "path": "backend/data/empire.db",
            "tables": 16,
            "key_tables": {
                "tasks": {"rows": 139, "purpose": "All desk tasks with status tracking"},
                "task_activity": {"rows": 165, "purpose": "Task history/changelog"},
                "desk_configs": {"rows": 15, "purpose": "AI desk configuration and system prompts"},
                "contacts": {"rows": 0, "purpose": "Contact directory"},
                "customers": {"rows": 113, "purpose": "Customer CRM data"},
                "invoices": {"rows": 9, "purpose": "Invoice records"},
                "payments": {"rows": 2, "purpose": "Payment records"},
                "expenses": {"rows": 6, "purpose": "Expense tracking"},
                "inventory_items": {"rows": 156, "purpose": "Materials/hardware inventory"},
                "vendors": {"rows": 51, "purpose": "Vendor directory"},
                "jobs": {"rows": 4, "purpose": "Job tracking"},
                "max_response_audit": {"rows": 94, "purpose": "AI response quality tracking"},
                "access_users": {"rows": 5, "purpose": "User accounts with roles"},
                "access_sessions": {"rows": 0, "purpose": "Tool authorization sessions"},
                "access_audit": {"rows": 0, "purpose": "Tool execution audit log"},
            },
        },
        "intake.db": {
            "path": "backend/data/intake.db",
            "tables": 2,
            "key_tables": {
                "intake_users": {"rows": 3, "purpose": "LuxeForge portal users"},
                "intake_projects": {"rows": 5, "purpose": "Client project submissions"},
            },
        },
        "brain/memories.db": {
            "path": "backend/data/brain/memories.db",
            "tables": 6,
            "key_tables": {
                "memories": {"rows": 3041, "purpose": "MAX persistent memory entries"},
                "conversation_summaries": {"rows": 99, "purpose": "Chat conversation summaries"},
            },
        },
        "brain/token_usage.db": {
            "path": "backend/data/brain/token_usage.db",
            "tables": 3,
            "key_tables": {
                "token_usage": {"rows": 1049, "purpose": "AI API call cost tracking"},
                "budget_config": {"rows": 1, "purpose": "Monthly budget settings ($50 default)"},
            },
        },
        "tool_audit.db": {
            "path": "backend/data/tool_audit.db",
            "tables": 2,
            "key_tables": {
                "tool_executions": {"rows": 46, "purpose": "Tool execution history"},
            },
        },
        "amp.db": {
            "path": "backend/data/amp.db",
            "tables": 4,
            "key_tables": {
                "amp_users": {"rows": 0, "purpose": "AMP platform users"},
                "amp_moods": {"rows": 0, "purpose": "Mood tracking entries"},
                "amp_journal": {"rows": 0, "purpose": "Journal entries"},
                "amp_progress": {"rows": 0, "purpose": "Progress tracking"},
            },
        },
        "empirebox.db": {
            "path": "backend/data/empirebox.db",
            "tables": 5,
            "key_tables": {
                "sf_customers": {"rows": 0, "purpose": "SupportForge customers"},
                "sf_tickets": {"rows": 0, "purpose": "Support tickets"},
                "sf_kb_articles": {"rows": 0, "purpose": "Knowledge base articles"},
            },
        },
    },

    "api_endpoints": {
        "max": [
            {"method": "POST", "path": "/api/v1/max/chat/stream", "description": "SSE streaming chat with MAX"},
            {"method": "GET", "path": "/api/v1/max/desks", "description": "List all AI desks"},
            {"method": "GET", "path": "/api/v1/max/models", "description": "Available AI models"},
            {"method": "GET", "path": "/api/v1/max/stats", "description": "MAX usage stats"},
            {"method": "POST", "path": "/api/v1/max/ai-desks/tasks", "description": "Submit task to desk system"},
            {"method": "GET", "path": "/api/v1/max/ai-desks/status", "description": "All desk statuses"},
            {"method": "GET", "path": "/api/v1/max/ai-desks/briefing", "description": "Morning briefing report"},
        ],
        "finance": [
            {"method": "GET", "path": "/api/v1/finance/dashboard", "description": "P&L overview"},
            {"method": "GET/POST", "path": "/api/v1/finance/invoices", "description": "List/create invoices"},
            {"method": "POST", "path": "/api/v1/finance/invoices/from-quote/{id}", "description": "Create invoice from quote"},
            {"method": "POST", "path": "/api/v1/finance/payments", "description": "Record payment"},
            {"method": "GET/POST", "path": "/api/v1/finance/expenses", "description": "Track expenses"},
            {"method": "GET", "path": "/api/v1/finance/revenue", "description": "Revenue by period"},
        ],
        "crm": [
            {"method": "GET/POST", "path": "/api/v1/crm/customers", "description": "Customer CRUD"},
            {"method": "POST", "path": "/api/v1/crm/customers/import-from-quotes", "description": "Auto-import from quotes"},
        ],
        "inventory": [
            {"method": "GET/POST", "path": "/api/v1/inventory/items", "description": "Materials tracking"},
            {"method": "GET", "path": "/api/v1/inventory/low-stock", "description": "Low stock alerts"},
            {"method": "GET/POST", "path": "/api/v1/inventory/vendors", "description": "Vendor management"},
        ],
        "costs": [
            {"method": "GET", "path": "/api/v1/costs/stats", "description": "Token usage stats"},
            {"method": "GET", "path": "/api/v1/costs/daily", "description": "Daily cost breakdown"},
            {"method": "GET", "path": "/api/v1/costs/weekly", "description": "Weekly cost breakdown"},
            {"method": "GET", "path": "/api/v1/costs/monthly", "description": "Monthly cost breakdown"},
            {"method": "GET", "path": "/api/v1/costs/by-provider", "description": "Cost by AI provider"},
            {"method": "GET", "path": "/api/v1/costs/by-feature", "description": "Cost by feature"},
            {"method": "GET", "path": "/api/v1/costs/by-business", "description": "Cost by business unit"},
            {"method": "GET", "path": "/api/v1/costs/transactions", "description": "Recent transactions"},
            {"method": "PUT", "path": "/api/v1/costs/budget", "description": "Update budget config"},
            {"method": "GET", "path": "/api/v1/costs/tenant/{id}", "description": "Tenant usage"},
            {"method": "GET", "path": "/api/v1/costs/tenant/{id}/budget", "description": "Tenant budget status"},
        ],
        "system": [
            {"method": "GET", "path": "/api/v1/system/stats", "description": "CPU, RAM, disk, temperature"},
            {"method": "GET", "path": "/api/v1/system/health", "description": "Service health check"},
            {"method": "GET", "path": "/api/v1/system/ollama/status", "description": "Ollama + RecoveryForge status"},
            {"method": "POST", "path": "/api/v1/system/ollama/toggle", "description": "Toggle Ollama on/off"},
        ],
        "socialforge": [
            {"method": "POST", "path": "/api/v1/socialforge/post/instagram", "description": "Post to Instagram"},
            {"method": "POST", "path": "/api/v1/socialforge/post/facebook", "description": "Post to Facebook"},
            {"method": "GET", "path": "/api/v1/socialforge/accounts", "description": "Check connected social accounts"},
        ],
        "other_groups": [
            "quotes", "chats", "files", "docker", "ollama", "notifications",
            "tickets", "customers (supportforge)", "kb", "tasks", "contacts",
            "vision", "social", "intake_auth", "jobs", "shipping",
            "craftforge", "woodcraft", "workroom", "marketplace", "listings",
            "payments", "crypto_payments", "llcfactory", "apostapp", "amp",
            "emails", "webhooks", "users", "auth", "onboarding",
            "recovery_forge", "recovery", "economic", "dev", "accuracy",
        ],
    },

    "ai_models": {
        "routing_chain": ["xAI Grok (primary)", "Claude Sonnet 4.6", "Groq Llama 3.3 70B", "OpenClaw", "Ollama"],
        "models": {
            "grok-3-fast": {"provider": "xAI", "cost_input": 5.00, "cost_output": 15.00, "timeout": 15, "primary": True},
            "claude-sonnet-4-6": {"provider": "Anthropic", "cost_input": 3.00, "cost_output": 15.00, "timeout": 30, "primary": False},
            "claude-opus-4-6": {"provider": "Anthropic", "cost_input": 15.00, "cost_output": 75.00, "timeout": 30, "primary": False, "used_by": "Atlas (CodeForge)"},
            "groq-llama-3.3-70b": {"provider": "Groq", "cost_input": 0.59, "cost_output": 0.79, "timeout": 10, "primary": False},
            "openclaw": {"provider": "Local", "cost_input": 0, "cost_output": 0, "timeout": 30, "primary": False},
            "ollama-llama3.1": {"provider": "Local", "cost_input": 0, "cost_output": 0, "timeout": 30, "primary": False},
        },
        "per_desk_routing": {
            "codeforge": "claude-opus-4-6",
            "analytics": "claude-sonnet-4-6",
            "quality": "claude-sonnet-4-6",
            "default": "grok-3-fast",
        },
    },

    "architecture": {
        "design_decisions": [
            "Single Next.js app (Command Center) replaces 4 separate servers",
            "4 tabs: MAX (gold), Workroom (green), CraftForge (yellow), Platform (blue)",
            "Warm off-white theme (#f5f3ef), gold accents (#b8960c), all buttons 44px+ for tablet",
            "Dual-use rule: RG dogfoods products first, then sells to SaaS subscribers",
            "Iframe rule: external apps (RecoveryForge, RelistApp) embedded via iframe in CC",
            "Desk separation: each desk has its own agent, personality, tools, and optional model preference",
            "AI routing fallback chain: Grok → Claude → Groq → OpenClaw → Ollama",
            "Tool blocks are the ONLY way MAX executes actions — text alone does nothing",
            "File safety: truncation protection, auto-backup, critical file guard for key files",
            "Cost tracking: every AI API call auto-logged with tokens, cost, provider, model",
            "Grok TTS Rex for all voice output ($0.05/min)",
            "Inpainting chain: Pixazo free → Stability free → Grok fallback",
            "LuxeForge free = dumb intake form ($0), paid = designer tools",
            "File naming: Name_YYYY-MM-DD_HHMM.ext",
            "Founder Override Protocol: founder commands execute immediately, no confirmation needed",
        ],
        "tech_stack": {
            "backend": "Python 3.12, FastAPI, SQLite (async), httpx",
            "frontend": "Next.js 14/15, React 18, TypeScript, Tailwind CSS",
            "ai": "xAI Grok, Claude 4.6, Groq, Ollama, OpenClaw",
            "icons": "lucide-react across all apps",
            "database": "SQLite with WAL mode, JSON file storage for chats/quotes",
            "hosting": "Self-hosted on EmpireDell, Cloudflare tunnel for external access",
        },
        "access_control": {
            "level_1": "AUTO — executes immediately (read operations, basic actions)",
            "level_2": "CONFIRM — requires Telegram confirmation (delete, modify, bulk operations)",
            "level_3": "PIN — requires 4-6 digit PIN (shell execute, deploy, erase operations)",
            "roles": ["founder (full access)", "admin (full access)", "manager (L1+L2, no L3)", "operator (L1 + own desk L2)", "viewer (read-only)"],
        },
    },

    "history": {
        "total_commits": 422,
        "key_milestones": [
            {"date": "2026-02", "event": "Empire project started on Beelink EQR5"},
            {"date": "2026-02-24", "event": "System crash from pkill -f — lesson learned"},
            {"date": "2026-03-06", "event": "Migration from ~/Empire/ to ~/empire-repo/, 228 files cleaned"},
            {"date": "2026-03-08", "event": "v4.0 marathon session — 110 files, 21,656 insertions, Command Center born"},
            {"date": "2026-03-09", "event": "PaymentModule, all 17 modules, marathon commit 4a06024 (170 files)"},
            {"date": "2026-03-10", "event": "Cost tracker shipped (11 endpoints), context bridge tools finalized"},
            {"date": "2026-03-14", "event": "Database purge + backup system, access control system"},
            {"date": "2026-03-15", "event": "RecoveryForge Layer 3 started (18,472 images), quality desk, accuracy monitor"},
            {"date": "2026-03-16", "event": "start-empire.sh cleanup, endpoint fixes, full app audit"},
            {"date": "2026-03-17", "event": "Live testing fixes — file safety, 3D avatar, timeouts, port refs, systemd services"},
            {"date": "2026-03-18", "event": "v5.0 Total Knowledge Build — ecosystem catalog, comprehensive report"},
            {"date": "2026-03-18", "event": "v5.0.1 — embedding fix, MAX behavior rules, Ollama toggle, landing pages, SocialForge wired, expanded tools"},
        ],
    },

    "known_issues": [
        "GPU: Quadro K600 with nouveau driver — unstable, needs proprietary driver",
        "CraftForge: full spec + 15 backend endpoints exist, ZERO frontend built",
        "MarketForge, ShipForge: screens exist but limited functionality",
        "AMP: current app 'didn't capture the idea' — needs rebuild to match real vision",
        "contacts table empty (0 rows) — customers table has 113 rows instead",
        "access_audit table empty — audit logging may not be fully wired",
        "OpenAI API key empty — was for TTS, replaced by Grok TTS Rex",
        "3D avatar (TalkingHead) needs live testing to confirm rendering",
        "Ollama: no production models downloaded (only LLaVA for classification)",
        "Some desk agent names duplicated: Zara (website + intake), Raven (legal + analytics), Phoenix (quality + lab)",
        "SendGrid API key needed for email sending from workroom@empirebox.store",
        "Facebook App Secret needed for long-lived social tokens (60 days)",
    ],

    "stats": {
        "total_commits": 422,
        "total_customers": 113,
        "total_inventory_items": 156,
        "total_tasks": 139,
        "active_tasks": None,  # needs live query
        "total_quotes": None,  # stored as JSON files
        "total_invoices": 9,
        "total_payments": 2,
        "total_expenses": 6,
        "total_vendors": 51,
        "total_jobs": 4,
        "total_memories": 3041,
        "total_ai_calls": 1049,
        "total_desks": 18,
        "total_tools": 37,
        "total_products": 22,
        "total_screens": 44,
        "total_api_endpoints": 350,
        "total_databases": 7,
        "total_db_tables": 38,
        "total_intake_users": 3,
        "total_intake_projects": 5,
        "total_access_users": 5,
    },
}


def get_product_info(name: str) -> dict:
    """Look up any product by name (fuzzy match)."""
    name_lower = name.lower().replace(" ", "_").replace("-", "_")
    for key, product in EMPIRE_CATALOG["products"].items():
        if name_lower in key or name_lower in product.get("name", "").lower().replace(" ", "_"):
            return product
    return {"error": f"Product '{name}' not found in catalog"}


def get_desk_info(name: str) -> dict:
    """Look up any desk by name."""
    name_lower = name.lower()
    for key, desk in EMPIRE_CATALOG["desks"].items():
        if name_lower in key or name_lower in desk.get("name", "").lower() or name_lower in desk.get("agent_name", "").lower():
            return desk
    return {"error": f"Desk '{name}' not found in catalog"}


def get_catalog_summary() -> str:
    """Return a formatted summary for the system prompt."""
    stats = EMPIRE_CATALOG["stats"]
    products = EMPIRE_CATALOG["products"]
    desks = EMPIRE_CATALOG.get("desks", {})
    tools = EMPIRE_CATALOG.get("tools", {})
    active = sum(1 for p in products.values() if p.get("status") == "active")
    dev = sum(1 for p in products.values() if p.get("status") == "dev")
    placeholder = sum(1 for p in products.values() if p.get("status") == "placeholder")

    lines = [
        f"Empire Ecosystem: {stats['total_products']} products ({active} active, {dev} dev, {placeholder} placeholder)",
        f"Desks: {stats['total_desks']} | Tools: {stats['total_tools']} | Screens: {stats['total_screens']} | Endpoints: ~{stats['total_api_endpoints']}",
        f"Data: {stats['total_customers']} customers, {stats['total_inventory_items']} inventory, {stats['total_tasks']} tasks, {stats['total_vendors']} vendors",
        "",
        "Active Products:",
    ]
    for key, p in products.items():
        if p.get("status") == "active":
            lines.append(f"  - {p['name']}: {p.get('description', '')[:80]}")
    lines.append("")
    lines.append("In Development:")
    for key, p in products.items():
        if p.get("status") == "dev":
            lines.append(f"  - {p['name']}: {p.get('description', '')[:80]}")

    # Desk roster summary
    lines.append("")
    lines.append("AI Desks (18):")
    for key, d in desks.items():
        agent = d.get("agent_name", "")
        model = d.get("model", "grok")
        lines.append(f"  - {d.get('name', key)} ({agent}) → {model}")

    # Tool categories summary
    lines.append("")
    lines.append("Tool Categories (37 total):")
    for cat_key, cat_data in tools.items():
        if isinstance(cat_data, dict) and "items" in cat_data:
            item_names = [i.get("name", "") for i in cat_data["items"] if isinstance(i, dict)]
            lines.append(f"  - {cat_data.get('name', cat_key)}: {', '.join(item_names[:6])}")
        elif isinstance(cat_data, list):
            item_names = [i.get("name", "") for i in cat_data if isinstance(i, dict)]
            lines.append(f"  - {cat_key}: {', '.join(item_names[:6])}")

    # Recent capabilities (Phase 0 additions)
    lines.append("")
    lines.append("Recent Capabilities (v5.1):")
    lines.append("  - env_get/env_set: Manage .env variables securely")
    lines.append("  - db_query: Read-only SQLite queries on empire.db")
    lines.append("  - file_edit: Fuzzy match + line-number mode")
    lines.append("  - shell_execute: Expanded allowlist (python3, sqlite3, sudo systemctl)")
    lines.append("  - Quote phase pipeline: 6-phase with founder review gates")

    return "\n".join(lines)
