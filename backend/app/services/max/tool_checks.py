"""Code-level sanity checks on Max tool results before Max acts on them.

Loud Failures, Quiet Failures (arxiv.org/html/2610.10062) found agents
catch explicit tool errors ~91% of the time but believable wrong values
only ~59%. Prompt reminders do not close that gap, so these checks live
in code — not in the system prompt.

On a failed check Max does not silently proceed: the result is marked
``failed-check``, logged, fed to the shadow confidence scorer when one
is present, and escalated to Rafael.
"""
from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from app.services.drawing.inches import format_inches

_DECIMAL_INCH = re.compile(r"\d+\.\d+\s*[\"″]")

logger = logging.getLogger("max.tool_checks")

CENT_TOLERANCE = 0.01
INCH_TOLERANCE = 1.0 / 16.0  # shop sheets snap to sixteenths

# Allowance applies on EACH side. Wood cut is true size. Foam cut == wood cut.
# fabric_cut = wood_cut + 2 * allowance(foam_thickness).
#
# Values are foam thickness + 2-1/2" staple-back (MODULE_STAPLE_IN in the
# upholstery shell renderer). The table is the source of truth at check
# time — do not recompute from a formula and drift from these rows.
FABRIC_CUT_ALLOWANCE: dict[float, float] = {
    0.5: 3.0,     # 1/2" foam  → 3" each side
    0.75: 3.25,   # 3/4" foam  → 3-1/4" each side
    1.0: 3.5,     # 1" foam    → 3-1/2" each side
    1.5: 4.0,     # 1-1/2" foam → 4" each side
    2.0: 4.5,     # 2" foam    → 4-1/2" each side
    2.5: 5.0,     # 2-1/2" foam → 5" each side
    3.0: 5.5,     # 3" foam    → 5-1/2" each side
    4.0: 6.5,     # 4" foam    → 6-1/2" each side
}

FAILED_CHECK = "failed-check"
CHECK_OK = "ok"

_MONEY_TOOLS = frozenset({
    "create_engine_quote",
    "create_quick_quote",
    "create_invoice_from_quote",
    "split_invoice_from_invoice",
    "draft_estimate_and_presentation",
    "deposit_pay_link",
    "search_quotes",
    "get_quote",
    "show_quote_for_review",
    "read_quickbooks",
    "qb_read",
    "quickbooks_read",
    "quickbooks_get_invoice",
    "quickbooks_get_estimate",
})
_CUT_TOOLS = frozenset({
    "render_shop_drawing",
    "sketch_to_drawing",
    "generate_drawing",
    "generate_cut_sheet",
    "cut_sheet",
})

_QB_SKIP_LINE_TYPES = frozenset({
    "SubTotalLineDetail",
    "DescriptionOnly",
    "GroupLineDetail",
})


@dataclass
class CheckFailure:
    check: str
    message: str
    expected: Any = None
    actual: Any = None


@dataclass
class SanityCheckResult:
    passed: bool
    failures: list[CheckFailure] = field(default_factory=list)
    checks_run: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        return CHECK_OK if self.passed else FAILED_CHECK


def format_measure(value: Any) -> str:
    """User-facing length. Fractions only — never ``14.5``."""
    try:
        return format_inches(float(value))
    except (TypeError, ValueError):
        return str(value)


def fabric_allowance_for_foam(foam_thickness: Any) -> Optional[float]:
    """Return the per-side allowance for a foam thickness, or None if unknown."""
    thickness = _as_inches(foam_thickness)
    if thickness is None:
        return None
    for key, allowance in FABRIC_CUT_ALLOWANCE.items():
        if abs(key - thickness) <= INCH_TOLERANCE / 2:
            return allowance
    return None


def expected_fabric_cut(wood_cut: float, foam_thickness: Any) -> Optional[float]:
    allowance = fabric_allowance_for_foam(foam_thickness)
    if allowance is None:
        return None
    return float(wood_cut) + 2.0 * allowance


def _as_money(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        value = value.replace("$", "").replace(",", "").strip()
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_inches(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        text = value.strip().replace('"', "").replace("″", "")
        if "-" in text and "/" in text:
            whole, frac = text.split("-", 1)
            num, den = frac.split("/", 1)
            try:
                return float(whole) + float(num) / float(den)
            except (TypeError, ValueError, ZeroDivisionError):
                return None
        if "/" in text:
            num, den = text.split("/", 1)
            try:
                return float(num) / float(den)
            except (TypeError, ValueError, ZeroDivisionError):
                return None
        value = text
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _money_close(a: float, b: float) -> bool:
    return abs(a - b) <= CENT_TOLERANCE


def _inch_close(a: float, b: float) -> bool:
    return abs(a - b) <= INCH_TOLERANCE / 2


def _first_money(payload: dict, *keys: str) -> Optional[float]:
    for key in keys:
        if key in payload:
            amount = _as_money(payload.get(key))
            if amount is not None:
                return amount
    return None


def _line_amount(item: Any) -> Optional[float]:
    if not isinstance(item, dict):
        return _as_money(item)
    detail = str(item.get("DetailType") or item.get("detail_type") or "")
    if detail in _QB_SKIP_LINE_TYPES:
        return None
    for key in (
        "Amount", "amount", "total", "line_total", "final_price",
        "proposed_price", "subtotal",
    ):
        if item.get(key) is not None:
            amount = _as_money(item.get(key))
            if amount is not None:
                return amount
    qty = _as_money(item.get("quantity") or item.get("Qty") or 1) or 1.0
    rate = _as_money(
        item.get("unit_price")
        or item.get("rate")
        or item.get("UnitPrice")
        or item.get("Qty")
    )
    if rate is None:
        return None
    return round(qty * rate, 2)


def _iter_line_items(payload: dict) -> list[dict]:
    for key in ("line_items", "lines", "Line", "Items", "items"):
        rows = payload.get(key)
        if isinstance(rows, list) and rows:
            return [row for row in rows if isinstance(row, dict) or row is not None]
    return []


def _nested_documents(payload: Any) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    docs: list[dict] = [payload]
    query = payload.get("QueryResponse")
    if isinstance(query, dict):
        docs.append(query)
        for key in ("Invoice", "Estimate", "Bill", "SalesReceipt", "Payment"):
            rows = query.get(key)
            if isinstance(rows, dict):
                docs.append(rows)
            elif isinstance(rows, list):
                docs.extend(row for row in rows if isinstance(row, dict))
    for key in (
        "packet", "invoice", "estimate", "quote", "Invoice", "Estimate",
        "Bill", "SalesReceipt", "document",
        "QueryResponse",
    ):
        nested = payload.get(key)
        if isinstance(nested, dict):
            docs.append(nested)
        elif isinstance(nested, list):
            docs.extend(row for row in nested if isinstance(row, dict))
    for key in ("quotes", "invoices", "estimates", "documents"):
        rows = payload.get(key)
        if isinstance(rows, list):
            docs.extend(row for row in rows if isinstance(row, dict))
    return docs


def check_quickbooks_totals(payload: dict) -> list[CheckFailure]:
    """Totals must equal the sum of their line items (cent rounding)."""
    lines = _iter_line_items(payload)
    total = _first_money(
        payload, "TotalAmt", "total", "Total", "DocNumberTotal", "amount",
    )
    if not lines or total is None:
        return []

    amounts = [_line_amount(row) for row in lines]
    usable = [amount for amount in amounts if amount is not None]
    if not usable:
        return []

    line_sum = round(sum(usable), 2)
    tax = _first_money(payload, "TxnTaxDetail.TotalTax", "tax_amount", "tax", "TaxAmt")
    # QB TxnTaxDetail is often a nested dict.
    tax_block = payload.get("TxnTaxDetail")
    if tax is None and isinstance(tax_block, dict):
        tax = _as_money(tax_block.get("TotalTax"))
    expected = line_sum if tax is None else round(line_sum + tax, 2)
    subtotal = _first_money(payload, "subtotal", "SubTotal")
    if tax is not None and subtotal is not None:
        expected = round(subtotal + tax, 2)
        if not _money_close(line_sum, subtotal):
            return [CheckFailure(
                check="quickbooks_line_sum",
                message=(
                    f"Line items sum to ${line_sum:,.2f} but subtotal is "
                    f"${subtotal:,.2f}"
                ),
                expected=subtotal,
                actual=line_sum,
            )]
    if _money_close(expected, total):
        return []
    return [CheckFailure(
        check="quickbooks_totals",
        message=(
            f"Total ${total:,.2f} does not equal the sum of line items "
            f"${expected:,.2f}"
        ),
        expected=expected,
        actual=total,
    )]


def check_deposit_balance(payload: dict) -> list[CheckFailure]:
    """deposit + balance == total on estimates and invoices."""
    # Client schedule split only: deposit due + remaining balance = total.
    # Do NOT pair quote.deposit_required with AR balance_due (outstanding).
    deposit = _first_money(
        payload,
        "deposit", "deposit_due", "deposit_amount", "Deposit",
    )
    balance = _first_money(
        payload,
        "balance", "Balance",
    )
    if balance is None and deposit is not None:
        balance = _first_money(payload, "balance_due", "BalanceRemaining")
    total = _first_money(payload, "TotalAmt", "total", "Total")
    if deposit is None or total is None:
        return []
    if balance is None:
        paid = _first_money(payload, "deposit_paid", "amount_paid", "AmountPaid")
        if paid is None:
            return []
        deposit = paid
        balance = _first_money(payload, "balance_due", "BalanceRemaining")
        if balance is None:
            return []
    summed = round(deposit + balance, 2)
    if _money_close(summed, total):
        return []
    return [CheckFailure(
        check="deposit_balance",
        message=(
            f"Deposit ${deposit:,.2f} + balance ${balance:,.2f} = "
            f"${summed:,.2f}, which does not equal total ${total:,.2f}"
        ),
        expected=total,
        actual=summed,
    )]


def _cut_fields(payload: dict) -> dict[str, Any]:
    cuts = payload.get("cuts") if isinstance(payload.get("cuts"), dict) else payload
    if not isinstance(cuts, dict):
        return {}
    wood = cuts.get("wood_cut") or cuts.get("board_cut") or cuts.get("wood")
    foam = cuts.get("foam_cut") or cuts.get("foam")
    fabric = cuts.get("fabric_cut") or cuts.get("fabric")
    thickness = (
        cuts.get("foam_thickness")
        or cuts.get("foam_thk")
        or cuts.get("seat_cushion_thickness")
        or payload.get("foam_thickness")
        or payload.get("seat_cushion_thickness")
    )
    if wood is None and foam is None and fabric is None:
        return {}
    return {
        "wood_cut": wood,
        "foam_cut": foam,
        "fabric_cut": fabric,
        "foam_thickness": thickness,
    }


def check_fabric_cuts(payload: dict) -> list[CheckFailure]:
    """fabric = wood + 2 × allowance(foam); foam cut == wood cut.

    Wood cut is true size. Allowance applies on each side and comes from
    :data:`FABRIC_CUT_ALLOWANCE`.
    """
    fields = _cut_fields(payload)
    if not fields:
        return []

    wood = _as_inches(fields.get("wood_cut"))
    foam_cut = _as_inches(fields.get("foam_cut"))
    fabric = _as_inches(fields.get("fabric_cut"))
    thickness = fields.get("foam_thickness")
    failures: list[CheckFailure] = []

    if wood is None:
        return [CheckFailure(
            check="wood_cut_missing",
            message="Cut sheet is missing the wood/board cut (true size).",
        )]

    if foam_cut is not None and not _inch_close(foam_cut, wood):
        failures.append(CheckFailure(
            check="foam_equals_wood",
            message=(
                f"Foam cut {format_measure(foam_cut)} must equal wood cut "
                f"{format_measure(wood)} (wood is true size)."
            ),
            expected=format_measure(wood),
            actual=format_measure(foam_cut),
        ))

    if fabric is None and thickness is None:
        return failures

    allowance = fabric_allowance_for_foam(thickness)
    if allowance is None:
        failures.append(CheckFailure(
            check="fabric_allowance_unknown",
            message=(
                f"No fabric-cut allowance for foam thickness "
                f"{format_measure(thickness) if thickness is not None else 'unknown'}."
            ),
            expected=sorted(format_measure(k) for k in FABRIC_CUT_ALLOWANCE),
            actual=format_measure(thickness) if thickness is not None else None,
        ))
        return failures

    expected = wood + 2.0 * allowance
    if fabric is None:
        failures.append(CheckFailure(
            check="fabric_cut_missing",
            message=(
                f"Fabric cut is missing. Expected {format_measure(expected)} "
                f"(wood {format_measure(wood)} + 2 × {format_measure(allowance)} "
                f"allowance for {format_measure(thickness)} foam)."
            ),
            expected=format_measure(expected),
        ))
        return failures

    if not _inch_close(fabric, expected):
        failures.append(CheckFailure(
            check="fabric_cut",
            message=(
                f"Fabric cut {format_measure(fabric)} must equal wood cut "
                f"{format_measure(wood)} + 2 × {format_measure(allowance)} "
                f"allowance ({format_measure(thickness)} foam) = "
                f"{format_measure(expected)}."
            ),
            expected=format_measure(expected),
            actual=format_measure(fabric),
        ))
    return failures


def validate_tool_payload(payload: Any, tool_name: str = "") -> SanityCheckResult:
    """Run every applicable check on a tool payload (and nested documents)."""
    result = SanityCheckResult(passed=True)
    if not isinstance(payload, dict):
        return result

    documents = _nested_documents(payload)
    seen: set[int] = set()
    for doc in documents:
        marker = id(doc)
        if marker in seen:
            continue
        seen.add(marker)

        money_failures = check_quickbooks_totals(doc)
        if money_failures or _iter_line_items(doc):
            result.checks_run.append("quickbooks_totals")
        result.failures.extend(money_failures)

        deposit_failures = check_deposit_balance(doc)
        if deposit_failures or _first_money(doc, "deposit", "deposit_due", "deposit_required"):
            result.checks_run.append("deposit_balance")
        result.failures.extend(deposit_failures)

        cut_failures = check_fabric_cuts(doc)
        if cut_failures or _cut_fields(doc):
            result.checks_run.append("fabric_cuts")
        result.failures.extend(cut_failures)

    # Deduplicate check names while preserving order.
    result.checks_run = list(dict.fromkeys(result.checks_run))
    result.passed = not result.failures
    return result


def should_check_tool(tool_name: str, payload: Any) -> bool:
    name = (tool_name or "").lower()
    if name in _MONEY_TOOLS or name in _CUT_TOOLS:
        return True
    if any(token in name for token in (
        "quickbooks", "invoice", "estimate", "quote", "cut_sheet", "cutsheet",
    )):
        return True
    if isinstance(payload, dict) and (
        _iter_line_items(payload)
        or _first_money(payload, "deposit", "deposit_due", "TotalAmt")
        or _cut_fields(payload)
    ):
        return True
    return False


def user_facing_failure_text(check: SanityCheckResult) -> str:
    """Escalation copy. Measurements stay in fractions; no decimal inches."""
    if check.passed:
        return ""
    lines = ["Tool result failed a code-level sanity check. Max did not act."]
    for failure in check.failures:
        message = failure.message
        if _DECIMAL_INCH.search(message):
            logger.error("Sanity-check message leaked a decimal inch: %s", message)
            message = _DECIMAL_INCH.sub(
                lambda m: format_measure(m.group(0).rstrip('"').rstrip("″")),
                message,
            )
        lines.append(f"• {message}")
    lines.append("Escalated to Rafael.")
    return "\n".join(lines)


def feed_shadow_confidence(
    tool_name: str,
    check: SanityCheckResult,
    payload: Any,
) -> Optional[dict]:
    """Feed a failed check to the shadow confidence scorer when present."""
    record = {
        "tool": tool_name,
        "status": FAILED_CHECK,
        "confidence": 0.0,
        "reason": "tool_result_sanity_check",
        "failures": [failure.check for failure in check.failures],
    }
    try:
        from app.services.max.accuracy_monitor import accuracy_monitor

        class _FailedVerification:
            claims_found = 1
            claims_verified = 0
            claims_stripped = 1

        accuracy_monitor.log_audit(
            user_query=f"tool:{tool_name}",
            response_text=user_facing_failure_text(check)[:2000],
            verification=_FailedVerification(),
            model_used="tool_checks",
            channel="tool_check",
            output_type="failed-check",
            quality_severity="critical",
        )
        record["shadow"] = "accuracy_monitor"
        return record
    except Exception as exc:
        logger.debug("Shadow confidence scorer skipped: %s", exc)
        record["shadow"] = None
        return record


def escalate_to_rafael(
    tool_name: str,
    check: SanityCheckResult,
    *,
    payload: Any = None,
) -> dict:
    """Log, score, and escalate a failed check. Does not act on the result."""
    text = user_facing_failure_text(check)
    logger.error(
        "failed-check tool=%s checks=%s failures=%s",
        tool_name,
        check.checks_run,
        [failure.check for failure in check.failures],
    )
    shadow = feed_shadow_confidence(tool_name, check, payload)
    notification = None
    telegram_sent = False
    try:
        from app.routers.notifications import notify_founder

        notification = notify_founder(
            "MAX",
            "review_needed",
            f"Max tool check failed: {tool_name}",
            text,
            "high",
            {
                "tool": tool_name,
                "status": FAILED_CHECK,
                "failures": [asdict(f) for f in check.failures],
                "acted": False,
            },
        )
    except Exception as exc:
        logger.warning("notify_founder failed during tool-check escalation: %s", exc)

    try:
        from app.services.max.telegram_bot import telegram_bot

        if getattr(telegram_bot, "is_configured", False):
            from app.services.max.tool_executor import _run_async

            telegram_sent = bool(_run_async(
                telegram_bot.send_message(
                    "🚨 <b>Max tool check failed</b>\n\n"
                    f"<b>Tool:</b> {tool_name}\n"
                    f"{text}"
                )
            ))
    except Exception as exc:
        logger.warning("Telegram escalation failed: %s", exc)

    return {
        "escalated_to": "rafael",
        "acted": False,
        "notification_id": (notification or {}).get("id") if isinstance(notification, dict) else None,
        "telegram_sent": telegram_sent,
        "shadow_confidence": shadow,
        "message": text,
    }


def gate_tool_result(tool_name: str, result: Any, params: Optional[dict] = None) -> Any:
    """Central gate: on a failed check, mark failed-check and escalate.

    Returns the original result when checks pass or do not apply. Never
    mutates a successful payload into an acted-on document after a fail.
    """
    from app.services.max.tool_executor import ToolResult

    if not isinstance(result, ToolResult) or not result.success:
        return result

    payload = result.result if isinstance(result.result, dict) else {}
    if params and isinstance(params, dict):
        merged = dict(payload)
        for key in ("cuts", "cut_sheet", "wood_cut", "foam_cut", "fabric_cut",
                    "foam_thickness", "line_items", "deposit", "balance",
                    "balance_due", "total", "TotalAmt", "Line"):
            if key in params and key not in merged:
                merged[key] = params[key]
        # Drawing tools often keep cuts on dims.
        dims = params.get("dims")
        if isinstance(dims, dict):
            for key in ("wood_cut", "foam_cut", "fabric_cut", "foam_thickness",
                        "board_cut", "seat_cushion_thickness", "width"):
                if key in dims and key not in merged:
                    merged[key] = dims[key]
            if "wood_cut" not in merged and dims.get("width") is not None:
                if any(k in dims for k in ("fabric_cut", "foam_cut", "foam_thickness")):
                    merged.setdefault("wood_cut", dims.get("width"))
        payload = merged

    if not should_check_tool(tool_name, payload):
        return result

    check = validate_tool_payload(payload, tool_name=tool_name)
    if check.passed:
        if isinstance(result.result, dict):
            result.result.setdefault("check_status", CHECK_OK)
        return result

    escalation = escalate_to_rafael(tool_name, check, payload=payload)
    return ToolResult(
        tool=tool_name,
        success=False,
        error=f"{FAILED_CHECK}: {check.failures[0].message}",
        result={
            "failed_check": True,
            "check_status": FAILED_CHECK,
            "acted": False,
            "escalated_to": "rafael",
            "failures": [asdict(f) for f in check.failures],
            "checks_run": check.checks_run,
            "escalation": escalation,
            "shadow_confidence": escalation.get("shadow_confidence"),
        },
    )


def attach_cut_sheet(
    wood_cut: Any,
    foam_thickness: Any,
    *,
    foam_cut: Any = None,
    fabric_cut: Any = None,
) -> dict:
    """Build a cut-sheet block. Computed values stay numeric; display is fractions."""
    wood = _as_inches(wood_cut)
    thickness = _as_inches(foam_thickness)
    foam = _as_inches(foam_cut) if foam_cut is not None else wood
    fabric = _as_inches(fabric_cut)
    allowance = fabric_allowance_for_foam(thickness)
    expected = expected_fabric_cut(wood, thickness) if wood is not None else None
    if fabric is None:
        fabric = expected
    sheet = {
        "wood_cut": wood,
        "foam_cut": foam,
        "fabric_cut": fabric,
        "foam_thickness": thickness,
        "allowance_each_side": allowance,
        "wood_cut_display": format_measure(wood) if wood is not None else None,
        "foam_cut_display": format_measure(foam) if foam is not None else None,
        "fabric_cut_display": format_measure(fabric) if fabric is not None else None,
        "allowance_display": format_measure(allowance) if allowance is not None else None,
        "foam_thickness_display": format_measure(thickness) if thickness is not None else None,
    }
    return sheet
