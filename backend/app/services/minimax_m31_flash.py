"""MiniMax-M3.1-Flash-Preview registry helpers and explicit probe.

Official id: MiniMax-M3.1-Flash-Preview
Docs: https://platform.minimax.io/docs/guides/models-intro
Available only on MiniMax M Plan and MiniMax Code. Uses MINIMAX_API_KEY.
H3 is a video model and is not registered here.

The probe makes one tiny chat call only when explicitly requested
(MINIMAX_M31_FLASH_PROBE=1 or scripts/minimax_m31_flash_probe.py --live).
Startup never spends unless that env is set.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

from app.services.max.routing_state import (
    MINIMAX_M31_FLASH_DISPLAY,
    MINIMAX_M31_FLASH_MODEL,
    env_flag,
    minimax_flash_allowed_for_edition,
    minimax_model_display_name,
)

logger = logging.getLogger("max.minimax_m31_flash")

MODEL_ID = MINIMAX_M31_FLASH_MODEL
DISPLAY_NAME = MINIMAX_M31_FLASH_DISPLAY

_PLAN_MARKERS = (
    "not support",
    "not available",
    "does not exist",
    "unknown model",
    "invalid model",
    "model_not_found",
    "not in your plan",
    "permission denied",
    "no permission",
    "access denied",
    "not authorized",
    "m plan",
    "minimax code",
)


class PlanUnsupportedError(RuntimeError):
    """This MiniMax key's plan does not include the requested model."""


def plan_unsupported_message(model: str = MODEL_ID, detail: str = "") -> str:
    extra = f" ({detail.strip()[:180]})" if (detail or "").strip() else ""
    return (
        f"{minimax_model_display_name(model)} is available only on MiniMax M Plan "
        f"and MiniMax Code. This key's plan does not support it. "
        f"Stay on MiniMax-M3 or upgrade the MiniMax plan.{extra}"
    )


def is_plan_unsupported_payload(
    model: str,
    body: str = "",
    status_code: Optional[int] = None,
    payload: Optional[dict[str, Any]] = None,
) -> bool:
    if (model or "").strip() != MODEL_ID:
        return False
    if status_code in {401, 403, 404}:
        return True
    text = (body or "").lower()
    if any(marker in text for marker in _PLAN_MARKERS):
        return True
    if isinstance(payload, dict):
        base = payload.get("base_resp") if isinstance(payload.get("base_resp"), dict) else {}
        try:
            code = int(base.get("status_code", payload.get("status_code", 0)) or 0)
        except (TypeError, ValueError):
            code = 0
        if code in {1004, 1008, 2013, 2049}:
            return True
        msg = str(base.get("status_msg") or payload.get("error") or "").lower()
        if any(marker in msg for marker in _PLAN_MARKERS):
            return True
    return False


def maybe_raise_plan_unsupported(model: str, *, body: str = "", status_code: Optional[int] = None, payload: Optional[dict] = None) -> None:
    if is_plan_unsupported_payload(model, body=body, status_code=status_code, payload=payload):
        raise PlanUnsupportedError(plan_unsupported_message(model, body))


def probe_enabled() -> bool:
    if os.getenv("PYTEST_CURRENT_TEST") and not env_flag("MINIMAX_M31_FLASH_PROBE", False):
        return False
    return env_flag("MINIMAX_M31_FLASH_PROBE", False)


def probe_m31_flash(*, live: bool = False, timeout: float = 3.0) -> dict[str, Any]:
    """Dry-run by default. One tiny completions call only when live=True."""
    report: dict[str, Any] = {
        "ok": True,
        "live": bool(live),
        "model": MODEL_ID,
        "display": DISPLAY_NAME,
        "founder_only": not env_flag("MINIMAX_M31_FLASH_FAMILY", False),
        "allowed_this_edition": minimax_flash_allowed_for_edition(),
        "key_present": bool((os.getenv("MINIMAX_API_KEY") or "").strip()),
        "reason": "dry-run: no HTTP",
    }
    if not live:
        return report
    key = (os.getenv("MINIMAX_API_KEY") or "").strip()
    if not key:
        report["ok"] = False
        report["reason"] = "MINIMAX_API_KEY is not set"
        return report
    if not minimax_flash_allowed_for_edition():
        report["ok"] = False
        report["reason"] = (
            "MiniMax-M3.1-Flash-Preview is founder-only. "
            "Set MINIMAX_M31_FLASH_FAMILY=1 to enable it on Max-e / Maxine."
        )
        return report
    import httpx

    base = (os.getenv("MINIMAX_BASE_URL") or "https://api.minimax.io/v1").rstrip("/")
    try:
        resp = httpx.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": MODEL_ID,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1,
            },
            timeout=timeout,
        )
    except Exception as exc:
        report["ok"] = False
        report["reason"] = f"{type(exc).__name__}"
        return report
    body = (resp.text or "")[:400]
    payload: Optional[dict[str, Any]] = None
    try:
        data = resp.json()
        payload = data if isinstance(data, dict) else None
    except Exception:
        payload = None
    if is_plan_unsupported_payload(MODEL_ID, body=body, status_code=resp.status_code, payload=payload):
        report["ok"] = False
        report["reason"] = plan_unsupported_message(MODEL_ID, body)
        return report
    if resp.status_code != 200:
        report["ok"] = False
        report["reason"] = f"MiniMax HTTP {resp.status_code}"
        return report
    report["reason"] = "ok"
    return report


def maybe_startup_probe() -> dict[str, Any]:
    """Register-only at boot unless MINIMAX_M31_FLASH_PROBE=1."""
    if not probe_enabled():
        logger.info(
            "MiniMax text registry includes %s (founder-only; probe skipped)",
            MODEL_ID,
        )
        return {"ok": True, "live": False, "model": MODEL_ID, "reason": "startup skip"}
    report = probe_m31_flash(live=True)
    if report.get("ok"):
        logger.info("MiniMax-M3.1-Flash-Preview probe ok")
    else:
        logger.warning("MiniMax-M3.1-Flash-Preview probe: %s", report.get("reason"))
    return report
