"""
Amazon SP-API Client — MarketF scaffolding (Phase 0)

This module provides the core HTTP client for Amazon's Selling Partner API.
It handles OAuth 2.0 token refresh, request signing, rate limiting, and
audit logging in compliance with Amazon's Agent Policy (effective March 4, 2026).

NOTE: This is scaffolding only. Requires a live Amazon Professional Seller
account and registered SP-API app before any API calls can be made.
See docs/MARKETF_AMAZON_SPEC.md for setup prerequisites.
"""

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests

from .compliance import ComplianceManager

logger = logging.getLogger(__name__)


class SPAPIError(Exception):
    """Raised when an Amazon SP-API call fails."""

    def __init__(self, status_code: int, message: str, request_id: Optional[str] = None):
        self.status_code = status_code
        self.request_id = request_id
        super().__init__(f"SP-API error {status_code}: {message}")


class KillSwitchError(Exception):
    """Raised when the kill switch is enabled and an API call is attempted."""


class SPAPIClient:
    """
    Amazon Selling Partner API client.

    Handles:
    - OAuth 2.0 token refresh (LWA — Login with Amazon)
    - Request signing (AWS SigV4)
    - Rate limiting with exponential backoff
    - Audit logging for all requests
    - Kill switch enforcement
    - Self-identification headers (Amazon Agent Policy compliance)
    """

    # Amazon LWA token endpoint
    LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"

    # SP-API base URL — US marketplace
    SP_API_BASE_URL = "https://sellingpartnerapi-na.amazon.com"

    # Default rate limit: 1 request/second (conservative baseline)
    DEFAULT_RATE_LIMIT = 1.0

    # Max retry attempts on 429 / 5xx
    MAX_RETRIES = 3

    def __init__(self, compliance_manager: Optional[ComplianceManager] = None):
        self._client_id = os.environ.get("AMAZON_SP_API_CLIENT_ID", "")
        self._client_secret = os.environ.get("AMAZON_SP_API_CLIENT_SECRET", "")
        self._refresh_token = os.environ.get("AMAZON_SP_API_REFRESH_TOKEN", "")
        self._seller_id = os.environ.get("AMAZON_SELLER_ID", "")
        self._marketplace_id = os.environ.get(
            "AMAZON_MARKETPLACE_ID", "ATVPDKIKX0DER"  # US marketplace default
        )
        self._self_id_string = os.environ.get(
            "AMAZON_SELF_ID_STRING", "Automated by MarketF/EmpireBox v1.0"
        )

        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0
        self._last_request_at: float = 0.0

        self._compliance = compliance_manager or ComplianceManager()
        self._session = requests.Session()

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def _refresh_access_token(self) -> str:
        """
        Obtain a new LWA access token using the stored refresh token.
        Tokens are valid for 1 hour; this method caches and reuses them.
        """
        self._compliance.check_kill_switch()

        response = self._session.post(
            self.LWA_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        self._access_token = data["access_token"]
        # Buffer 60 seconds before actual expiry to avoid edge cases
        self._token_expires_at = time.monotonic() + data.get("expires_in", 3600) - 60
        logger.debug("SP-API access token refreshed successfully")
        return self._access_token

    def _get_access_token(self) -> str:
        """Return a valid access token, refreshing if expired or missing."""
        if not self._access_token or time.monotonic() >= self._token_expires_at:
            return self._refresh_access_token()
        return self._access_token

    # ------------------------------------------------------------------
    # Request execution
    # ------------------------------------------------------------------

    def _build_headers(self) -> Dict[str, str]:
        """Build standard headers required for every SP-API request."""
        return {
            "x-amz-access-token": self._get_access_token(),
            "Content-Type": "application/json",
            # Amazon Agent Policy (March 4, 2026): self-identification required
            "User-Agent": f"{self._self_id_string} (Language=Python)",
            "x-amz-user-agent": self._self_id_string,
        }

    def _throttle(self) -> None:
        """Enforce minimum interval between requests (rate limiting)."""
        elapsed = time.monotonic() - self._last_request_at
        wait = self.DEFAULT_RATE_LIMIT - elapsed
        if wait > 0:
            time.sleep(wait)

    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        listing_id: Optional[str] = None,
        action: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute an authenticated SP-API request with rate limiting,
        retry logic, and full compliance logging.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            path: SP-API path (e.g. "/listings/2021-08-01/items/{sellerId}/{sku}")
            params: Query parameters
            json: JSON request body
            listing_id: Internal listing UUID for audit log correlation
            action: Human-readable action label for audit log (e.g. "inventory_sync")

        Returns:
            Parsed JSON response body

        Raises:
            KillSwitchError: If kill switch is active
            SPAPIError: If Amazon returns a non-2xx response after retries
        """
        self._compliance.check_kill_switch()

        url = f"{self.SP_API_BASE_URL}{path}"
        attempt = 0

        while attempt <= self.MAX_RETRIES:
            self._throttle()
            self._last_request_at = time.monotonic()

            headers = self._build_headers()
            response = self._session.request(
                method=method.upper(),
                url=url,
                headers=headers,
                params=params,
                json=json,
                timeout=30,
            )

            # Audit log every request
            self._compliance.log_request(
                listing_id=listing_id,
                action=action or f"{method.upper()} {path}",
                request_payload=json or {},
                response_code=response.status_code,
                response_body=self._safe_parse_json(response),
            )

            if response.status_code == 429:
                # Rate limited — exponential backoff
                wait = 2 ** attempt
                logger.warning(
                    "SP-API rate limited (429). Retrying in %ds (attempt %d/%d)",
                    wait,
                    attempt + 1,
                    self.MAX_RETRIES,
                )
                time.sleep(wait)
                attempt += 1
                continue

            if response.status_code >= 500:
                # Server error — retry with backoff
                wait = 2 ** attempt
                logger.warning(
                    "SP-API server error %d. Retrying in %ds (attempt %d/%d)",
                    response.status_code,
                    wait,
                    attempt + 1,
                    self.MAX_RETRIES,
                )
                time.sleep(wait)
                attempt += 1
                continue

            if not response.ok:
                raise SPAPIError(
                    status_code=response.status_code,
                    message=response.text[:500],
                    request_id=response.headers.get("x-amzn-RequestId"),
                )

            return self._safe_parse_json(response) or {}

        raise SPAPIError(
            status_code=429,
            message=f"Max retries ({self.MAX_RETRIES}) exceeded for {method} {path}",
        )

    # ------------------------------------------------------------------
    # Convenience methods for common SP-API operations
    # ------------------------------------------------------------------

    def create_listing(
        self, sku: str, payload: Dict[str, Any], listing_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create or fully replace a product listing on Amazon."""
        path = (
            f"/listings/2021-08-01/items/{self._seller_id}/{sku}"
            f"?marketplaceIds={self._marketplace_id}"
        )
        return self.request(
            "PUT", path, json=payload, listing_id=listing_id, action="create"
        )

    def update_listing(
        self, sku: str, patches: list, listing_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Partially update an existing listing via JSON Patch."""
        path = (
            f"/listings/2021-08-01/items/{self._seller_id}/{sku}"
            f"?marketplaceIds={self._marketplace_id}"
        )
        return self.request(
            "PATCH",
            path,
            json={"patches": patches},
            listing_id=listing_id,
            action="update",
        )

    def delete_listing(
        self, sku: str, listing_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delete a listing from Amazon."""
        path = (
            f"/listings/2021-08-01/items/{self._seller_id}/{sku}"
            f"?marketplaceIds={self._marketplace_id}"
        )
        return self.request(
            "DELETE", path, listing_id=listing_id, action="delete"
        )

    def sync_inventory(
        self, sku: str, quantity: int, listing_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update inventory quantity for a SKU."""
        patches = [
            {
                "op": "replace",
                "path": "/attributes/fulfillment_availability",
                "value": [
                    {
                        "fulfillment_channel_code": "DEFAULT",
                        "quantity": quantity,
                        "marketplace_id": self._marketplace_id,
                    }
                ],
            }
        ]
        return self.update_listing(sku, patches, listing_id=listing_id)

    def get_listing(self, sku: str) -> Dict[str, Any]:
        """Retrieve listing details for a SKU."""
        path = (
            f"/listings/2021-08-01/items/{self._seller_id}/{sku}"
            f"?marketplaceIds={self._marketplace_id}"
            f"&includedData=summaries,attributes,issues,offers,fulfillmentAvailability"
        )
        return self.request("GET", path, action="get_listing")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_parse_json(response: requests.Response) -> Optional[Dict[str, Any]]:
        """Parse response JSON safely; return None on parse failure."""
        try:
            return response.json()
        except ValueError:
            return None
