"""H62 FIX (2026-08-22) — close the three remaining FOUNDER_PIN literal-default call sites.

HOTFIX 4.2 (2026-07-24) replaced the privilege-escalation default
`os.getenv("FOUNDER_PIN", "<PIN>")` in `app/services/max/tool_executor.py`
with a fail-closed pattern. It missed three other call sites. This test
proves they now refuse correctly when FOUNDER_PIN is unset.

Three sites covered:
  - app/routers/max/router.py:5027  POST /api/v1/max/code-task   → 403
  - app/routers/max/router.py:5060  POST /api/v1/max/verify-pin  → 403
  - app/routers/auth.py:184         POST /api/v1/founder-token   → 401

The literal default being closed is `REGRESSION_LITERAL` (the historical
privilege-escalation default that this fix removes). Named as a constant so
its purpose is unmistakable to the next reader.

Each endpoint is invoked twice with FOUNDER_PIN unset:
  (a) caller provides an empty / non-matching PIN  → must refuse
      (status unchanged from the existing mismatch path)
  (b) caller provides `REGRESSION_LITERAL`        → must refuse
      (the exact attack this fix closes)

The CRITICAL log assertion proves the operator gets a loud signal at the
moment the gate fires — not only at module import.

Reference pattern (already fixed in HOTFIX 4.2):
  app/services/max/tool_executor.py:60–110
"""
from __future__ import annotations

import asyncio
import logging
import os

import pytest
from fastapi import HTTPException


# The literal that was the privilege-escalation default before this fix.
# Defining it as a named constant (rather than inlining) makes the test's
# purpose unmistakable: any caller passing this string used to walk past
# the PIN gate when FOUNDER_PIN was unset.
REGRESSION_LITERAL = "7777"


# ───────────────────────────────────────────────────────────────────
# /api/v1/max/verify-pin  (app/routers/max/router.py:5060)
# ───────────────────────────────────────────────────────────────────


def test_verify_pin_refuses_with_empty_pin_when_env_unset(monkeypatch, caplog):
    """POST /api/v1/max/verify-pin with FOUNDER_PIN unset and an
    empty caller PIN must refuse with 403 — the same status the
    existing mismatch path uses. Behaviour unchanged for
    legitimate callers."""
    monkeypatch.delenv("FOUNDER_PIN", raising=False)

    from app.routers.max.router import verify_pin, VerifyPinRequest

    with caplog.at_level(logging.CRITICAL, logger="max.api"):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(verify_pin(VerifyPinRequest(pin="")))

    assert exc.value.status_code == 403, (
        f"unset FOUNDER_PIN must refuse with 403 (same as mismatch); "
        f"got {exc.value.status_code}"
    )
    assert any(
        r.levelno == logging.CRITICAL and "FOUNDER_PIN" in r.getMessage()
        for r in caplog.records
    ), (
        "expected a CRITICAL log line on the max.api logger when "
        "FOUNDER_PIN is unset; operator must see the failure"
    )


def test_verify_pin_refuses_with_regression_literal_when_env_unset(monkeypatch):
    """POST /api/v1/max/verify-pin with FOUNDER_PIN unset but the
    caller passing REGRESSION_LITERAL must refuse with 403. This is
    the exact attack the fix closes: typing the historical default
    used to walk past the gate when the env was unset."""
    monkeypatch.delenv("FOUNDER_PIN", raising=False)

    from app.routers.max.router import verify_pin, VerifyPinRequest

    with pytest.raises(HTTPException) as exc:
        asyncio.run(verify_pin(VerifyPinRequest(pin=REGRESSION_LITERAL)))

    assert exc.value.status_code == 403, (
        f"REGRESSION_LITERAL must not bypass the gate; "
        f"got status {exc.value.status_code}"
    )


# ───────────────────────────────────────────────────────────────────
# /api/v1/max/code-task  (app/routers/max/router.py:5027)
# ───────────────────────────────────────────────────────────────────


def _build_code_task_request(pin: str):
    """Build a CodeTaskRequest with a non-founder channel so the PIN
    check is actually enforced. The default channel='web_cc' would
    bypass PIN via is_founder_message()."""
    from app.routers.max.router import CodeTaskRequest
    return CodeTaskRequest(prompt="regression-pin-test", pin=pin, channel="telegram")


def test_code_task_refuses_with_empty_pin_when_env_unset(monkeypatch, caplog):
    """POST /api/v1/max/code-task with FOUNDER_PIN unset and an
    empty caller PIN must refuse with 403 — the same status the
    existing mismatch path uses."""
    monkeypatch.delenv("FOUNDER_PIN", raising=False)

    from app.routers.max.router import submit_code_task

    with caplog.at_level(logging.CRITICAL, logger="max.api"):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(submit_code_task(_build_code_task_request(pin="")))

    assert exc.value.status_code == 403, (
        f"unset FOUNDER_PIN must refuse with 403 (same as mismatch); "
        f"got {exc.value.status_code}"
    )
    assert any(
        r.levelno == logging.CRITICAL and "FOUNDER_PIN" in r.getMessage()
        for r in caplog.records
    ), (
        "expected a CRITICAL log line on the max.api logger when "
        "FOUNDER_PIN is unset"
    )


def test_code_task_refuses_with_regression_literal_when_env_unset(monkeypatch):
    """POST /api/v1/max/code-task with FOUNDER_PIN unset but caller
    passing REGRESSION_LITERAL must refuse with 403. Attack closed."""
    monkeypatch.delenv("FOUNDER_PIN", raising=False)

    from app.routers.max.router import submit_code_task

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            submit_code_task(_build_code_task_request(pin=REGRESSION_LITERAL))
        )

    assert exc.value.status_code == 403, (
        f"REGRESSION_LITERAL must not bypass the gate; "
        f"got status {exc.value.status_code}"
    )


# ───────────────────────────────────────────────────────────────────
# /api/v1/founder-token  (app/routers/auth.py:184)
# ───────────────────────────────────────────────────────────────────


def test_founder_token_refuses_with_empty_pin_when_env_unset(monkeypatch, caplog):
    """POST /api/v1/founder-token with FOUNDER_PIN unset and an
    empty caller PIN must refuse with 401 — the same status the
    existing mismatch path uses. THIS IS THE HIGHEST-CONSEQUENCE
    site: a successful match here issues a JWT carrying founder
    claims. The literal-default bug was effectively an unauthenticated
    founder-token endpoint whenever FOUNDER_PIN was unset."""
    monkeypatch.delenv("FOUNDER_PIN", raising=False)

    from app.routers.auth import founder_token, FounderPinRequest

    with caplog.at_level(logging.CRITICAL, logger="empire.auth"):
        with pytest.raises(HTTPException) as exc:
            founder_token(FounderPinRequest(pin=""))

    assert exc.value.status_code == 401, (
        f"unset FOUNDER_PIN must refuse with 401 (same as mismatch); "
        f"got {exc.value.status_code}"
    )
    assert any(
        r.levelno == logging.CRITICAL and "FOUNDER_PIN" in r.getMessage()
        for r in caplog.records
    ), (
        "expected a CRITICAL log line on the empire.auth logger when "
        "FOUNDER_PIN is unset"
    )


def test_founder_token_refuses_with_regression_literal_when_env_unset(monkeypatch):
    """POST /api/v1/founder-token with FOUNDER_PIN unset but caller
    passing REGRESSION_LITERAL must refuse with 401. THIS is the
    privilege-escalation attack the fix closes: a chat caller (or a
    prompt-injection attack on the chat layer) could walk out with
    a founder JWT just by typing the historical default."""
    monkeypatch.delenv("FOUNDER_PIN", raising=False)

    from app.routers.auth import founder_token, FounderPinRequest

    with pytest.raises(HTTPException) as exc:
        founder_token(FounderPinRequest(pin=REGRESSION_LITERAL))

    assert exc.value.status_code == 401, (
        f"REGRESSION_LITERAL must not bypass the JWT gate; "
        f"got status {exc.value.status_code}"
    )


# ───────────────────────────────────────────────────────────────────
# Sweep proof — the active default pattern must be gone from app/.
# ───────────────────────────────────────────────────────────────────


def test_no_active_literal_default_remains_in_app():
    """Static guard: `os.getenv("FOUNDER_PIN", "<literal>")` must
    appear nowhere in app/. The fix removed all three sites; this
    test would catch any future regression where someone
    reintroduces the privilege-escalation default."""
    import re
    from pathlib import Path

    backend_app = Path(__file__).resolve().parents[1] / "app"
    pattern = re.compile(
        r'os\.(?:getenv|environ\.get)\(\s*["\']FOUNDER_PIN["\']\s*,\s*["\'][^"\']+["\']\s*\)'
    )
    offenders = []
    for py in backend_app.rglob("*.py"):
        text = py.read_text(encoding="utf-8", errors="replace")
        for m in pattern.finditer(text):
            offenders.append(f"{py.relative_to(backend_app.parent)}:{pattern.search(text, m.start()).string[:0] or ''}")

    # Filter out the existing pedagogical references in tool_executor.py
    # and the new comments in router.py / auth.py that mention the literal
    # in prose — only flag the *active* default shape.
    active_offenders = [
        o for o in offenders
        if 'os.getenv("FOUNDER_PIN", "' in o or "os.getenv('FOUNDER_PIN', '" in o
        or 'os.environ.get("FOUNDER_PIN", "' in o or "os.environ.get('FOUNDER_PIN', '" in o
    ]

    # Simpler & safer: re-grep just the active pattern in a way that
    # excludes comment lines.
    active_offenders = []
    for py in backend_app.rglob("*.py"):
        for n, line in enumerate(py.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if ('os.getenv("FOUNDER_PIN"' in line or "os.getenv('FOUNDER_PIN'" in line
                or 'os.environ.get("FOUNDER_PIN"' in line or "os.environ.get('FOUNDER_PIN'" in line):
                # Must NOT have a literal default — the default must be "" or absent.
                if not re.search(
                    r'os\.(?:getenv|environ\.get)\(\s*["\']FOUNDER_PIN["\']\s*,\s*["\']["\']?\s*\)',
                    line,
                ) and not re.search(
                    r'os\.(?:getenv|environ\.get)\(\s*["\']FOUNDER_PIN["\']\s*\)',
                    line,
                ):
                    active_offenders.append(f"{py.relative_to(backend_app.parent)}:{n}: {line.strip()}")

    assert active_offenders == [], (
        f"FOUNDER_PIN literal default must be gone from app/; offenders:\n"
        + "\n".join(active_offenders)
    )