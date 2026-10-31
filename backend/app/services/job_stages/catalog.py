"""Canonical 8-stage job document set.

Order is binding. Stages 6 (referral totals) and 7 (revision comparison)
are conditional. Stage 4 (workroom approval) is the client-estimate gate.
"""
from __future__ import annotations

from typing import Any

STATUS_NOT_STARTED = "not_started"
STATUS_DRAFTED = "drafted"
STATUS_APPROVED = "approved"
STATUS_DONE = "done"

VALID_STATUSES = (
    STATUS_NOT_STARTED,
    STATUS_DRAFTED,
    STATUS_APPROVED,
    STATUS_DONE,
)

STAGE_PRELIM = "prelim_info"
STAGE_DRAWING = "drawing"
STAGE_PRESENTATION = "presentation_board"
STAGE_WORKROOM = "workroom_approval"
STAGE_ESTIMATE = "estimate"
STAGE_REFERRAL = "referral_totals"
STAGE_REVISION = "revision_comparison"
STAGE_INVOICE = "square_invoice"

WORKROOM_MARKUP = 0.20
GATE_STAGE_KEY = STAGE_WORKROOM

DOC_TYPE_SLUGS = {
    STAGE_PRELIM: "PrelimInfo",
    STAGE_DRAWING: "Drawing",
    STAGE_PRESENTATION: "PresentationBoard",
    STAGE_WORKROOM: "WorkroomApproval",
    STAGE_ESTIMATE: "Estimate",
    STAGE_REFERRAL: "ReferralTotals",
    STAGE_REVISION: "RevisionComparison",
    STAGE_INVOICE: "SquareInvoice",
}

# document_type / filename tokens that map a job_documents row to a stage
DOCUMENT_TYPE_ALIASES = {
    STAGE_PRELIM: (
        "prelim", "prelim_info", "info_sheet", "site_photo", "photo",
        "photos", "measurement", "measurements", "notes", "first_notes",
        "intake", "site",
    ),
    STAGE_DRAWING: (
        "drawing", "drawings", "elevation", "plan", "shop_drawing",
        "gold_template",
    ),
    STAGE_PRESENTATION: (
        "presentation", "presentation_board", "board", "mockup",
        "concept", "layers",
    ),
    STAGE_WORKROOM: (
        "workroom_approval", "workroom", "approval", "approval_doc",
    ),
    STAGE_ESTIMATE: (
        "estimate", "quote", "client_estimate", "internal_estimate",
    ),
    STAGE_REFERRAL: (
        "referral", "referral_totals", "referral_total",
    ),
    STAGE_REVISION: (
        "revision", "revision_comparison", "change_order", "comparison",
    ),
    STAGE_INVOICE: (
        "invoice", "square", "square_invoice",
    ),
}

STAGES: tuple[dict[str, Any], ...] = (
    {
        "key": STAGE_PRELIM,
        "order": 1,
        "title": "Prelim Info Sheet",
        "doc_type": DOC_TYPE_SLUGS[STAGE_PRELIM],
        "description": "Site measurements, photos, first notes.",
        "conditional": False,
        "required_when": None,
        "audience": "internal",
    },
    {
        "key": STAGE_DRAWING,
        "order": 2,
        "title": "Drawing",
        "doc_type": DOC_TYPE_SLUGS[STAGE_DRAWING],
        "description": "Elevation/plan with full dims, on the gold template.",
        "conditional": False,
        "required_when": None,
        "audience": "internal",
    },
    {
        "key": STAGE_PRESENTATION,
        "order": 3,
        "title": "Presentation Board",
        "doc_type": DOC_TYPE_SLUGS[STAGE_PRESENTATION],
        "description": "Concept, layers and fabric for the designer or client.",
        "conditional": False,
        "required_when": None,
        "audience": "client",
    },
    {
        "key": STAGE_WORKROOM,
        "order": 4,
        "title": "Workroom Approval",
        "doc_type": DOC_TYPE_SLUGS[STAGE_WORKROOM],
        "description": (
            "Compact 3-page approval: measurements and proposed prices "
            "(unit, unit price, qty, base, +20%, client total), terms and "
            "a confirm line; full-page elevation; site photo. Big bold "
            "black fonts. Workroom must approve before any estimate goes "
            "to the client."
        ),
        "conditional": False,
        "required_when": None,
        "audience": "internal",
        "pages": 3,
        "gate": True,
    },
    {
        "key": STAGE_ESTIMATE,
        "order": 5,
        "title": "Estimate",
        "doc_type": DOC_TYPE_SLUGS[STAGE_ESTIMATE],
        "description": (
            "Willard layout, grouped by area and within each area by "
            "Labor / Materials / Install. Client copy carries the Square "
            "pay link + QR and terms; internal copy shows base + markup."
        ),
        "conditional": False,
        "required_when": None,
        "audience": "both",
        "copies": ("client", "internal"),
    },
    {
        "key": STAGE_REFERRAL,
        "order": 6,
        "title": "Referral Totals",
        "doc_type": DOC_TYPE_SLUGS[STAGE_REFERRAL],
        "description": "Only if the job has a referral.",
        "conditional": True,
        "required_when": "referral",
        "audience": "internal",
    },
    {
        "key": STAGE_REVISION,
        "order": 7,
        "title": "Revision Comparison",
        "doc_type": DOC_TYPE_SLUGS[STAGE_REVISION],
        "description": "Only when the job is revised.",
        "conditional": True,
        "required_when": "revision",
        "audience": "both",
    },
    {
        "key": STAGE_INVOICE,
        "order": 8,
        "title": "Square Invoice",
        "doc_type": DOC_TYPE_SLUGS[STAGE_INVOICE],
        "description": (
            "Always a draft until Rafael expressly says send. Never auto-send."
        ),
        "conditional": False,
        "required_when": None,
        "audience": "client",
        "send_policy": "express_rafael_only",
    },
)

STAGES_BY_KEY = {stage["key"]: stage for stage in STAGES}

# Tokens that mean the founder expressly authorized a Square send.
RAFAEL_SEND_PHRASES = (
    "rafael says send",
    "rafael said send",
    "rafael expressly says send",
    "rafael expressly said send",
    "rafael authorized send",
    "send authorized by rafael",
)

RAFAEL_ACTORS = ("rafael", "rafael giraldo", "rg")
WORKROOM_APPROVERS = ("rafael", "rafael giraldo", "rg", "workroom")
MAX_APPROVE_BLOCKLIST = (
    "max", "max-agent", "max_agent", "max agent",
    "assistant", "agent", "system",
)


def stage_definition(stage_key: str) -> dict[str, Any]:
    stage = STAGES_BY_KEY.get(stage_key)
    if not stage:
        raise KeyError(f"Unknown job stage: {stage_key}")
    return stage


def infer_stage_key(document_type: str | None, filename: str | None = None) -> str | None:
    """Map a job_documents row onto a stage key."""
    haystacks = [
        (document_type or "").strip().lower().replace("-", "_").replace(" ", "_"),
        (filename or "").strip().lower().replace("-", "_"),
    ]
    for stage_key, aliases in DOCUMENT_TYPE_ALIASES.items():
        for token in haystacks:
            if not token:
                continue
            if token == stage_key or token in aliases:
                return stage_key
            if any(alias in token for alias in aliases if len(alias) > 3):
                return stage_key
    return None
