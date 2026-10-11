"""MiniMax remaining-quota and credit probes.

Public docs name GET /v1/token_plan/remains (host varies: www.minimax.io
and api.minimax.io). Percentages on the wire are REMAINING, not used.
HTTP 200 is not success — read base_resp.status_code (0 = ok; 1004/2049
= auth). Gift credits auto-apply after plan quota; this module never
treats a credit balance as spendable room.

No live generation. Keys stay in env and never appear in logs.
"""
from __future__ import annotations

import logging
import os
import re
import time
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("max.minimax_quota")

_KEY_RE = re.compile(
    r"(?i)(authorization|api[_-]?key|bearer|secret|token)\s*[:=]\s*\S+"
)
_BEARER_RE = re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]+")

AUTH_FAILURE_CODES = frozenset({1004, 2049})
DEFAULT_SUCCESS_TTL_SECONDS = 15  # 10–30s brief positive cache
DEFAULT_FAILURE_TTL_SECONDS = 45  # 30–60s negative cache
DEFAULT_PROBE_TIMEOUT_SECONDS = 3.0
MAX_PROBE_TIMEOUT_SECONDS = 3.0

# Docs + observed hosts. First match with a usable envelope wins.
REMAINS_PATHS = (
    "/v1/token_plan/remains",
    "/v1/api/openplatform/coding_plan/remains",
)
CREDIT_PATHS = (
    "/v1/api/openplatform/credit",
    "/v1/credit",
    "/v1/credit_balance",
)


class QuotaUnavailable(Exception):
    """Remains/credit endpoint was missing, rejected, or unparseable."""


def redact_secret(text: str) -> str:
    if not text:
        return ""
    out = _BEARER_RE.sub("Bearer [KEY_REDACTED]", str(text))
    out = _KEY_RE.sub("[KEY_REDACTED]", out)
    key = os.getenv("MINIMAX_API_KEY", "")
    if key and len(key) >= 8:
        out = out.replace(key, "[KEY_REDACTED]")
    return out


def _api_key() -> str:
    return (os.getenv("MINIMAX_API_KEY") or "").strip()


def _hosts() -> list[str]:
    raw = (os.getenv("MINIMAX_REMAINS_BASE") or "").strip().rstrip("/")
    hosts: list[str] = []
    if raw:
        hosts.append(raw)
    base = (os.getenv("MINIMAX_BASE_URL") or "https://api.minimax.io/v1").strip().rstrip("/")
    parsed = urlparse(base if "://" in base else f"https://{base}")
    origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else "https://api.minimax.io"
    for candidate in (
        origin,
        "https://api.minimax.io",
        "https://www.minimax.io",
    ):
        if candidate not in hosts:
            hosts.append(candidate)
    return hosts


def _headers() -> dict[str, str]:
    key = _api_key()
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _float(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip().rstrip("%")
        try:
            return float(text)
        except ValueError:
            return None
    return None


def _walk_remaining(obj: Any, found: list[tuple[str, float]], prefix: str = "") -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            lower = str(key).lower()
            num = _float(value)
            if num is not None and any(token in lower for token in ("remain", "left", "unused")):
                # Percentages are remaining. Absolute counts stay tagged.
                found.append((name, num))
            elif isinstance(value, (dict, list)):
                _walk_remaining(value, found, name)
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            _walk_remaining(item, found, f"{prefix}[{idx}]")


def _walk_credits(obj: Any) -> Optional[float]:
    if isinstance(obj, dict):
        for key in (
            "credit",
            "credits",
            "credit_balance",
            "balance",
            "gift_credit",
            "gift_credits",
            "available_credit",
        ):
            if key in obj:
                num = _float(obj.get(key))
                if num is not None:
                    return num
        for value in obj.values():
            nested = _walk_credits(value)
            if nested is not None:
                return nested
    elif isinstance(obj, list):
        for item in obj:
            nested = _walk_credits(item)
            if nested is not None:
                return nested
    return None


def parse_remains(payload: dict) -> dict:
    """Normalize a remains envelope. Percentages stay remaining (not used)."""
    if not isinstance(payload, dict):
        raise QuotaUnavailable("remains payload is not an object")
    base = payload.get("base_resp") if isinstance(payload.get("base_resp"), dict) else {}
    status = base.get("status_code", payload.get("status_code", 0))
    try:
        status_i = int(status)
    except (TypeError, ValueError):
        status_i = 0
    if status_i in AUTH_FAILURE_CODES:
        raise QuotaUnavailable("minimax remains auth failed")
    if status_i not in (0, 200) and not payload.get("model_remains"):
        raise QuotaUnavailable(f"minimax remains status {status_i}")

    found: list[tuple[str, float]] = []
    _walk_remaining(payload, found)
    pcts = [(name, value) for name, value in found if 0 <= value <= 100]
    if not pcts:
        raise QuotaUnavailable("no remaining-percent fields in remains payload")
    remaining_pct = min(value for _name, value in pcts)
    used_pct = max(0.0, min(100.0, 100.0 - remaining_pct))
    buckets = payload.get("model_remains") if isinstance(payload.get("model_remains"), list) else []
    return {
        "ok": True,
        "available": True,
        "remaining_pct": round(remaining_pct, 2),
        "used_pct": round(used_pct, 2),
        "windows": [{"path": name, "remaining_pct": value} for name, value in pcts],
        "bucket_count": len(buckets),
        "credit_hint": _walk_credits(payload),
        "status_code": status_i,
    }


_cache: dict[str, Any] = {
    "remains": None,
    "remains_at": 0.0,
    "credits": None,
    "credits_at": 0.0,
}


def cache_ttl() -> int:
    """Legacy single TTL. Prefer success/failure TTLs below."""
    raw = (os.getenv("MINIMAX_REMAINS_TTL_SECONDS") or "").strip()
    try:
        return max(5, int(raw)) if raw else DEFAULT_SUCCESS_TTL_SECONDS
    except ValueError:
        return DEFAULT_SUCCESS_TTL_SECONDS


def success_ttl() -> float:
    raw = (os.getenv("MINIMAX_REMAINS_SUCCESS_TTL") or "").strip()
    try:
        value = float(raw) if raw else DEFAULT_SUCCESS_TTL_SECONDS
    except ValueError:
        value = DEFAULT_SUCCESS_TTL_SECONDS
    return min(30.0, max(10.0, value))


def failure_ttl() -> float:
    raw = (os.getenv("MINIMAX_REMAINS_FAILURE_TTL") or "").strip()
    try:
        value = float(raw) if raw else DEFAULT_FAILURE_TTL_SECONDS
    except ValueError:
        value = DEFAULT_FAILURE_TTL_SECONDS
    return min(60.0, max(30.0, value))


def probe_timeout() -> float:
    raw = (os.getenv("MINIMAX_REMAINS_TIMEOUT") or "").strip()
    try:
        value = float(raw) if raw else DEFAULT_PROBE_TIMEOUT_SECONDS
    except ValueError:
        value = DEFAULT_PROBE_TIMEOUT_SECONDS
    return min(MAX_PROBE_TIMEOUT_SECONDS, max(0.2, value))


def _ttl_for(payload: Optional[dict]) -> float:
    if payload and payload.get("available"):
        return success_ttl()
    return failure_ttl()


def _cache_fresh(key: str) -> Optional[dict]:
    row = _cache.get(key)
    at = float(_cache.get(f"{key}_at") or 0)
    if not row or at <= 0:
        return None
    if time.time() - at >= _ttl_for(row):
        return None
    return dict(row)


def _store_cache(key: str, payload: dict) -> dict:
    _cache[key] = payload
    _cache[f"{key}_at"] = time.time()
    return dict(payload)


def _get_json(url: str, timeout: Optional[float] = None) -> dict:
    if not _api_key():
        raise QuotaUnavailable("MINIMAX_API_KEY not set")
    limit = probe_timeout() if timeout is None else min(probe_timeout(), max(0.1, float(timeout)))
    try:
        with httpx.Client(timeout=limit) as client:
            resp = client.get(url, headers=_headers())
    except Exception as exc:
        raise QuotaUnavailable(redact_secret(f"{type(exc).__name__}")) from None
    try:
        data = resp.json()
    except Exception:
        raise QuotaUnavailable(f"non-json remains HTTP {resp.status_code}") from None
    if not isinstance(data, dict):
        raise QuotaUnavailable("remains JSON is not an object")
    return data


def remains_probe_enabled() -> bool:
    raw = (os.getenv("MINIMAX_REMAINS_PROBE") or "1").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    if os.getenv("PYTEST_CURRENT_TEST"):
        return False
    key = _api_key()
    if not key or key.startswith("test") or key in {"mm", "fake", "dummy", "test-mm-key", "test-minimax-key"}:
        return False
    return True


def fetch_remains(*, force: bool = False) -> dict:
    """Best-effort remains snapshot. Never logs the key.

    One overall budget of ``probe_timeout()`` (≤ 3s). Successes cache
    10–30s; failures cache 30–60s so a down endpoint does not stall chat.
    """
    if not remains_probe_enabled() and not force:
        return {
            "ok": False,
            "available": False,
            "remaining_pct": None,
            "used_pct": None,
            "windows": [],
            "reason": "remains probe disabled (tests / placeholder key)",
        }
    if not force:
        cached = _cache_fresh("remains")
        if cached is not None:
            return cached
    errors: list[str] = []
    deadline = time.monotonic() + probe_timeout()
    for host in _hosts():
        for path in REMAINS_PATHS:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                errors.append("probe budget exhausted")
                break
            url = f"{host}{path}"
            try:
                parsed = parse_remains(_get_json(url, timeout=remaining))
                parsed["endpoint"] = path
                parsed["host"] = urlparse(host).netloc
                return _store_cache("remains", parsed)
            except QuotaUnavailable as exc:
                errors.append(f"{path}: {exc}")
                continue
        else:
            continue
        break
    logger.info("minimax remains unavailable: %s", "; ".join(redact_secret(e) for e in errors[:6]))
    return _store_cache("remains", {
        "ok": False,
        "available": False,
        "remaining_pct": None,
        "used_pct": None,
        "windows": [],
        "reason": "remains endpoint unavailable; using local meter only",
    })


def fetch_credits(*, force: bool = False) -> dict:
    """Best-effort credit balance. Absence is not spendable room."""
    if not remains_probe_enabled() and not force:
        return {"ok": False, "available": False, "balance": None, "reason": "probe disabled"}
    if not force:
        cached = _cache_fresh("credits")
        if cached is not None:
            return cached
    if not _api_key():
        return _store_cache("credits", {"ok": False, "available": False, "balance": None, "reason": "no key"})
    deadline = time.monotonic() + probe_timeout()
    for host in _hosts():
        for path in CREDIT_PATHS:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                data = _get_json(f"{host}{path}", timeout=remaining)
            except QuotaUnavailable:
                continue
            balance = _walk_credits(data)
            if balance is None:
                continue
            parsed = {
                "ok": True,
                "available": True,
                "balance": balance,
                "endpoint": path,
                "host": urlparse(host).netloc,
            }
            return _store_cache("credits", parsed)
    remains = _cache_fresh("remains") or fetch_remains(force=force)
    hint = remains.get("credit_hint")
    if hint is not None:
        parsed = {"ok": True, "available": True, "balance": hint, "endpoint": "remains.credit_hint"}
        return _store_cache("credits", parsed)
    return _store_cache("credits", {
        "ok": False,
        "available": False,
        "balance": None,
        "reason": "credit endpoint not found",
    })


def clear_quota_cache() -> None:
    _cache["remains_at"] = 0.0
    _cache["credits_at"] = 0.0
    _cache["remains"] = None
    _cache["credits"] = None
