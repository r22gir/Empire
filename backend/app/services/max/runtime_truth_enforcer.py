"""Runtime-truth enforcement for MAX operational claims."""
from __future__ import annotations

import re
from typing import Any

from app.services.max.tool_result_normalizer import normalize_tool_results


VERIFICATION_REQUIRED_TOOLS = {
    "send_email",
    "send_quote_email",
    "send_quote_telegram",
    "send_telegram",
    "svg_to_pdf",
    "present",
    "file_write",
    "file_edit",
    "file_append",
    "web_read",
}

ATTACHMENT_REQUEST_RE = re.compile(r"\b(attach|attached|attachment|pdf|document|file)\b", re.IGNORECASE)


def _tool_failure_reason(entry: dict[str, Any], user_message: str | None = None) -> str | None:
    tool = entry.get("tool") or "unknown_tool"
    if tool not in VERIFICATION_REQUIRED_TOOLS:
        return None
    if not entry.get("success"):
        return f"{tool}: {entry.get('error') or 'verification did not report success'}"

    result = entry.get("result")
    result = result if isinstance(result, dict) else {}

    if tool == "send_email" and ATTACHMENT_REQUEST_RE.search(user_message or ""):
        if int(result.get("attachments_sent") or 0) <= 0:
            return "send_email: requested attachment was not verified"
    if tool == "send_quote_email":
        if int(result.get("attachments_sent") or 0) <= 0 or not result.get("pdf_path"):
            return "send_quote_email: quote PDF attachment was not verified"
    if tool in {"svg_to_pdf", "present"}:
        pdf_path = result.get("pdf_path")
        size = int(result.get("size_bytes") or result.get("pdf_size_bytes") or 0)
        if not pdf_path or size <= 0:
            return f"{tool}: generated PDF artifact was not verified"
    if tool in {"file_write", "file_edit", "file_append"}:
        if not result.get("path"):
            return f"{tool}: saved file path was not verified"
    return None


def runtime_truth_failures(tool_results: list[Any] | None, user_message: str | None = None) -> list[str]:
    failures: list[str] = []
    for entry in normalize_tool_results(tool_results):
        reason = _tool_failure_reason(entry, user_message=user_message)
        if reason:
            failures.append(reason)
    return failures


def should_halt_after_tool_failure(tool_results: list[Any] | None, user_message: str | None = None) -> bool:
    return bool(runtime_truth_failures(tool_results, user_message=user_message))


def runtime_truth_failure_message(failures: list[str]) -> str:
    unique = list(dict.fromkeys([failure for failure in failures if failure]))
    reason = "; ".join(unique) if unique else "operation verification failed"
    return f"I attempted this, but verification failed: {reason}"


def enforce_runtime_truth_response(
    user_message: str | None,
    response_text: str,
    tool_results: list[Any] | None,
) -> str:
    failures = runtime_truth_failures(tool_results, user_message=user_message)
    if failures:
        return runtime_truth_failure_message(failures)
    return response_text
