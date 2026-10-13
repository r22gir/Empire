"""
Sandbox-only URL/credential guards for accounting connectors.

Never write to live QuickBooks, Alegra, Siigo, or DIAN.
Never load client_aliases.json or business.json.
"""
from __future__ import annotations

import os
from urllib.parse import urlparse

QBO_PRODUCTION_HOSTS = frozenset(
    {
        "quickbooks.api.intuit.com",
        "app.qbo.intuit.com",
        "qbo.intuit.com",
        "accounts.intuit.com",
    }
)
QBO_SANDBOX_HOSTS = frozenset(
    {
        "sandbox-quickbooks.api.intuit.com",
        "sandbox.qbo.intuit.com",
        "sandbox-accounts.platform.intuit.com",
    }
)
QBO_DEFAULT_API = "https://sandbox-quickbooks.api.intuit.com"

ALEGRA_SANDBOX_HOSTS = frozenset(
    {
        "sandbox.alegra.com",
        "api.sandbox.alegra.com",
        "api.alegra.com",  # Alegra uses the same host; environment token must be sandbox
    }
)
SIIGO_SANDBOX_HOSTS = frozenset(
    {
        "sandbox.siigo.com",
        "api-sandbox.siigo.com",
        "services.siigo.com",  # environment header must be sandbox
    }
)

PRODUCTION_HINTS = (
    "production",
    "prod",
    "live",
    "dian.gov.co",
    "catalogo-vpfe.dian.gov.co",
    "vpfe.dian.gov.co",
)


class SandboxOnlyError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class LiveWriteBlocked(Exception):
    def __init__(self, message: str = "Live-data writes are blocked"):
        super().__init__(message)
        self.message = message
        self.status_code = 403


def _host(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return (parsed.hostname or "").strip().lower()


def assert_sandbox_url(url: str, *, allowed_hosts: set[str], connector: str) -> str:
    if not url:
        raise SandboxOnlyError(f"{connector} sandbox URL is required")
    host = _host(url)
    lowered = url.lower()
    if any(hint in lowered for hint in PRODUCTION_HINTS if hint not in {"api.alegra.com", "services.siigo.com"}):
        if "dian.gov.co" in lowered or "production" in lowered or "/prod" in lowered:
            raise SandboxOnlyError(
                f"{connector} refused a production/live URL: {host or url}",
                403,
            )
    if host in QBO_PRODUCTION_HOSTS:
        raise SandboxOnlyError(
            f"{connector} production host is forbidden: {host}",
            403,
        )
    if host and host not in allowed_hosts:
        raise SandboxOnlyError(
            f"{connector} host '{host}' is not on the sandbox allow-list",
            403,
        )
    return url.rstrip("/")


def qbo_sandbox_base() -> str:
    env = (os.getenv("QBO_ENVIRONMENT") or "sandbox").strip().lower()
    if env not in {"sandbox", "sandbox-quickbooks"}:
        raise SandboxOnlyError(
            f"QBO_ENVIRONMENT must be sandbox (got {env!r}). Live QuickBooks is forbidden.",
            403,
        )
    raw = (os.getenv("QBO_API_BASE") or QBO_DEFAULT_API).strip()
    return assert_sandbox_url(raw, allowed_hosts=QBO_SANDBOX_HOSTS, connector="qbo")


def assert_sandbox_credentials(*, prefix: str, required: tuple[str, ...]) -> dict[str, str]:
    """
    Read sandbox credential env vars only. Empty is allowed (offline fixture mode).
    Values that look like production tokens are rejected.
    """
    found: dict[str, str] = {}
    for key in required:
        name = f"{prefix}_{key}"
        val = (os.getenv(name) or "").strip()
        if val:
            lowered = val.lower()
            if "prod" in name.lower() or lowered.startswith("live_") or "production" in lowered:
                raise SandboxOnlyError(
                    f"{name} looks like a live credential and is refused",
                    403,
                )
            found[key.lower()] = val
    return found


def refuse_live_write(action: str, connector: str) -> None:
    raise LiveWriteBlocked(
        f"{connector} refuses live-data write: {action}. Sandbox pull / local drafts only."
    )
