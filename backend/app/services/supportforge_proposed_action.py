"""Propose an owner action for a family-help / SupportForge request.

Kinds and statuses are the PR #124 Sprint J model:

    kind:   adjust | fix | create
    status: proposed | accepted | rejected | completed

Empire Assist: Family Requests reuses the *kind* enum and classifier
verbatim. The founder request-log lifecycle (new / planned / in_progress /
done / declined) is a display mapping of the same proposal states — see
``family_request_log.LOG_STATUS_FROM_PROPOSAL``.
"""
from __future__ import annotations

from typing import Literal

ProposedKind = Literal["adjust", "fix", "create"]
ProposedStatus = Literal["proposed", "accepted", "rejected", "completed"]

CREATE_HINTS = (
    "create", "crear", "nuevo", "nueva", "añadir", "anadir", "agregar",
    "add ", "make ", "build", "construir", "nueva pagina", "nueva página",
    "new feature", "nueva funcion", "nueva función",
)
FIX_HINTS = (
    "fix", "arreglar", "roto", "rota", "broken", "error", "bug",
    "no funciona", "no anda", "falla", "crash", "se cayo", "se cayó",
    "repair", "reparar", "no carga", "no abre",
)

VALID_KINDS = frozenset({"adjust", "fix", "create"})
VALID_STATUSES = frozenset({"proposed", "accepted", "rejected", "completed"})


def classify_proposed_action(subject: str, message: str = "") -> ProposedKind:
    text = f"{subject} {message}".strip().lower()
    if any(hint in text for hint in CREATE_HINTS):
        return "create"
    if any(hint in text for hint in FIX_HINTS):
        return "fix"
    return "adjust"


def summarize_proposed_action(
    kind: ProposedKind,
    subject: str,
    edition_id: str | None = None,
) -> str:
    edition = edition_id or "this edition"
    topic = (subject or "the reported request").strip()
    if kind == "fix":
        return (
            f"Fix a problem in {edition}: {topic}. "
            "Diagnose and repair only after the owner accepts — do not auto-deploy."
        )
    if kind == "create":
        return (
            f"Create something new for {edition}: {topic}. "
            "This is a proposal only — do not scaffold or generate code automatically."
        )
    return (
        f"Adjust existing {edition} behavior: {topic}. "
        "Review the request and change configuration or copy — do not build automatically."
    )


def propose_action(subject: str, message: str = "", edition_id: str | None = None) -> dict:
    kind = classify_proposed_action(subject, message)
    return {
        "kind": kind,
        "summary": summarize_proposed_action(kind, subject, edition_id),
        "status": "proposed",
        "auto_build": False,
    }
