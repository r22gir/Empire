"""Turn a Spanish (or mixed) transcript into document fields.

No network and no speech engine. Tests pass a transcript fixture.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional

DOC_TYPES = (
    "reservation",
    "quote",
    "invoice",
    "contract",
    "payment_plan",
    "meeting_notes",
    "general",
)

DOC_LABELS = {
    "reservation": "Separación de lote",
    "quote": "Cotización",
    "invoice": "Factura",
    "contract": "Contrato",
    "payment_plan": "Plan de pagos",
    "meeting_notes": "Notas de reunión",
    "general": "Documento",
}

_LISTO = re.compile(r"\b(listo|lista|ya esta|cerrar borrador|terminar borrador)\b", re.I)
_LOT = re.compile(r"\blote\s+([A-Za-z]?\d+)\b", re.I)
_NAME = re.compile(
    r"\b(?:para|cliente|comprador|a nombre de)\s+"
    r"([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñüÜ]+(?:\s+[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñüÜ]+){0,3})"
)
_PCT = re.compile(r"cuota\s+inicial\s+(?:del?\s+|de\s+)?(\d{1,3})\s*%", re.I)
_MONTHS = re.compile(
    r"(?:saldo\s+en|en|a)\s+(\d{1,3})\s+mes(?:es)?|(\d{1,3})\s+cuotas",
    re.I,
)
_SEP = re.compile(r"separaci[oó]n(?:\s+(?:de|es))?\s+\$?\s*([\d][\d\.]*)", re.I)
_PRICE = re.compile(
    r"(?:precio|valor|cuesta|vale)\s+(?:es|de)?\s*\$?\s*([\d][\d\.]*)",
    re.I,
)
_BALLOON = re.compile(
    r"(?:cuota\s+final|contra\s+(?:el\s+)?(?:cr[eé]dito|hipoteca|subsidio)|subsidio)"
    r"(?:\s+(?:de|por))?\s+\$?\s*([\d][\d\.]*)",
    re.I,
)
_HOUSE = re.compile(r"\b(?:casa\s+tipo|tipo)\s*t?\s*([123])\b", re.I)
_PRODUCT = re.compile(
    r"\b(coaching|programa|curso|membres[ií]a|taller)\b(?:\s+de\s+|\s+)[\"“]?"
    r"([A-Za-zÁÉÍÓÚÑáéíóúñüÜ0-9 ]{3,60}?)(?=\s+para\b|\s+precio\b|\s+por\b|,|$)",
    re.I,
)


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text or "")
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn").lower()


def parse_cop_amount(raw: str) -> Optional[int]:
    digits = re.sub(r"[^\d]", "", raw or "")
    if not digits:
        return None
    return int(digits)


def detect_language(text: str) -> str:
    """Lightweight guess. Documents still use locale es-CO."""
    folded = f" {_fold(text)} "
    es = sum(token in folded for token in (" el ", " la ", " para ", " lote ", " cuota ", " mes ", " de "))
    en = sum(token in folded for token in (" the ", " quote ", " invoice ", " payment ", " for ", " meeting "))
    if en > es and es == 0:
        return "en"
    return "es"


def extract_fields(transcript: str) -> dict:
    text = (transcript or "").strip()
    folded = _fold(text)
    fields: dict = {
        "raw": text,
        "ready": bool(_LISTO.search(folded)),
        "language": detect_language(text),
        "locale": "es-CO",
    }
    lot = _LOT.search(text)
    if lot:
        fields["lot_number"] = lot.group(1)
    name = _NAME.search(text)
    if name:
        fields["buyer_name"] = name.group(1).strip()
    pct = _PCT.search(folded)
    if pct:
        fields["cuota_inicial_pct"] = int(pct.group(1))
    months = _MONTHS.search(folded)
    if months:
        fields["installments"] = int(months.group(1) or months.group(2))
    separacion = _SEP.search(folded)
    if separacion:
        amount = parse_cop_amount(separacion.group(1))
        if amount:
            fields["separacion"] = amount
    price = _PRICE.search(folded)
    if price:
        amount = parse_cop_amount(price.group(1))
        if amount:
            fields["price"] = amount
    balloon = _BALLOON.search(folded)
    if balloon and balloon.group(1):
        amount = parse_cop_amount(balloon.group(1))
        if amount:
            fields["balloon"] = amount
    house = _HOUSE.search(folded)
    if house:
        fields["house_type"] = f"T{house.group(1)}"
    if "casa" in folded:
        fields["mentions_house"] = True
    if "con acabados" in folded:
        fields["finishes"] = "con_acabados"
    elif "sin acabados" in folded:
        fields["finishes"] = "sin_acabados"
    product = _PRODUCT.search(text)
    if product:
        kind = _fold(product.group(1))
        if kind.startswith("membres"):
            fields["product_kind"] = "membership"
        elif kind.startswith("curso"):
            fields["product_kind"] = "course"
        else:
            fields["product_kind"] = "coaching"
        fields["product_name"] = product.group(2).strip(" .")
    if "separ" in folded:
        fields["intent_reservation"] = True
    return fields


def propose_doc_type(transcript: str, fields: dict, edition: str = "") -> str:
    folded = _fold(transcript or "")
    edition = (edition or "").lower()
    reservation = fields.get("lot_number") or fields.get("intent_reservation")
    if reservation and edition != "amp":
        return "reservation"
    if "factura" in folded or "invoice" in folded:
        return "invoice"
    if "contrato" in folded:
        return "contract"
    if "cotiz" in folded or "quote" in folded:
        return "quote"
    if "plan de pago" in folded:
        return "payment_plan"
    if "reun" in folded or "minuta" in folded or "meeting" in folded:
        return "meeting_notes"
    if fields.get("product_kind"):
        if "factura" in folded:
            return "invoice"
        if "contrato" in folded:
            return "contract"
        return "quote"
    if edition == "amp" and any(word in folded for word in ("programa", "curso", "membres", "coaching")):
        return "quote"
    return "general"


def merge_fields(base: Optional[dict], new: Optional[dict]) -> dict:
    merged = dict(base or {})
    for key, value in (new or {}).items():
        if key == "raw":
            continue
        if value in (None, "", [], {}):
            continue
        if key == "ready":
            merged["ready"] = bool(merged.get("ready") or value)
            continue
        merged[key] = value
    return merged


_QUESTIONS = {
    "buyer_name": "¿A nombre de quién queda el documento?",
    "lot_number": "¿Cuál lote vamos a separar?",
    "price": "¿Cuál es el precio en pesos? No uso un valor que no me hayas dicho.",
    "cuota_inicial_pct": "¿Qué porcentaje de cuota inicial quieres?",
    "installments": "¿En cuántos meses queda el saldo?",
    "product_name": "¿Cómo se llama el programa, curso o membresía?",
    "house_type": "¿Casa tipo T1, T2 o T3?",
    "finishes": "¿Con acabados o sin acabados?",
    "option": "Elige una de las opciones para seguir.",
}


def missing_fields(doc_type: str, fields: dict) -> list[str]:
    needed: list[str] = []
    if doc_type == "meeting_notes":
        return []
    if doc_type == "general":
        return []
    if not fields.get("buyer_name"):
        needed.append("buyer_name")
    if doc_type == "reservation" and not fields.get("lot_number"):
        needed.append("lot_number")
    if doc_type in {"reservation", "payment_plan", "quote", "invoice", "contract"} and not fields.get("price"):
        needed.append("price")
    if doc_type in {"reservation", "payment_plan"}:
        if not fields.get("cuota_inicial_pct") and doc_type == "reservation":
            needed.append("cuota_inicial_pct")
        if not fields.get("installments"):
            needed.append("installments")
    if doc_type in {"quote", "invoice", "contract"} and fields.get("product_kind") and not fields.get("product_name"):
        needed.append("product_name")
    if fields.get("mentions_house") and not fields.get("house_type"):
        needed.append("house_type")
    if fields.get("mentions_house") and fields.get("house_type") and not fields.get("finishes"):
        needed.append("finishes")
    return needed


def looks_like_draft_followup(text: str) -> bool:
    folded = _fold(text)
    if _LISTO.search(folded):
        return True
    return bool(re.search(r"\b(plan\s+[abc]|tipo\s*t?\s*[123]|con acabados|sin acabados)\b", folded))


def choice_from_text(text: str) -> Optional[str]:
    folded = _fold(text)
    if re.search(r"\bplan\s+a\b", folded):
        return "plan_a"
    if re.search(r"\bplan\s+b\b", folded):
        return "plan_b"
    if re.search(r"\bplan\s+c\b", folded):
        return "plan_c"
    house = re.search(r"\btipo\s*t?\s*([123])\b", folded)
    if house:
        return f"T{house.group(1)}"
    if "sin acabados" in folded:
        return "sin_acabados"
    if "con acabados" in folded:
        return "con_acabados"
    return None


def follow_up_question(missing: list[str]) -> str:
    if not missing:
        return "Cuando termines, di listo. El documento queda en borrador hasta que lo apruebes."
    return _QUESTIONS.get(missing[0], "¿Qué dato falta?")
