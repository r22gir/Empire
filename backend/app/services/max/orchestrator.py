"""MAX Orchestrator — Autonomous feature proposal generator."""
import asyncio, json, os, time, sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from app.services.max.queue import get_pending, mark_done, save_proposal, check_approval
from app.services.max.ai_router import AIMessage, ai_router
from app.services.max.brain.memory_store import MemoryStore

LOG = Path(os.path.expanduser("~/empire-repo-v10/backend/data/max/max.log"))
PROPOSALS_DIR = Path(os.path.expanduser("~/empire-repo-v10/backend/data/max/proposals"))

def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}\n"
    print(f"[{ts}] {msg}")
    LOG.open("a").write(line)

# ── Hermes Context ──────────────────────────────────────────────────────────────
HERMES_CONTEXT = """You are MAX, the AI Orchestrator for EmpireBox.
EmpireBox is an AI-powered business automation platform with these components:
- Backend: FastAPI on ports 8000 (stable) / 8010 (v10)
- Frontend: Next.js Command Center on ports 3005 (stable) / 3010 (v10)
- AI Routing: MiniMax (primary) → Claude → Groq → OpenClaw → Ollama
- Services: Telegram bot, Cloudflare tunnel, OpenClaw worker, Ollama

Business metrics:
- 113 customers across Workroom (drapery), WoodCraft (CNC), LuxeForge (intake)
- Stripe MRR tracking active
- L3 PIN for production deploys: 7777

User preferences:
- Desktop-first, mobile-responsive UI required
- Founder-gated approvals: CONFIRM DIFF → [APPROVE] before any code write
- ALWAYS stage in ~/empire-repo-v10 before touching production
- Never fabricate business data — always look up real info

Your task: Generate structured feature proposals in JSON format.
"""

PROPOSAL_SCHEMA = """Output a valid JSON object with this exact structure:
{
  "feature": "short feature name",
  "priority": "high|medium|low",
  "impact": "quantified impact (e.g. 'MRR +$50/mo' or 'Save 2hrs/day')",
  "files_to_modify": ["path1", "path2"],
  "test_strategy": "how to validate this feature works",
  "risk": "Low|Medium|High",
  "rollback_plan": "how to undo if it breaks"
}
Only output the JSON — no markdown, no explanation."""

def get_memory_context() -> str:
    """Query Hermes for relevant memories: past decisions, preferences, business state."""
    try:
        store = MemoryStore()
        memories = store.get_recent(category=None, limit=10)
        if not memories:
            memories = store.get_recent(category=None, limit=5)
        context_parts = []
        for m in memories:
            context_parts.append(f"- {m.get('subject', 'unknown')}: {m.get('content', '')[:200]}")
        return "\n".join(context_parts) if context_parts else "No prior context available."
    except Exception as e:
        return f"(Memory unavailable: {e})"

async def generate_proposal(prompt: dict) -> dict:
    from app.lib.ai_router import ai_router
    from app.services.hermes.memory_store import MemoryStore
    import json, re
    fallback = {"id": prompt["id"], "feature": prompt["text"], "priority": prompt.get("priority", "medium"), "impact": "TBD", "files_to_modify": ["~/empire-repo-v10/staging_only"], "test_strategy": "pytest + Playwright", "risk": "Medium", "rollback_plan": "Revert commit & restore backup", "status": "draft"}
    try:
        hermes = MemoryStore()
        ctx = hermes.get_context("preferences,past_decisions,business_metrics") if hasattr(hermes, "get_context") else "desktop-first, L2/L3 gates, 113 customers"

        # MiniMax-friendly: external schema string, START_JSON/END_JSON delimiters
        schema = '{"feature":"string","priority":"high|medium|low","impact":"string","files_to_modify":["string"],"test_strategy":"string","risk":"Low|Medium|High","rollback_plan":"string"}'
        sys_msg = (
            f"You are MAX, EmpireBox's AI orchestrator.\n"
            f"Output ONLY a single JSON object matching this schema:\n{schema}\n"
            f"Rules:\n"
            f"1. Wrap output EXACTLY in START_JSON and END_JSON tags\n"
            f"2. ALL file paths MUST start with ~/empire-repo-v10/\n"
            f"3. NEVER mention ~/empire-repo/ (production)\n"
            f"4. If unsure, use empty array for files_to_modify\n"
            f"Context: {ctx}\n"
            f"User request: {prompt['text']}"
        )

        resp = await ai_router.chat(messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt["text"]}])

        # Parse: first try START_JSON...END_JSON, then fallback to raw regex
        match = re.search(r'START_JSON\s*(.*?)\s*END_JSON', resp, re.DOTALL)
        if not match:
            match = re.search(r'\{.*\}', resp, re.DOTALL)
        if not match:
            raise ValueError(f"No JSON found in response: {resp[:100]}")

        data = json.loads(match.group(1 if match.lastindex else 0))
        for k, v in fallback.items():
            data.setdefault(k, v)
        data["id"], data["status"] = prompt["id"], "draft"

        # Safety: block any prod paths
        if any("empire-repo/" in f and "empire-repo-v10/" not in f for f in data.get("files_to_modify", [])):
            raise ValueError("PROD_PATH_BLOCKED")

        log(f"✅ Proposal generated: {data.get('feature', 'unknown')}")
        return data
    except Exception as e:
        log(f"⚠️ LLM failed: {e}. Fallback used.")
        return fallback
async def main():
    log("🤖 MAX orchestrator started")
    while True:
        try:
            for p in get_pending():
                pid = p.get("id") or f"p_{int(time.time())}"
                prompt_text = p.get("text", "")
                priority = p.get("priority", "medium")

                log(f"📥 Processing prompt: {pid}: {prompt_text[:50]}...")

                # Generate proposal with LLM (MiniMax primary)
                proposal = await generate_proposal({
                    "id": pid,
                    "text": prompt_text,
                    "priority": priority
                })

                # Save proposal
                save_proposal(pid, proposal)
                log(f"💾 Proposal saved: {proposal.get('feature', 'unknown')}")

                # Mark prompt as processed
                mark_done(pid)

                # Wait for approval (poll every 10s, up to 8 hours)
                for _ in range(2880):
                    app = check_approval(pid)
                    if app == "approved":
                        log(f"✅ PROPOSAL APPROVED: {proposal.get('feature')}")
                        break
                    if app and app != "approved":
                        log(f"❌ PROPOSAL {app.upper()}: {proposal.get('feature')}")
                        break
                    await asyncio.sleep(10)
        except Exception as e:
            import traceback
            log(f"⚠️ Orchestrator error: {e} — {traceback.format_exc()[-200:]}")
            await asyncio.sleep(5)
        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())