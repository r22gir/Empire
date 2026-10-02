"""Turn a voice transcript into items, dimensions, fabric, client, and choices.

Deterministic on purpose so a transcript fixture maps to the same items
without a model call. Drawing knobs are delegated to the bench fabrication
parser already used by the shop sheets.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from app.config.workroom_billing import founder_requests_nelmas_billing
from app.services.drawing.bench_fabrication_params import parse_bench_fabrication_from_text
from app.services.voice_documents.edition import FORBIDDEN_CLIENT_NAMES

_DONE = re.compile(
    r"^(?:ok[, ]+)?(?:that(?:'s| is) (?:all|it)|i(?:'m| am) done|all done|done|finished)\.?$",
    re.IGNORECASE,
)
_SEND = re.compile(
    r"\b(?:send(?: it| the quote| the invoice| this)?|email(?: it| this| the quote)?)\b",
    re.IGNORECASE,
)
_INCH = r"(?:inches|inch|in|\")"


@dataclass
class ExtractedItem:
    item_type: str
    name: str
    width_in: Optional[float] = None
    depth_in: Optional[float] = None
    seat_height_in: Optional[float] = None
    back_height_in: Optional[float] = None
    shape: str = "straight"
    panel_style: str = "flat"
    has_back: bool = True
    seat_sections: Optional[int] = None
    back_sections: Optional[int] = None
    seat_cushion_thickness: Optional[float] = None
    back_thickness: Optional[float] = None
    back_angle_deg: Optional[float] = None
    overhang_in: Optional[float] = None
    fabric_mode: Optional[str] = None  # com | workroom | None
    fabric_name: str = ""
    welt: Optional[str] = None  # none | self | contrast | None
    raw: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_type": self.item_type,
            "name": self.name,
            "width_in": self.width_in,
            "depth_in": self.depth_in,
            "seat_height_in": self.seat_height_in,
            "back_height_in": self.back_height_in,
            "shape": self.shape,
            "panel_style": self.panel_style,
            "has_back": self.has_back,
            "seat_sections": self.seat_sections,
            "back_sections": self.back_sections,
            "seat_cushion_thickness": self.seat_cushion_thickness,
            "back_thickness": self.back_thickness,
            "back_angle_deg": self.back_angle_deg,
            "overhang_in": self.overhang_in,
            "fabric_mode": self.fabric_mode,
            "fabric_name": self.fabric_name,
            "welt": self.welt,
        }


@dataclass
class Extraction:
    transcript: str
    client_name: str = ""
    items: list[ExtractedItem] = field(default_factory=list)
    document_kind: str = "quote"
    bill_as_nelmas: bool = False
    done: bool = False
    send_requested: bool = False
    document_intent: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "client_name": self.client_name,
            "document_kind": self.document_kind,
            "bill_as_nelmas": self.bill_as_nelmas,
            "done": self.done,
            "send_requested": self.send_requested,
            "document_intent": self.document_intent,
            "items": [item.to_dict() for item in self.items],
        }


def is_done_utterance(text: str) -> bool:
    t = re.sub(r"\s+", " ", (text or "").strip())
    if _DONE.match(t):
        return True
    return bool(re.search(
        r"(?:^|[.!?]\s+)(?:ok[, ]+)?(?:that(?:'s| is) (?:all|it)|i(?:'m| am) done|done)\s*[.!]?\s*$",
        t,
        re.IGNORECASE,
    )) and len(t) < 80


def _num(match: re.Match | None) -> Optional[float]:
    if not match:
        return None
    try:
        return float(match.group(1))
    except (IndexError, ValueError):
        return None


def _first(text: str, patterns: list[str]) -> Optional[float]:
    for pattern in patterns:
        found = _num(re.search(pattern, text, re.IGNORECASE))
        if found is not None:
            return found
    return None


def _client_name(text: str) -> str:
    patterns = [
        r"\b(?:quote|estimate|invoice|drawing)\s+for\s+([A-Za-z][A-Za-z'’\-]+(?:\s+[A-Za-z][A-Za-z'’\-]+){0,2})",
        r"\bfor\s+([A-Za-z][A-Za-z'’\-]+(?:\s+[A-Za-z][A-Za-z'’\-]+){0,2})",
        r"\bclient(?:\s+is|\s+name)?\s*[:=]?\s+([A-Za-z][A-Za-z'’\-]+(?:\s+[A-Za-z][A-Za-z'’\-]+){0,2})",
    ]
    stop = {
        "a", "an", "the", "this", "that", "my", "me", "our", "her", "his",
        "straight", "curved", "raked", "supplied", "com", "one", "two",
    }
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        raw = match.group(1).strip(" .,")
        parts = []
        for part in raw.split():
            if part.lower() in stop:
                break
            if part.lower() in FORBIDDEN_CLIENT_NAMES:
                continue
            parts.append(part[:1].upper() + part[1:])
        if parts:
            return " ".join(parts[:3])
    return ""


def _fabric_mode(text: str) -> tuple[Optional[str], str]:
    t = text.lower()
    name = ""
    named = re.search(
        r"(?:fabric|com)\s+(?:is\s+)?([A-Za-z][A-Za-z0-9 \-]{2,40})",
        text,
        re.IGNORECASE,
    )
    if named:
        name = named.group(1).strip(" .,")
        name = re.split(r"\b(?:plain|seats|backs|for|with)\b", name, maxsplit=1)[0].strip(" .,")
    if re.search(r"\b(?:we supply|workroom(?:-|\s)supplied|our fabric|shop fabric)\b", t):
        return "workroom", name
    if re.search(r"\b(?:com\b|c\.o\.m|customer(?:'s|s)? fabric|supplied fabric|client(?:'s|s)? fabric)\b", t):
        return "com", name or "supplied"
    return None, name


def _welt(text: str) -> Optional[str]:
    t = text.lower()
    if re.search(r"\bno welt\b|\bwithout welt\b|\bno welting\b", t):
        return "none"
    if re.search(r"\bcontrast welt", t):
        return "contrast"
    if re.search(r"\bself[- ]welt|\bwith welt\b|\bwelted\b|\bwelting\b", t):
        return "self"
    return None


def _kind(text: str) -> str:
    t = text.lower()
    if re.search(r"\bpayment plan\b", t):
        return "payment_plan"
    if re.search(r"\bcontract\b", t):
        return "contract"
    if re.search(r"\binvoice\b", t) and not re.search(r"\bquote\b", t):
        return "invoice"
    if re.search(r"\b(?:just|only)\s+(?:a\s+)?(?:the\s+)?drawing\b|\bdrawing only\b", t):
        return "drawing"
    if re.search(r"\bnotes?\b", t) and not re.search(r"\b(?:quote|bench|banquette|drawing)\b", t):
        return "notes"
    return "quote"


def _item_type(text: str) -> tuple[str, str, str]:
    t = text.lower()
    shape = "straight"
    if re.search(r"\bu[- ]?shape", t):
        shape = "u_shape"
    elif re.search(r"\bl[- ]?shape", t):
        shape = "l_shape"
    if "banquette" in t or "booth" in t:
        return "banquette", "Banquette", shape
    if "bench" in t:
        return "bench", "Bench", shape
    if re.search(r"\bseat cushions?\b", t) and "back" not in t and "bench" not in t:
        return "seat_cushion", "Seat cushion", shape
    if re.search(r"\bback cushions?\b", t) and "bench" not in t and "banquette" not in t:
        return "back_cushion", "Back cushion", shape
    if "roman" in t:
        return "roman_shade", "Roman shade", shape
    if re.search(r"\bdrapery\b|\bcurtain\b", t):
        return "drapery", "Drapery", shape
    if "pillow" in t:
        return "throw_pillow", "Pillow", shape
    return "", "", shape


def _has_document_intent(text: str, item_type: str) -> bool:
    t = text.lower()
    if item_type:
        return True
    return bool(re.search(
        r"\b(?:quote|estimate|invoice|drawing|contract|payment plan|upholster|cushion|fabric|inches|inch)\b",
        t,
    ))


def _panel(text: str) -> str:
    t = text.lower()
    if "tuft" in t:
        return "tufted"
    if "channel" in t:
        return "vertical_channels"
    return "flat"


def extract_transcript(text: str, *, prior: Optional[Extraction] = None) -> Extraction:
    """Extract from one note. When prior is set, later notes overlay it."""
    raw = (text or "").strip()
    base = prior
    item = ExtractedItem(item_type="", name="")
    if base and base.items:
        prev = base.items[0]
        item = ExtractedItem(**prev.to_dict(), raw=prev.raw)

    kind_text = raw.lower()
    item_type, name, shape = _item_type(raw)
    if item_type:
        item.item_type = item_type
        item.name = name
        item.shape = shape
    if shape != "straight" or not item.shape:
        if shape != "straight":
            item.shape = shape

    width = _first(raw, [
        rf"(\d+(?:\.\d+)?)\s*{_INCH}\s*(?:long|wide|length|width)",
        r"(\d+(?:\.\d+)?)\s*(?:foot|feet|ft)\s*(?:long|wide|length|width)",
    ])
    if width is not None and re.search(r"\b(?:foot|feet|ft)\b", raw, re.IGNORECASE) and not re.search(
        rf"(\d+(?:\.\d+)?)\s*{_INCH}\s*(?:long|wide|length|width)", raw, re.IGNORECASE
    ):
        width = width * 12.0
    depth = _first(raw, [rf"(\d+(?:\.\d+)?)\s*{_INCH}\s*deep", r"(\d+(?:\.\d+)?)\s*(?:inch(?:es)?|in)\s*depth"])
    seat_h = _first(raw, [
        rf"(\d+(?:\.\d+)?)\s*{_INCH}\s*(?:high|tall|seat height)",
        r"seat height\s+(\d+(?:\.\d+)?)",
    ])
    back_h = _first(raw, [
        r"back(?:\s+height)?\s+(\d+(?:\.\d+)?)",
        rf"(\d+(?:\.\d+)?)\s*{_INCH}\s*back",
    ])
    if width is not None:
        item.width_in = width
    if depth is not None:
        item.depth_in = depth
    if seat_h is not None:
        item.seat_height_in = seat_h
    if back_h is not None:
        item.back_height_in = back_h

    fab = parse_bench_fabrication_from_text(raw)
    for key in (
        "seat_sections", "back_sections", "seat_cushion_thickness",
        "back_thickness", "back_angle_deg", "seat_cushion_overhang",
    ):
        if key in fab:
            if key == "seat_cushion_overhang":
                item.overhang_in = fab[key]
            else:
                setattr(item, key, fab[key])

    if re.search(r"\bno back\b|\bbackless\b", raw, re.IGNORECASE):
        item.has_back = False
    style = _panel(raw)
    if style != "flat" or "flat" in raw.lower():
        item.panel_style = style

    fabric_mode, fabric_name = _fabric_mode(raw)
    if fabric_mode:
        item.fabric_mode = fabric_mode
    if fabric_name:
        item.fabric_name = fabric_name
    welt = _welt(raw)
    if welt:
        item.welt = welt

    client = _client_name(raw) or (base.client_name if base else "")
    kind = _kind(raw)
    if kind == "quote" and base and base.document_kind != "quote" and not re.search(
        r"\bquote\b", raw, re.IGNORECASE
    ):
        kind = base.document_kind
    if re.search(r"\bquote\b|\bestimate\b", raw, re.IGNORECASE):
        kind = "quote"

    intent = _has_document_intent(raw, item.item_type) or bool(base and base.document_intent)
    done = is_done_utterance(raw)
    send_requested = bool(_SEND.search(raw)) and not done

    items = [item] if item.item_type or item.width_in or item.fabric_mode else []
    if not items and base:
        items = list(base.items)

    return Extraction(
        transcript=raw,
        client_name=client,
        items=items,
        document_kind=kind,
        bill_as_nelmas=founder_requests_nelmas_billing(raw) or bool(base and base.bill_as_nelmas),
        done=done,
        send_requested=send_requested,
        document_intent=intent or done,
    )


def merge_extractions(parts: list[Extraction]) -> Extraction:
    """Replay notes in order so later speech overlays earlier speech."""
    merged: Optional[Extraction] = None
    chunks: list[str] = []
    done = False
    send_requested = False
    for part in parts:
        chunks.append(part.transcript)
        merged = extract_transcript(part.transcript, prior=merged)
        done = done or part.done or is_done_utterance(part.transcript)
        send_requested = send_requested or part.send_requested
    if merged is None:
        return Extraction(transcript="")
    merged.transcript = "\n".join(c for c in chunks if c)
    merged.done = done
    merged.send_requested = send_requested
    return merged
