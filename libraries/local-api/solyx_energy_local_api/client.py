"""HTTP client for the local API of the Solyx Energy Sensorbox."""

from http import HTTPStatus
import logging
import re
from typing import Any

import aiohttp
from yarl import URL

from .exceptions import (
    SolyxEnergyAuthError,
    SolyxEnergyCertificateError,
    SolyxEnergyDataError,
    SolyxEnergyLocalControlDisabledError,
    SolyxEnergyWriteError,
)
from .models import LocalInfo, LocalStatus, OperationMode

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 443
# The device answers within a second; a dead device should not block for minutes.
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)

_FINGERPRINT_PATTERN = re.compile(r"[0-9a-f]{64}")


def normalize_fingerprint(cert_sha256: str) -> str:
    """Return the certificate SHA-256 as 64 lowercase hex characters, or raise ValueError."""
    fingerprint = cert_sha256.strip().lower().replace(":", "")
    if not _FINGERPRINT_PATTERN.fullmatch(fingerprint):
        raise ValueError("The certificate fingerprint must be 64 hexadecimal characters")
    return fingerprint


class SolyxEnergyLocalApiClient:
    """HTTPS client for the local API of a Sensorbox on the home network.

    The device uses a self-signed certificate, so it is pinned by its SHA-256
    fingerprint instead of being checked against a certificate authority. The
    token is only sent once the fingerprint matched.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        token: str,
        cert_sha256: str,
        *,
        port: int = DEFAULT_PORT,
    ) -> None:
        """Initialize the local API client."""
        self._session = session
        self._base_url = URL.build(scheme="https", host=host.strip("[]"), port=port)
        self._token = token
        self._ssl = aiohttp.Fingerprint(bytes.fromhex(normalize_fingerprint(cert_sha256)))

    async def _async_request(
        self, method: str, path: str, *, json: object = None, write: bool = False,
    ) -> Any:  # noqa: ANN401
        """Send a request to the device and return the decoded JSON body, if any."""
        error = SolyxEnergyWriteError if write else SolyxEnergyDataError
        try:
            async with self._session.request(
                method,
                self._base_url.with_path(path),
                headers={"Authorization": f"Bearer {self._token}"},
                json=json,
                ssl=self._ssl,
                timeout=REQUEST_TIMEOUT,
            ) as response:
                if response.status == HTTPStatus.UNAUTHORIZED:
                    raise SolyxEnergyAuthError("The Sensorbox rejected the access token.") from None
                if response.status == HTTPStatus.FORBIDDEN:
                    raise SolyxEnergyLocalControlDisabledError(
                        "Local control is turned off; turn it on in the Solyx Energy app.",
                    ) from None
                if response.status == HTTPStatus.TOO_MANY_REQUESTS:
                    raise error("The Sensorbox is rate limiting requests; try again later.") from None
                if response.status not in (HTTPStatus.OK, HTTPStatus.ACCEPTED):
                    raise error(f"Request to the Sensorbox failed with HTTP {response.status}") from None
                if response.status == HTTPStatus.ACCEPTED:
                    return None
                return await response.json()

        except aiohttp.ServerFingerprintMismatch as err:
            raise SolyxEnergyCertificateError(
                "The Sensorbox presented a certificate that does not match the fingerprint.",
            ) from err
        except aiohttp.ClientError as err:
            raise error(f"Request to the Sensorbox failed due to a communication error: {err}") from err
        except TimeoutError as err:
            raise error("Request to the Sensorbox timed out.") from err
        except ValueError as err:
            raise error(f"Response of the Sensorbox could not be parsed: {err}") from err

    async def _async_get_object(self, path: str) -> dict[str, Any]:
        """Fetch a JSON object from the device."""
        response_payload = await self._async_request("GET", path)
        if not isinstance(response_payload, dict):
            raise SolyxEnergyDataError(f"Invalid response from the Sensorbox for {path}") from None
        return response_payload

    async def async_get_info(self) -> LocalInfo:
        """Fetch the device ID, model and firmware versions."""
        return LocalInfo.from_dict(await self._async_get_object("/info"))

    async def async_get_status(self) -> LocalStatus:
        """Fetch the control source, Nymo measurements, savings and settings."""
        return LocalStatus.from_dict(await self._async_get_object("/status"))

    async def async_set_operation_mode(
        self, mode: OperationMode, power_percent: int | None = None,
    ) -> None:
        """Set the operation mode; DIRECT takes a power percentage (0-100, default 50).

        Needs local control to be turned on in the Solyx Energy app.
        """
        payload: dict[str, object] = {"mode": str(mode)}
        if power_percent is not None:
            payload["powerPercent"] = power_percent
        await self._async_request("POST", "/operationMode", json=payload, write=True)
        _LOGGER.debug("Operation mode has successfully been set to %s", payload)

    async def async_test_connection(self) -> LocalInfo:
        """Validate the address, certificate and token; return the device info."""
        return await self.async_get_info()
