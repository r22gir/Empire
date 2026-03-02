"""
Amazon SP-API Compliance Module — MarketF scaffolding (Phase 0)

Provides:
- Kill switch enforcement (Amazon Agent Policy, March 4, 2026)
- Self-identification header values
- Audit logging of all SP-API requests to the database

See docs/MARKETF_AMAZON_SPEC.md and docs/AMAZON_COMPLIANCE_CHECKLIST.md.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class KillSwitchError(Exception):
    """Raised when the Amazon kill switch is enabled."""


class ComplianceManager:
    """
    Manages compliance requirements for Amazon SP-API operations:

    1. Kill switch — immediately halt all Amazon API activity when enabled
    2. Self-identification — ensure every request carries the required
       automated-tool identifier per Amazon's Agent Policy (March 4, 2026)
    3. Audit logging — record every SP-API call with timestamp, payload, and response
    """

    def __init__(self, db_session=None):
        """
        Args:
            db_session: Optional SQLAlchemy session for persisting audit logs.
                        If None, logs are written to the application logger only.
        """
        self._db_session = db_session

    # ------------------------------------------------------------------
    # Kill switch
    # ------------------------------------------------------------------

    @staticmethod
    def is_kill_switch_enabled() -> bool:
        """
        Return True if the Amazon kill switch is currently active.

        The kill switch can be enabled by setting the environment variable
        AMAZON_KILL_SWITCH_ENABLED=true (case-insensitive). This allows
        immediate shutdown without a code deployment.
        """
        return os.environ.get("AMAZON_KILL_SWITCH_ENABLED", "false").lower() == "true"

    def check_kill_switch(self) -> None:
        """
        Raise KillSwitchError if the kill switch is enabled.

        Call this at the start of every SP-API operation to enforce the
        compliance requirement for immediate halt capability.
        """
        if self.is_kill_switch_enabled():
            logger.critical(
                "Amazon kill switch is ENABLED. All SP-API operations are halted. "
                "Set AMAZON_KILL_SWITCH_ENABLED=false to re-enable."
            )
            raise KillSwitchError(
                "Amazon SP-API operations are disabled (kill switch active). "
                "Set AMAZON_KILL_SWITCH_ENABLED=false to resume."
            )

    @staticmethod
    def enable_kill_switch() -> None:
        """
        Programmatically enable the kill switch.

        Note: For production use, set AMAZON_KILL_SWITCH_ENABLED=true in the
        environment rather than calling this method, as the environment variable
        persists across process restarts.
        """
        os.environ["AMAZON_KILL_SWITCH_ENABLED"] = "true"
        logger.critical("Amazon kill switch ENABLED — all SP-API operations halted")

    @staticmethod
    def disable_kill_switch() -> None:
        """Re-enable Amazon SP-API operations by disabling the kill switch."""
        os.environ["AMAZON_KILL_SWITCH_ENABLED"] = "false"
        logger.info("Amazon kill switch disabled — SP-API operations resumed")

    # ------------------------------------------------------------------
    # Self-identification
    # ------------------------------------------------------------------

    @staticmethod
    def get_self_id_string() -> str:
        """
        Return the self-identification string required by Amazon's Agent Policy.

        Per Amazon's policy effective March 4, 2026, all automated tools must
        identify themselves in API calls. The string is configurable via the
        AMAZON_SELF_ID_STRING environment variable.
        """
        return os.environ.get(
            "AMAZON_SELF_ID_STRING", "Automated by MarketF/EmpireBox v1.0"
        )

    def get_compliance_headers(self) -> Dict[str, str]:
        """
        Return the HTTP headers required for Amazon Agent Policy compliance.

        These headers must be included in every SP-API request.
        """
        self_id = self.get_self_id_string()
        return {
            "User-Agent": f"{self_id} (Language=Python)",
            "x-amz-user-agent": self_id,
        }

    # ------------------------------------------------------------------
    # Audit logging
    # ------------------------------------------------------------------

    def log_request(
        self,
        action: str,
        request_payload: Dict[str, Any],
        response_code: int,
        response_body: Optional[Dict[str, Any]],
        listing_id: Optional[str] = None,
    ) -> None:
        """
        Record an SP-API call in the audit log.

        Logs are written to:
        1. The application logger (always)
        2. The database `amazon_sync_log` table (if db_session is provided)

        Args:
            action: Action type (e.g. "create", "update", "inventory_sync")
            request_payload: Sanitized request body (no credentials)
            response_code: HTTP response status code
            response_body: Parsed response body (may be None)
            listing_id: Internal UUID of the amazon_listings record, if applicable
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        logger.info(
            "SP-API audit | action=%s listing_id=%s status=%d timestamp=%s",
            action,
            listing_id or "n/a",
            response_code,
            timestamp,
        )

        if self._db_session is not None:
            self._persist_log(
                listing_id=listing_id,
                action=action,
                request_payload=request_payload,
                response_code=response_code,
                response_body=response_body,
            )

    def _persist_log(
        self,
        action: str,
        request_payload: Dict[str, Any],
        response_code: int,
        response_body: Optional[Dict[str, Any]],
        listing_id: Optional[str] = None,
    ) -> None:
        """
        Persist an audit log entry to the amazon_sync_log database table.

        Requires the database schema from docs/MARKETF_AMAZON_SPEC.md to be applied.
        Failures are logged as warnings but do not raise — audit logging must
        not disrupt normal API operations.
        """
        try:
            # Import here to avoid hard dependency when db is not available
            from sqlalchemy import text  # noqa: PLC0415

            self._db_session.execute(
                text(
                    """
                    INSERT INTO amazon_sync_log
                        (listing_id, action, request_payload, response_code, response_body)
                    VALUES
                        (:listing_id, :action, :request_payload::jsonb,
                         :response_code, :response_body::jsonb)
                    """
                ),
                {
                    "listing_id": listing_id,
                    "action": action,
                    "request_payload": str(request_payload),
                    "response_code": response_code,
                    "response_body": str(response_body) if response_body else None,
                },
            )
            self._db_session.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to persist SP-API audit log: %s", exc)
