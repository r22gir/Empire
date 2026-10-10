"""Edition configs for the voice-to-document engine.

Workroom is wired to saved rates, the bench drawing engine, and
Empire / Nelma billing. Max-e and Maxine share the core and declare
their own output names; their rate and drawing adapters are unported
until those editions land.

Repo business.json is founder-only (Chief-e leak gate).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DOCUMENT_KINDS = (
    "quote",
    "invoice",
    "drawing",
    "contract",
    "payment_plan",
    "notes",
)

PORTABLE_CORE = (
    "backend/app/services/voice_documents/extract.py",
    "backend/app/services/voice_documents/session.py",
    "backend/app/services/voice_documents/send_gate.py",
    "backend/app/services/voice_documents/pipeline.py",
    "backend/app/services/voice_documents/kinds.py",
    "backend/app/services/voice_documents/email_format.py",
    "backend/app/routers/voice_documents.py",
)

EDITION_SPECIFIC = (
    "backend/app/services/voice_documents/edition.py",
    "backend/app/services/voice_documents/adapters/workroom.py",
)


@dataclass(frozen=True)
class EditionConfig:
    edition_id: str
    label: str
    business_unit: str
    default_document_kind: str
    enabled_kinds: tuple[str, ...]
    rate_adapter: str
    drawing_adapter: str
    client_brand_default: str
    auto_send: bool = False
    founder_name_on_client_docs: bool = False

    def allows(self, kind: str) -> bool:
        return kind in self.enabled_kinds


def _owner_tokens() -> tuple[str, ...]:
    tokens = {"rafael"}
    try:
        from app.edition import is_founder_edition, workroom_business_config

        if not is_founder_edition():
            return tuple(sorted(tokens))
        data = workroom_business_config()
    except Exception:
        path = Path(__file__).resolve().parents[2] / "config" / "business.json"
        try:
            from app.edition import is_founder_edition

            if not is_founder_edition():
                return tuple(sorted(tokens))
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError, TypeError, Exception):
            data = {}
    owner = str(data.get("owner_name") or "").strip()
    if owner and owner.lower() not in frozenset({"workroom", "empire"}):
        tokens.add(owner.lower())
    return tuple(sorted(tokens))


def forbidden_client_names() -> tuple[str, ...]:
    """Owner tokens. Family editions do not read repo business.json."""
    return _owner_tokens()


FORBIDDEN_CLIENT_NAMES = ()  # call forbidden_client_names() — do not cache at import

WORKROOM = EditionConfig(
    edition_id="workroom",
    label="Workroom Max",
    business_unit="workroom",
    default_document_kind="quote",
    enabled_kinds=DOCUMENT_KINDS,
    rate_adapter="workroom",
    drawing_adapter="workroom_bench",
    client_brand_default="Empire Workroom",
    auto_send=False,
)

MAX_E = EditionConfig(
    edition_id="max_e",
    label="Max-e",
    business_unit="max_e",
    default_document_kind="quote",
    enabled_kinds=DOCUMENT_KINDS,
    rate_adapter="unported",
    drawing_adapter="unported",
    client_brand_default="Max-e",
    auto_send=False,
)

MAXINE = EditionConfig(
    edition_id="maxine",
    label="Maxine",
    business_unit="maxine",
    default_document_kind="notes",
    enabled_kinds=DOCUMENT_KINDS,
    rate_adapter="unported",
    drawing_adapter="unported",
    client_brand_default="Maxine",
    auto_send=False,
)

_EDITIONS = {
    WORKROOM.edition_id: WORKROOM,
    MAX_E.edition_id: MAX_E,
    MAXINE.edition_id: MAXINE,
}


def get_edition(edition_id: str | None = None) -> EditionConfig:
    key = (edition_id or "workroom").strip().lower().replace("-", "_")
    if key in {"maxe", "max_e"}:
        return MAX_E
    return _EDITIONS.get(key, WORKROOM)
