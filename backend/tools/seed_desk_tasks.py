"""
Seed each AI desk with 2 actionable research/startup tasks.
Idempotent: skips if seed tasks already exist.
Run: cd ~/Empire/backend && ./venv/bin/python tools/seed_desk_tasks.py
"""
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import get_db
from app.db.init_db import init_database

SEED_TASKS = [
    # ── forge ──
    {"desk": "forge", "priority": "high", "tags": ["pricing", "templates"],
     "title": "Build standard pricing template for top 5 window treatments",
     "description": "Create a reusable pricing template for: pinch pleat drapes, ripplefold drapes, Roman shades, roller shades, and cornices. Include base labor hours, fullness ratios, yardage calcs for common sizes (36x48, 48x60, 72x84), markup formulas. Rates: $50/hr labor, 2x fabric markup, 6% DC tax."},
    {"desk": "forge", "priority": "normal", "tags": ["suppliers", "fabric"],
     "title": "Research DC-area fabric suppliers and build vendor directory",
     "description": "Compile vendor directory: Kravet, Robert Allen, Fabricut, Schumacher, Duralee. Document minimum orders, lead times, return policies, local showroom locations (DC Design Center), online ordering, designer discount requirements."},

    # ── market ──
    {"desk": "market", "priority": "normal", "tags": ["ebay", "remnants"],
     "title": "Research eBay listing strategy for custom fabric remnants",
     "description": "Analyze how drapery workrooms sell fabric remnants on eBay. Research best categories, pricing for 1-5 yard remnant bolts, shipping strategies, photo requirements, keyword optimization. Study top sellers in 'designer fabric remnants'."},
    {"desk": "market", "priority": "normal", "tags": ["facebook", "marketplace"],
     "title": "Audit Facebook Marketplace for local drapery/upholstery demand",
     "description": "Survey FB Marketplace in DC/MD/VA for custom window treatment and upholstery demand. Identify common searches, competitor pricing, popular treatment types, whether to list services or finished products."},

    # ── marketing ──
    {"desk": "marketing", "priority": "high", "tags": ["instagram", "content-calendar"],
     "title": "Draft 4-week Instagram content calendar for spring launch",
     "description": "Create 4-week Instagram calendar (3 posts/week, 12 total) for DC homeowners and designers. Week 1: behind-the-scenes. Week 2: treatment types. Week 3: before/after. Week 4: spring refresh tips. Include caption templates, hashtag sets (#customdrapes #dcinteriordesign), best posting times."},
    {"desk": "marketing", "priority": "normal", "tags": ["pinterest", "social-media"],
     "title": "Research Pinterest strategy for custom window treatment business",
     "description": "Research Pinterest business account setup for 'custom window treatments DC'. Board structure (by room, by treatment), pin dimensions, keyword strategy, 10 trending pins to model after."},

    # ── support ──
    {"desk": "support", "priority": "high", "tags": ["faq", "auto-response"],
     "title": "Build FAQ and auto-response library for common service questions",
     "description": "Create FAQ covering top 15 questions: order timeline, deposit policy, washing drapes, motorized shade operation, hem issues, warranty, commercial work, service area, consultations, own fabric. Build auto-response templates with Empire-specific details (50% deposit, 1-year warranty, DC metro area)."},
    {"desk": "support", "priority": "normal", "tags": ["warranty", "policy"],
     "title": "Design warranty policy and service-level commitments",
     "description": "Draft warranty and service policy: workmanship warranty (1 year), fabric warranty (per manufacturer ~3 years), hardware warranty (Somfy 5 years, standard 2 years), 24hr support response, 48hr service scheduling, callbacks/remake policy. Research DC luxury market competitors."},

    # ── sales ──
    {"desk": "sales", "priority": "high", "tags": ["lead-scoring", "strategy"],
     "title": "Build lead scoring criteria specific to DC drapery market",
     "description": "Define scoring weights: lead source (designer referral=highest, Yelp=medium, cold social=lowest), property type, project scope (whole house vs single room), budget signals, urgency, geography (Georgetown/Capitol Hill premium). Set qualification threshold at 30/100."},
    {"desk": "sales", "priority": "high", "tags": ["consultation", "templates"],
     "title": "Create consultation checklist and follow-up email templates",
     "description": "Standardized in-home consultation: pre-visit prep, during-visit checklist (measure windows, photograph, discuss style, note light/privacy, identify hardware), post-visit sequence (same-day thank you, 3-day quote, 7-day follow-up). Draft email templates in English and Spanish."},

    # ── finance ──
    {"desk": "finance", "priority": "high", "tags": ["accounting", "setup"],
     "title": "Set up chart of accounts and expense categories for drapery business",
     "description": "Define categories. Revenue: custom drapery, Roman shades, roller shades, cornices, upholstery, consultation fees, rush charges. Expenses: fabric, lining, hardware, thread/notions, contractor labor, vehicle, insurance, software, marketing, rent. Target margins per category (material 2x = 50%, labor goal 60%)."},
    {"desk": "finance", "priority": "normal", "tags": ["taxes", "compliance"],
     "title": "Research DC business tax obligations and quarterly filing schedule",
     "description": "Compile: DC sales tax (6%), taxability rules for fabrication vs installation labor, quarterly estimated tax deadlines, DC franchise tax ($250 min), federal quarterly payments, 1099 requirements for contractor payments >$600. Create quarterly compliance calendar for 2026."},

    # ── clients ──
    {"desk": "clients", "priority": "high", "tags": ["crm", "intake-form"],
     "title": "Design client intake form and CRM data structure",
     "description": "Define CRM fields. Required: name, phone, email, address, source, project type, budget. Optional: interior designer, HOA restrictions, pets (fabric recs), children (durability), style preference (modern/traditional/transitional), color palette. Design one-page intake form for consultations."},
    {"desk": "clients", "priority": "normal", "tags": ["crm", "best-practices"],
     "title": "Research CRM best practices for high-touch residential service businesses",
     "description": "Research CRM strategies from luxury home service businesses (designers, builders, landscape architects) in DC. Follow-up frequency, re-engagement triggers (12 months post-install, seasonal), referral chain tracking, repeat business prediction, client segmentation."},

    # ── contractors ──
    {"desk": "contractors", "priority": "high", "tags": ["onboarding", "installers"],
     "title": "Build installer vetting checklist and onboarding process",
     "description": "Vetting: verify insurance ($1M GL min), 3 references, skills assessment (motorization, heavy drapery, commercial), background check, vehicle/tools inventory. Onboarding: pay rate agreement, scheduling access, quality standards, photo documentation requirements, customer interaction guidelines. Research DMV installer pay rates."},
    {"desk": "contractors", "priority": "normal", "tags": ["motorization", "certification"],
     "title": "Research motorization certification requirements (Somfy, Lutron)",
     "description": "Research Somfy and Lutron certification: training programs, costs, duration, required tools, per-installer vs per-business, typical markup for motorized vs manual. Also research Hunter Douglas PowerView and Rollease Acmeda. Prioritize certifications for Empire."},

    # ── it ──
    {"desk": "it", "priority": "high", "tags": ["health-check", "audit"],
     "title": "Run full Empire service health audit and document architecture",
     "description": "Audit all services: Backend (8000), Homepage (8080), Dashboard (3009), WorkroomForge (3001), LuxeForge (3002), Empire App (3000), OpenClaw (7878), Ollama (11434). Document status, RAM usage, error patterns. Create architecture diagram. Verify backup status (Google Drive rclone)."},
    {"desk": "it", "priority": "normal", "tags": ["monitoring", "backups"],
     "title": "Set up automated daily backup verification and disk space monitoring",
     "description": "Design monitoring: daily backup verification (rclone sync confirmation), disk space alert (80% NVMe), RAM tracking (80% threshold), service uptime for all ports. Lightweight cron-based with Telegram alerts. Avoid heavy tools that strain the Mini PC."},

    # ── website ──
    {"desk": "website", "priority": "high", "tags": ["seo", "local-search"],
     "title": "Research local SEO strategy for 'custom drapes Washington DC'",
     "description": "Top 20 keyword targets with search volume, Google Business Profile optimization, local citation directories (Yelp, Houzz, Angi, Thumbtack, BBB), review generation strategy (20+ Google reviews target), blog content topics. Analyze top 3 competitors in Google local pack."},
    {"desk": "website", "priority": "normal", "tags": ["copywriting", "homepage"],
     "title": "Draft homepage copy and meta descriptions for Empire web presence",
     "description": "Write homepage: hero headline/subhead, services overview (custom drapery, Roman shades, motorized, upholstery), about section, service area (DC/MD/VA), CTA (free consultation). Meta title <60 chars, meta description <160 chars for 'custom window treatments Washington DC'. OpenGraph descriptions."},

    # ── legal ──
    {"desk": "legal", "priority": "high", "tags": ["contract", "template"],
     "title": "Draft standard client contract for custom window treatment orders",
     "description": "Template covering: scope of work, pricing/payment (50% deposit, balance at install), timeline estimates (4-6 weeks typical), cancellation policy, change order process, warranty (1 year workmanship), liability limitations, dispute resolution. Include signature blocks. Mark as DRAFT — needs legal review."},
    {"desk": "legal", "priority": "high", "tags": ["licensing", "compliance"],
     "title": "Research DC business license and home improvement contractor requirements",
     "description": "DC basic business license, DC home improvement contractor license (if needed for installation), VA and MD equivalent requirements, insurance minimums, bonding requirements, HOA/condo restrictions for window treatment installations. Create compliance checklist with renewal dates."},

    # ── lab ──
    {"desk": "lab", "priority": "high", "tags": ["ai-vision", "experiment"],
     "title": "Prototype AI-powered window measurement from phone photos",
     "description": "Test xAI Vision for estimating window dimensions from phone photos. Plan: 10 photos of known-size windows from 6-8 feet, include reference objects, send to xAI Vision with measurement prompt, compare to actual measurements. Track accuracy within 0.5 inch. ForgeDesk already has AI vision endpoints."},
    {"desk": "lab", "priority": "normal", "tags": ["automation", "workflows"],
     "title": "Brainstorm automation workflows for the 12-desk system",
     "description": "Map ideal inter-desk flows: (1) Sales lead → client record → consultation schedule. (2) Quote approved → invoice → fabric order → installer assignment. (3) Installation complete → satisfaction survey → review request → thank-you note. Document as sequence diagrams with triggers and data passed."},
]


def seed():
    init_database()
    with get_db() as conn:
        existing = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE metadata LIKE '%\"seed\": true%'"
        ).fetchone()[0]
        if existing > 0:
            print(f"Seed tasks already exist ({existing}). Skipping. Use --force to re-seed.")
            if "--force" not in sys.argv:
                return 0
            conn.execute("DELETE FROM tasks WHERE metadata LIKE '%\"seed\": true%'")
            conn.commit()
            print(f"Deleted {existing} existing seed tasks.")

        for task in SEED_TASKS:
            conn.execute(
                """INSERT INTO tasks (title, description, status, priority, desk, assigned_to, created_by, tags, metadata)
                   VALUES (?, ?, 'todo', ?, ?, 'MAX', 'system', ?, ?)""",
                (
                    task["title"],
                    task["description"],
                    task["priority"],
                    task["desk"],
                    json.dumps(task.get("tags", [])),
                    json.dumps({"seed": True, "category": "research"}),
                )
            )
        conn.commit()
        print(f"Seeded {len(SEED_TASKS)} tasks across 12 desks.")
        return len(SEED_TASKS)


if __name__ == "__main__":
    seed()
