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
    """Generate a structured feature proposal using MiniMax LLM.

    Args:
        prompt: {"id": str, "text": str, "priority": str}

    Returns:
        dict matching proposal schema above
    """
    prompt_text = prompt.get("text", "")
    priority = prompt.get("priority", "medium")
    pid = prompt.get("id", f"p_{int(time.time())}")

    log(f"🧠 Generating proposal via MiniMax for: {prompt_text[:50]}...")

    # Build system prompt with Hermes context
    memory_context = get_memory_context()
    system_msg = f"""{HERMES_CONTEXT}

Recent MAX context:
{memory_context}

User request: {prompt_text}
Priority: {priority}

{PROPOSAL_SCHEMA}"""

    # Call MiniMax via ai_router (primary model is MiniMax)
    messages = [AIMessage(role="user", content=system_msg)]

    content = ""
    try:
        response = await ai_router.chat(
            messages=messages,
            desk="max_orchestrator",  # routes to MiniMax primary
            tenant_id="system",
            source="orchestrator",
        )

        content = response.content.strip()

        # Clean thinking tags
        content = content.replace("", "").replace("<think>", "").replace("", "").strip()

        # Try to find JSON object - handle nested braces
        proposal = None
        import re
        # First try direct JSON parse
        try:
            proposal = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON object with balanced braces
            try:
                brace_start = content.find('{')
                if brace_start >= 0:
                    brace_count = 0
                    for i, c in enumerate(content[brace_start:], start=brace_start):
                        if c == '{':
                            brace_count += 1
                        elif c == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_str = content[brace_start:i+1]
                                proposal = json.loads(json_str)
                                break
            except (json.JSONDecodeError, ValueError):
                pass

        if proposal is None:
            raise ValueError(f"Could not extract JSON from response: {content[:200]}")

        proposal["id"] = pid
        proposal["status"] = "draft"
        log(f"✅ Proposal generated via {response.model_used}: {proposal.get('feature', 'unknown')}")
        return proposal

    except (json.JSONDecodeError, ValueError) as e:
        log(f"⚠️ Failed to parse LLM response: {e}. Response: {content[:200] if content else 'N/A'}")
    except Exception as e:
        log(f"⚠️ LLM call failed: {type(e).__name__}: {e}")

    # Fallback: static proposal
    log(f"⚠️ Using fallback proposal for: {prompt_text[:50]}")
    return {
        "id": pid,
        "feature": prompt_text,
        "priority": priority,
        "impact": "TBD — requires estimation",
        "files_to_modify": [],
        "test_strategy": "Manual testing + CI validation",
        "risk": "Medium",
        "rollback_plan": "git revert to previous commit",
        "status": "draft",
        "fallback": True,
    }

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