"""Spanish draft outlines for Cibernettic. Not legal text and not a price list.

Each document is a BORRADOR. Placeholders stay empty until Juan fills them.
Nothing here is a clause, a fee, or a company identifier.
"""
from __future__ import annotations

WATERMARK = "BORRADOR – requiere revisión de abogado"

SERVICE_LINES = (
    ("ciberseguridad", "Ciberseguridad"),
    ("gestion_datos", "Gestión de datos"),
    ("dba", "Administración de bases de datos (DBA)"),
    ("redes_voip", "Redes y VoIP"),
    ("bi", "Inteligencia de negocios (BI)"),
)

DOCUMENTS = (
    ("propuesta", "Propuesta de servicios"),
    ("sla", "Acuerdo de nivel de servicio"),
    ("nda", "Acuerdo de confidencialidad"),
    ("contrato", "Contrato de servicios"),
)

# Voice extractor keys. Unknown keys leave {{linea_servicio}} blank.
_FROM_EXTRACT = {
    "cyber": "ciberseguridad",
    "audit": "ciberseguridad",
    "assessment": "ciberseguridad",
    "managed": "gestion_datos",
    "backup": "gestion_datos",
    "dba": "dba",
    "network": "redes_voip",
    "bi": "bi",
}


def _line_title(line_key: str | None) -> tuple[str, str]:
    for key, title in SERVICE_LINES:
        if key == line_key:
            return key, title
    return "", "{{linea_servicio}}"


def _doc_title(doc_key: str) -> str:
    for key, title in DOCUMENTS:
        if key == doc_key:
            return title
    raise KeyError(doc_key)


def draft_body(doc_key: str, line_key: str | None) -> str:
    """Outline only. {{precio}} and the company fields are not filled here."""
    title = _doc_title(doc_key)
    _key, line = _line_title(line_key)
    return (
        f"{WATERMARK}\n\n"
        f"{title}\n"
        f"Línea de servicio: {line}\n\n"
        "Este texto es un esquema para revisión. No es una cláusula, "
        "no fija un precio y no identifica una sociedad.\n\n"
        "Cliente: {{cliente}}\n"
        "Proveedor: {{proveedor}}\n"
        "Alcance: {{alcance}}\n"
        "Vigencia: {{vigencia}}\n"
        "Entregables: {{entregables}}\n"
        "Precio: {{precio}}\n"
        "Moneda: {{moneda}}\n"
        "Notas para el abogado: {{contenido_abogado}}\n"
    )


def build_draft(doc_key: str, line_key: str | None = None) -> dict:
    title = _doc_title(doc_key)
    key, line = _line_title(line_key)
    return {
        "doc_type": doc_key,
        "service_line": key or None,
        "title": title if not key else f"{title} · {line}",
        "locale": "es",
        "status": "draft",
        "sent": False,
        "approved_by_lawyer": False,
        "body": draft_body(doc_key, key or None),
    }


def list_drafts() -> list[dict]:
    rows = []
    for line_key, _title in SERVICE_LINES:
        for doc_key, _doc_title in DOCUMENTS:
            rows.append(build_draft(doc_key, line_key))
    return rows


def drafts_for_detected_line(service_line: str | None) -> list[dict]:
    mapped = _FROM_EXTRACT.get((service_line or "").strip().lower())
    return [build_draft(doc_key, mapped) for doc_key, _title in DOCUMENTS]
