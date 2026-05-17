# backend/threecx_client.py

"""
3CX REST API v2 client.

Handles authentication (OAuth2 client credentials), token refresh,
and all API calls. Nothing in here touches the database — that is
the caller's responsibility. This keeps the client testable in
isolation.

API reference: https://www.3cx.com/docs/3cx-rest-api/
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import httpx

from config import (
    THREECX_HOST,
    THREECX_CLIENT_ID,
    THREECX_CLIENT_SECRET,
)

logger = logging.getLogger(__name__)

# 3CX token endpoint path — fixed across all v18+ installations
_TOKEN_PATH = "/connect/token"

# Active calls endpoint — returns all calls currently in progress
_ACTIVE_CALLS_PATH = "/callcontrol/activecalls"

# CDR endpoint — returns completed call records with filters
_CDR_PATH = "/callhistory/list"

# Extensions / agent status
_EXTENSIONS_PATH = "/extensions/list"


@dataclass
class TokenState:
    """
    Holds the current OAuth2 access token and its expiry.

    We refresh proactively 60 seconds before expiry so we never
    make an API call with an expired token.
    """
    access_token: str = ""
    expires_at: float = 0.0  # Unix timestamp

    def is_valid(self) -> bool:
        return bool(self.access_token) and time.time() < (self.expires_at - 60)


class ThreeCXClient:
    """
    Thin wrapper around the 3CX REST API v2.

    Usage:
        client = ThreeCXClient()
        active = client.get_active_calls()
        history = client.get_call_history(since=datetime.utcnow() - timedelta(hours=1))
    """

    def __init__(self):
        self._host = THREECX_HOST.rstrip("/")
        self._client_id = THREECX_CLIENT_ID
        self._client_secret = THREECX_CLIENT_SECRET
        self._token = TokenState()
        # Reuse a single httpx client for connection pooling
        self._http = httpx.Client(timeout=15)

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _ensure_token(self):
        """
        Fetch or refresh the access token if needed.

        3CX uses the OAuth2 client credentials flow. The token is
        short-lived (typically 3600 seconds) so we cache it and
        only refresh when it's about to expire.
        """
        if self._token.is_valid():
            return

        logger.debug("Fetching new 3CX access token")
        response = self._http.post(
            f"{self._host}{_TOKEN_PATH}",
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        payload = response.json()

        self._token.access_token = payload["access_token"]
        expires_in = int(payload.get("expires_in", 3600))
        self._token.expires_at = time.time() + expires_in
        logger.info("3CX token acquired, expires in %ds", expires_in)

    def _get(self, path: str, params: dict | None = None) -> Any:
        """Authenticated GET with automatic token refresh."""
        self._ensure_token()
        response = self._http.get(
            f"{self._host}{path}",
            params=params,
            headers={"Authorization": f"Bearer {self._token.access_token}"},
        )
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Active calls (live call wall)
    # ------------------------------------------------------------------

    def get_active_calls(self) -> list[dict]:
        """
        Returns all calls currently in progress on the PBX.

        Each call object includes:
          - Id, Status, EstablishedAt, CallType
          - Parties[0] (caller) and Parties[1] (callee) with Number, DisplayName
          - ServerNumber, CallsCount

        This is what powers the live call wall on the dashboard.
        """
        try:
            data = self._get(_ACTIVE_CALLS_PATH)
            return data.get("list", data) if isinstance(data, dict) else data
        except httpx.HTTPStatusError as exc:
            logger.error("get_active_calls failed: HTTP %d", exc.response.status_code)
            return []
        except Exception as exc:
            logger.error("get_active_calls error: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Call history (completed calls → write to your DB)
    # ------------------------------------------------------------------

    def get_call_history(
            self,
            since: datetime,
            until: datetime | None = None,
            page_size: int = 500,
    ) -> list[dict]:
        """
        Fetches completed call records from the 3CX CDR endpoint.

        `since` is the lower bound — in the polling job we pass the
        timestamp of the last successful poll so we only get new records.

        The endpoint is paginated. We walk all pages automatically and
        return a flat list. 500 per page is the safe maximum 3CX supports.
        """
        until = until or datetime.utcnow()
        all_records: list[dict] = []
        skip = 0

        while True:
            try:
                data = self._get(_CDR_PATH, params={
                    "startDate": since.strftime("%Y-%m-%dT%H:%M:%S"),
                    "endDate": until.strftime("%Y-%m-%dT%H:%M:%S"),
                    "$top": page_size,
                    "$skip": skip,
                })
            except Exception as exc:
                logger.error("get_call_history page skip=%d error: %s", skip, exc)
                break

            records = data.get("list", []) if isinstance(data, dict) else data
            if not records:
                break

            all_records.extend(records)

            if len(records) < page_size:
                break  # last page
            skip += page_size

        logger.info(
            "Fetched %d CDR records from 3CX (%s → %s)",
            len(all_records),
            since.isoformat(),
            until.isoformat(),
        )
        return all_records

    # ------------------------------------------------------------------
    # Extensions / agent status
    # ------------------------------------------------------------------

    def get_extensions(self) -> list[dict]:
        """
        Returns all extensions with their current status.

        Useful for resolving extension numbers to real agent names,
        and for showing who is Available / DND / Away on the dashboard.
        """
        try:
            data = self._get(_EXTENSIONS_PATH)
            return data.get("list", data) if isinstance(data, dict) else data
        except Exception as exc:
            logger.error("get_extensions error: %s", exc)
            return []

    def close(self):
        self._http.close()