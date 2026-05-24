"""Canonical runtime result normalization for MAX orchestration."""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


def _object_payload(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "model_dump"):
        try:
            dumped = value.model_dump()
            if isinstance(dumped, dict):
                return dumped
        except Exception:
            pass
    if hasattr(value, "dict"):
        try:
            dumped = value.dict()
            if isinstance(dumped, dict):
                return dumped
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        return {k: v for k, v in vars(value).items() if not k.startswith("_")}
    return {}


def normalize_runtime_result(value: Any) -> dict[str, Any]:
    """Normalize any provider/tool/SDK result to a non-throwing shape.

    Returned keys are intentionally stable for runtime-truth code:
    success, data, error, provider, raw_type.
    """
    raw_type = type(value).__name__
    if value is None:
        return {
            "success": False,
            "data": None,
            "error": "no result returned",
            "provider": None,
            "raw_type": "NoneType",
        }
    if isinstance(value, BaseException):
        return {
            "success": False,
            "data": None,
            "error": str(value) or raw_type,
            "provider": None,
            "raw_type": raw_type,
        }

    payload = _object_payload(value)
    provider = payload.get("provider") or payload.get("model_provider") or payload.get("model")

    if "success" in payload:
        success = bool(payload.get("success"))
    elif "ok" in payload:
        success = bool(payload.get("ok"))
    elif "error" in payload and payload.get("error"):
        success = False
    elif hasattr(value, "status_code"):
        try:
            status_code = int(getattr(value, "status_code"))
            success = 200 <= status_code < 300
        except Exception:
            success = True
    else:
        success = True

    error = payload.get("error") or payload.get("last_error")
    if not success and not error:
        error = payload.get("detail") or payload.get("message") or "operation did not report success"

    if "data" in payload:
        data = payload.get("data")
    elif "result" in payload:
        data = payload.get("result")
    elif "payload" in payload:
        data = payload.get("payload")
    elif hasattr(value, "json") and callable(getattr(value, "json")):
        try:
            data = value.json()
        except Exception:
            data = payload or None
    else:
        excluded = {
            "tool",
            "name",
            "tool_name",
            "success",
            "ok",
            "error",
            "last_error",
            "detail",
            "message",
            "provider",
            "model_provider",
            "model",
        }
        data = {k: v for k, v in payload.items() if k not in excluded} or payload or value

    return {
        "success": bool(success),
        "data": data,
        "error": str(error) if error else None,
        "provider": str(provider) if provider else None,
        "raw_type": raw_type,
    }


def normalize_tool_result_entry(value: Any) -> dict[str, Any]:
    """Normalize MAX tool result wrappers while preserving tool/result keys."""
    normalized = normalize_runtime_result(value)
    payload = _object_payload(value)
    tool = payload.get("tool") or payload.get("name") or payload.get("tool_name")
    data = normalized["data"]
    return {
        "tool": tool,
        "success": normalized["success"],
        "result": data,
        "error": normalized["error"],
        "provider": normalized["provider"],
        "raw_type": normalized["raw_type"],
    }


def normalize_tool_results(values: list[Any] | None) -> list[dict[str, Any]]:
    return [normalize_tool_result_entry(value) for value in (values or [])]
