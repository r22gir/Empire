"""Square Invoices API — Share link (SHARE_MANUALLY) only. Never email/SMS/send."""
from __future__ import annotations

import logging
import re
import uuid
from datetime import date, timedelta
from typing import Any, Callable, Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("max.client_invoice.square")

SQUARE_API = "https://connect.squareup.com/v2"
DELIVERY_SHARE_LINK = "SHARE_MANUALLY"
_FORBIDDEN_DELIVERY = frozenset({"EMAIL", "SMS", "TEXT"})
_FORBIDDEN_PATH = re.compile(r"/(send)(Mail)?/?$", re.IGNORECASE)
_REDACT = re.compile(r"(?i)(authorization|access_token|bearer)\s*[:=]\s*\S+")


class SquareSendForbidden(RuntimeError):
    """Raised if any Square call would email, text, or /send the client."""


class SquareInvoiceError(RuntimeError):
    pass


def resolve_square_due_date(invoice: dict | None = None, business=None) -> str:
    """Square payment_requests.due_date. Default is due-on-receipt (invoice date).

    Configurable via invoice['square_due_date'] (YYYY-MM-DD) or
    invoice/business square_due_days (0 = due on receipt).
    """
    invoice = invoice or {}
    explicit = invoice.get("square_due_date") or getattr(business, "square_due_date", None)
    if explicit and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(explicit)[:10]):
        return str(explicit)[:10]
    days = invoice.get("square_due_days")
    if days is None:
        days = getattr(business, "square_due_days", 0)
    try:
        days = int(days if days is not None else 0)
    except (TypeError, ValueError):
        days = 0
    raw = str(invoice.get("invoice_date") or invoice.get("created_at") or date.today().isoformat())[:10]
    try:
        base = date.fromisoformat(raw)
    except ValueError:
        base = date.today()
    return (base + timedelta(days=days)).isoformat()


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        return _REDACT.sub(r"\1: [redacted]", value)
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if str(k).lower() in {"authorization", "access_token", "token", "square_token"}:
                out[k] = "[redacted]"
            else:
                out[k] = _redact(v)
        return out
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


def _cents(amount: float) -> int:
    return int(round(float(amount or 0) * 100))


def _log(log: list | None, event: str, **fields: Any) -> None:
    row = {"event": event, **_redact(fields)}
    if log is not None:
        log.append(row)
    logger.info("square %s %s", event, {k: v for k, v in row.items() if k != "event"})


def _assert_safe_path(path: str) -> None:
    if _FORBIDDEN_PATH.search(path or "") or "sendMail" in (path or ""):
        raise SquareSendForbidden(f"Square send path is forbidden: {path}")


def _assert_share_link(invoice_body: dict) -> None:
    method = str((invoice_body or {}).get("delivery_method") or "").upper()
    if method in _FORBIDDEN_DELIVERY:
        raise SquareSendForbidden(f"Square delivery_method {method} is forbidden; SHARE_MANUALLY only")
    if method != DELIVERY_SHARE_LINK:
        raise SquareSendForbidden(
            f"Square delivery_method must be {DELIVERY_SHARE_LINK} (Share link), got {method or '(empty)'}"
        )


class SquareInvoiceClient:
    """Thin Square Invoices client. Injectable HTTP. No send function exists."""

    def __init__(
        self,
        *,
        access_token: str,
        location_id: str,
        http: Optional[httpx.Client] = None,
        http_factory: Optional[Callable[[], httpx.Client]] = None,
        log: Optional[list] = None,
        api_base: str = SQUARE_API,
    ):
        if not (access_token or "").strip():
            raise SquareInvoiceError("Square access token is not configured for this business")
        if not (location_id or "").strip():
            raise SquareInvoiceError("Square location id is not configured for this business")
        self._token = access_token
        self.location_id = location_id
        self._http = http
        self._http_factory = http_factory
        self.log = log if log is not None else []
        self.api_base = api_base.rstrip("/")

    def _client(self) -> httpx.Client:
        if self._http is not None:
            return self._http
        if self._http_factory is not None:
            return self._http_factory()
        return httpx.Client(timeout=20)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Square-Version": "2024-12-18",
        }

    def request(self, method: str, path: str, json_body: dict | None = None) -> dict:
        _assert_safe_path(path)
        if path.rstrip("/").endswith("/send"):
            raise SquareSendForbidden("Square /send is not implemented and is forbidden")
        url = path if path.startswith("http") else f"{self.api_base}{path}"
        own = self._http is None and self._http_factory is None
        client = self._client()
        try:
            resp = client.request(method.upper(), url, headers=self._headers(), json=json_body)
        finally:
            if own:
                client.close()
        _log(self.log, "square_http", method=method.upper(), path=urlparse(url).path,
             delivery_method=(json_body or {}).get("invoice", {}).get("delivery_method")
             if isinstance(json_body, dict) else None,
             status=resp.status_code)
        if resp.status_code >= 400:
            raise SquareInvoiceError(f"Square {method} {urlparse(url).path} failed ({resp.status_code})")
        try:
            return resp.json() if resp.content else {}
        except Exception as exc:
            raise SquareInvoiceError("Square returned a non-JSON body") from exc

    def create_share_link_invoice(
        self,
        *,
        invoice_number: str,
        client_name: str,
        client_email: str,
        line_items: list[dict],
        total: float,
        due_date: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict:
        """Create + publish a Square invoice that can only be shared by link."""
        due = due_date or resolve_square_due_date()
        key = idempotency_key or f"inv-{invoice_number}-{uuid.uuid4().hex[:8]}"

        customer = self.request("POST", "/customers", {
            "idempotency_key": f"{key}-cust",
            "given_name": (client_name or "Client").split(" ", 1)[0],
            "family_name": " ".join((client_name or "Client").split(" ")[1:]) or "Account",
            "email_address": client_email or None,
            "reference_id": invoice_number,
        })
        customer_id = (customer.get("customer") or {}).get("id")
        if not customer_id:
            raise SquareInvoiceError("Square customer create did not return an id")

        order_lines = []
        for it in line_items or []:
            name = str(it.get("description") or it.get("client_description") or "Item")[:100]
            qty = str(int(float(it.get("quantity", 1) or 1)))
            amt = it.get("total", it.get("amount"))
            if amt is None:
                amt = float(it.get("quantity", 1) or 1) * float(it.get("unit_price", it.get("rate", 0)) or 0)
            order_lines.append({
                "name": name,
                "quantity": qty if float(qty) > 0 else "1",
                "base_price_money": {"amount": _cents(float(amt) / max(float(qty or 1), 1)), "currency": "USD"},
            })
        if not order_lines:
            order_lines = [{
                "name": f"Invoice {invoice_number}",
                "quantity": "1",
                "base_price_money": {"amount": _cents(total), "currency": "USD"},
            }]

        order = self.request("POST", "/orders", {
            "idempotency_key": f"{key}-order",
            "order": {"location_id": self.location_id, "reference_id": invoice_number, "line_items": order_lines},
        })
        order_id = (order.get("order") or {}).get("id")
        if not order_id:
            raise SquareInvoiceError("Square order create did not return an id")

        invoice_body = {
            "location_id": self.location_id,
            "order_id": order_id,
            "primary_recipient": {"customer_id": customer_id},
            "delivery_method": DELIVERY_SHARE_LINK,
            "invoice_number": str(invoice_number)[:20],
            "payment_requests": [{
                "request_type": "BALANCE",
                "due_date": str(due)[:10],
            }],
            "accepted_payment_methods": {"card": True},
        }
        _assert_share_link(invoice_body)
        created = self.request("POST", "/invoices", {
            "idempotency_key": f"{key}-inv",
            "invoice": invoice_body,
        })
        inv = created.get("invoice") or {}
        _assert_share_link(inv if inv.get("delivery_method") else invoice_body)
        if str(inv.get("delivery_method") or DELIVERY_SHARE_LINK).upper() != DELIVERY_SHARE_LINK:
            raise SquareSendForbidden("Square returned a non-share-link delivery method")
        inv_id = inv.get("id")
        version = inv.get("version", 0)
        if not inv_id:
            raise SquareInvoiceError("Square invoice create did not return an id")

        published = self.request("POST", f"/invoices/{inv_id}/publish", {
            "version": version,
            "idempotency_key": f"{key}-pub",
        })
        pub = published.get("invoice") or inv
        if str(pub.get("delivery_method") or "").upper() in _FORBIDDEN_DELIVERY:
            raise SquareSendForbidden("Square publish returned EMAIL/SMS delivery")
        url = pub.get("public_url") or inv.get("public_url")
        if not url:
            raise SquareInvoiceError("Square publish did not return a public_url")
        _log(self.log, "square_share_link",
             invoice_id=inv_id, delivery_method=DELIVERY_SHARE_LINK, public_url=url)
        return {
            "square_invoice_id": inv_id,
            "public_url": url,
            "delivery_method": DELIVERY_SHARE_LINK,
            "delivery_label": "Share link",
            "version": pub.get("version", version),
        }
