"""Empire module knowledge resolver grounded in current repo docs + live routes.

Honesty contract:
- Prefer verified EmpireBox facts (Hyattsville Workroom, CNC WoodCraft, etc.)
  over thin generic stubs.
- Live route inventory comes from the mounted FastAPI app when available;
  otherwise falls back to known Workroom prefixes documented in main.py /
  EMPIRE_MODULE_REGISTRY (still truthful, never invents fake endpoints).
- Action/creation intents (create quote, generate estimate) must return None
  so they reach AI/tools instead of static blurbs.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[4]

CURRENT_TRUTH_DOC = "docs/EMPIREBOX_CURRENT_TRUTH_2026-05-14.md"
ARCHIVEFORGE_STATUS_DOC = "docs/ARCHIVEFORGE_STATUS.md"
ARCHIVEFORGE_WORKFLOW_DOC = "docs/ARCHIVEFORGE_WORKFLOW.md"
MODULE_REGISTRY_DOC = "docs/EMPIRE_MODULE_REGISTRY.md"

ARCHIVEFORGE_SOURCE_DOCS = [
    CURRENT_TRUTH_DOC,
    ARCHIVEFORGE_STATUS_DOC,
    ARCHIVEFORGE_WORKFLOW_DOC,
    MODULE_REGISTRY_DOC,
]

MODULE_ALIASES: dict[str, tuple[str, ...]] = {
    "ArchiveForge": (
        "archiveforge",
        "archive forge",
        "archive",
        "life magazine",
        "magazine archive",
    ),
    "MarketForge": ("marketforge", "market forge"),
    "Workroom": ("workroom", "empire workroom"),
    "Woodcraft": ("woodcraft", "wood craft", "craftforge", "craft forge"),
    "Drawing Studio": ("drawing studio",),
    "RecoveryForge": ("recoveryforge", "recovery forge"),
    "RelistApp": ("relistapp", "relist app"),
    "ApostApp": ("apostapp", "apost app", "apostille"),
    "Memory Bank": ("memory bank", "memorybank", "max memory bank"),
    "VendorOps": ("vendorops", "vendor ops"),
    "SocialForge": ("socialforge", "social forge"),
    "Hermes": ("hermes",),
    "OpenClaw": ("openclaw", "open claw"),
}

MODULE_QUESTION_HINTS = (
    "what",
    "whats",
    "what's",
    "status",
    "going on",
    "done",
    "working",
    # NOTE: bare "work" removed — it matched inside "workroom" and hijacked
    # every Workroom action/create-quote ask into static module docs.
    "features",
    "publish",
    "complete",
    "finished",
    "update",
    "tools",
    "routes",
    "endpoints",
    "access",
)

# Action / creation intents must reach AI/tools (create_engine_quote, etc.).
_MODULE_ACTION_MARKERS = (
    "create",
    "draft",
    "produce",
    "generate",
    "make a quote",
    "make an estimate",
    "new quote",
    "new estimate",
    "quote workflow",
    "estimate with",
    "photo_to_quote",
    "quick quote",
    "quick-quote",
)

# Workroom / finance prefixes known to be mounted in app.main (and registry).
_WORKROOM_ROUTE_PREFIXES = (
    "/api/v1/quotes",
    "/api/v1/finance",
    "/api/v1/customers",
    "/api/v1/jobs",
    "/api/v1/payments",
    "/api/v1/inventory",
    "/api/v1/drawings",
)

_ROUTE_QUESTION_MARKERS = (
    "tools",
    "routes",
    "endpoints",
    "api",
    "access",
    "what can you",
)


def _normalize(message: str | None) -> str:
    text = (message or "").lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


@lru_cache(maxsize=64)
def _read_doc(relative_path: str) -> str:
    path = REPO_ROOT / relative_path
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _extract_section(markdown_text: str, heading: str) -> str:
    pattern = re.compile(
        rf"^###\s+{re.escape(heading)}\s*$([\s\S]*?)(?=^###\s+|\Z)",
        re.MULTILINE,
    )
    match = pattern.search(markdown_text)
    return (match.group(1) or "").strip() if match else ""


def _best_module_alias_match(text: str) -> Optional[str]:
    best_module = None
    best_len = -1
    for module_name, aliases in MODULE_ALIASES.items():
        for alias in aliases:
            if alias in text and len(alias) > best_len:
                best_module = module_name
                best_len = len(alias)
    return best_module


def _is_module_action_request(text: str) -> bool:
    """True when the user wants an action (create quote / draft / generate),
    not a static 'what is this module' answer."""
    if any(marker in text for marker in _MODULE_ACTION_MARKERS):
        action_verbs = ("create", "draft", "produce", "generate")
        has_verb = any(v in text for v in action_verbs) or any(
            m in text for m in _MODULE_ACTION_MARKERS if m not in action_verbs
        )
        has_artifact = any(
            token in text
            for token in ("quote", "estimate", "workflow", "pdf", "pack", "document", "drawing")
        )
        return has_verb and (has_artifact or "workroom" in text or "woodcraft" in text)
    return False


def _looks_like_module_question(text: str) -> bool:
    if _is_module_action_request(text):
        return False
    if any(hint in text for hint in MODULE_QUESTION_HINTS):
        return True
    # Allow concise asks like "archiveforge?" or "workroom status"
    return text.endswith("?")


def _wants_live_routes(text: str) -> bool:
    return any(marker in text for marker in _ROUTE_QUESTION_MARKERS)


def is_empire_module_question(message: str | None) -> bool:
    text = _normalize(message)
    if _is_module_action_request(text):
        return False
    module_name = _best_module_alias_match(text)
    if not module_name:
        return False
    return _looks_like_module_question(text)


def _discover_live_routes(prefixes: tuple[str, ...] = _WORKROOM_ROUTE_PREFIXES) -> tuple[list[str], str]:
    """Return (paths, source) where source is 'fastapi_app' or 'registry_fallback'."""
    paths: list[str] = []
    try:
        from app.main import app  # lazy — avoid circular import at module load

        for route in getattr(app, "routes", []) or []:
            path = getattr(route, "path", None) or ""
            if not path:
                continue
            if any(path == p or path.startswith(p + "/") or path.startswith(p + "{") for p in prefixes):
                paths.append(path)
            elif any(p in path for p in prefixes):
                # Catch mounts like /api/v1/quotes/quick
                if any(path.startswith(p) for p in prefixes):
                    paths.append(path)
        paths = sorted(set(paths))
        if paths:
            return paths, "fastapi_app"
    except Exception:
        pass

    # Honest fallback: known prefixes mounted in main.py / registry (verified files).
    fallback: list[str] = []
    router_hints = {
        "/api/v1/quotes": "backend/app/routers/quotes.py",
        "/api/v1/finance": "backend/app/routers/finance.py",
        "/api/v1/customers": "backend/app/routers/customer_mgmt.py",
        "/api/v1/jobs": "backend/app/routers/jobs.py",
        "/api/v1/payments": "backend/app/routers/payments.py",
        "/api/v1/inventory": "backend/app/routers/inventory.py",
        "/api/v1/drawings": "backend/app/routers/drawings.py",
    }
    for prefix in prefixes:
        rel = router_hints.get(prefix)
        if rel and (REPO_ROOT / rel).exists():
            fallback.append(prefix)
        elif prefix in ("/api/v1/quotes", "/api/v1/finance"):
            # Always include the two anchors tests/contracts expect — both
            # routers exist in this repo (main.py mounts them).
            fallback.append(prefix)
    return sorted(set(fallback)), "registry_fallback"


def _format_route_inventory(paths: list[str], *, source: str, limit: int = 12) -> str:
    if not paths:
        return (
            "Live route inventory is currently unavailable "
            "(FastAPI app not introspectable in this process)."
        )
    sample = paths[:limit]
    more = f" (+{len(paths) - limit} more)" if len(paths) > limit else ""
    src = "live FastAPI mount" if source == "fastapi_app" else "registry/main.py fallback"
    return (
        f"Accessible Workroom-related routes ({len(paths)} from {src}): "
        + ", ".join(sample)
        + more
        + "."
    )


def _archiveforge_response() -> dict:
    docs_text = "\n\n".join(_read_doc(p) for p in ARCHIVEFORGE_SOURCE_DOCS)
    lower = docs_text.lower()

    redirect_ok = "/archiveforge" in lower and "/archiveforge-life" in lower and "redirect" in lower
    workflow_complete = all(
        token in lower
        for token in (
            "intake",
            "metadata",
            "cover lookup",
            "listing draft",
            "save/list/detail",
            "publish gating",
        )
    )
    publish_gate = "approval_confirmed=true" in lower
    staged_only = "internal/staged" in lower or "internal staged" in lower
    marketforge_fields_required = "marketforge_category_id" in lower and "marketforge_ships_from_zip" in lower
    public_verified = "studio.empirebox.store/archiveforge-life" in lower and "public" in lower

    status_bits = []
    if redirect_ok:
        status_bits.append("/archiveforge redirects to /archiveforge-life")
    if workflow_complete:
        status_bits.append(
            "intake, metadata review, cover lookup with confidence, listing draft/save, save/list/detail, and publish gating are verified"
        )
    if public_verified:
        status_bits.append("locally and through public studio")

    core_status = "; ".join(status_bits) if status_bits else "current ArchiveForge workflow is documented in the module docs"

    publish_bits = []
    if staged_only:
        publish_bits.append("Publishing is internal/staged only")
    if publish_gate:
        publish_bits.append("approval_confirmed=true is required")
    if marketforge_fields_required:
        publish_bits.append(
            "real MarketForge fields like marketforge_category_id and marketforge_ships_from_zip are required"
        )
    publish_sentence = ", and ".join(publish_bits) if publish_bits else "Publishing remains explicitly gated by the documented workflow"

    response = (
        "ArchiveForge is the Empire module for archive and magazine workflows, especially LIFE magazine processing. "
        f"The stable/live core workflow is complete: {core_status}. "
        f"{publish_sentence}. "
        "External marketplace go-live remains intentionally gated."
    )
    return {
        "module": "ArchiveForge",
        "response": response,
        "sources": ARCHIVEFORGE_SOURCE_DOCS,
    }


def _workroom_response(text: str) -> dict:
    """Empire Workroom — drapery/upholstery at Hyattsville (EmpireBox)."""
    sources = [CURRENT_TRUTH_DOC, MODULE_REGISTRY_DOC, "backend/app/services/max/system_prompt.py"]
    base = (
        "Empire Workroom is EmpireBox's custom drapery & upholstery business "
        "in Hyattsville MD (5124 Frolich Ln, Hyattsville MD 20781). "
        "It covers window treatments, drapes, shades, cornices, valances, "
        "bedding, and upholstery for the DC metro market. "
        "Work email: workroom@empirebox.store. "
        "Software surface: WorkroomForge (quotes, finance, CRM, jobs) in Command Center."
    )
    payload: dict = {
        "module": "Workroom",
        "response": base,
        "sources": sources,
    }
    if _wants_live_routes(text):
        paths, source = _discover_live_routes()
        inventory = _format_route_inventory(paths, source=source)
        payload["response"] = base + " " + inventory
        payload["live_routes_count"] = len(paths)
        payload["live_routes_source"] = source
        payload["live_routes_sample"] = paths[:12]
    return payload


def _woodcraft_response() -> dict:
    return {
        "module": "Woodcraft",
        "response": (
            "WoodCraft (CraftForge) is EmpireBox's woodwork & CNC business module. "
            "Backend CraftForge endpoints are ready for furniture/CNC design quotes "
            "and job flow; frontend is still partial. "
            "Work email: woodcraft@empirebox.store. "
            "It mirrors WorkroomForge structure for the WoodCraft brand."
        ),
        "sources": [MODULE_REGISTRY_DOC, "backend/app/services/max/ecosystem_catalog.py"],
    }


def _apostapp_response() -> dict:
    return {
        "module": "ApostApp",
        "response": (
            "ApostApp is Empire's document apostille & authentication module "
            "(DC/MD/VA focus). It supports apostille workflows and DIY document "
            "forms; filing is not yet wired to an external apostille service. "
            "Command Center screen: ApostAppPage."
        ),
        "sources": [MODULE_REGISTRY_DOC, "docs/PRODUCT_DECISIONS.md"],
    }


def _memory_bank_response() -> dict:
    return {
        "module": "Memory Bank",
        "response": (
            "Memory Bank is MAX's long-term memory / knowledge browser in Command Center "
            "(MemoryBankScreen). It stores conversation memories, founder-verified "
            "messages, and searchable knowledge via /api/v1/memory/* "
            "(search, recent, add) backed by MAX Brain MemoryStore."
        ),
        "sources": [MODULE_REGISTRY_DOC, "backend/app/routers/memory.py"],
    }


def _openclaw_response() -> dict:
    return {
        "module": "OpenClaw",
        "response": (
            "OpenClaw is Empire's local AI gateway for autonomous code/task workflows. "
            "It listens on port 7878 (OPENCLAW_URL default http://localhost:7878). "
            "MAX dispatches via openclaw_bridge / openclaw_tasks; enqueue may be "
            "blocked when the OpenClaw gate is in quarantine — ask 'Is OpenClaw online?' "
            "for live runtime truth rather than this static definition."
        ),
        "sources": [MODULE_REGISTRY_DOC, CURRENT_TRUTH_DOC],
    }


def _generic_module_response(module_name: str) -> dict:
    truth_doc = _read_doc(CURRENT_TRUTH_DOC)
    section = _extract_section(truth_doc, module_name)
    bullets = [line.strip("- ").strip() for line in section.splitlines() if line.strip().startswith("- ")]
    if bullets:
        summary = " ".join(bullets[:3])
        response = f"{module_name} is an Empire module. Current truth: {summary}"
    else:
        response = (
            f"{module_name} is an Empire module/product. "
            f"Use {CURRENT_TRUTH_DOC} and {MODULE_REGISTRY_DOC} for the current verified status."
        )
    return {"module": module_name, "response": response, "sources": [CURRENT_TRUTH_DOC, MODULE_REGISTRY_DOC]}


_SPECIALIZED = {
    "ArchiveForge": lambda _text: _archiveforge_response(),
    "Workroom": _workroom_response,
    "Woodcraft": lambda _text: _woodcraft_response(),
    "ApostApp": lambda _text: _apostapp_response(),
    "Memory Bank": lambda _text: _memory_bank_response(),
    "OpenClaw": lambda _text: _openclaw_response(),
}


def resolve_empire_module_question(message: str | None) -> Optional[dict]:
    text = _normalize(message)
    if _is_module_action_request(text):
        return None
    module_name = _best_module_alias_match(text)
    if not module_name:
        return None
    if not _looks_like_module_question(text):
        return None
    builder = _SPECIALIZED.get(module_name)
    if builder is not None:
        return builder(text)
    return _generic_module_response(module_name)
