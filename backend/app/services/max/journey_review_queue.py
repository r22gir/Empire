"""
Customer Journey Review Queue — proposed matches, no live writes
=================================================================

This service generates a list of *proposed* matches between
anonymous quotes → customers and dangling invoices → quotes, plus
a small set of orphan payments → invoices if any exist.

The matching is **deterministic, read-only, and never applied**.
The founder reviews each proposal and approves only the ones that
are correct. The live DB is never modified by this service.

Matching signals and weights
----------------------------
For quote → customer:

    +50  email exact match (case-insensitive, trimmed)
    +50  phone exact match (digits only, ignoring formatting)
    +30  name exact match (case-insensitive, whitespace-normalized)
    +15  name token overlap ≥ 80% (Jaccard on word tokens)
    +10  name token overlap ≥ 50% (weaker)
     +5  first-letter-of-first-name + last-name matches (last-name-anchor)

For invoice → quote (when invoice.quote_id is missing or dangling):

    +50  client_email → quote.customer_email match
    +30  client_name → quote.customer_name match
    +20  amount exact match + date within 7 days
    +10  amount within 1% + date within 7 days
     +5  amount within 5% + date within 30 days

For payment → invoice (when payment.invoice_id is missing or dangling):

    +50  amount exact match + date within 14 days
    +20  amount within 1% + date within 14 days
    +10  customer_id matches the invoice's customer_id

Confidence bands
----------------
    high    : score ≥ 70
    medium  : 40 ≤ score < 70
    low     : score < 40

Every proposal carries:

    - source_type / source_id
    - target_type / target_id
    - confidence (high | medium | low)
    - confidence_score (0..100)
    - match_reasons (list of human-readable strings)
    - risks (list of human-readable warnings)
    - action: always "proposed_only"
    - requires_founder_approval: always True
    - proposal_id (stable hash of source+target+rule-set)

The proposal_id is stable across runs: a re-run of the queue produces
the same id for the same (source, target, score). This lets the UI
deduplicate and lets the audit log track which proposals have been
seen before.

Anti-spam: a single source is only paired with the top-K targets
(per matching signal) to avoid combinatorial explosion. K=5 by
default.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Reuse the read-only DB opener from journey_linkage
from app.services.max.journey_linkage import (
    _open_db,
    _resolve_db_path,
    BACKFILL_AUDIT_PATH,
    DEFAULT_DB_PATH,
    TAG_ANONYMOUS,
    TAG_ORPHAN,
    TAG_NO_QUOTE,
    TAG_HAS_LINKED,
    TAG_UNKNOWN,
)

logger = logging.getLogger("max.journey_review_queue")


# ── Configuration ───────────────────────────────────────────────────────

# Top-K candidate targets per source
TOP_K_TARGETS = 5

# Confidence thresholds
THRESHOLD_HIGH = 70
THRESHOLD_MEDIUM = 40

# Date windows (days)
WINDOW_AMOUNT_EXACT = 7
WINDOW_AMOUNT_NEAR = 30
WINDOW_PAYMENT = 14


# ── Normalization helpers ──────────────────────────────────────────────


def _norm_email(s: Optional[str]) -> str:
    if not s:
        return ""
    return s.strip().lower()


def _norm_phone(s: Optional[str]) -> str:
    """Normalize phone to digits only. Used for exact phone matching."""
    if not s:
        return ""
    return re.sub(r"\D", "", s)


def _norm_name(s: Optional[str]) -> str:
    if not s:
        return ""
    # Collapse whitespace and lowercase
    return re.sub(r"\s+", " ", s.strip().lower())


def _name_tokens(s: Optional[str]) -> set[str]:
    n = _norm_name(s)
    if not n:
        return set()
    return set(t for t in n.split() if len(t) >= 2)


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _date_diff_days(d1: Optional[str], d2: Optional[str]) -> Optional[int]:
    """Compute |d1 - d2| in days. Returns None if either is missing
    or unparseable. Accepts ISO dates or YYYY-MM-DD strings.
    """
    if not d1 or not d2:
        return None
    try:
        a = datetime.fromisoformat(d1[:10])
        b = datetime.fromisoformat(d2[:10])
        return abs((a - b).days)
    except (ValueError, TypeError):
        return None


def _amount_close(a: Optional[float], b: Optional[float], tolerance_pct: float) -> bool:
    if a is None or b is None:
        return False
    if a == 0 and b == 0:
        return True
    if a == 0 or b == 0:
        return False
    return abs(a - b) / max(abs(a), abs(b)) <= tolerance_pct / 100.0


# ── Proposal dataclass ─────────────────────────────────────────────────


@dataclass
class Proposal:
    """A single proposed match for the founder to review."""
    proposal_id: str
    source_type: str  # quote | invoice | payment
    source_id: str
    target_type: str  # customer | quote | invoice
    target_id: str
    confidence: str  # high | medium | low
    confidence_score: int
    match_reasons: list = field(default_factory=list)
    risks: list = field(default_factory=list)
    action: str = "proposed_only"
    requires_founder_approval: bool = True
    source_summary: Optional[dict] = None  # small preview of source row
    target_summary: Optional[dict] = None  # small preview of target row
    generated_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ── Proposal ID hashing ────────────────────────────────────────────────


def _proposal_id(source_type: str, source_id: str, target_type: str,
                 target_id: str, score: int) -> str:
    """Stable proposal id. Same inputs → same id across runs."""
    raw = f"{source_type}:{source_id}->{target_type}:{target_id}:{score}"
    return "p_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# ── Scoring helpers ────────────────────────────────────────────────────


def _score_quote_to_customer(quote: dict, customer: dict) -> tuple[int, list[str], list[str]]:
    """Score the match between an anonymous quote and a customer.

    Returns (score, reasons, risks).
    """
    score = 0
    reasons = []
    risks = []

    q_email = _norm_email(quote.get("customer_email"))
    c_email = _norm_email(customer.get("email"))
    q_phone = _norm_phone(quote.get("customer_phone"))
    c_phone = _norm_phone(customer.get("phone"))
    q_name = _norm_name(quote.get("customer_name"))
    c_name = _norm_name(customer.get("name"))
    q_tokens = _name_tokens(quote.get("customer_name"))
    c_tokens = _name_tokens(customer.get("name"))

    if q_email and c_email:
        if q_email == c_email:
            score += 50
            reasons.append(f"email exact match ({c_email})")
        else:
            risks.append(f"email mismatch (quote={q_email!r} customer={c_email!r})")
    elif q_email and not c_email:
        risks.append("customer has no email recorded")

    if q_phone and c_phone:
        if q_phone == c_phone:
            score += 50
            reasons.append(f"phone exact match ({c_phone})")
        elif len(q_phone) >= 7 and len(c_phone) >= 7 and q_phone[-7:] == c_phone[-7:]:
            score += 20
            reasons.append("phone last-7-digits match")
        else:
            risks.append(f"phone mismatch (quote={q_phone!r} customer={c_phone!r})")

    if q_name and c_name:
        if q_name == c_name:
            score += 30
            reasons.append(f"name exact match ({c_name!r})")
        else:
            j = _jaccard(q_tokens, c_tokens)
            if j >= 0.8 and (q_tokens & c_tokens):
                score += 15
                reasons.append(f"name high overlap (jaccard={j:.2f})")
            elif j >= 0.5 and (q_tokens & c_tokens):
                score += 10
                reasons.append(f"name moderate overlap (jaccard={j:.2f})")
            else:
                risks.append(f"name low overlap (quote={q_name!r} customer={c_name!r}, jaccard={j:.2f})")

            # Last-name-anchor: if the last word of each name is the same.
            # Use the original name string (not the token set) to get a
            # deterministic "last word" — sets have no order, so we can't
            # rely on list(set)[-1].
            q_words = _norm_name(quote.get("customer_name")).split()
            c_words = _norm_name(customer.get("name")).split()
            q_last = q_words[-1] if q_words else ""
            c_last = c_words[-1] if c_words else ""
            if q_last and c_last and q_last == c_last and len(q_last) >= 3:
                # Only award if not already awarded for full name match
                if "name exact match" not in " ".join(reasons):
                    score += 5
                    reasons.append(f"last-name anchor match ({q_last!r})")

    if not reasons:
        risks.append("no matching signals")

    return score, reasons, risks


def _score_invoice_to_quote(invoice: dict, quote: dict) -> tuple[int, list[str], list[str]]:
    """Score the match between a dangling invoice and a quote.

    The invoice's quote_id either is missing or points to a row that
    doesn't exist in quotes_v2. We try to find a real quote this
    invoice could belong to.
    """
    score = 0
    reasons = []
    risks = []

    i_email = _norm_email(invoice.get("client_email"))
    q_email = _norm_email(quote.get("customer_email"))
    i_name = _norm_name(invoice.get("client_name"))
    q_name = _norm_name(quote.get("customer_name"))

    if i_email and q_email:
        if i_email == q_email:
            score += 50
            reasons.append(f"client_email ↔ quote.customer_email match ({i_email})")
        else:
            risks.append(f"email mismatch (invoice={i_email!r} quote={q_email!r})")
    elif i_email and not q_email:
        risks.append("quote has no customer_email recorded")
    elif q_email and not i_email:
        # If the invoice has a customer_id set, the customer is known but the
        # quote isn't linked; this is a less risky situation than the reverse.
        if not invoice.get("customer_id"):
            risks.append("invoice has no client_email recorded")

    if i_name and q_name:
        if i_name == q_name:
            score += 30
            reasons.append(f"client_name ↔ quote.customer_name match ({i_name!r})")
        else:
            j = _jaccard(_name_tokens(invoice.get("client_name")),
                         _name_tokens(quote.get("customer_name")))
            if j >= 0.8:
                score += 10
                reasons.append(f"client_name high overlap (jaccard={j:.2f})")
            else:
                risks.append(f"name low overlap (jaccard={j:.2f})")

    # Amount + date proximity
    try:
        i_total = float(invoice.get("total") or 0)
    except (TypeError, ValueError):
        i_total = 0.0
    try:
        q_total = float(quote.get("total") or 0)
    except (TypeError, ValueError):
        q_total = 0.0
    days = _date_diff_days(invoice.get("created_at"), quote.get("created_at"))

    if i_total and q_total:
        if _amount_close(i_total, q_total, 0.01) and days is not None and days <= WINDOW_AMOUNT_EXACT:
            score += 20
            reasons.append(f"amount match (Δ≤1%) within {days}d")
        elif _amount_close(i_total, q_total, 0.01):
            score += 10
            reasons.append(f"amount match (Δ≤1%); date gap {days}d (>{WINDOW_AMOUNT_EXACT}d)")
        elif _amount_close(i_total, q_total, 5.0) and days is not None and days <= WINDOW_AMOUNT_NEAR:
            score += 5
            reasons.append(f"amount within 5% within {days}d")
        else:
            if i_total != q_total:
                risks.append(f"amounts differ (invoice={i_total:.2f} quote={q_total:.2f})")

    if not reasons:
        risks.append("no matching signals")

    return score, reasons, risks


def _score_payment_to_invoice(payment: dict, invoice: dict) -> tuple[int, list[str], list[str]]:
    """Score the match between an orphan payment and an invoice."""
    score = 0
    reasons = []
    risks = []

    try:
        p_amt = float(payment.get("amount") or 0)
    except (TypeError, ValueError):
        p_amt = 0.0
    try:
        i_total = float(invoice.get("total") or 0)
    except (TypeError, ValueError):
        i_total = 0.0
    try:
        i_paid = float(invoice.get("amount_paid") or 0)
    except (TypeError, ValueError):
        i_paid = 0.0

    days = _date_diff_days(payment.get("payment_date"), invoice.get("created_at"))

    if p_amt and i_total:
        if _amount_close(p_amt, i_total, 0.01) and days is not None and days <= WINDOW_PAYMENT:
            score += 50
            reasons.append(f"amount == invoice.total within {days}d")
        elif _amount_close(p_amt, i_total, 0.01):
            score += 20
            reasons.append(f"amount == invoice.total; date gap {days}d")
        elif _amount_close(p_amt, i_paid, 0.01) and i_paid and days is not None and days <= WINDOW_PAYMENT:
            score += 30
            reasons.append(f"amount == amount_paid within {days}d")
        else:
            risks.append(f"amount differs from invoice total/paid (payment={p_amt:.2f})")

    if payment.get("customer_id") and invoice.get("customer_id"):
        if payment["customer_id"] == invoice["customer_id"]:
            score += 10
            reasons.append("customer_id matches invoice.customer_id")
        else:
            risks.append("customer_id mismatch")

    if not reasons:
        risks.append("no matching signals")

    return score, reasons, risks


def _band(score: int) -> str:
    if score >= THRESHOLD_HIGH:
        return "high"
    if score >= THRESHOLD_MEDIUM:
        return "medium"
    return "low"


# ── Source-row fetchers (with a small preview summary) ────────────────


def _fetch_anonymous_quotes(con: sqlite3.Connection) -> list[dict]:
    """Return anonymous quotes (no customer_id) with preview fields."""
    rows = con.execute("""
        SELECT id, quote_number, customer_name, customer_email, customer_phone,
               total, status, created_at
        FROM quotes_v2
        WHERE customer_id IS NULL OR customer_id = ''
        ORDER BY created_at
    """).fetchall()
    return [dict(r) for r in rows]


def _fetch_all_customers(con: sqlite3.Connection) -> list[dict]:
    """Return all customers (the pool of candidate targets)."""
    rows = con.execute(
        "SELECT id, name, email, phone, address FROM customers ORDER BY name"
    ).fetchall()
    return [dict(r) for r in rows]


def _fetch_dangling_invoices(con: sqlite3.Connection) -> list[dict]:
    """Return invoices whose quote_id is missing or doesn't exist in quotes_v2."""
    rows = con.execute("""
        SELECT id, invoice_number, customer_id, quote_id, client_name, client_email,
               total, amount_paid, balance_due, status, created_at, paid_at
        FROM invoices
        WHERE (quote_id IS NULL OR quote_id = ''
               OR NOT EXISTS (SELECT 1 FROM quotes_v2 q WHERE q.id = invoices.quote_id))
        ORDER BY created_at
    """).fetchall()
    return [dict(r) for r in rows]


def _fetch_all_quotes_v2(con: sqlite3.Connection) -> list[dict]:
    """Return all quotes_v2 rows (the pool for invoice→quote matching)."""
    rows = con.execute("""
        SELECT id, quote_number, customer_id, customer_name, customer_email,
               total, status, created_at
        FROM quotes_v2
    """).fetchall()
    return [dict(r) for r in rows]


def _fetch_orphan_payments(con: sqlite3.Connection) -> list[dict]:
    """Return payments whose invoice_id is missing or dangling."""
    rows = con.execute("""
        SELECT id, customer_id, invoice_id, amount, method, payment_date
        FROM payments
        WHERE (invoice_id IS NULL OR invoice_id = ''
               OR NOT EXISTS (SELECT 1 FROM invoices i WHERE i.id = payments.invoice_id))
    """).fetchall()
    return [dict(r) for r in rows]


def _fetch_all_invoices(con: sqlite3.Connection) -> list[dict]:
    """Return all invoices (the pool for payment→invoice matching)."""
    rows = con.execute("""
        SELECT id, invoice_number, customer_id, total, amount_paid, created_at
        FROM invoices
    """).fetchall()
    return [dict(r) for r in rows]


# ── Top-K candidate selection (per source) ────────────────────────────


def _top_k_targets(scored: list[tuple[int, dict, list[str], list[str]]], k: int) -> list:
    """Return top-K (score, target, reasons, risks) tuples, sorted desc by score.

    Stable secondary sort: by target id, so the output is deterministic.
    """
    sorted_targets = sorted(
        scored,
        key=lambda x: (-x[0], (x[1].get("id") or "")),
    )
    return sorted_targets[:k]


# ── Main review-queue generator ────────────────────────────────────────


def generate_review_queue(
    db_path: Optional[str] = None,
    min_confidence: str = "low",
) -> list[Proposal]:
    """Generate the founder-review proposal list.

    Returns a list of Proposal objects. The list is intentionally
    ordered: highest-confidence first, then by source type (quote,
    invoice, payment), then by source_id.

    `min_confidence` filters the output:
        - "low"    : include everything
        - "medium" : include medium and high
        - "high"   : include only high
    The default is "low" so the founder sees the full set.
    """
    path = db_path or _resolve_db_path()
    generated_at = datetime.now(timezone.utc).isoformat()

    proposals: list[Proposal] = []

    with _open_db(path) as con:
        # 1. Anonymous quotes → customers
        customers = _fetch_all_customers(con)
        anonymous_quotes = _fetch_anonymous_quotes(con)
        logger.info(
            f"review-queue: {len(anonymous_quotes)} anonymous quotes, "
            f"{len(customers)} customers in pool"
        )

        for q in anonymous_quotes:
            scored = []
            for c in customers:
                s, reasons, risks = _score_quote_to_customer(q, c)
                if s > 0:
                    scored.append((s, c, reasons, risks))
            top = _top_k_targets(scored, TOP_K_TARGETS)
            for s, c, reasons, risks in top:
                proposals.append(Proposal(
                    proposal_id=_proposal_id("quote", q["id"], "customer", c["id"], s),
                    source_type="quote",
                    source_id=q["id"],
                    target_type="customer",
                    target_id=c["id"],
                    confidence=_band(s),
                    confidence_score=s,
                    match_reasons=reasons,
                    risks=risks,
                    source_summary={
                        "quote_id": q["id"],
                        "quote_number": q.get("quote_number"),
                        "customer_name": q.get("customer_name"),
                        "customer_email": q.get("customer_email"),
                        "customer_phone": q.get("customer_phone"),
                        "total": q.get("total"),
                        "status": q.get("status"),
                        "created_at": q.get("created_at"),
                    },
                    target_summary={
                        "customer_id": c["id"],
                        "name": c.get("name"),
                        "email": c.get("email"),
                        "phone": c.get("phone"),
                    },
                    generated_at=generated_at,
                ))

        # 2. Dangling invoices → quotes
        quotes_v2 = _fetch_all_quotes_v2(con)
        dangling_invoices = _fetch_dangling_invoices(con)
        logger.info(
            f"review-queue: {len(dangling_invoices)} dangling invoices, "
            f"{len(quotes_v2)} quotes_v2 in pool"
        )

        for inv in dangling_invoices:
            scored = []
            for q in quotes_v2:
                s, reasons, risks = _score_invoice_to_quote(inv, q)
                if s > 0:
                    scored.append((s, q, reasons, risks))
            top = _top_k_targets(scored, TOP_K_TARGETS)
            for s, q, reasons, risks in top:
                proposals.append(Proposal(
                    proposal_id=_proposal_id("invoice", inv["id"], "quote", q["id"], s),
                    source_type="invoice",
                    source_id=inv["id"],
                    target_type="quote",
                    target_id=q["id"],
                    confidence=_band(s),
                    confidence_score=s,
                    match_reasons=reasons,
                    risks=risks,
                    source_summary={
                        "invoice_id": inv["id"],
                        "invoice_number": inv.get("invoice_number"),
                        "client_name": inv.get("client_name"),
                        "client_email": inv.get("client_email"),
                        "customer_id": inv.get("customer_id"),
                        "total": inv.get("total"),
                        "amount_paid": inv.get("amount_paid"),
                        "status": inv.get("status"),
                        "created_at": inv.get("created_at"),
                    },
                    target_summary={
                        "quote_id": q["id"],
                        "quote_number": q.get("quote_number"),
                        "customer_name": q.get("customer_name"),
                        "customer_email": q.get("customer_email"),
                        "total": q.get("total"),
                    },
                    generated_at=generated_at,
                ))

        # 3. Orphan payments → invoices
        invoices = _fetch_all_invoices(con)
        orphan_payments = _fetch_orphan_payments(con)
        logger.info(
            f"review-queue: {len(orphan_payments)} orphan payments, "
            f"{len(invoices)} invoices in pool"
        )

        for pay in orphan_payments:
            scored = []
            for inv in invoices:
                s, reasons, risks = _score_payment_to_invoice(pay, inv)
                if s > 0:
                    scored.append((s, inv, reasons, risks))
            top = _top_k_targets(scored, TOP_K_TARGETS)
            for s, inv, reasons, risks in top:
                proposals.append(Proposal(
                    proposal_id=_proposal_id("payment", pay["id"], "invoice", inv["id"], s),
                    source_type="payment",
                    source_id=pay["id"],
                    target_type="invoice",
                    target_id=inv["id"],
                    confidence=_band(s),
                    confidence_score=s,
                    match_reasons=reasons,
                    risks=risks,
                    source_summary={
                        "payment_id": pay["id"],
                        "customer_id": pay.get("customer_id"),
                        "amount": pay.get("amount"),
                        "method": pay.get("method"),
                        "payment_date": pay.get("payment_date"),
                    },
                    target_summary={
                        "invoice_id": inv["id"],
                        "invoice_number": inv.get("invoice_number"),
                        "total": inv.get("total"),
                        "amount_paid": inv.get("amount_paid"),
                    },
                    generated_at=generated_at,
                ))

    # 4. Apply min_confidence filter
    band_order = {"low": 0, "medium": 1, "high": 2}
    cutoff = band_order.get(min_confidence, 0)
    proposals = [p for p in proposals if band_order[p.confidence] >= cutoff]

    # 5. Sort: high → medium → low, then by source type, then by source_id
    type_order = {"quote": 0, "invoice": 1, "payment": 2}
    proposals.sort(key=lambda p: (
        -band_order[p.confidence],
        type_order.get(p.source_type, 99),
        p.source_id,
    ))

    return proposals


# ── Review-queue persistence (read-only: just a snapshot) ────────────

REVIEW_QUEUE_PATH = "/home/rg/empire-repo-main/backend/data/journey_review_queue.json"


def write_review_queue_snapshot(
    proposals: list[Proposal],
    path: str = REVIEW_QUEUE_PATH,
) -> str:
    """Write the current proposal list to a JSON snapshot file.

    This is the ONLY write performed by the review-queue service.
    The live DB is never modified. The snapshot is a regenerable
    artifact and is gitignored.
    """
    snapshot = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "proposal_count": len(proposals),
        "by_confidence": {
            "high": sum(1 for p in proposals if p.confidence == "high"),
            "medium": sum(1 for p in proposals if p.confidence == "medium"),
            "low": sum(1 for p in proposals if p.confidence == "low"),
        },
        "by_source_type": {
            "quote": sum(1 for p in proposals if p.source_type == "quote"),
            "invoice": sum(1 for p in proposals if p.source_type == "invoice"),
            "payment": sum(1 for p in proposals if p.source_type == "payment"),
        },
        "proposals": [p.to_dict() for p in proposals],
    }
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(snapshot, indent=2, default=str))
    tmp.replace(p)
    return str(p)


# ── Live-writes guard ─────────────────────────────────────────────────


class LiveWritesDisabledError(RuntimeError):
    """Raised when a code path tries to write to the live DB.

    The review-queue service is read-only. Any code that attempts
    to mutate the live DB (set quotes_v2.customer_id, clear a
    dangling invoice.quote_id, link a payment to an invoice, etc.)
    must be gated by a founder-approved `JOURNEY_REVIEW_APPLY_ENABLED`
    env var. By default that var is unset, so the apply path
    raises LiveWritesDisabledError.
    """
    pass


def apply_approval_enabled() -> bool:
    """Whether the apply-approval path is enabled.

    This is a separate, opt-in flag. The current pass ships with
    the flag unset, so the apply endpoint always returns
    "approval endpoint reserved; live writes disabled".
    """
    return os.environ.get("JOURNEY_REVIEW_APPLY_ENABLED", "").strip().lower() in (
        "1", "true", "yes", "on",
    )
