"""MAX Orchestrator — Autonomous feature proposal generator."""
import asyncio, json, os, time, sys, traceback
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
    from app.services.max.ai_router import ai_router
    from app.services.max.brain.memory_store import MemoryStore
    import json, re

    pid = prompt.get("id") or f"p_{int(time.time())}"
    prompt_text = prompt.get("text", "Unknown prompt")
    priority = prompt.get("priority", "medium")

    # Safe fallback — all required keys present
    fallback = {
        "id": pid,
        "feature": prompt_text,
        "priority": priority,
        "impact": "TBD",
        "files_to_modify": ["~/empire-repo-v10/staging_only"],
        "test_strategy": "pytest + Playwright",
        "risk": "Medium",
        "rollback_plan": "Revert commit & restore backup",
        "status": "draft",
    }

    try:
        mems = hermes.search_memories("preferences past_decisions business_metrics EmpireBox", limit=5)
        ctx = "; ".join([f"{m.get('subject','')}: {m.get('content','')[:100]}" for m in mems]) if mems else "desktop-first, L2/L3 gates, 113 customers"
    except Exception:
        ctx = "desktop-first, L2/L3 gates, 113 customers"

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
            f"User request: {prompt_text}"
        )

        resp = await ai_router.chat(messages=[AIMessage(role="system", content=sys_msg), AIMessage(role="user", content=prompt_text)])
        resp_text = resp.content if hasattr(resp, 'content') else str(resp)

        match = re.search(r'START_JSON\s*(.*?)\s*END_JSON', resp_text, re.DOTALL)
        if not match:
            match = re.search(r'\{.*\}', resp_text, re.DOTALL)
        if not match:
            raise ValueError(f"No JSON found in response: {resp_text[:100]}")

        data = json.loads(match.group(1 if match.lastindex else 0))
        for k, v in fallback.items():
            data.setdefault(k, v)
        data["id"] = pid

        if not data.get("feature"):
            log(f"⚠️ LLM missing 'feature', using prompt text")
            data["feature"] = prompt_text

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
                try:
                    pid = p.get("id") or f"p_{int(time.time())}"
                    prompt_text = p.get("text", "")
                    priority = p.get("priority", "medium")
                    proposal = None  # Ensure exists in except scope

                    log(f"📥 Processing prompt: {pid}: {prompt_text[:50]}...")

                    proposal = await generate_proposal({
                        "id": pid,
                        "text": prompt_text,
                        "priority": priority
                    })
                    log(f"🔍 DEBUG: proposal type={type(proposal)} keys={list(proposal.keys()) if isinstance(proposal, dict) else 'NOT_DICT'}")

                    # Validate required keys
                    if not isinstance(proposal, dict):
                        log(f"⚠️ Proposal {pid} is not a dict: {type(proposal)}. Using fallback.")
                        proposal = {"id": pid, "feature": prompt_text, "priority": priority, "impact": "TBD", "files_to_modify": [], "test_strategy": "pytest", "risk": "Medium", "rollback_plan": "git revert", "status": "draft"}
                    elif not proposal.get("feature"):
                        log(f"⚠️ Proposal {pid} missing 'feature'. Using fallback.")
                        proposal["feature"] = prompt_text

                    safe_proposal = {"id": pid, "status": "draft", **proposal}
                    save_proposal(pid, safe_proposal)
                    log(f"💾 Proposal saved: {proposal.get('feature', 'unknown')}")

                    mark_done(pid)

                    for _ in range(2880):
                        app = check_approval(pid)
                        if app == "approved":
                            log(f"✅ PROPOSAL APPROVED: {proposal.get('feature')}")
                            break
                        if app and app != "approved":
                            log(f"❌ PROPOSAL {app.upper()}: {proposal.get('feature')}")
                            break
                        await asyncio.sleep(10)
                except (KeyError, AttributeError, TypeError) as e:
                    log(f"⚠️ Processing error {type(e).__name__}: {e} | pid={pid} | proposal_type={type(proposal)} | trace={traceback.format_exc()[-150:]}")
                    continue
                except Exception as e:
                    log(f"⚠️ Processing error: {e} | pid={pid} | trace={traceback.format_exc()[-150:]}")
                    continue
        except Exception as e:
            log(f"⚠️ Orchestrator error: {e} — {traceback.format_exc()[-200:]}")
            await asyncio.sleep(5)
        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())