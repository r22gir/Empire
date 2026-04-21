"""VendorOps scheduled renewal alert runner.

Keeps delivery separate from MAX and payments. The runner calls the existing
VendorOps delivery path so route-triggered and scheduled delivery share the
same idempotency/status behavior.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("vendorops.alert_runner")

DEFAULT_INTERVAL_SECONDS = 3600


class VendorOpsAlertRunner:
    def __init__(self):
        self.interval_seconds = int(os.getenv("VENDOROPS_ALERT_RUNNER_INTERVAL_SECONDS", str(DEFAULT_INTERVAL_SECONDS)))
        self._running = False
        self.last_run_at: str | None = None
        self.last_result: dict[str, Any] | None = None
        self.last_error: str | None = None

    async def run_once(self, *, limit: int = 50) -> dict[str, Any]:
        from app.routers.vendorops import deliver_renewal_alerts

        result = await deliver_renewal_alerts(limit=limit)
        self.last_run_at = datetime.now(timezone.utc).isoformat()
        self.last_result = result
        self.last_error = None
        logger.info("VendorOps alert runner processed %s alert(s)", result.get("processed"))
        return result

    async def start(self):
        if self._running:
            return
        self._running = True
        logger.info("VendorOps alert runner started; interval=%ss", self.interval_seconds)
        while self._running:
            try:
                await self.run_once()
            except Exception as exc:
                self.last_error = str(exc)
                logger.warning("VendorOps alert runner failed: %s", exc)
            await asyncio.sleep(self.interval_seconds)

    def stop(self):
        self._running = False

    def status(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "interval_seconds": self.interval_seconds,
            "last_run_at": self.last_run_at,
            "last_result": self.last_result,
            "last_error": self.last_error,
        }


vendorops_alert_runner = VendorOpsAlertRunner()


async def run_vendorops_alert_delivery_once(limit: int = 50) -> dict[str, Any]:
    return await vendorops_alert_runner.run_once(limit=limit)
