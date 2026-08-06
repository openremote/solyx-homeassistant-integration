"""Tests for the Solyx Energy API client."""

import time
from typing import Any, Self

import pytest
from solyx_energy_api.client import SolyxEnergyApiClient
from solyx_energy_api.exceptions import (
    SolyxEnergyAuthError,
    SolyxEnergyDataError,
    SolyxEnergyTokenError,
    SolyxEnergyWriteError,
)

BASE_URL = "https://staging.cloud.solyxenergy.nl"
REALM_ID = "solyx"
DEVICE_ID = "nymo-12345"
TOKEN_PAYLOAD = {"access_token": "new-token", "expires_in": 300}
ASSET_PAYLOAD = {"attributes": {"powerBoiler": {"value": 100.0}}}
ATTRIBUTE_NAME = "operatingMode"

TOKEN_URL = f"{BASE_URL}/auth/realms/{REALM_ID}/protocol/openid-connect/token"
ASSET_URL = f"{BASE_URL}/api/{REALM_ID}/asset/{DEVICE_ID}"
ATTRIBUTE_URL = f"{BASE_URL}/api/{REALM_ID}/asset/{DEVICE_ID}/attribute/{ATTRIBUTE_NAME}"


class MockResponse:
    def __init__(self, status: int = 200, payload: object = None) -> None:
        self.status = status
        self._payload = payload

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_args: object) -> None:
        pass

    async def json(self) -> object:
        return self._payload


class MockSession:
    def __init__(self) -> None:
        self.responses: dict[tuple[str, str], MockResponse] = {}
        self.requests: list[tuple[str, str, dict[str, Any]]] = []

    def add_response(
        self,
        method: str,
        url: str,
        *,
        status: int = 200,
        payload: object = None,
    ) -> None:
        self.responses[(method, url)] = MockResponse(status, payload)

    def _request(self, method: str, url: str, **kwargs: Any) -> MockResponse:
        self.requests.append((method, url, kwargs))
        return self.responses[(method, url)]

    def post(self, url: str, **kwargs: Any) -> MockResponse:
        return self._request("POST", url, **kwargs)

    def get(self, url: str, **kwargs: Any) -> MockResponse:
        return self._request("GET", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> MockResponse:
        return self._request("PUT", url, **kwargs)


@pytest.fixture
def mock_session() -> MockSession:
    return MockSession()


@pytest.fixture
def client(mock_session: MockSession) -> SolyxEnergyApiClient:
    return create_client(mock_session, cached_token=True)


def create_client(
    mock_session: MockSession, *, cached_token: bool = False,
) -> SolyxEnergyApiClient:
    client = SolyxEnergyApiClient(
        mock_session,  # type: ignore[arg-type]
        "test-id",
        "test-secret",
        base_url=BASE_URL,
        realm_id=REALM_ID,
    )
    if cached_token:
        client._access_token = "valid-token"
        client._token_expiry = time.monotonic() + 3600
    return client


async def test_token_refresh_success(mock_session: MockSession) -> None:
    """A successful token request stores the access token from the response."""
    mock_session.add_response("POST", TOKEN_URL, payload=TOKEN_PAYLOAD)
    client = create_client(mock_session)
    await client._async_update_access_token()
    assert client._access_token == "new-token"


async def test_token_refresh_auth_error(mock_session: MockSession) -> None:
    """A 401 from the token endpoint means the credentials are wrong."""
    mock_session.add_response("POST", TOKEN_URL, status=401)
    client = create_client(mock_session)
    with pytest.raises(SolyxEnergyAuthError):
        await client._async_update_access_token()


async def test_token_refresh_token_error(mock_session: MockSession) -> None:
    """A non-auth HTTP failure raises SolyxEnergyTokenError."""
    mock_session.add_response("POST", TOKEN_URL, status=503)
    client = create_client(mock_session)
    with pytest.raises(SolyxEnergyTokenError):
        await client._async_update_access_token()


async def test_get_asset_data_success(
    mock_session: MockSession, client: SolyxEnergyApiClient,
) -> None:
    """A successful GET returns data and sends the bearer token."""
    mock_session.add_response("GET", ASSET_URL, payload=ASSET_PAYLOAD)
    result = await client.async_get_asset_data(DEVICE_ID)
    assert result == ASSET_PAYLOAD
    assert mock_session.requests[-1][2]["headers"]["Authorization"] == "Bearer valid-token"


async def test_get_asset_data_error(
    mock_session: MockSession, client: SolyxEnergyApiClient,
) -> None:
    """A 5xx response while reading data raises SolyxEnergyDataError."""
    mock_session.add_response("GET", ASSET_URL, status=500)
    with pytest.raises(SolyxEnergyDataError):
        await client.async_get_asset_data(DEVICE_ID)


async def test_get_asset_data_auth_error(
    mock_session: MockSession, client: SolyxEnergyApiClient,
) -> None:
    """A 401 while reading data clears the cached token."""
    mock_session.add_response("GET", ASSET_URL, status=401)
    with pytest.raises(SolyxEnergyAuthError):
        await client.async_get_asset_data(DEVICE_ID)
    assert client._access_token is None


async def test_set_asset_attribute_success(
    mock_session: MockSession, client: SolyxEnergyApiClient,
) -> None:
    """A successful PUT sends the value as JSON with the bearer token."""
    mock_session.add_response("PUT", ATTRIBUTE_URL)
    await client.async_set_asset_attribute(DEVICE_ID, ATTRIBUTE_NAME, "DIRECT")
    request = mock_session.requests[-1][2]
    assert request["headers"]["Authorization"] == "Bearer valid-token"
    assert request["json"] == "DIRECT"


async def test_set_asset_attribute_error(
    mock_session: MockSession, client: SolyxEnergyApiClient,
) -> None:
    """A 5xx response while writing raises SolyxEnergyWriteError."""
    mock_session.add_response("PUT", ATTRIBUTE_URL, status=500)
    with pytest.raises(SolyxEnergyWriteError):
        await client.async_set_asset_attribute(DEVICE_ID, ATTRIBUTE_NAME, "DIRECT")


async def test_set_asset_attribute_auth_error(
    mock_session: MockSession, client: SolyxEnergyApiClient,
) -> None:
    """A 403 while writing clears the cached token."""
    mock_session.add_response("PUT", ATTRIBUTE_URL, status=403)
    with pytest.raises(SolyxEnergyAuthError):
        await client.async_set_asset_attribute(DEVICE_ID, ATTRIBUTE_NAME, "DIRECT")
    assert client._access_token is None


async def test_test_connection_success(
    mock_session: MockSession, client: SolyxEnergyApiClient,
) -> None:
    """async_test_connection validates credentials by fetching asset data."""
    mock_session.add_response("GET", ASSET_URL, payload=ASSET_PAYLOAD)
    await client.async_test_connection(DEVICE_ID)
