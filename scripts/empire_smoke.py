#!/usr/bin/env python3
"""One-command Empire non-regression smoke checks."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


BACKEND = "http://127.0.0.1:8000"
PORTAL = "http://127.0.0.1:3005"


@dataclass
class Check:
    name: str
    url: str
    validator: Callable[[Any, str], tuple[bool, str]]


def _json_has(key: str) -> Callable[[Any, str], tuple[bool, str]]:
    def validate(data: Any, _body: str) -> tuple[bool, str]:
        ok = isinstance(data, dict) and key in data
        return ok, f"found key {key!r}" if ok else f"missing key {key!r}"
    return validate


def _max_status(data: Any, _body: str) -> tuple[bool, str]:
    ok = isinstance(data, dict) and data.get("status") == "ok" and bool(data.get("current_commit"))
    return ok, f"commit {data.get('current_commit')}" if ok else "MAX status/current_commit missing"


def _openclaw(data: Any, _body: str) -> tuple[bool, str]:
    gate = data.get("openclaw_gate", {}) if isinstance(data, dict) else {}
    ok = isinstance(data, dict) and data.get("status") == "online" and gate.get("allowed") is True
    return ok, f"gate {gate.get('state')}: {gate.get('reason')}" if ok else "OpenClaw not online or gate not allowed"


def _html(_data: Any, body: str) -> tuple[bool, str]:
    ok = "<html" in body.lower()
    return ok, "html returned" if ok else "html marker missing"


CHECKS = [
    Check("MAX runtime truth path", f"{BACKEND}/api/v1/max/status", _max_status),
    Check("Empire Workroom", f"{BACKEND}/api/v1/inventory/dashboard?business=workroom", _json_has("total_items")),
    Check("WoodCraft", f"{BACKEND}/api/v1/craftforge/dashboard", _json_has("pipeline")),
    Check("LuxeForge", f"{BACKEND}/api/v1/quote-requests", _json_has("requests")),
    Check("ArchiveForge", f"{BACKEND}/api/v1/archiveforge/stats", _json_has("total_items")),
    Check("ApostApp", f"{BACKEND}/api/v1/apostapp/dashboard", _json_has("total_orders")),
    Check("OpenClaw health", f"{BACKEND}/api/v1/openclaw/health", _openclaw),
    Check("TranscriptForge standalone route", f"{BACKEND}/api/v1/transcriptforge/modes", _json_has("modes")),
    Check("System", f"{BACKEND}/api/v1/system/stats", _json_has("cpu")),
    Check("Tokens & Costs", f"{BACKEND}/api/v1/costs/overview?days=1", _json_has("total")),
    Check("Portal root", f"{PORTAL}/", _html),
]


def fetch(url: str) -> tuple[int, str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "empire-smoke/1.0"})
    with urllib.request.urlopen(req, timeout=10) as response:
        body = response.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = None
        return response.status, body, data


def main() -> int:
    failed = 0
    for check in CHECKS:
        try:
            status, body, data = fetch(check.url)
            ok, detail = check.validator(data, body)
            ok = ok and 200 <= status < 300
            marker = "PASS" if ok else "FAIL"
            print(f"[{marker}] {check.name}: HTTP {status}; {detail}")
            failed += 0 if ok else 1
        except urllib.error.HTTPError as exc:
            print(f"[FAIL] {check.name}: HTTP {exc.code}; {exc.reason}")
            failed += 1
        except Exception as exc:
            print(f"[FAIL] {check.name}: {exc}")
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
