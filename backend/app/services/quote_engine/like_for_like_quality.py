"""Like-for-like quote quality comparison.

Max used to flag estimates as "50% below average" by comparing a job total
against an unrelated average (whole prior job, or every quote on disk).
That falsely blocked scoped work such as Le Midi Phase 2 office-only
drapery versus the Phase 1 whole-house ticket.

This module compares by product/scope category and size-normalized unit
rate (per width, per linear foot, or per item). It flags only when enough
same-category history exists. The block reason lists the comparables used.

Founder-review block is preserved: a flag is always a block. Nothing here
auto-unblocks a quote.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

logger = logging.getLogger("max.quality")

# Flag only when the unit rate is at least this far below the like-for-like
# average. 0.50 = "50% below average".
BELOW_AVERAGE_THRESHOLD = 0.50
MIN_COMPARABLES = 3

# Skip junk / placeholder quotes when loading history.
MIN_SCOPE_AMOUNT = 1.0

# Most-specific first. Sheers must not match generic drapery.
# Banquette must be classified before bench ("banquette bench" etc.).
_SCOPE_RULES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("sheers", "width", (
        "sheer", "sheers", "voile", "sunscreensheer",
    )),
    ("drapery_ripplefold", "width", (
        "ripplefold", "ripple fold", "ripple-fold", "ripple_fold",
    )),
    ("drapery_pinch_pleat", "width", (
        "pinch pleat", "pinch-pleat", "french pleat", "euro pleat",
        "goblet pleat", "cartridge pleat",
    )),
    ("roman_shade", "item", ("roman shade", "roman shades", "romans")),
    ("roller_shade", "item", ("roller shade", "roller shades")),
    ("valance", "lf", ("valance", "valances")),
    ("cornice", "lf", ("cornice", "cornices")),
    ("banquette", "lf", ("banquette", "booth", "banquettes")),
    ("upholstery_bench", "lf", ("bench", "benches", "window seat")),
    ("drapery", "width", (
        "drapery", "draperies", "drape", "drapes", "curtain", "curtains",
        "panel", "panels", "window treatment",
    )),
)

_FAMILY = {
    "drapery_ripplefold": "drapery",
    "drapery_pinch_pleat": "drapery",
    "drapery": "drapery",
    "sheers": "sheers",
    "roman_shade": "roman_shade",
    "roller_shade": "roller_shade",
    "valance": "valance",
    "cornice": "cornice",
    "banquette": "banquette",
    "upholstery_bench": "upholstery_bench",
}

_WIDTH_UNITS = {"width", "widths", "wd", "wds", "panel", "panels"}
_LF_UNITS = {"lf", "lin ft", "lin. ft", "linear ft", "linear_ft", "linear foot", "linear feet"}

_WIDTHS_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:widths?|wds?)\b",
    re.IGNORECASE,
)
_LF_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:lin(?:ear)?\.?\s*(?:ft|feet)|lf)\b",
    re.IGNORECASE,
)


@dataclass
class Comparable:
    quote_id: str
    quote_number: str
    label: str
    category: str
    unit: str
    size: float
    amount: float
    unit_rate: float

    def render(self) -> str:
        return (
            f"{self.quote_number or self.quote_id} {self.label}: "
            f"${self.unit_rate:,.2f}/{self.unit} "
            f"({_fmt_size(self.size, self.unit)}, ${self.amount:,.2f})"
        )


@dataclass
class CategoryComparison:
    category: str
    unit: str
    size: float
    amount: float
    unit_rate: float
    comparables: list[Comparable] = field(default_factory=list)
    average_unit_rate: Optional[float] = None
    below_ratio: Optional[float] = None
    flagged: bool = False
    skip_reason: Optional[str] = None


@dataclass
class LikeForLikeResult:
    flagged: bool
    blocked: bool
    reasons: list[str] = field(default_factory=list)
    comparisons: list[CategoryComparison] = field(default_factory=list)

    def never_auto_unblocks(self) -> bool:
        """A flag is a founder-review block. Callers must not clear it."""
        return (not self.flagged) or self.blocked


def classify_scope(item: dict, extra_text: str = "") -> Optional[str]:
    """Return the most specific scope category for a line/room item."""
    blob = _item_text(item, extra_text)
    if not blob:
        return None
    for category, _unit, needles in _SCOPE_RULES:
        if any(needle in blob for needle in needles):
            return category
    return None


def size_unit_for(category: str) -> str:
    for cat, unit, _needles in _SCOPE_RULES:
        if cat == category:
            return unit
    return "item"


def extract_size(item: dict, category: str) -> float:
    """Size in the category's unit (widths, LF, or item count)."""
    unit = size_unit_for(category)
    explicit = _explicit_size(item, unit)
    if explicit > 0:
        return explicit

    text = _item_text(item)
    if unit == "width":
        match = _WIDTHS_RE.search(text)
        if match:
            return float(match.group(1))
        computed = _widths_from_window(item)
        if computed > 0:
            return computed
    if unit == "lf":
        match = _LF_RE.search(text)
        if match:
            return float(match.group(1))
        inches = _first_number(item, (
            "width_in", "window_width_in", "length_in", "width", "length",
        ))
        if inches and inches > 12:
            return round(inches / 12.0, 4)
        if inches and inches > 0:
            return inches
    qty = _as_float(item.get("quantity"))
    if qty and qty > 0:
        return qty
    return 1.0 if unit == "item" else 0.0


def item_amount(item: dict) -> float:
    for key in ("amount", "price", "subtotal", "final_price", "proposed_price"):
        value = _as_float(item.get(key))
        if value and value > 0:
            return value
    qty = _as_float(item.get("quantity"), 1.0) or 1.0
    rate = _as_float(item.get("rate") or item.get("unit_price") or item.get("unit_price_used"))
    if rate and rate > 0:
        return round(qty * rate, 2)
    return 0.0


def extract_scope_rates(
    quote: dict,
    *,
    categories: Optional[Iterable[str]] = None,
) -> dict[str, dict[str, float]]:
    """Roll line/room items into per-category amount + size + unit_rate."""
    wanted = set(categories) if categories else None
    buckets: dict[str, dict[str, float]] = {}
    for item in iter_scope_items(quote):
        # Classify from the item only. Project-level text on a mixed
        # Phase 1 job must not paint every line as "drapery".
        category = classify_scope(item)
        if not category:
            continue
        if wanted is not None and category not in wanted:
            if _FAMILY.get(category) not in wanted:
                continue
        amount = item_amount(item)
        size = extract_size(item, category)
        if amount < MIN_SCOPE_AMOUNT or size <= 0:
            continue
        bucket = buckets.setdefault(category, {"amount": 0.0, "size": 0.0, "unit_rate": 0.0})
        bucket["amount"] = round(bucket["amount"] + amount, 2)
        bucket["size"] = round(bucket["size"] + size, 4)
    for category, bucket in buckets.items():
        if bucket["size"] > 0:
            bucket["unit_rate"] = round(bucket["amount"] / bucket["size"], 2)
    return buckets


def iter_scope_items(quote: dict) -> Iterable[dict]:
    for item in quote.get("line_items") or quote.get("items") or []:
        if isinstance(item, dict):
            yield item
    for room in quote.get("rooms") or []:
        if not isinstance(room, dict):
            continue
        room_name = room.get("name") or room.get("room") or ""
        for key in ("windows", "upholstery", "items"):
            for raw in room.get(key) or []:
                if isinstance(raw, dict):
                    yield {**raw, "_room": room_name}
    tiers = quote.get("tiers") or {}
    if isinstance(tiers, dict):
        for tier in tiers.values():
            if isinstance(tier, dict):
                for raw in tier.get("items") or []:
                    if isinstance(raw, dict):
                        yield raw


def load_history_quotes(
    quotes_dir: Optional[str] = None,
    *,
    exclude_id: Optional[str] = None,
    injected: Optional[list[dict]] = None,
) -> list[dict]:
    if injected is not None:
        return [q for q in injected if _usable_history(q, exclude_id)]
    directory = quotes_dir or _default_quotes_dir()
    if not directory or not os.path.isdir(directory):
        return []
    loaded: list[dict] = []
    try:
        names = os.listdir(directory)
    except OSError as exc:
        logger.debug("Quote history dir unreadable: %s", exc)
        return []
    for fname in names:
        if not fname.endswith(".json") or fname.startswith("_") or "_verification" in fname:
            continue
        path = os.path.join(directory, fname)
        try:
            with open(path) as handle:
                quote = json.load(handle)
        except Exception:
            continue
        if isinstance(quote, dict) and _usable_history(quote, exclude_id):
            loaded.append(quote)
    return loaded


def evaluate_like_for_like(
    quote: dict,
    *,
    history: Optional[list[dict]] = None,
    quotes_dir: Optional[str] = None,
    min_comparables: int = MIN_COMPARABLES,
    below_threshold: float = BELOW_AVERAGE_THRESHOLD,
) -> LikeForLikeResult:
    """Compare this quote's scoped unit rates against like-for-like history.

    Never auto-unblocks: flagged implies blocked.
    """
    if not isinstance(quote, dict):
        return LikeForLikeResult(flagged=False, blocked=False)

    current_scopes = extract_scope_rates(quote)
    if not current_scopes:
        # No classifiable scope — do not fall back to whole-job average.
        return LikeForLikeResult(flagged=False, blocked=False)

    past = history if history is not None else load_history_quotes(
        quotes_dir,
        exclude_id=str(quote.get("id") or "") or None,
    )

    comparisons: list[CategoryComparison] = []
    reasons: list[str] = []
    flagged = False

    for category, bucket in current_scopes.items():
        comparison = _compare_category(
            quote,
            category,
            bucket,
            past,
            min_comparables=min_comparables,
            below_threshold=below_threshold,
        )
        comparisons.append(comparison)
        if comparison.flagged:
            flagged = True
            reasons.append(_block_reason(comparison))

    return LikeForLikeResult(
        flagged=flagged,
        blocked=flagged,  # founder-review block; never auto-unblock
        reasons=reasons,
        comparisons=comparisons,
    )


def format_block_message(result: LikeForLikeResult) -> str:
    if not result.flagged:
        return ""
    return " ".join(result.reasons)


def run_quote_quality_gate(
    quote: dict,
    *,
    quotes_dir: Optional[str] = None,
    comparable_quotes: Optional[list[dict]] = None,
    founder_override: bool = False,
):
    """The production quote-create / quote-send quality door.

    Both `/quotes` create and send call this. Tests must enter here — not a
    parallel simulator — so a mock office drapery and an underpriced twin
    exercise the same gate the founder hits.
    """
    from app.services.max.response_quality_engine import Channel, quality_engine

    ctx: dict[str, Any] = {"quote_data": quote}
    if quotes_dir is not None:
        ctx["quotes_dir"] = quotes_dir
    if comparable_quotes is not None:
        ctx["comparable_quotes"] = comparable_quotes
    # Match the production call shape so tests that stub
    # quality_engine.validate(content, channel, context) still bind.
    kwargs = {"channel": Channel.QUOTE, "context": ctx}
    if founder_override:
        kwargs["founder_override"] = True
    return quality_engine.validate(json.dumps(quote, default=str), **kwargs)


def _compare_category(
    quote: dict,
    category: str,
    bucket: dict[str, float],
    history: list[dict],
    *,
    min_comparables: int,
    below_threshold: float,
) -> CategoryComparison:
    unit = size_unit_for(category)
    comparison = CategoryComparison(
        category=category,
        unit=unit,
        size=bucket["size"],
        amount=bucket["amount"],
        unit_rate=bucket["unit_rate"],
    )
    comparables = _collect_comparables(history, category)
    comparison.comparables = comparables
    if len(comparables) < min_comparables:
        comparison.skip_reason = (
            f"insufficient_history:{len(comparables)}<{min_comparables}"
        )
        return comparison

    average = sum(row.unit_rate for row in comparables) / len(comparables)
    comparison.average_unit_rate = round(average, 2)
    if average <= 0:
        comparison.skip_reason = "zero_average"
        return comparison

    below = (average - bucket["unit_rate"]) / average
    comparison.below_ratio = below
    if below >= below_threshold:
        comparison.flagged = True
    return comparison


def _collect_comparables(history: list[dict], category: str) -> list[Comparable]:
    family = _FAMILY.get(category, category)
    rows: list[Comparable] = []
    for past in history:
        scopes = extract_scope_rates(past)
        chosen = _pick_history_scope(scopes, category, family)
        if not chosen:
            continue
        hist_category, hist = chosen
        rows.append(Comparable(
            quote_id=str(past.get("id") or ""),
            quote_number=str(past.get("quote_number") or past.get("id") or ""),
            label=_history_label(past, hist_category),
            category=hist_category,
            unit=size_unit_for(hist_category),
            size=hist["size"],
            amount=hist["amount"],
            unit_rate=hist["unit_rate"],
        ))
    return rows


def _pick_history_scope(
    scopes: dict[str, dict[str, float]],
    category: str,
    family: str,
) -> Optional[tuple[str, dict[str, float]]]:
    if category in scopes:
        return category, scopes[category]
    # Specific current category may use generic family history (drapery),
    # but never a different product family (sheers / bench / banquette).
    if category != family and family in scopes:
        return family, scopes[family]
    if category == "drapery":
        # Generic drapery may use ripplefold / pinch-pleat history.
        for sibling in ("drapery_ripplefold", "drapery_pinch_pleat"):
            if sibling in scopes:
                return sibling, scopes[sibling]
    return None


def _block_reason(comparison: CategoryComparison) -> str:
    avg = comparison.average_unit_rate or 0.0
    pct = max(comparison.below_ratio or 0.0, 0.0)
    used = comparison.comparables
    listed = "; ".join(row.render() for row in used)
    return (
        f"{comparison.category} ${comparison.unit_rate:,.2f}/{comparison.unit} "
        f"is {pct:.0%} below like-for-like average ${avg:,.2f}/{comparison.unit} "
        f"({len(used)} comparables). BLOCKED — founder review required. "
        f"Comparables used: {listed}."
    )


def _history_label(quote: dict, category: str) -> str:
    parts = [
        quote.get("project_name") or "",
        quote.get("customer_name") or "",
        category.replace("_", " "),
    ]
    return " — ".join(p for p in parts if p).strip(" —")


def _usable_history(quote: dict, exclude_id: Optional[str]) -> bool:
    if quote.get("is_test"):
        return False
    qid = str(quote.get("id") or "")
    if exclude_id and qid and qid == str(exclude_id):
        return False
    status = str(quote.get("status") or "").lower()
    if status in {"cancelled", "canceled", "void"}:
        return False
    return True


def _default_quotes_dir() -> str:
    try:
        from app.services.data_paths import quotes_data_dir
        return str(quotes_data_dir())
    except Exception:
        return os.path.expanduser("~/empire-repo/backend/data/quotes")


def _item_text(item: dict, extra: str = "") -> str:
    pieces = [
        extra,
        item.get("description"),
        item.get("name"),
        item.get("type"),
        item.get("item_type"),
        item.get("style"),
        item.get("item_style"),
        item.get("category"),
        item.get("product_category"),
        item.get("product"),
        item.get("treatment"),
        item.get("heading"),
        item.get("_room"),
        item.get("room"),
        item.get("area"),
    ]
    return " ".join(str(p).lower() for p in pieces if p)


def _explicit_size(item: dict, unit: str) -> float:
    if unit == "width":
        for key in ("widths", "num_widths", "width_count"):
            value = _as_float(item.get(key))
            if value and value > 0:
                return value
        item_unit = str(item.get("unit") or "").lower()
        qty = _as_float(item.get("quantity"))
        if qty and qty > 0 and item_unit in _WIDTH_UNITS:
            return qty
    if unit == "lf":
        for key in ("linear_ft", "length_ft", "lf", "lineal_ft"):
            value = _as_float(item.get(key))
            if value and value > 0:
                return value
        item_unit = str(item.get("unit") or "").lower()
        qty = _as_float(item.get("quantity"))
        if qty and qty > 0 and item_unit in _LF_UNITS:
            return qty
    if unit == "item":
        qty = _as_float(item.get("quantity"))
        if qty and qty > 0:
            return qty
    return 0.0


def _widths_from_window(item: dict) -> float:
    width = _first_number(item, (
        "window_width_in", "width_in", "finished_width", "width",
    ))
    if not width or width <= 0:
        return 0.0
    fullness = _as_float(item.get("fullness"), 2.5) or 2.5
    fabric = _as_float(item.get("fabric_width_in") or item.get("fabric_width"), 54.0) or 54.0
    if fullness <= 0 or fabric <= 0:
        return 0.0
    import math
    return float(math.ceil(width * fullness / fabric))


def _first_number(item: dict, keys: tuple[str, ...]) -> float:
    for key in keys:
        value = _as_float(item.get(key))
        if value and value > 0:
            return value
        inputs = item.get("inputs")
        if isinstance(inputs, dict):
            value = _as_float(inputs.get(key))
            if value and value > 0:
                return value
    return 0.0


def _as_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _fmt_size(size: float, unit: str) -> str:
    if abs(size - round(size)) < 1e-6:
        return f"{int(round(size))} {unit}{'s' if int(round(size)) != 1 else ''}"
    return f"{size:.2f} {unit}s"
