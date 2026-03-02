#!/usr/bin/env python3
"""
Seed MAX's Brain with foundational knowledge.
Run once to populate the external drive memory database.

Usage: python3 ~/Empire/scripts/seed_brain.py
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.services.max.brain.memory_store import MemoryStore
from app.services.max.brain.brain_config import get_brain_path, get_db_path

def seed():
    brain_path = get_brain_path()
    db_path = get_db_path()
    print(f"Brain path: {brain_path}")
    print(f"Database:   {db_path}")

    store = MemoryStore(db_path)

    # Check if already seeded
    existing = store.count()
    if existing > 0:
        print(f"\nBrain already has {existing} memories.")
        resp = input("Re-seed? This adds without duplicating. (y/N): ").strip().lower()
        if resp != "y":
            print("Skipping seed.")
            return

    print("\nSeeding foundational knowledge...\n")
    count = 0

    # ── Founder Profile ──────────────────────────────────────────
    founder_memories = [
        ("The founder's name is RG. He runs Empire Box and all its businesses.", 10),
        ("RG prefers direct, no-BS communication. Show options, not just one answer.", 9),
        ("RG is based in the Washington, DC area.", 8),
        ("RG wants to delegate operations to AI desks and supervise from the Command Center.", 9),
        ("RG's priority order: WorkroomForge (revenue), CraftForge (product), SocialForge (growth), AMP (paused).", 8),
        ("RG speaks English and Spanish fluently.", 7),
        ("RG's hardware: AZW EQ Mini PC (Beelink) with AMD Ryzen 7 5825U, 27GB RAM, Ubuntu 24.", 7),
        ("CRITICAL: Never run sensors-detect on this machine — it crashes the system.", 10),
        ("CRITICAL: Never use pkill -f with broad patterns — caused a system crash on Feb 24, 2026.", 10),
    ]
    for content, importance in founder_memories:
        store.add_memory(
            category="founder",
            content=content,
            subject="RG",
            importance=importance,
            source="seed",
            tags=["founder", "profile"],
        )
        count += 1
    print(f"  Founder profile: {len(founder_memories)} memories")

    # ── Business Knowledge ───────────────────────────────────────
    business_memories = [
        ("WorkroomForge does custom window treatments in the DC area: drapes, shades, cornices, valances, bedding, upholstery.", "overview", 10),
        ("Standard markup on fabric is 2x wholesale. Labor rate is $50/hr.", "pricing", 9),
        ("Standard terms: 50% deposit at approval, balance at installation. Net 30 for commercial.", "terms", 9),
        ("Primary fabric suppliers: Kravet, Robert Allen, Fabricut, Schumacher, Duralee.", "suppliers", 8),
        ("Tax rate for DC is 6%.", "pricing", 9),
        ("CNC machine: Inventables X-Carve. 3D Printer: Elegoo Saturn (large format resin).", "equipment", 7),
        ("WorkroomForge port: 3001. LuxeForge port: 3002. Founder Dashboard port: 3009.", "tech", 7),
        ("FastAPI backend runs on port 8000. All routes under /api/v1/.", "tech", 8),
        ("AI routing priority: xAI Grok (primary) -> Claude (fallback) -> Ollama (local).", "tech", 8),
    ]
    for content, subcat, importance in business_memories:
        store.add_memory(
            category="business",
            subcategory=subcat,
            content=content,
            subject="WorkroomForge" if "WorkroomForge" in content or "fabric" in content.lower() else "Empire",
            importance=importance,
            source="seed",
            tags=["business", subcat],
        )
        count += 1
    print(f"  Business knowledge: {len(business_memories)} memories")

    # ── Knowledge Base entries ───────────────────────────────────
    knowledge_entries = [
        ("workroomforge", "pricing", "fabric_markup", "2x wholesale cost"),
        ("workroomforge", "pricing", "labor_rate", "$50/hr"),
        ("workroomforge", "pricing", "dc_tax_rate", "6%"),
        ("workroomforge", "terms", "residential_deposit", "50% at approval, balance at installation"),
        ("workroomforge", "terms", "commercial_terms", "Net 30"),
        ("workroomforge", "supplier", "primary_suppliers", "Kravet, Robert Allen, Fabricut, Schumacher, Duralee"),
        ("workroomforge", "procedure", "quote_workflow", "Measure -> Select fabric -> Calculate yardage -> Price labor -> Add tax -> Present quote"),
        ("empire", "tech", "backend_port", "8000"),
        ("empire", "tech", "frontend_port", "3009"),
        ("empire", "tech", "ai_priority", "Grok -> Claude -> Ollama"),
    ]
    for business, category, key, value in knowledge_entries:
        store.add_knowledge(business, category, key, value, source="seed")
        count += 1
    print(f"  Knowledge base: {len(knowledge_entries)} entries")

    # ── Empire Tech Stack ────────────────────────────────────────
    tech_memories = [
        ("Empire ecosystem: FastAPI backend + Next.js 14 frontend apps.", "tech", 8),
        ("Key ports: Backend 8000, Homepage 8080, Empire App 3000, WorkroomForge 3001, LuxeForge 3002, Founder Dashboard 3009.", "tech", 8),
        ("Empire uses Tailwind CSS with custom design system: --gold (#D4AF37), --purple (#8B5CF6), --void (#05050d).", "design", 7),
        ("All icons use lucide-react across every app.", "design", 6),
        ("Fonts: Outfit (UI text) + JetBrains Mono (code).", "design", 6),
        ("MAX Brain runs on Ollama (Mistral 7B for reasoning, nomic-embed-text for embeddings) stored on BACKUP11 external drive.", "tech", 9),
    ]
    for content, subcat, importance in tech_memories:
        store.add_memory(
            category="business",
            subcategory=subcat,
            content=content,
            subject="Empire",
            importance=importance,
            source="seed",
            tags=["tech", "empire"],
        )
        count += 1
    print(f"  Tech stack: {len(tech_memories)} memories")

    # ── Operational State ────────────────────────────────────────
    ops_memories = [
        ("Current active products: WorkroomForge (live), LuxeForge (live), CraftForge (in development).", 8),
        ("Planned products: ContractorForge, SupportForge, SocialForge, MarketForge, AMP (paused).", 6),
        ("MAX Response Canvas v2 completed — 3 phases: charts/media/comms all built.", 7),
    ]
    for content, importance in ops_memories:
        store.add_memory(
            category="operational",
            content=content,
            importance=importance,
            source="seed",
            tags=["operational", "status"],
        )
        count += 1
    print(f"  Operational state: {len(ops_memories)} memories")

    # ── Summary ──────────────────────────────────────────────────
    total = store.count()
    print(f"\n{'='*50}")
    print(f"  MAX Brain seeded successfully!")
    print(f"  Total memories in DB: {total}")
    print(f"  New memories added: {count}")
    print(f"  Database: {db_path}")
    print(f"{'='*50}")


if __name__ == "__main__":
    seed()
