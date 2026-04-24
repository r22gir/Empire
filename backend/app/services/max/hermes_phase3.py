"""Hermes Phase 3 gated browser assistance and extra-channel interface points."""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urlparse

import httpx
from bs4 import BeautifulSoup

from app.services.max.hermes_memory import TRUTH_HIERARCHY, memory_root
from app.services.max.surface_identity import normalize_surface


BROWSER_ACTION_STATES = ("planned", "approved", "completed", "failed")
PHASE3_CHANNELS = ("whatsapp", "discord")

BROWSER_WORKFLOWS: dict[str, dict[str, Any]] = {
    "life_magazine_lookup_assist": {
        "label": "LIFE magazine lookup assistance",
        "description": "Read-only issue lookup and page extraction assistance for LIFE magazine references.",
        "allowed_steps": ("open_lookup_page", "extract_issue_candidates", "stage_lookup_notes"),
    },
    "repetitive_form_navigation_prep": {
        "label": "Repetitive form navigation/prep",
        "description": "Read form structure, identify navigation steps, and stage optional fields without submission.",
        "allowed_steps": ("open_form_page", "extract_form_structure", "stage_optional_fields"),
    },
    "read_only_page_extraction": {
        "label": "Read-only page extraction",
        "description": "Fetch page title/meta/headings/forms for review only.",
        "allowed_steps": ("open_page", "extract_read_only_content"),
    },
    "optional_field_fill_staging": {
        "label": "Optional field fill staging",
        "description": "Stage optional field values from a Hermes draft without submission.",
        "allowed_steps": ("open_form_page", "identify_editable_fields", "stage_optional_fields"),
    },
}

PLAN_MARKERS = (
    "browser assist",
    "browser assistance",
    "browser action",
    "browser plan",
    "plan hermes browser",
    "browser lookup",
    "read-only page extract",
    "page extraction",
    "page extract",
    "form navigation",
    "stage fields",
)
APPROVAL_PATTERN = re.compile(r"\bapprove\s+hermes\s+browser\s+action\s+([A-Za-z0-9_:-]+)\b", re.IGNORECASE)
EXECUTION_PATTERN = re.compile(r"\b(?:run|execute)\s+hermes\s+browser\s+action\s+([A-Za-z0-9_:-]+)\b", re.IGNORECASE)
LOG_MARKERS = (
    "browser logs",
    "browser log",
    "browser audit",
    "browser action logs",
    "show hermes browser logs",
)
CHANNEL_MARKERS = (
    "hermes channels",
    "extra channels",
    "whatsapp status",
    "discord status",
    "show hermes channels",
)


def browser_actions_root() -> Path:
    return memory_root() / "BROWSER_ACTIONS"


def browser_action_records_dir() -> Path:
    return browser_actions_root() / "records"


def browser_action_audit_log_path() -> Path:
    return browser_actions_root() / "audit.jsonl"


def channels_root() -> Path:
    return memory_root() / "CHANNELS"


def channel_interfaces_path() -> Path:
    return channels_root() / "interfaces.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def _invalidate_prompt_cache() -> None:
    try:
        from app.services.max.system_prompt import _prompt_cache

        _prompt_cache.update({"prompt": None, "expires": 0})
    except Exception:
        pass


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _json_load(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _record_path(action_id: str) -> Path:
    return browser_action_records_dir() / f"{action_id}.json"


def _append_audit(
    *,
    action_id: str | None,
    event: str,
    actor: str,
    state: str | None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_hermes_phase3_scaffold()
    entry = {
        "timestamp": _now(),
        "action_id": action_id,
        "event": event,
        "actor": actor,
        "state": state,
        "details": details or {},
    }
    with browser_action_audit_log_path().open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def _phase3_channel_defaults() -> dict[str, Any]:
    whatsapp_configured = bool(os.getenv("HERMES_WHATSAPP_WEBHOOK_URL") or os.getenv("WHATSAPP_ACCESS_TOKEN"))
    discord_configured = bool(os.getenv("HERMES_DISCORD_BOT_TOKEN") or os.getenv("DISCORD_BOT_TOKEN"))
    return {
        "whatsapp": {
            "channel": "whatsapp",
            "status": "partial_disabled_gateway" if whatsapp_configured else "disabled",
            "enabled": False,
            "interface_point": "phase3_gateway_placeholder",
            "transport_configured": whatsapp_configured,
            "browser_assist_supported": False,
            "autonomous_messaging_allowed": False,
            "reason": (
                "Transport config exists but autonomous messaging remains disabled."
                if whatsapp_configured
                else "No verified transport/auth configured. Interface point only."
            ),
        },
        "discord": {
            "channel": "discord",
            "status": "partial_disabled_gateway" if discord_configured else "disabled",
            "enabled": False,
            "interface_point": "phase3_gateway_placeholder",
            "transport_configured": discord_configured,
            "browser_assist_supported": False,
            "autonomous_messaging_allowed": False,
            "reason": (
                "Transport config exists but autonomous messaging remains disabled."
                if discord_configured
                else "No verified transport/auth configured. Interface point only."
            ),
        },
    }


def ensure_hermes_phase3_scaffold() -> dict[str, Any]:
    browser_actions_root().mkdir(parents=True, exist_ok=True)
    browser_action_records_dir().mkdir(parents=True, exist_ok=True)
    channels_root().mkdir(parents=True, exist_ok=True)
    if not browser_action_audit_log_path().exists():
        browser_action_audit_log_path().write_text("", encoding="utf-8")
    if not channel_interfaces_path().exists():
        _json_dump(channel_interfaces_path(), _phase3_channel_defaults())
    return {
        "browser_actions_dir": str(browser_actions_root()),
        "browser_action_records_dir": str(browser_action_records_dir()),
        "browser_action_audit_log": str(browser_action_audit_log_path()),
        "channels_dir": str(channels_root()),
        "channel_interfaces": str(channel_interfaces_path()),
    }


def _extract_url(text: str) -> str | None:
    match = re.search(r"https?://[^\s)>\]]+", text or "")
    return match.group(0).rstrip(".,") if match else None


def _extract_date(text: str) -> str | None:
    match = re.search(r"\b(20\d{2}|19\d{2})-\d{2}-\d{2}\b", text or "")
    return match.group(0) if match else None


def _extract_subject(text: str) -> str | None:
    quoted = re.search(r'"([^"]+)"', text or "")
    if quoted:
        return quoted.group(1).strip()
    if "apollo 11" in (text or "").lower():
        return "Apollo 11"
    match = re.search(r"\b(?:subject|cover|lookup)\s+([A-Za-z0-9 '&()/.-]+)", text or "", flags=re.IGNORECASE)
    return match.group(1).strip() if match else None


def _safe_url_for_life_lookup(message: str) -> str:
    date_hint = _extract_date(message) or ""
    subject = _extract_subject(message) or "LIFE magazine"
    query = " ".join(part for part in ["LIFE magazine", date_hint, subject] if part).strip()
    return f"https://books.google.com/books?q={quote_plus(query)}"


def _extract_workflow_from_message(message: str | None) -> str | None:
    text = (message or "").lower()
    if "life magazine" in text or ("life" in text and "lookup" in text):
        return "life_magazine_lookup_assist"
    if ("stage fields" in text or "field staging" in text or "fill staging" in text) and _extract_url(text):
        return "optional_field_fill_staging"
    if "form" in text and any(token in text for token in ("browser", "navigate", "navigation", "prep", "prepare")):
        return "repetitive_form_navigation_prep"
    if any(token in text for token in ("page extract", "page extraction", "read-only page extract", "extract page")) and _extract_url(text):
        return "read_only_page_extraction"
    return None


def detect_browser_plan_request(message: str | None) -> str | None:
    text = (message or "").lower()
    if not any(marker in text for marker in PLAN_MARKERS):
        return None
    return _extract_workflow_from_message(text)


def is_browser_plan_request(message: str | None) -> bool:
    return detect_browser_plan_request(message) is not None


def parse_approval_request(message: str | None) -> str | None:
    match = APPROVAL_PATTERN.search(message or "")
    return match.group(1) if match else None


def parse_execution_request(message: str | None) -> str | None:
    match = EXECUTION_PATTERN.search(message or "")
    return match.group(1) if match else None


def is_browser_log_request(message: str | None) -> bool:
    text = (message or "").lower()
    return any(marker in text for marker in LOG_MARKERS)


def is_channel_status_request(message: str | None) -> bool:
    text = (message or "").lower()
    return any(marker in text for marker in CHANNEL_MARKERS)


def _latest_phase2_draft_for_message(message: str) -> dict[str, Any] | None:
    try:
        from app.services.max.hermes_phase2 import latest_prefill_draft
    except Exception:
        return None
    text = (message or "").lower()
    if "life" in text:
        return latest_prefill_draft("life_magazine_intake")
    if "vendorops" in text or "vendor ops" in text:
        return latest_prefill_draft("vendorops_vendor_entry")
    if "relist" in text:
        return latest_prefill_draft("relistapp_source_import")
    if "marketforge" in text or "market forge" in text:
        return latest_prefill_draft("marketforge_batch_intake")
    return latest_prefill_draft()


def _planned_steps(workflow_key: str, target_url: str | None, staged_fields: dict[str, Any]) -> list[dict[str, Any]]:
    if workflow_key == "life_magazine_lookup_assist":
        return [
            {"step": "open_lookup_page", "status": "planned", "target_url": target_url},
            {"step": "extract_issue_candidates", "status": "planned"},
            {"step": "stage_lookup_notes", "status": "planned"},
        ]
    if workflow_key == "repetitive_form_navigation_prep":
        return [
            {"step": "open_form_page", "status": "planned", "target_url": target_url},
            {"step": "extract_form_structure", "status": "planned"},
            {"step": "stage_optional_fields", "status": "planned", "field_count": len(staged_fields)},
        ]
    if workflow_key == "optional_field_fill_staging":
        return [
            {"step": "open_form_page", "status": "planned", "target_url": target_url},
            {"step": "identify_editable_fields", "status": "planned"},
            {"step": "stage_optional_fields", "status": "planned", "field_count": len(staged_fields)},
        ]
    return [
        {"step": "open_page", "status": "planned", "target_url": target_url},
        {"step": "extract_read_only_content", "status": "planned"},
    ]


def _save_action_record(record: dict[str, Any]) -> dict[str, Any]:
    ensure_hermes_phase3_scaffold()
    record["updated_at"] = _now()
    _json_dump(_record_path(record["id"]), record)
    _invalidate_prompt_cache()
    return record


def get_browser_action(action_id: str) -> dict[str, Any] | None:
    ensure_hermes_phase3_scaffold()
    return _json_load(_record_path(action_id))


def list_browser_actions(*, state: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    ensure_hermes_phase3_scaffold()
    records: list[dict[str, Any]] = []
    for path in sorted(browser_action_records_dir().glob("*.json"), reverse=True):
        data = _json_load(path)
        if data:
            records.append(data)
    records.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    if state:
        records = [item for item in records if item.get("state") == state]
    return records[:limit]


def create_browser_action_plan(message: str, *, channel: str = "web") -> dict[str, Any]:
    workflow_key = detect_browser_plan_request(message)
    if not workflow_key:
        raise ValueError("Hermes browser-assist workflow not detected.")
    ensure_hermes_phase3_scaffold()
    draft = _latest_phase2_draft_for_message(message) or {}
    staged_fields = ((draft.get("fields") or {}) if workflow_key in {"repetitive_form_navigation_prep", "optional_field_fill_staging"} else {})
    target_url = _extract_url(message)
    if workflow_key == "life_magazine_lookup_assist" and not target_url:
        target_url = _safe_url_for_life_lookup(message)
    action_id = _new_id("hermes_browser")
    record = {
        "id": action_id,
        "type": "browser_action",
        "workflow_key": workflow_key,
        "workflow_label": BROWSER_WORKFLOWS[workflow_key]["label"],
        "created_at": _now(),
        "updated_at": _now(),
        "surface": normalize_surface(channel),
        "authority": "gated_browser_assist_beneath_max",
        "truth_hierarchy": list(TRUTH_HIERARCHY),
        "state": "planned",
        "browser_actions_enabled": False,
        "approval_required": True,
        "approved_at": None,
        "approved_by": None,
        "submission_allowed": False,
        "autonomous_submission_allowed": False,
        "autonomous_messaging_allowed": False,
        "docker_required": False,
        "target_url": target_url,
        "founder_message": message.strip(),
        "planned_actions": _planned_steps(workflow_key, target_url, staged_fields),
        "approved_actions": [],
        "completed_actions": [],
        "failed_actions": [],
        "staged_fields": staged_fields,
        "phase2_draft_ref": draft.get("id"),
        "approval_phrase": f"approve hermes browser action {action_id}",
        "execute_phrase": f"execute hermes browser action {action_id}",
        "execution_result": None,
        "failure_reason": None,
    }
    _save_action_record(record)
    _append_audit(
        action_id=action_id,
        event="plan_created",
        actor="hermes",
        state="planned",
        details={"workflow_key": workflow_key, "target_url": target_url, "phase2_draft_ref": draft.get("id")},
    )
    return record


def approve_browser_action(action_id: str, *, actor: str = "founder") -> dict[str, Any]:
    record = get_browser_action(action_id)
    if not record:
        raise FileNotFoundError(f"Browser action not found: {action_id}")
    if record.get("state") in {"completed", "failed"}:
        return record
    record["state"] = "approved"
    record["browser_actions_enabled"] = True
    record["approved_at"] = _now()
    record["approved_by"] = actor
    record["approved_actions"] = [
        {**item, "status": "approved"}
        for item in record.get("planned_actions") or []
    ]
    _save_action_record(record)
    _append_audit(
        action_id=action_id,
        event="approval_granted",
        actor=actor,
        state="approved",
        details={"browser_actions_enabled": True},
    )
    return record


def _extract_page_details(url: str) -> dict[str, Any]:
    response = httpx.get(
        url,
        timeout=15.0,
        follow_redirects=True,
        headers={"User-Agent": "EmpireBox Hermes Browser Assist/1.0"},
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    meta = ""
    desc = soup.find("meta", attrs={"name": "description"})
    if desc and desc.get("content"):
        meta = desc.get("content", "").strip()
    headings = [
        item.get_text(" ", strip=True)[:160]
        for item in soup.find_all(["h1", "h2", "h3"], limit=6)
        if item.get_text(" ", strip=True)
    ]
    forms: list[dict[str, Any]] = []
    for idx, form in enumerate(soup.find_all("form")[:3], start=1):
        fields = []
        for field in form.find_all(["input", "select", "textarea"])[:20]:
            name = field.get("name") or field.get("id") or field.get("aria-label") or field.get("placeholder")
            if not name:
                continue
            fields.append(
                {
                    "name": name,
                    "type": field.get("type") if field.name == "input" else field.name,
                    "required": bool(field.get("required")),
                }
            )
        forms.append(
            {
                "form_index": idx,
                "action": form.get("action"),
                "method": (form.get("method") or "get").upper(),
                "fields": fields,
                "field_count": len(fields),
            }
        )
    return {
        "requested_url": url,
        "final_url": str(response.url),
        "status_code": response.status_code,
        "title": (soup.title.string.strip() if soup.title and soup.title.string else ""),
        "meta_description": meta,
        "headings": headings,
        "forms": forms,
        "form_count": len(forms),
    }


def execute_browser_action(action_id: str, *, actor: str = "founder") -> dict[str, Any]:
    record = get_browser_action(action_id)
    if not record:
        raise FileNotFoundError(f"Browser action not found: {action_id}")
    if record.get("state") != "approved":
        _append_audit(
            action_id=action_id,
            event="execution_blocked_missing_approval",
            actor=actor,
            state=record.get("state"),
            details={"reason": "explicit_founder_approval_required_before_execution"},
        )
        return {
            "executed": False,
            "blocked": True,
            "reason": "explicit_founder_approval_required_before_execution",
            "record": record,
        }

    _append_audit(
        action_id=action_id,
        event="execution_started",
        actor=actor,
        state="approved",
        details={"workflow_key": record.get("workflow_key"), "target_url": record.get("target_url")},
    )
    try:
        target_url = record.get("target_url")
        if not target_url:
            raise ValueError("No target URL available for browser assist execution.")

        page = _extract_page_details(target_url)
        result: dict[str, Any] = {
            "mode": "gated_read_only_browser_assist",
            "workflow_key": record.get("workflow_key"),
            "page": page,
            "staged_fields": record.get("staged_fields") or {},
            "submission_performed": False,
            "browser_submission_allowed": False,
        }
        if record.get("workflow_key") == "life_magazine_lookup_assist":
            result["lookup_summary"] = {
                "issue_date_hint": _extract_date(record.get("founder_message") or ""),
                "cover_subject_hint": _extract_subject(record.get("founder_message") or ""),
            }
        if record.get("workflow_key") in {"repetitive_form_navigation_prep", "optional_field_fill_staging"}:
            result["staging_summary"] = {
                "field_count": len(result["staged_fields"]),
                "phase2_draft_ref": record.get("phase2_draft_ref"),
                "forms_detected": page.get("form_count"),
            }

        record["state"] = "completed"
        record["completed_actions"] = [
            {**item, "status": "completed"}
            for item in (record.get("approved_actions") or record.get("planned_actions") or [])
        ]
        record["execution_result"] = result
        record["failure_reason"] = None
        _save_action_record(record)
        _append_audit(
            action_id=action_id,
            event="execution_completed",
            actor=actor,
            state="completed",
            details={"final_url": page.get("final_url"), "status_code": page.get("status_code")},
        )
        return {"executed": True, "blocked": False, "record": record, "result": result}
    except Exception as exc:
        record["state"] = "failed"
        record["failed_actions"] = [
            {**item, "status": "failed", "error": str(exc)}
            for item in (record.get("approved_actions") or record.get("planned_actions") or [])
        ]
        record["failure_reason"] = str(exc)
        record["execution_result"] = None
        _save_action_record(record)
        _append_audit(
            action_id=action_id,
            event="execution_failed",
            actor=actor,
            state="failed",
            details={"error": str(exc)},
        )
        return {"executed": False, "blocked": False, "record": record, "error": str(exc)}


def read_browser_action_audit(limit: int = 25) -> list[dict[str, Any]]:
    ensure_hermes_phase3_scaffold()
    lines = browser_action_audit_log_path().read_text(encoding="utf-8").splitlines()
    entries = []
    for line in lines:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    entries.sort(key=lambda item: item.get("timestamp") or "", reverse=True)
    return entries[:limit]


def get_channel_interfaces() -> dict[str, Any]:
    ensure_hermes_phase3_scaffold()
    data = _json_load(channel_interfaces_path()) or {}
    defaults = _phase3_channel_defaults()
    merged = {**defaults, **data}
    return merged


def get_phase3_status() -> dict[str, Any]:
    ensure_hermes_phase3_scaffold()
    actions = list_browser_actions(limit=100)
    state_counts = {state: 0 for state in BROWSER_ACTION_STATES}
    for item in actions:
        if item.get("state") in state_counts:
            state_counts[item["state"]] += 1
    return {
        "browser_assist_mode": "gated",
        "browser_actions_enabled": "gated_by_explicit_founder_approval",
        "supported_browser_workflows": [
            {"key": key, "label": value["label"], "description": value["description"]}
            for key, value in BROWSER_WORKFLOWS.items()
        ],
        "action_counts": state_counts,
        "latest_action": actions[0] if actions else None,
        "audit_log_path": str(browser_action_audit_log_path()),
        "audit_event_count": len(read_browser_action_audit(limit=500)),
        "extra_channels": get_channel_interfaces(),
        "truth_boundary": "supporting_only_beneath_context_and_registry_truth",
        "production_services_in_docker": False,
        "autonomous_submission_allowed": False,
        "autonomous_messaging_allowed": False,
    }


def render_phase3_summary_for_prompt(*, compact: bool = False) -> str:
    status = get_phase3_status()
    channels = status.get("extra_channels") or {}
    if compact:
        return "Phase 3: gated browser assist."
    lines = [
        "### Phase 3 Browser Assist (gated only)",
        "- Every browser action requires explicit founder approval before execution.",
        "- Allowed scope: LIFE lookup assist, repetitive form navigation/prep, read-only extraction, optional field-fill staging.",
        "- Disallowed: autonomous submit/publish/checkout/messaging/deployment.",
        f"- Browser action states: {', '.join(BROWSER_ACTION_STATES)}.",
        f"- Audit log: {status.get('audit_log_path')}.",
        "- Empire production services remain native; Hermes does not move them into Docker.",
    ]
    for name in PHASE3_CHANNELS:
        channel = channels.get(name) or {}
        lines.append(f"- {name.title()}: {channel.get('status')} — {channel.get('reason')}")
    return "\n".join(lines)


def format_browser_plan_response(record: dict[str, Any]) -> str:
    steps = [
        f"- {item.get('step')}: {item.get('status')}"
        for item in record.get("planned_actions") or []
    ]
    if not steps:
        steps = ["- No browser steps were planned."]
    return "\n".join([
        f"Hermes prepared a planned browser action set for {record.get('workflow_label')}.",
        f"- Action id: {record.get('id')}",
        f"- State: {record.get('state')}",
        f"- Target URL: {record.get('target_url') or 'not set'}",
        *steps,
        f"- Browser actions enabled: {record.get('browser_actions_enabled')}",
        "- Founder approval is required before execution.",
        f"- Approve with: {record.get('approval_phrase')}",
        f"- Execute after approval with: {record.get('execute_phrase')}",
        "- No form submission, checkout, publish, or autonomous messaging will occur.",
    ])


def format_browser_approval_response(record: dict[str, Any]) -> str:
    return "\n".join([
        f"Hermes browser action approved for MAX control.",
        f"- Action id: {record.get('id')}",
        f"- State: {record.get('state')}",
        f"- Browser actions enabled: {record.get('browser_actions_enabled')}",
        f"- Approved by: {record.get('approved_by')}",
        "- Execution is still separate and will remain read-only/staging only.",
        f"- Run with: {record.get('execute_phrase')}",
    ])


def format_browser_execution_response(result: dict[str, Any]) -> str:
    if result.get("blocked"):
        return (
            "Hermes browser execution is blocked until explicit founder approval is recorded.\n"
            f"- Reason: {result.get('reason')}"
        )
    record = result.get("record") or {}
    if result.get("executed"):
        page = ((result.get("result") or {}).get("page") or {})
        return "\n".join([
            "Hermes browser assist completed under MAX authority.",
            f"- Action id: {record.get('id')}",
            f"- State: {record.get('state')}",
            f"- Final URL: {page.get('final_url')}",
            f"- Page title: {page.get('title') or 'n/a'}",
            f"- Forms detected: {page.get('form_count')}",
            "- No form submission or messaging was performed.",
        ])
    return "\n".join([
        "Hermes browser assist failed.",
        f"- Action id: {record.get('id')}",
        f"- State: {record.get('state')}",
        f"- Error: {result.get('error') or record.get('failure_reason')}",
    ])


def format_browser_audit_response(entries: list[dict[str, Any]]) -> str:
    lines = [
        "Hermes browser action audit log.",
        f"- Entries shown: {len(entries)}",
    ]
    if not entries:
        lines.append("- No browser action audit entries recorded.")
        return "\n".join(lines)
    for item in entries:
        lines.append(
            f"- {item.get('timestamp')} | {item.get('action_id')} | {item.get('event')} | state={item.get('state')}"
        )
    return "\n".join(lines)


def format_channel_status_response(channels: dict[str, Any]) -> str:
    lines = [
        "Hermes extra-channel interface status.",
        "- MAX remains the authority; autonomous messaging is disabled.",
    ]
    for name in PHASE3_CHANNELS:
        item = channels.get(name) or {}
        lines.append(
            f"- {name.title()}: {item.get('status')} | enabled={item.get('enabled')} | {item.get('reason')}"
        )
    return "\n".join(lines)
