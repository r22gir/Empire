"""Company setup interview — edition-scoped merge into business.json.

Never replaces the whole file. Family editions stay in their own data
dir. Secrets (WhatsApp keys) live in the edition secrets file and are
never returned or logged.
"""
from __future__ import annotations

from app.services.company_setup.schema import (
    INTERVIEW_SECTIONS,
    SECTION_IDS,
    configured_report,
    is_configured,
)
from app.services.company_setup.store import load_merged, save_section

__all__ = [
    "INTERVIEW_SECTIONS",
    "SECTION_IDS",
    "configured_report",
    "is_configured",
    "load_merged",
    "save_section",
]
