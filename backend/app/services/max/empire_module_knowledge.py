"""Empire module knowledge resolver grounded in current repo docs."""
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
    "Workroom": ("workroom",),
    "Drawing Studio": ("drawing studio",),
    "RecoveryForge": ("recoveryforge", "recovery forge"),
    "RelistApp": ("relistapp", "relist app"),
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
    "work",
    "features",
    "publish",
    "complete",
    "finished",
    "update",
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


def _looks_like_module_question(text: str) -> bool:
    if any(hint in text for hint in MODULE_QUESTION_HINTS):
        return True
    return text.endswith("?")


def is_empire_module_question(message: str | None) -> bool:
    text = _normalize(message)
    module_name = _best_module_alias_match(text)
    if not module_name:
        return False
    return _looks_like_module_question(text)


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


def resolve_empire_module_question(message: str | None) -> Optional[dict]:
    text = _normalize(message)
    module_name = _best_module_alias_match(text)
    if not module_name:
        return None
    if not _looks_like_module_question(text):
        return None
    if module_name == "ArchiveForge":
        return _archiveforge_response()
    return _generic_module_response(module_name)
