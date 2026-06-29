"""HTTP API related functions for updating and retrieving data from the Solyx Energy cloud environment."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import aiohttp

from .const import BASE_URL, REALM_ID

_LOGGER = logging.getLogger(__name__)

class SolyxEnergyTokenError(Exception):
    """Error during access token retrieval from the Solyx Energy cloud environment."""

class SolyxEnergyDataError(Exception):
    """Error during data retrieval from the Solyx Energy cloud environment."""

class SolyxEnergyApiClient:
    """HTTP API client with OAuth2 authentication to the Solyx Energy cloud environment."""

    def __init__(
            self,
            session: aiohttp.ClientSession,
            client_id: str,
            client_secret: str
    ) -> None:
        self._session = session
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token: str | None = None
        self._token_expiry: float = 0.0

    async def _async_update_access_token(self) -> str:
        """Function that obtains the access token from the Keycloak HTTP token endpoint"""
        if self._access_token and time.monotonic() < self._token_expiry - 30:
            _LOGGER.debug("Access token still valid, skipping refresh.")
            return self._access_token

        request_url = f"{BASE_URL}/auth/realms/{REALM_ID}/protocol/openid-connect/token"
        request_data = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret
        }
        try:
            async with self._session.post(
                    request_url, data=request_data, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status in (401, 403):
                    raise SolyxEnergyTokenError(f"Token request failed due to an authentication error (HTTP {resp.status}).")
                if resp.status != 200:
                    raise SolyxEnergyTokenError(f"Token request failed with HTTP {resp.status}")

                response_payload = await resp.json()

        except aiohttp.ClientError as err:
            raise SolyxEnergyTokenError(f"Token request failed due to a communication error: {err}")
        except asyncio.TimeoutError as err:
            raise SolyxEnergyTokenError(f"Token request failed due to a timeout: {err}")

        self._access_token = response_payload["access_token"]
        self._token_expiry = time.monotonic() + response_payload.get("expires_in", 300)

        _LOGGER.debug("Access token refreshed successfully.")
        return self._access_token


    def _get_auth_headers(self) -> dict[str, str]:
        """Retrieves the authorization header for HTTP requests to the Solyx Energy cloud environment."""
        return {"Authorization": f"Bearer {self._access_token}"}


    async def async_get_asset_data(self, asset_id: str) -> dict[str, Any]:
        """Fetches asset/device data from the Solyx Energy cloud environment."""
        await self._async_update_access_token()

        request_url = f"{BASE_URL}/api/{REALM_ID}/asset/{asset_id}"
        try:
            async with self._session.get(
                    request_url,
                    headers=self._get_auth_headers(),
                    timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status in (401, 403):
                    self._access_token = None
                    raise SolyxEnergyDataError("Failed to retrieve asset data from Solyx Energy cloud; you were unauthorized.")
                if response.status != 200:
                    raise SolyxEnergyDataError(f"Failed to retrieve asset data from Solyx Energy cloud; error {response.status}")
                return await response.json()
        except aiohttp.ClientError as err:
            raise SolyxEnergyDataError(f"Failed to retrieve asset data from Solyx Energy cloud; {err}")
        except asyncio.TimeoutError as err:
            raise SolyxEnergyDataError(f"Failed to retrieve asset data from Solyx Energy cloud; request timed out.")


    async def async_test_connection(self, device_id: str) -> None:
        """Validate credentials and the existence of the Device ID by fetching data, and catching any HTTP errors"""
        await self.async_get_asset_data(device_id)