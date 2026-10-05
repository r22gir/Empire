"""Match an uploaded quote/estimate PDF to a saved quote and summarize diffs.

Read-only. Used by the attachment-reader path so Max reports line/total/deposit
differences instead of telling Rafael to email the PDF.
"""
from __future__ import annotations

import re
from typing import Any, Optional

_EST_RE = re.compile(r"\bEST-\d{4}-\d{3,4}\b", re.IGNORECASE)
_MONEY_RE = re.compile(
    r"(?:total|grand\s*total|amount\s*due|estimate\s*total|project\s*total)"
    r"[^$\d]{0,40}\$?\s*([\d,]+(?:\.\d{2})?)",
    re.IGNORECASE,
)
_DEPOSIT_RE = re.compile(
    r"deposit[^$\d]{0,40}\$?\s*([\d,]+(?:\.\d{2})?)",
    re.IGNORECASE,
)
_CLIENT_RE = re.compile(
    r"(?:bill\s*to|customer|client|prepared\s*for)\s*[:\-]?\s*([^\n]{3,60})",
    re.IGNORECASE,
)


def _money(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return round(float(str(v).replace(",", "").replace("$", "").strip()), 2)
    except (TypeError, ValueError):
        return None


def _fmt(v: Optional[float]) -> str:
    if v is None:
        return "—"
    return f"${v:,.2f}"


def extract_estimate_number(filename: str | None, text: str | None) -> Optional[str]:
    for source in (text or "", filename or ""):
        m = _EST_RE.search(source)
        if m:
            return m.group(0).upper()
    return None


def _pdf_total(text: str) -> Optional[float]:
    matches = list(_MONEY_RE.finditer(text or ""))
    if not matches:
        # fall back: last large money-looking amount
        amounts = re.findall(r"\$\s*([\d,]+\.\d{2})", text or "")
        if amounts:
            return _money(amounts[-1])
        return None
    return _money(matches[-1].group(1))


def _pdf_deposit(text: str) -> Optional[float]:
    m = _DEPOSIT_RE.search(text or "")
    return _money(m.group(1)) if m else None


def _line_diff(saved_items: list[dict], text: str) -> list[str]:
    lines: list[str] = []
    saved_descs = []
    for it in saved_items or []:
        desc = str(it.get("description") or it.get("name") or "").strip()
        if desc:
            saved_descs.append(desc)
    if not saved_descs:
        return lines
    lower = (text or "").lower()
    missing = [d for d in saved_descs if d.lower()[:24] not in lower]
    if missing:
        lines.append(
            f"- Line items in saved quote not clearly in the PDF ({len(missing)} of "
            f"{len(saved_descs)}): " + "; ".join(missing[:5])
            + ("…" if len(missing) > 5 else "")
        )
    else:
        lines.append(f"- Line items: all {len(saved_descs)} saved descriptions appear in the PDF text.")
    return lines


def compare_attachment_to_saved_quote(
    filename: str | None,
    extracted_text: str | None,
) -> Optional[str]:
    """Return a short comparison block, or None if this is not an estimate PDF."""
    text = extracted_text or ""
    qn = extract_estimate_number(filename, text)
    looks_like_quote = bool(qn) or bool(
        re.search(r"\b(estimate|quote|proposal|deposit)\b", text[:2000], re.I)
    )
    if not looks_like_quote:
        return None

    try:
        from app.services.quote_service import get_quote_by_number, search_quotes
    except Exception:
        return None

    quote = None
    if qn:
        try:
            quote = get_quote_by_number(qn)
        except Exception:
            quote = None

    if quote is None:
        # Try client name from PDF against search
        cm = _CLIENT_RE.search(text[:3000])
        client_hint = (cm.group(1).strip() if cm else "")[:40]
        if client_hint:
            try:
                hits = search_quotes(client_hint, limit=3) or []
            except TypeError:
                try:
                    hits = search_quotes(query=client_hint) or []
                except Exception:
                    hits = []
            except Exception:
                hits = []
            if isinstance(hits, dict):
                hits = hits.get("quotes") or hits.get("results") or []
            if hits:
                quote = hits[0] if isinstance(hits[0], dict) else None
                if quote and not qn:
                    qn = str(quote.get("quote_number") or "")

    if quote is None:
        if qn:
            return (
                f"Parsed estimate **{qn}** from the upload, but no matching saved "
                f"quote was found. I will not email it — say if you want a new quote drafted."
            )
        return None

    saved_total = _money(
        quote.get("final_price")
        or quote.get("total")
        or quote.get("grand_total")
        or quote.get("amount")
    )
    dep = quote.get("deposit") if isinstance(quote.get("deposit"), dict) else {}
    saved_deposit = _money(
        dep.get("deposit_amount")
        or dep.get("amount")
        or quote.get("deposit_amount")
        or quote.get("deposit_due")
    )
    pdf_total = _pdf_total(text)
    pdf_deposit = _pdf_deposit(text)
    client = (
        quote.get("customer_name")
        or quote.get("client_name")
        or quote.get("customer")
        or "—"
    )
    status = quote.get("status") or "—"
    items = quote.get("line_items") or []

    diffs: list[str] = []
    if pdf_total is not None and saved_total is not None:
        if abs(pdf_total - saved_total) > 0.01:
            diffs.append(f"- Total: PDF {_fmt(pdf_total)} vs saved {_fmt(saved_total)}")
        else:
            diffs.append(f"- Total: match at {_fmt(saved_total)}")
    elif saved_total is not None:
        diffs.append(f"- Saved total: {_fmt(saved_total)} (could not parse a clear total from the PDF)")
    if pdf_deposit is not None or saved_deposit is not None:
        if (
            pdf_deposit is not None
            and saved_deposit is not None
            and abs(pdf_deposit - saved_deposit) > 0.01
        ):
            diffs.append(f"- Deposit: PDF {_fmt(pdf_deposit)} vs saved {_fmt(saved_deposit)}")
        elif pdf_deposit is not None and saved_deposit is not None:
            diffs.append(f"- Deposit: match at {_fmt(saved_deposit)}")
        else:
            diffs.append(
                f"- Deposit: PDF {_fmt(pdf_deposit)} / saved {_fmt(saved_deposit)}"
            )
    diffs.extend(_line_diff(items, text))

    qn_disp = str(quote.get("quote_number") or qn or "—")
    header = (
        f"Matched upload to saved quote **{qn_disp}** "
        f"(client: {client}, status: {status})."
    )
    body = "\n".join(diffs) if diffs else "- No clear diffs parsed."
    return (
        f"{header}\n{body}\n"
        "I will not email this PDF. Say if you want edits on the saved quote."
    )


def build_attachment_local_answer(filename: str | None, extracted_text: str) -> str:
    """User-facing attachment-reader reply (avoids bare 'I read' claim phrasing)."""
    compare = compare_attachment_to_saved_quote(filename, extracted_text)
    preview = (extracted_text or "")[:1500]
    parts = [
        f"Attached file contents ({filename or 'upload'}):",
        preview,
    ]
    if compare:
        parts.extend(["", "Quote match:", compare])
    return "\n".join(parts)
