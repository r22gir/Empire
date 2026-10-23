"""Rafael 2026-10-23 estimate / invoice rules for Max.

Canonical source for Max chat, draft_estimate_and_presentation, and the
Willard area-layout PDF renderer: landscape Empire chrome, area → LABOR /
MATERIALS / INSTALLATION, client TOTAL only vs internal RATE / AMOUNT /
MARKUP / TOTAL. Format reference only — never loaded as a live job.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable, Literal, Sequence

from app.services.pricing.dimensions import format_inches_plain, plain_fractions

FORMAT_ID = "rafael_willard_2026_10_23"
FORMAT_DATE = "2026-10-23"
REFERENCE_DOCS = ("Willard area layout",)
WILLARD_FORMAT_PENDING = True  # format reference only; not founder-approved

CLIENT_FACTOR = 1.20
DEFAULT_DEPOSIT_PERCENT = 50.0
INSTALL_PER_8FT = 245.0
TRACK_PER_8FT = 325.0
SECTION_FT = 8.0

AREA_MAIN_DRAPERY = "Main Drapery"
AREA_SHEERS = "Sheers"
GROUP_LABOR = "Labor"
GROUP_MATERIALS = "Materials"
GROUP_INSTALLATION = "Installation"
GROUP_ORDER = (GROUP_LABOR, GROUP_MATERIALS, GROUP_INSTALLATION)

VARIANT_CLIENT = "client"
VARIANT_CLIENT_SIMPLE = "client_simple"
VARIANT_INTERNAL = "internal"
VARIANT_DEFAULT = VARIANT_CLIENT_SIMPLE
EstimateVariant = Literal["client", "client_simple", "internal"]

_BRAND_RE = re.compile(
    r"\b("
    r"Fabricut|Schumacher|Kravet|Ferrick\s+Mason|Abnormals|Kristy\s+Stafford|"
    r"Robert\s+Allen|Pindler|Stroheim|Brunschwig|Lee\s+Jofa|Cowtan|"
    r"Osborne\s+(?:and|&)\s+Little|Romano|Kirsch|Rowley|Graber|Hunter\s+Douglas"
    r")\b",
    re.I,
)
_SUPPLIER_RE = re.compile(
    r"\b(wholesale|supplier|mill(?:\s+name)?|vendor|sku\s*#?\s*\S+)\b",
    re.I,
)
_FABRIC_CODE_RE = re.compile(r"\b([VFL]\d{3,}-[A-Za-z0-9][A-Za-z0-9 \-/]*)")
_HOUR_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:hr|hrs|hour|hours)\b", re.I)


@dataclass(frozen=True)
class WillardLayout:
    """Landscape Willard area-layout sheet geometry (letter, points).

    Content 30–762, ITEM at 30, DESCRIPTION at 92, QTY at 520; internal
    RATE 570 / AMOUNT 630 / MARKUP 690 / TOTAL 762.
    """

    page_w: float = 792.0
    page_h: float = 612.0
    margin_l: float = 30.0
    margin_r: float = 30.0
    content_right: float = 762.0
    header_h: float = 44.0
    footer_h: float = 26.0
    title_y: float = 66.0  # SVG top-down; painter converts
    subtitle_y: float = 84.0
    body_start_y: float = 104.0
    col_item: float = 30.0
    col_desc: float = 92.0
    col_qty: float = 520.0
    col_rate: float = 570.0
    col_amount: float = 630.0
    col_markup: float = 690.0
    col_total: float = 762.0
    line_leading: float = 8.4
    wrap_chars: int = 86
    layout_overrides: dict[str, float] = field(default_factory=dict)

    def tuned(self, **overrides: float) -> "WillardLayout":
        """Return a copy with named knobs replaced."""
        data = {**self.layout_overrides, **overrides}
        return replace(self, **{k: v for k, v in data.items() if hasattr(self, k)})


DEFAULT_LAYOUT = WillardLayout()


# Injected into Max system / desk prompts and TOOLS_DOC.
MAX_ESTIMATE_RULES = f"""
== Estimate / invoice format (Rafael {FORMAT_DATE}; Willard area layout) ==
New fabrication uses the Willard area layout. Re-line keeps Header-B
and the old $145/window install unless the founder opts that job in.
- New fabrication: landscape Empire chrome. The default client PDF is
  client_simple: one short line per area plus its client price, an
  Includes line, COM as "Fabric provided by client", then grand total,
  deposit, and balance. No qty/rate/widths/yardage, no Labor/Materials/
  Installation subtotals, no markup. The detailed client variant
  (variant=client) still groups by AREA → LABOR / MATERIALS /
  INSTALLATION with ITEM / DESCRIPTION / QTY / TOTAL. Internal adds
  RATE, AMOUNT (base), MARKUP 20%, TOTAL (client). Designer name and
  markup come from job/quote metadata only.
- COM lines print COM, never $0.00. New-fab track prints as $325/8 ft;
  new-fab install as $245/8 ft.
- New fabrication (lined main drapery + sheers): per-width labor at the
  new_fab_per_width rate, width count = coverage × 2.5 fullness / 54"
  goods (sheers use 110" goods).
- Re-line keeps the existing 48" half-width math, $145/window install
  through 8 ft then $20/ft over, and track_hours only when the founder
  sets that per-quote override. install_per_window still means the
  window rate.
- New-fab track is a complete track per ft (${TRACK_PER_8FT:.0f} per
  {SECTION_FT:.0f} ft prorated, carriers included) on BOTH layers.
  Hourly install/track is unreachable unless the founder sets an
  explicit per-quote override. Default tool calls never pass hours.
- Upholstery estimates keep Description, Qty, Unit, Sq ft, Price/sq ft,
  Total.
- Measurements in fractions only (e.g. 189 3/8"), never decimals.
- Empire Workroom branding unless billed_by is Nelma's. Never print the
  founder's personal name. Never print fabric brand or supplier names; use
  internal fabric codes (V###-Color).
- Email / item lists: one item per line (never a comma-joined paragraph).
"""


def normalize_variant(variant: str | None = None) -> str:
    """Map a caller variant to client_simple (default), client, or internal."""
    raw = str(variant or VARIANT_DEFAULT).strip().lower().replace("-", "_")
    if raw in {VARIANT_INTERNAL, "office", "shop", "workroom"}:
        return VARIANT_INTERNAL
    if raw in {VARIANT_CLIENT, "client_detailed", "detailed", "full"}:
        return VARIANT_CLIENT
    return VARIANT_CLIENT_SIMPLE


def _join_and(parts: Sequence[str]) -> str:
    items = [p for p in parts if p]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])} and {items[-1]}"


def _area_lines(area: dict) -> list[dict]:
    rows: list[dict] = []
    for group in area.get("groups") or []:
        rows.extend(group.get("lines") or [])
    return rows


def simple_area_blurb(area: dict) -> str:
    """One short client line: 'A. Main Drapery: lined ripplefold, … — fabrication, track and installation'."""
    name = format_measurement_text(scrub_brands(str(area.get("name") or "Area").strip()))
    match = re.match(r"^([A-Za-z])\.\s*(.+?)(?:\s*\(([^)]+)\))?\s*$", name)
    if match:
        letter = match.group(1).upper()
        kind = re.sub(r"\s+", " ", match.group(2)).strip().title()
        detail = format_measurement_text((match.group(3) or "").strip())
    else:
        letter = ""
        kind = name.title()
        detail = ""
    lines = _area_lines(area)
    blob = " ".join(
        f"{ln.get('item') or ''} {ln.get('description') or ''} {ln.get('group') or ''}"
        for ln in lines
    ).lower()
    if "sheer" in kind.lower():
        work = "ripplefold"
    elif "lined" in blob or "lining" in blob:
        work = "lined ripplefold"
    else:
        work = "ripplefold"
    scope: list[str] = []
    if any(
        str(ln.get("group") or "") == GROUP_LABOR
        or str(ln.get("item") or "") in {"Drapes", "Sheers"}
        for ln in lines
    ):
        scope.append("fabrication")
    if any(
        str(ln.get("item") or "").lower() == "track" or "track" in str(ln.get("description") or "").lower()
        for ln in lines
    ):
        scope.append("track")
    if any(
        str(ln.get("item") or "").lower() == "install"
        or str(ln.get("group") or "") == GROUP_INSTALLATION
        for ln in lines
    ):
        scope.append("installation")
    head = f"{letter}. {kind}".strip() if letter else kind
    mid = f"{work}, {detail}" if detail else work
    joined = _join_and(scope)
    text = f"{head}: {mid} — {joined}" if joined else f"{head}: {mid}"
    return format_measurement_text(scrub_brands(text))


def simple_includes_line(areas: Sequence[dict]) -> str:
    lines = [ln for area in areas for ln in _area_lines(area)]
    blob = " ".join(str(ln.get("description") or "") + " " + str(ln.get("item") or "") for ln in lines).lower()
    bits: list[str] = []
    if "track" in blob:
        bits.append("track")
    if "install" in blob:
        bits.append("installation")
    if "removal" in blob or "remove" in blob:
        bits.append("removal")
    if not bits:
        return ""
    return f"Includes {_join_and(bits)}."


def simple_com_line(areas: Sequence[dict]) -> str:
    lines = [ln for area in areas for ln in _area_lines(area)]
    if any(is_com_line(ln) for ln in lines):
        return "Fabric provided by client"
    return ""


def client_factor(quote: dict | None = None) -> float:
    meta = _meta(quote)
    raw = meta.get("client_factor")
    if raw is None and quote:
        raw = quote.get("client_factor")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = CLIENT_FACTOR
    return value if value > 0 else CLIENT_FACTOR


def designer_name(quote: dict | None = None) -> str:
    """Designer label from job/quote metadata only. Never infer from a name."""
    sources = [_meta(quote), quote or {}, (quote or {}).get("project") or {}]
    for src in sources:
        if not isinstance(src, dict):
            continue
        for key in ("designer_name", "designer", "designer_label"):
            raw = src.get(key)
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
    return "Designer"


def designer_factor(quote: dict | None = None) -> float:
    """Extra multiplier on the client price for the designer column.

    1.0 means the designer column equals the client price (the 20% is the
    client factor). A value > 1 is an additional designer markup.
    """
    meta = _meta(quote)
    raw = meta.get("designer_markup_factor") or meta.get("designer_factor")
    if raw is None and quote:
        raw = quote.get("designer_markup_factor") or quote.get("designer_factor")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = 1.0
    return value if value > 0 else 1.0


def money_round(value: float) -> float:
    """Half-up to cents so 643.125 → 643.13 (not banker's 643.12)."""
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def apply_client(base: float, quote: dict | None = None) -> float:
    return money_round(float(base) * client_factor(quote))


def apply_designer(base: float, quote: dict | None = None) -> float:
    return money_round(apply_client(base, quote) * designer_factor(quote))


def section_prorate(width_in: float, rate_per_section: float, section_ft: float = SECTION_FT) -> dict:
    """Price a measured run at ``rate`` per ``section_ft`` feet, prorated.

    Whole feet are rounded up (249 5/16\" → 21 ft) then multiplied by
    rate/section_ft (e.g. $325/8 = $40.625/ft, $245/8 = $30.625/ft).
    """
    import math
    feet = int(math.ceil(float(width_in) / 12.0 - 1e-9))
    rate_per_ft = float(rate_per_section) / float(section_ft)
    amount = money_round(feet * rate_per_ft)
    return {
        "amount": amount,
        "method": "section_prorate",
        "width_ft": float(feet),
        "feet": feet,
        "sections": feet / float(section_ft),
        "section_ft": float(section_ft),
        "rate_per_section": float(rate_per_section),
        "rate_per_ft": rate_per_ft,
    }


def founder_hourly_override(opening: dict | None = None) -> bool:
    """True only when the founder set an explicit per-quote hourly override.

    Re-line ``track_hours`` is that historic override. New fabrication
    ignores hours unless ``hourly_override`` / ``founder_hourly`` is set.
    """
    if not opening:
        return False
    if opening.get("hourly_override") in (True, "true", "True", 1, "1"):
        return True
    if opening.get("founder_hourly") in (True, "true", "True", 1, "1"):
        return True
    if opening.get("founder_hourly_override") in (True, "true", "True", 1, "1"):
        return True
    return False


def install_section_price(
    width_in: float,
    *,
    flat: float | None = None,
    hourly: float | None = None,
    override: bool = False,
) -> dict:
    """New-fab removal + install: $245 / 8 ft prorated.

    Hourly is unreachable unless ``override`` is true and ``hourly`` is set.
    """
    if hourly is not None and override:
        hours = float(hourly)
        from app.services.pricing.workroom_rules import rule
        rate = rule("track_labor_per_hour")
        return {
            "amount": money_round(hours * rate),
            "method": "hourly_override",
            "hours": hours,
            "rate": rate,
            "width_ft": float(width_in) / 12.0,
        }
    if flat is not None:
        return {
            "amount": money_round(float(flat)),
            "method": "flat",
            "width_ft": float(width_in) / 12.0,
        }
    from app.services.pricing.workroom_rules import rule
    return section_prorate(width_in, rule("install_per_8ft"), rule("install_section_ft"))


def track_section_price(
    width_in: float,
    *,
    hours: float | None = None,
    flat: float | None = None,
    override: bool = False,
) -> dict:
    """New-fab track: $325 / 8 ft prorated.

    Hourly is unreachable unless ``override`` is true and ``hours`` is set.
    """
    if hours is not None and override:
        from app.services.pricing.workroom_rules import rule
        rate = rule("track_labor_per_hour")
        return {
            "amount": money_round(float(hours) * rate),
            "method": "hourly_override",
            "hours": float(hours),
            "rate": rate,
            "width_ft": float(width_in) / 12.0,
        }
    if flat is not None:
        return {
            "amount": money_round(float(flat)),
            "method": "flat",
            "width_ft": float(width_in) / 12.0,
        }
    from app.services.pricing.workroom_rules import rule
    return section_prorate(width_in, rule("track_per_8ft"), rule("install_section_ft"))


def format_section_desc(kind: str, width_in: float, priced: dict) -> str:
    width = format_inches_plain(width_in)
    width_ft = priced.get("width_ft") or (float(width_in) / 12.0)
    ft_label = _ft_label(width_ft)
    if priced.get("method") == "hourly_override":
        hours = priced.get("hours")
        rate = priced.get("rate")
        return f"{kind} · {width} · {hours:g} hr @ ${float(rate):,.0f} (hourly override)"
    if priced.get("method") == "flat":
        return f"{kind} · {width} · flat ${priced['amount']:,.0f}"
    rate = priced.get("rate_per_section") or 0
    section = priced.get("section_ft") or SECTION_FT
    return (
        f"{kind} · {width} · {ft_label} · "
        f"${float(rate):,.0f} per {section:g} ft section, prorated"
    )


def _ft_label(width_ft: float) -> str:
    whole = int(round(width_ft * 16))
    inches = whole  # already feet; show as a short feet+fraction string
    # width_ft is feet; display as e.g. 8 ft or 13 1/3 ft → keep simple.
    if abs(width_ft - round(width_ft)) < 1e-6:
        return f"{int(round(width_ft))} ft"
    # Common 8-ft prorate widths: 160" = 13 1/3 ft. Show two decimals only when
    # we cannot make a clean fraction of a foot; still never print inch decimals.
    numer = int(round(width_ft * 12))
    feet, rem = divmod(numer, 12)
    if rem == 0:
        return f"{feet} ft"
    from fractions import Fraction
    frac = Fraction(rem, 12).limit_denominator(12)
    if feet:
        return f"{feet} {frac.numerator}/{frac.denominator} ft"
    return f"{frac.numerator}/{frac.denominator} ft"


def classify_group(item: dict) -> str:
    """Map a line into Labor / Materials / Installation.

    Willard area layout: track hardware is MATERIALS; removal+install is
    INSTALLATION. Hourly track labor is INSTALLATION only as an override.
    """
    explicit = str(item.get("group") or item.get("line_group") or "").strip()
    if explicit:
        title = explicit.title()
        if title in GROUP_ORDER:
            return title
        low = explicit.lower()
        if low in {"installation", "install"}:
            return GROUP_INSTALLATION
        if low in {"materials", "material"}:
            return GROUP_MATERIALS
        if low in {"labor", "preparation", "construction"}:
            return GROUP_LABOR
    cat = str(item.get("category") or "").strip().lower()
    unit = str(item.get("unit") or "").strip().lower()
    desc = str(item.get("description") or "").lower()
    item_name = str(item.get("item") or "").lower()
    if item_name == "install" or cat in {"installation", "install"}:
        return GROUP_INSTALLATION
    if any(w in desc for w in (
        "removal and installation", "removal + install", "reinstall",
        "track re-center",
    )):
        return GROUP_INSTALLATION
    if item_name in {"track", "batons", "lining", "fabric", "hem", "bump"}:
        return GROUP_MATERIALS
    if cat in {"materials", "material", "com_fabric", "fabric"} or unit in {"yd", "yard", "yards", "yds"}:
        return GROUP_MATERIALS
    if any(w in desc for w in (
        "lining", "bump", "interlining", "carrier", "baton",
        "complete ripplefold track", "fabric ·", "com (", "napped",
    )) and "removal" not in desc and "re-line" not in desc and "reline" not in desc:
        return GROUP_MATERIALS
    if unit in {"hr", "hour", "hours"} and "override" in desc:
        return GROUP_INSTALLATION
    return GROUP_LABOR


def classify_area(item: dict, *, default: str = AREA_MAIN_DRAPERY) -> str:
    for key in ("area", "section", "section_name"):
        raw = item.get(key)
        if isinstance(raw, str) and raw.strip():
            return _canonical_area(raw)
    room = str(item.get("room") or "").strip()
    if room:
        return _canonical_area(room)
    desc = str(item.get("description") or "")
    if re.search(r"\bsheer", desc, re.I):
        return AREA_SHEERS
    return default


def _canonical_area(name: str) -> str:
    stripped = name.strip()
    # Keep labeled bands: "A. MAIN DRAPERY (96\" opening)"
    if re.match(r"^[A-Z]\.\s+", stripped):
        return stripped
    low = re.sub(r"\s+", " ", stripped).lower()
    if low in {"sheer", "sheers", "ripplefold sheers"}:
        return AREA_SHEERS
    if low in {"main drapery", "drapery", "main", "panels", "side panels"}:
        return AREA_MAIN_DRAPERY
    if "sheer" in low:
        return AREA_SHEERS
    if "drapery" in low or "drape" in low:
        return AREA_MAIN_DRAPERY
    return stripped


def group_willard_areas(items: Sequence[dict]) -> list[dict]:
    """Group lines into areas → Labor / Materials / Installation."""
    order: list[str] = []
    buckets: dict[str, list[dict]] = {}
    for raw in items or []:
        if not isinstance(raw, dict):
            continue
        if _skip_structure_row(raw):
            continue
        area = classify_area(raw)
        if area not in buckets:
            order.append(area)
            buckets[area] = []
        line = dict(raw)
        line["area"] = area
        line["group"] = classify_group(line)
        buckets[area].append(line)

    areas = []
    for name in order:
        lines = buckets[name]
        groups = []
        for gname in GROUP_ORDER:
            grouped = [ln for ln in lines if ln["group"] == gname]
            if not grouped:
                continue
            sub = money_round(sum(_base_amount(ln) for ln in grouped))
            groups.append({"name": gname, "lines": grouped, "subtotal": sub})
        areas.append({
            "name": name,
            "groups": groups,
            "subtotal": money_round(sum(g["subtotal"] for g in groups)),
        })
    return areas


def packet_to_areas(packet: dict) -> list[dict]:
    """Prefer packet['areas']; else lift rooms / openings into Willard areas."""
    if packet.get("areas"):
        return list(packet["areas"])
    items = []
    for room in packet.get("rooms") or []:
        room_name = room.get("room") or room.get("name") or ""
        for group in room.get("groups") or []:
            gname = group.get("name") or GROUP_LABOR
            for line in group.get("lines") or []:
                row = dict(line)
                row.setdefault("room", room_name)
                row.setdefault("group", gname)
                if not row.get("area"):
                    desc = str(row.get("description") or "")
                    row["area"] = AREA_SHEERS if re.search(r"\bsheer", desc, re.I) else (
                        AREA_MAIN_DRAPERY if room_name else AREA_MAIN_DRAPERY
                    )
                    if room_name and row["area"] in {AREA_MAIN_DRAPERY, AREA_SHEERS}:
                        # Keep the area name canonical; room stays on the line.
                        pass
                items.append(row)
    if items:
        return group_willard_areas(items)
    return group_willard_areas(packet.get("line_items") or packet.get("items") or [])


def quote_to_areas(quote: dict) -> list[dict]:
    meta = _meta(quote)
    if isinstance(meta.get("willard_areas"), list) and meta["willard_areas"]:
        return meta["willard_areas"]
    if quote.get("areas"):
        return list(quote["areas"])
    if quote.get("rooms"):
        return packet_to_areas(quote)
    return group_willard_areas(quote.get("line_items") or quote.get("items") or [])


def is_upholstery_quote(quote: dict) -> bool:
    items = quote.get("line_items") or quote.get("items") or []
    for it in items:
        if not isinstance(it, dict):
            continue
        if it.get("sq_ft") not in (None, "") or it.get("price_per_sqft") not in (None, ""):
            return True
        snap = it.get("pricing_snapshot") or {}
        if isinstance(snap, dict) and snap.get("sq_ft") not in (None, ""):
            return True
        unit = str(it.get("unit") or "").lower()
        if unit in {"sqft", "sq ft", "sf"}:
            return True
    return False


def uses_willard_layout(quote: dict | None) -> bool:
    """True for new-fab Willard estimates. Re-line Header-B stays off."""
    if not quote:
        return False
    if is_upholstery_quote(quote):
        return False
    meta = _meta(quote)
    fmt = str(meta.get("estimate_format") or quote.get("estimate_format") or "").lower()
    if fmt in {FORMAT_ID, "willard", "rafael", "rafael_willard"}:
        return True
    if meta.get("willard_areas"):
        return True
    areas = quote.get("areas") or []
    if areas:
        names = {
            str(g.get("name") or "")
            for area in areas
            for g in (area.get("groups") or [])
        }
        if names & {"Preparation", "Construction"}:
            return False
        if names & set(GROUP_ORDER):
            return True
    return False


def scrub_brands(text: str) -> str:
    """Never print mill / supplier names. Keep V###-Color codes."""
    s = text or ""
    codes = _FABRIC_CODE_RE.findall(s)
    s = _BRAND_RE.sub("", s)
    s = _SUPPLIER_RE.sub("", s)
    s = re.sub(r"\s*·\s*·\s*", " · ", s)
    s = re.sub(r"\s{2,}", " ", s)
    s = s.strip(" ·,;")
    if codes and not _FABRIC_CODE_RE.search(s):
        s = (s + " · " if s else "") + codes[0].strip()
    return s


def format_measurement_text(text: str) -> str:
    from app.services.estimates.mclean_estimate_pdf import inches_to_fractions
    return plain_fractions(inches_to_fractions(text or ""))


def format_item_list(items: Iterable[Any]) -> str:
    """One item per line for email / chat. Never a comma-joined paragraph."""
    lines: list[str] = []
    for raw in items or []:
        if raw is None:
            continue
        if isinstance(raw, dict):
            text = str(raw.get("description") or raw.get("name") or raw.get("title") or "").strip()
        else:
            text = str(raw).strip()
        if not text:
            continue
        for part in re.split(r"[\n;]+", text):
            bit = part.strip().lstrip("-• ").strip()
            if not bit:
                continue
            # A comma list of several short items → one per line.
            if ", " in bit and not re.search(r"\d,\d{3}", bit) and len(bit) < 160:
                pieces = [p.strip() for p in bit.split(",") if p.strip()]
                if len(pieces) >= 2 and all(len(p) < 60 for p in pieces):
                    lines.extend(pieces)
                    continue
            lines.append(bit)
    return "\n".join(lines)


def money(value: Any) -> str:
    if value is None:
        return "COM"
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "COM"


def is_com_line(item: dict) -> bool:
    if item.get("com") is True:
        return True
    desc = str(item.get("description") or "").lower()
    item_name = str(item.get("item") or "").lower()
    amounts = []
    for key in ("base_amount", "client_amount", "amount"):
        if item.get(key) is not None:
            try:
                amounts.append(float(item[key]))
            except (TypeError, ValueError):
                pass
    if any(abs(v) > 1e-9 for v in amounts):
        return False
    if "com" in desc:
        return True
    if item.get("base_amount") is None and item.get("client_amount") is None:
        if item_name in {"fabric", "hem"}:
            return True
    return False


def format_rate_label(item: dict) -> str:
    """Willard area layout: section rates print as $245/8 ft and $325/8 ft."""
    if is_com_line(item):
        return ""
    raw = item.get("base_rate", item.get("rate", item.get("unit_price")))
    if raw is None:
        return ""
    try:
        rate = float(raw)
    except (TypeError, ValueError):
        return ""
    install_ft = INSTALL_PER_8FT / SECTION_FT
    track_ft = TRACK_PER_8FT / SECTION_FT
    if abs(rate - install_ft) < 1e-6 or abs(rate - INSTALL_PER_8FT) < 1e-6:
        if str(item.get("unit") or "").lower() in {"ft", "lf"} or "install" in str(item.get("item") or "").lower():
            return f"${INSTALL_PER_8FT:.0f}/{SECTION_FT:.0f} ft"
    if abs(rate - track_ft) < 1e-6 or abs(rate - TRACK_PER_8FT) < 1e-6:
        return f"${TRACK_PER_8FT:.0f}/{SECTION_FT:.0f} ft"
    desc = str(item.get("description") or "").lower()
    if "prorated" in desc and "install" in desc:
        return f"${INSTALL_PER_8FT:.0f}/{SECTION_FT:.0f} ft"
    if "prorated" in desc and "track" in desc:
        return f"${TRACK_PER_8FT:.0f}/{SECTION_FT:.0f} ft"
    return money(rate)


def item_label(item: dict) -> str:
    raw = str(item.get("item") or "").strip()
    if raw:
        return raw
    desc = str(item.get("description") or "").lower()
    group = classify_group(item)
    if group == GROUP_INSTALLATION:
        return "Install"
    if "sheer" in desc:
        return "Sheers"
    if "lining" in desc:
        return "Lining"
    if "baton" in desc:
        return "Batons"
    if "track" in desc:
        return "Track"
    if "hem" in desc:
        return "Hem"
    if "fabric" in desc or "com" in desc:
        return "Fabric"
    if "bump" in desc:
        return "Bump"
    if group == GROUP_LABOR:
        return "Drapes"
    return "Item"


def markup_label(item: dict, quote: dict | None = None) -> str:
    if is_com_line(item) or _base_amount(item) == 0:
        return ""
    return f"{(client_factor(quote) - 1.0) * 100:.2f}%"


def totals_from_areas(areas: Sequence[dict], quote: dict | None = None) -> dict:
    base = money_round(sum(float(a.get("subtotal") or 0) for a in areas))
    client = apply_client(base, quote)
    designer = apply_designer(base, quote)
    deposit_pct = DEFAULT_DEPOSIT_PERCENT
    if quote is not None:
        try:
            deposit_pct = float(quote.get("deposit_percent") or DEFAULT_DEPOSIT_PERCENT)
        except (TypeError, ValueError):
            deposit_pct = DEFAULT_DEPOSIT_PERCENT
    client_deposit = money_round(client * deposit_pct / 100.0)
    return {
        "base": base,
        "client": client,
        "designer": designer,
        "deposit_percent": deposit_pct,
        "deposit": client_deposit,
        "balance": money_round(client - client_deposit),
        "paid": _paid(quote),
    }


def display_amount(base: float, variant: str, quote: dict | None = None) -> float:
    if variant == VARIANT_INTERNAL:
        return money_round(float(base))
    return apply_client(base, quote)


def _base_amount(it: dict) -> float:
    for key in ("base_amount", "base", "amount", "subtotal", "final_price"):
        if it.get(key) is not None:
            try:
                val = float(it[key])
                if key == "final_price" and not it.get("price_overridden") and it.get("amount") is not None:
                    continue
                if val or key in {"amount", "subtotal", "base_amount", "base"}:
                    if key == "final_price" and it.get("price_overridden"):
                        return money_round(val)
            except (TypeError, ValueError):
                pass
    if it.get("price_overridden") and it.get("final_price") is not None:
        try:
            return money_round(float(it["final_price"]))
        except (TypeError, ValueError):
            return 0.0
    amount = it.get("amount")
    if amount is None:
        amount = it.get("subtotal")
    if amount is None:
        try:
            qty = float(it.get("quantity") or 1)
            rate = it.get("base_rate", it.get("rate", it.get("unit_price")))
            amount = money_round(qty * float(rate or 0))
        except (TypeError, ValueError):
            amount = 0.0
    try:
        return float(amount or 0)
    except (TypeError, ValueError):
        return 0.0


def _skip_structure_row(it: dict) -> bool:
    unit = str(it.get("unit") or "").lower()
    cat = str(it.get("category") or "").lower()
    desc = str(it.get("description") or "").strip().upper()
    if unit in {"section", "note", "subtotal"}:
        return True
    if cat in {"section_header", "section", "subtotal", "subtotal_row", "note"}:
        return True
    if desc.startswith("SECTION") or desc.startswith("SUBTOTAL"):
        return True
    return False


def _meta(quote: dict | None) -> dict:
    if not quote:
        return {}
    meta = quote.get("metadata")
    return meta if isinstance(meta, dict) else {}


def _paid(quote: dict | None) -> float:
    if not quote:
        return 0.0
    payments = quote.get("payments")
    if isinstance(payments, list) and payments:
        total = 0.0
        for pay in payments:
            if isinstance(pay, dict):
                try:
                    total += float(pay.get("amount") or pay.get("paid") or 0)
                except (TypeError, ValueError):
                    pass
        return money_round(total)
    for key in ("deposit_paid", "amount_paid", "paid_to_date"):
        if quote.get(key) not in (None, ""):
            try:
                return money_round(float(quote[key]))
            except (TypeError, ValueError):
                pass
    return 0.0


def willard_metadata(packet: dict, *, designer: str | None = None) -> dict:
    return {
        "estimate_format": FORMAT_ID,
        "estimate_layout": "willard",
        "client_factor": client_factor(packet),
        "designer_name": designer or designer_name(packet),
        "designer_markup_factor": designer_factor(packet),
        "install_rule": f"${INSTALL_PER_8FT:.0f} per {SECTION_FT:.0f} ft section, prorated",
        "track_rule": f"${TRACK_PER_8FT:.0f} per {SECTION_FT:.0f} ft section, prorated",
        "reference_docs": list(REFERENCE_DOCS),
        "willard_format_pending": WILLARD_FORMAT_PENDING,
        "willard_areas": packet.get("areas") or [],
    }


# Mock opening uses the REV C generator dimensions so Max's tool can
# reproduce that structure and totals. Names are invented — not a live job.
MOCK_MAIN_WIDTH_IN = 249 + 5 / 16
MOCK_FINISHED_LENGTH_IN = 93 + 5 / 16
MOCK_SHEER_COVERAGE_IN = 189 + 3 / 8
MOCK_WALL_HEIGHT_IN = 95 + 13 / 16
# Half-up cents on the REV C rate card + mock dimensions.
# The draft JSON summed 4740.35 because 853.125 and 643.125 were
# rounded in opposite directions; Max uses consistent half-up.
MOCK_BASE_TOTAL = 4740.36
MOCK_CLIENT_TOTAL = 5688.43
MOCK_DESIGNER_SHARE = 948.07


def mock_willard_line_items() -> list[dict]:
    """REV C *structure* with invented names. Same dimensions as the rate-card fixture."""
    from app.services.estimates.workroom_packet import build_packet
    packet = build_packet(mock_drapery_spec())
    items = []
    for area in packet.get("areas") or []:
        for group in area.get("groups") or []:
            for line in group.get("lines") or []:
                items.append(dict(line))
    return items


def mock_willard_document(**overrides: Any) -> dict:
    """Quote-shaped mock for the Willard renderer. Invented names only."""
    from app.services.estimates.workroom_packet import build_packet
    packet = build_packet(mock_drapery_spec())
    items = mock_willard_line_items()
    doc = {
        "quote_number": "EST-MOCK-WILLARD",
        "date": "2026-10-23",
        "created_at": "2026-10-23",
        "billed_by": "empire_workroom",
        "customer_name": "Mock Design Studio",
        "project_name": "Mock Office Wall",
        "rev": "C",
        "estimate_format": FORMAT_ID,
        "client_factor": CLIENT_FACTOR,
        "designer_name": "Designer",
        "designer_share_20pct": packet.get("designer_share_20pct"),
        "line_items": items,
        "areas": packet.get("areas") or [],
        "notes": "Mock data only. Not a real client.",
        "terms": "50% deposit to begin · balance due on completion.",
        "deposit_percent": 50,
        "specifications": [
            f'Mock opening {format_inches_plain(MOCK_MAIN_WIDTH_IN)} W × {format_inches_plain(MOCK_WALL_HEIGHT_IN)} H',
            "Main drapery covers the full opening, lined ripplefold, 2.5× on 54\" goods",
            f'Sheers cover {format_inches_plain(MOCK_SHEER_COVERAGE_IN)}, 2.5× on 110\" goods',
            "Install $245 base per 8 ft, prorated; track $325 per 8 ft, prorated, carriers included",
        ],
        "metadata": {"estimate_format": FORMAT_ID, "willard_format_pending": True},
    }
    doc.update(overrides)
    return doc


def mock_drapery_spec(**overrides: Any) -> dict:
    """Openings spec for draft_estimate_and_presentation. Mock data only.

    Dimensions match the REV C generator fixture (249 5/16\" wall, 93 5/16\"
    FL, 189 3/8\" sheers) so Max's tool can reproduce that structure and
    totals. Client / project names are invented.
    """
    spec = {
        "quote_number": "EST-MOCK-WILLARD",
        "date": "2026-10-23",
        "billed_by": "empire_workroom",
        "estimate_format": FORMAT_ID,
        "client_factor": CLIENT_FACTOR,
        "designer_name": "Designer",
        "designer_markup_factor": 1.0,
        "prepared_for": {
            "company": "Mock Design Studio",
            "attn": "Mock Designer",
            "email": "mock-designer@example.test",
            "phone": "(000) 000-0000",
            "address": "100 Mock Street, Test City, MD",
        },
        "project": {
            "name": "Mock Office Wall",
            "phase": "Main Drapery + Sheers",
            "address": "200 Mock Avenue, Test City, MD",
            "sidemark": "MOCK-PROOF",
            "scope": "New lined ripplefold + sheers · 8 ft-section prorated install",
        },
        "notes": "Mock data only. Not a real client.",
        "openings": [
            {
                "room": "Office",
                "area": f'A. MAIN DRAPERY (wall to wall {format_inches_plain(MOCK_MAIN_WIDTH_IN)})',
                "mark": "OF",
                "width": MOCK_MAIN_WIDTH_IN,
                "height": MOCK_WALL_HEIGHT_IN,
                "finished_length": MOCK_FINISHED_LENGTH_IN,
                "panels": 2,
                "fabrication": "new",
                "reline": False,
                "com": True,
                "hem": True,
                "batons": 2,
                "control": "center",
                "fullness": 2.5,
                "goods_width": 54,
                "sheers": {
                    "area": f'B. SHEERS ({format_inches_plain(MOCK_SHEER_COVERAGE_IN)} across glass + door)',
                    "coverage": MOCK_SHEER_COVERAGE_IN,
                    "fullness": 2.5,
                    "goods_width": 110,
                    "control": "center",
                    "com": True,
                    "batons": 2,
                },
            }
        ],
    }
    spec.update(overrides)
    return spec
