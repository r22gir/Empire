"""Hermes Phase 2 form-prep assist and scheduled-result intake beneath MAX."""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.services.max.hermes_memory import TRUTH_HIERARCHY, memory_root
from app.services.max.surface_identity import normalize_surface


WORKFLOW_SPECS: dict[str, dict[str, Any]] = {
    "life_magazine_intake": {
        "label": "LIFE magazine intake",
        "aliases": ("life magazine", "life issue", "life intake", "archiveforge"),
        "required_fields": ("publication_title", "issue_date", "cover_subject", "condition", "source_box"),
        "target_route": "/api/v1/archiveforge",
        "field_order": (
            "publication_title",
            "issue_date",
            "cover_subject",
            "condition",
            "source_box",
            "tier",
            "comp_range_estimate",
            "notes",
        ),
    },
    "vendorops_vendor_entry": {
        "label": "VendorOps vendor entry",
        "aliases": ("vendorops", "vendor ops", "vendor entry", "vendor account"),
        "required_fields": ("vendor_name", "category", "vendor_url"),
        "target_route": "/api/v1/vendorops/accounts",
        "field_order": (
            "vendor_name",
            "category",
            "purpose",
            "vendor_url",
            "monthly_cost_usd",
            "renewal_date",
            "tier",
            "credential_ref",
            "notes",
        ),
    },
    "relistapp_source_import": {
        "label": "RelistApp source import",
        "aliases": ("relistapp", "relist app", "source import", "source product"),
        "required_fields": ("source_platform", "source_url", "title"),
        "target_route": "/api/v1/relist/sources/import-full",
        "field_order": (
            "source_platform",
            "source_url",
            "title",
            "source_price_usd",
            "shipping_cost_usd",
            "brand",
            "category",
            "condition",
            "notes",
        ),
    },
    "marketforge_batch_intake": {
        "label": "MarketForge batch intake",
        "aliases": ("marketforge", "market forge", "batch intake", "batch import"),
        "required_fields": ("batch_name", "item_count", "category"),
        "target_route": "/api/v1/marketplace/products",
        "field_order": (
            "batch_name",
            "item_count",
            "category",
            "condition",
            "source_channel",
            "target_channels",
            "notes",
        ),
    },
}

SCHEDULED_RESULT_TYPES = {
    "daily_summary": "Daily summary",
    "weekly_summary": "Weekly summary",
    "renewal_reminder": "Renewal reminder",
    "repetitive_task_prep": "Repetitive task prep",
}

PREFILL_MARKERS = (
    "prepare",
    "prefill",
    "pre-fill",
    "draft",
    "intake",
    "vendor entry",
    "source import",
    "batch intake",
)

SCHEDULED_MARKERS = (
    "scheduled result",
    "scheduled results",
    "daily summary",
    "weekly summary",
    "renewal reminder",
    "renewal reminders",
    "repetitive task prep",
    "scheduled summary",
    "show hermes schedule",
    "show hermes scheduled",
)

CONDITION_TOKENS = ("sealed", "new", "like new", "vg+", "vg", "good", "fair", "poor")
KNOWN_MARKETPLACES = ("ebay", "facebook marketplace", "facebook", "mercari", "etsy", "poshmark", "amazon")
KNOWN_VENDOR_CATEGORIES = ("software", "marketplace", "shipping", "saas", "payments", "automation", "research", "inventory")


def drafts_path() -> Path:
    return memory_root() / "DRAFTS"


def scheduled_path() -> Path:
    return memory_root() / "SCHEDULED"


def ensure_hermes_phase2_scaffold() -> dict[str, Any]:
    root = memory_root()
    root.mkdir(parents=True, exist_ok=True)
    drafts_path().mkdir(parents=True, exist_ok=True)
    scheduled_path().mkdir(parents=True, exist_ok=True)
    return {
        "drafts_dir": str(drafts_path()),
        "scheduled_dir": str(scheduled_path()),
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _json_load(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _invalidate_prompt_cache() -> None:
    try:
        from app.services.max.system_prompt import _prompt_cache

        _prompt_cache.update({"prompt": None, "expires": 0})
    except Exception:
        pass


def _list_json_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for item in sorted(path.glob("*.json"), reverse=True):
        data = _json_load(item)
        if data:
            records.append(data)
    records.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return records


def _extract_url(text: str) -> str | None:
    match = re.search(r"https?://[^\s)>\]]+", text)
    return match.group(0).rstrip(".,") if match else None


def _extract_money(text: str, label: str | None = None) -> float | None:
    if label:
        pattern = rf"{re.escape(label)}[^$0-9]*(?:\$)?([0-9]+(?:\.[0-9]{{1,2}})?)"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    match = re.search(r"\$([0-9]+(?:\.[0-9]{1,2})?)", text)
    return float(match.group(1)) if match else None


def _extract_range(text: str) -> str | None:
    match = re.search(r"\$([0-9]+(?:\.[0-9]{1,2})?)\s*(?:-|to)\s*\$?([0-9]+(?:\.[0-9]{1,2})?)", text, flags=re.IGNORECASE)
    if not match:
        return None
    return f"${match.group(1)}-${match.group(2)}"


def _extract_item_count(text: str) -> int | None:
    patterns = (
        r"(\d+)\s+(?:items|item|issues|magazines|products)",
        r"batch of\s+(\d+)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _extract_condition(text: str) -> str | None:
    lower = text.lower()
    for token in CONDITION_TOKENS:
        if token in lower:
            return token.upper() if token.startswith("vg") else token.title()
    return None


def _extract_tier(text: str) -> str | None:
    match = re.search(r"\btier\s*([ABC])\b", text, flags=re.IGNORECASE)
    return match.group(1).upper() if match else None


def _extract_date(text: str) -> str | None:
    iso = re.search(r"\b(20\d{2}|19\d{2})-\d{2}-\d{2}\b", text)
    if iso:
        return iso.group(0)
    patterns = ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y", "%m/%d/%Y", "%m-%d-%Y")
    candidates = re.findall(r"[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{4}", text)
    for candidate in candidates:
        cleaned = re.sub(r"\s+", " ", candidate.strip())
        for fmt in patterns:
            try:
                return datetime.strptime(cleaned, fmt).date().isoformat()
            except ValueError:
                continue
    return None


def _extract_box(text: str) -> str | None:
    match = re.search(r"\bbox\s+([A-Za-z0-9-]+)\b", text, flags=re.IGNORECASE)
    return f"Box {match.group(1)}" if match else None


def _extract_quoted_text(text: str) -> str | None:
    match = re.search(r'"([^"]+)"', text)
    if match:
        return match.group(1).strip()
    match = re.search(r"'([^']+)'", text)
    return match.group(1).strip() if match else None


def _humanize_host(url: str | None) -> str | None:
    if not url:
        return None
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    label = host.split(".")[0]
    return label.replace("-", " ").title() if label else None


def _platform_from_url(url: str | None) -> str | None:
    host = (urlparse(url).netloc.lower() if url else "")
    if "amazon" in host:
        return "amazon"
    if "walmart" in host:
        return "walmart"
    if "aliexpress" in host:
        return "aliexpress"
    if "ebay" in host:
        return "ebay"
    if "etsy" in host:
        return "etsy"
    if "facebook" in host:
        return "facebook"
    return host.split(".")[0] if host else None


def _extract_category(text: str) -> str | None:
    lower = text.lower()
    for token in KNOWN_VENDOR_CATEGORIES:
        if token in lower:
            return token
    match = re.search(r"\bcategory[:\s]+([a-zA-Z0-9 _-]+)", text, flags=re.IGNORECASE)
    return match.group(1).strip().lower() if match else None


def _extract_target_channels(text: str) -> list[str]:
    lower = text.lower()
    found = []
    for token in KNOWN_MARKETPLACES:
        if token in lower:
            found.append("facebook marketplace" if token == "facebook" else token)
    deduped: list[str] = []
    for item in found:
        if item not in deduped:
            deduped.append(item)
    return deduped


def _normalize_vendor_tier(text: str) -> str | None:
    match = re.search(r"\b(free|starter|pro)\b", text, flags=re.IGNORECASE)
    return match.group(1).lower() if match else None


def _extract_subject(text: str, fallback_tokens: tuple[str, ...] = ()) -> str | None:
    quoted = _extract_quoted_text(text)
    if quoted:
        return quoted
    for token in fallback_tokens:
        pattern = rf"{re.escape(token)}[:\s]+([A-Za-z0-9 '&()/.-]+)"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def detect_prefill_workflow(message: str | None) -> str | None:
    text = (message or "").lower()
    if not any(marker in text for marker in PREFILL_MARKERS):
        return None
    if "life magazine" in text or "life issue" in text or "archiveforge" in text:
        return "life_magazine_intake"
    if "vendorops" in text or "vendor ops" in text or "vendor entry" in text:
        return "vendorops_vendor_entry"
    if "relistapp" in text or "relist app" in text or "source import" in text:
        return "relistapp_source_import"
    if "marketforge" in text or "market forge" in text or "batch intake" in text:
        return "marketforge_batch_intake"
    return None


def is_prefill_request(message: str | None) -> bool:
    return detect_prefill_workflow(message) is not None


def is_scheduled_result_request(message: str | None) -> bool:
    text = (message or "").lower()
    return any(marker in text for marker in SCHEDULED_MARKERS)


def _parse_life_magazine_fields(message: str) -> dict[str, Any]:
    return {
        "publication_title": "LIFE",
        "issue_date": _extract_date(message),
        "cover_subject": _extract_subject(message, fallback_tokens=("cover", "subject")) or ("Apollo 11" if "apollo 11" in message.lower() else None),
        "condition": _extract_condition(message),
        "source_box": _extract_box(message),
        "tier": _extract_tier(message),
        "comp_range_estimate": _extract_range(message),
        "notes": message.strip(),
    }


def _parse_vendorops_fields(message: str) -> dict[str, Any]:
    url = _extract_url(message)
    vendor_name = _extract_subject(message, fallback_tokens=("for", "vendor"))
    if vendor_name:
        vendor_name = re.split(r"\s+(?:category|purpose|renewal|tier|https?://)", vendor_name, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    return {
        "vendor_name": vendor_name or _humanize_host(url),
        "category": _extract_category(message),
        "purpose": _extract_subject(message, fallback_tokens=("purpose",)),
        "vendor_url": url,
        "monthly_cost_usd": _extract_money(message, "monthly") or _extract_money(message, "cost"),
        "renewal_date": _extract_date(message),
        "tier": _normalize_vendor_tier(message) or "free",
        "credential_ref": "founder_to_supply",
        "notes": message.strip(),
    }


def _parse_relistapp_fields(message: str) -> dict[str, Any]:
    url = _extract_url(message)
    return {
        "source_platform": _platform_from_url(url),
        "source_url": url,
        "title": _extract_quoted_text(message) or _extract_subject(message, fallback_tokens=("title", "product")) or _humanize_host(url),
        "source_price_usd": _extract_money(message, "price") or _extract_money(message),
        "shipping_cost_usd": _extract_money(message, "shipping"),
        "brand": _extract_subject(message, fallback_tokens=("brand",)),
        "category": _extract_category(message),
        "condition": _extract_condition(message) or "New",
        "notes": message.strip(),
    }


def _parse_marketforge_fields(message: str) -> dict[str, Any]:
    return {
        "batch_name": _extract_quoted_text(message) or _extract_subject(message, fallback_tokens=("batch", "lot")) or "Founder batch",
        "item_count": _extract_item_count(message),
        "category": _extract_category(message),
        "condition": _extract_condition(message),
        "source_channel": _extract_subject(message, fallback_tokens=("source", "channel")),
        "target_channels": _extract_target_channels(message),
        "notes": message.strip(),
    }


WORKFLOW_PARSERS = {
    "life_magazine_intake": _parse_life_magazine_fields,
    "vendorops_vendor_entry": _parse_vendorops_fields,
    "relistapp_source_import": _parse_relistapp_fields,
    "marketforge_batch_intake": _parse_marketforge_fields,
}


def _ordered_fields(workflow_key: str, fields: dict[str, Any]) -> dict[str, Any]:
    spec = WORKFLOW_SPECS[workflow_key]
    ordered: dict[str, Any] = {}
    for key in spec["field_order"]:
        value = fields.get(key)
        if value not in (None, "", [], {}):
            ordered[key] = value
    for key, value in fields.items():
        if key not in ordered and value not in (None, "", [], {}):
            ordered[key] = value
    return ordered


def save_prefill_draft(draft: dict[str, Any]) -> dict[str, Any]:
    ensure_hermes_phase2_scaffold()
    target = drafts_path() / f"{draft['created_at'].replace(':', '').replace('-', '').replace('+', '_')}_{draft['id']}.json"
    _json_dump(target, draft)
    _invalidate_prompt_cache()
    return {**draft, "path": str(target)}


def prepare_prefill_draft(
    workflow_key: str,
    *,
    message: str,
    channel: str = "web",
    source: str = "hermes",
) -> dict[str, Any]:
    if workflow_key not in WORKFLOW_SPECS:
        raise ValueError(f"Unknown Hermes workflow: {workflow_key}")
    fields = WORKFLOW_PARSERS[workflow_key](message)
    fields = _ordered_fields(workflow_key, fields)
    spec = WORKFLOW_SPECS[workflow_key]
    missing = [item for item in spec["required_fields"] if not fields.get(item)]
    draft = {
        "id": _new_id("hermes_draft"),
        "type": "form_prefill_draft",
        "workflow_key": workflow_key,
        "workflow_label": spec["label"],
        "created_at": _now(),
        "surface": normalize_surface(channel),
        "source": source,
        "authority": "supporting_prefill_draft_only",
        "truth_hierarchy": list(TRUTH_HIERARCHY),
        "target_route": spec["target_route"],
        "fields": fields,
        "required_fields": list(spec["required_fields"]),
        "missing_required_fields": missing,
        "review_state": "pending_founder_confirmation",
        "confirmation_required": True,
        "browser_actions_enabled": False,
        "submission_allowed": False,
        "execution_allowed": False,
        "founder_message": message.strip(),
    }
    return save_prefill_draft(draft)


def prepare_prefill_draft_from_message(message: str, *, channel: str = "web") -> dict[str, Any]:
    workflow_key = detect_prefill_workflow(message)
    if not workflow_key:
        raise ValueError("Hermes prefill workflow not detected from message.")
    return prepare_prefill_draft(workflow_key, message=message, channel=channel)


def list_prefill_drafts(*, workflow_key: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
    ensure_hermes_phase2_scaffold()
    drafts = _list_json_records(drafts_path())
    if workflow_key:
        drafts = [item for item in drafts if item.get("workflow_key") == workflow_key]
    return drafts[:limit]


def latest_prefill_draft(workflow_key: str | None = None) -> dict[str, Any] | None:
    drafts = list_prefill_drafts(workflow_key=workflow_key, limit=1)
    return drafts[0] if drafts else None


def mark_draft_presented(draft_id: str) -> dict[str, Any] | None:
    ensure_hermes_phase2_scaffold()
    for path in drafts_path().glob("*.json"):
        data = _json_load(path)
        if data and data.get("id") == draft_id:
            data["last_presented_at"] = _now()
            data["review_state"] = "presented_by_max_pending_founder_confirmation"
            _json_dump(path, data)
            _invalidate_prompt_cache()
            return data
    return None


def ingest_scheduled_result(
    *,
    result_type: str,
    title: str,
    summary: str,
    payload: dict[str, Any] | None = None,
    schedule: str | None = None,
    source: str = "hermes",
) -> dict[str, Any]:
    if result_type not in SCHEDULED_RESULT_TYPES:
        raise ValueError(f"Unsupported scheduled result type: {result_type}")
    ensure_hermes_phase2_scaffold()
    record = {
        "id": _new_id("hermes_result"),
        "type": "scheduled_result",
        "result_type": result_type,
        "result_label": SCHEDULED_RESULT_TYPES[result_type],
        "schedule": schedule or result_type.replace("_", " "),
        "title": title.strip(),
        "summary": summary.strip(),
        "payload": payload or {},
        "created_at": _now(),
        "source": source,
        "authority": "supporting_scheduled_result_only",
        "truth_hierarchy": list(TRUTH_HIERARCHY),
        "review_state": "pending_founder_review",
        "browser_actions_enabled": False,
        "submission_allowed": False,
        "execution_allowed": False,
    }
    target = scheduled_path() / f"{record['created_at'].replace(':', '').replace('-', '').replace('+', '_')}_{record['id']}.json"
    _json_dump(target, record)
    _invalidate_prompt_cache()
    return {**record, "path": str(target)}


def list_scheduled_results(*, result_type: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
    ensure_hermes_phase2_scaffold()
    results = _list_json_records(scheduled_path())
    if result_type:
        results = [item for item in results if item.get("result_type") == result_type]
    return results[:limit]


def mark_scheduled_result_presented(result_id: str) -> dict[str, Any] | None:
    ensure_hermes_phase2_scaffold()
    for path in scheduled_path().glob("*.json"):
        data = _json_load(path)
        if data and data.get("id") == result_id:
            data["last_presented_at"] = _now()
            data["review_state"] = "presented_by_max"
            _json_dump(path, data)
            _invalidate_prompt_cache()
            return data
    return None


def get_phase2_status() -> dict[str, Any]:
    ensure_hermes_phase2_scaffold()
    drafts = list_prefill_drafts(limit=25)
    results = list_scheduled_results(limit=25)
    return {
        "drafts_dir": str(drafts_path()),
        "scheduled_dir": str(scheduled_path()),
        "supported_workflows": [
            {"key": key, "label": spec["label"], "target_route": spec["target_route"]}
            for key, spec in WORKFLOW_SPECS.items()
        ],
        "draft_count": len(drafts),
        "scheduled_result_count": len(results),
        "latest_draft": drafts[0] if drafts else None,
        "latest_scheduled_result": results[0] if results else None,
        "truth_boundary": "supporting_only_beneath_context_and_registry_truth",
    }


def render_phase2_summary_for_prompt(*, compact: bool = False) -> str:
    status = get_phase2_status()
    latest_draft = status.get("latest_draft") or {}
    latest_result = status.get("latest_scheduled_result") or {}
    workflows = ", ".join(item["label"] for item in status["supported_workflows"])
    if compact:
        return "Phase 2: confirmation-only drafts/results; no browser actions or submissions."
    lines = [
        "### Phase 2 Assist (supporting only)",
        f"- Prefill workflows: {workflows}.",
        f"- Stored drafts: {status['draft_count']}.",
        f"- Scheduled results: {status['scheduled_result_count']}.",
        "- MAX may present Hermes drafts/results for founder confirmation only.",
        "- Browser actions: disabled. Form submission: disabled.",
    ]
    if latest_draft:
        lines.append(
            f"- Latest draft: {latest_draft.get('workflow_label')} ({latest_draft.get('id')}) "
            f"state={latest_draft.get('review_state')}."
        )
    if latest_result:
        lines.append(
            f"- Latest scheduled result: {latest_result.get('result_label')} "
            f"\"{latest_result.get('title')}\" state={latest_result.get('review_state')}."
        )
    return "\n".join(lines)


def format_prefill_response(draft: dict[str, Any]) -> str:
    ready_fields = draft.get("fields") or {}
    field_lines = [
        f"- {key}: {value}"
        for key, value in ready_fields.items()
    ]
    if not field_lines:
        field_lines = ["- No fields were inferred from the request."]
    missing = draft.get("missing_required_fields") or []
    missing_line = ", ".join(missing) if missing else "none"
    return "\n".join([
        f"Hermes prepared a {draft.get('workflow_label')} draft for MAX review.",
        f"- Draft id: {draft.get('id')}",
        f"- Authority: {draft.get('authority')}",
        f"- Target route: {draft.get('target_route')} (not executed)",
        *field_lines,
        f"- Missing required fields: {missing_line}",
        "- Browser actions: disabled",
        "- Submission: disabled",
        "- Founder confirmation is required before MAX creates or submits anything.",
    ])


def format_scheduled_results_response(results: list[dict[str, Any]]) -> str:
    lines = [
        "Hermes scheduled-result intake (supporting only).",
        f"- Results surfaced: {len(results)}",
        "- Runtime and registry truth still outrank these Hermes summaries.",
    ]
    if not results:
        lines.append("- No scheduled results are currently stored.")
        return "\n".join(lines)
    for item in results:
        lines.append(
            f"- {item.get('result_label')}: {item.get('title')} — {item.get('summary')}"
        )
    lines.append("- Nothing was submitted or executed from these results.")
    return "\n".join(lines)
