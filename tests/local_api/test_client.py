"""Tests for the Solyx Energy local API client."""

from typing import Any, Self

import aiohttp
import pytest
from solyx_energy_local_api.client import (
    SolyxEnergyLocalApiClient,
    normalize_fingerprint,
)
from solyx_energy_local_api.exceptions import (
    SolyxEnergyAuthError,
    SolyxEnergyCertificateError,
    SolyxEnergyDataError,
    SolyxEnergyLocalControlDisabledError,
    SolyxEnergyWriteError,
)
from solyx_energy_local_api.models import (
    Boiler,
    Command,
    ControlSource,
    Grid,
    Legionella,
    LocalInfo,
    LocalStatus,
    NymoStatus,
    OperationMode,
    Savings,
    Settings,
    Temperatures,
)
from yarl import URL

HOST = "192.168.1.236"
TOKEN = "test-token"
CERT_SHA256 = "eae6038094000826b79ba312250ba11e0a4e49e3960da1dd03f6af75863bf4d7"
INFO_PAYLOAD = {
    "deviceId": "1020BAF5D988",
    "model": "nymo",
    "espFirmwareVersion": "1.0.0",
    "firmwareVersion": "1.2.3",
    "sensorBoxFirmwareVersion": "2.1.12",
}
# A /status response as the Sensorbox sends it
STATUS_PAYLOAD = {
    "controlSource": "LOCAL",
    "command": {"operationMode": "DIRECT", "powerPercent": 75},
    "nymo": {
        "connected": True,
        "mode": "PWR_BOOST",
        "controlValue": 74,
        "boiler": {"power": 1450, "voltage": 231, "current": 6.3},
        "grid": {"power": -320, "lineVoltages": [231, 229, 230], "lineCurrents": [2, 1, 1]},
        "temperatures": {"heatSink": 35, "mainPcb": 31, "frontPcb": 29},
        "radioSignal": -38.5,
        "age": 4,
    },
    "savings": {
        "today": 1200, "yesterday": 3400, "thisWeek": 9800, "lastWeek": 21000, "thisMonth": 41000,
        "lastMonth": 88000, "thisYear": 512000, "lastYear": 1100000, "total": 2300000, "age": 12,
    },
    "settings": {
        "threshold1": 100, "threshold2": 0, "powerLimit": 0, "boostMinutes": 30,
        "legionella": {"enabled": True, "intervalDays": 7, "daysSinceMaxTemperature": 3},
        "age": 12,
    },
    "sensorbox": {"wifiSignal": -51},
}
# Right after a restart, before the Sensorbox has read the Nymo
EMPTY_STATUS_PAYLOAD = {
    "controlSource": "CLOUD",
    "command": {"operationMode": None, "powerPercent": None},
    "nymo": {
        "connected": None, "mode": None, "controlValue": None, "boiler": None, "grid": None,
        "temperatures": None, "radioSignal": None, "age": None,
    },
    "savings": None,
    "settings": None,
    "sensorbox": {"wifiSignal": None},
}


class MockResponse:
    def __init__(self, status: int = 200, payload: object = None) -> None:
        self.status = status
        self._payload = payload

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_args: object) -> None:
        pass

    async def json(self) -> object:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class MockSession:
    def __init__(self) -> None:
        self.responses: dict[tuple[str, str], MockResponse | Exception] = {}
        self.requests: list[tuple[str, URL, dict[str, Any]]] = []

    def add_response(
        self, method: str, path: str, *, status: int = 200, payload: object = None,
    ) -> None:
        self.responses[(method, path)] = MockResponse(status, payload)

    def add_error(self, method: str, path: str, error: Exception) -> None:
        self.responses[(method, path)] = error

    def request(self, method: str, url: URL, **kwargs: Any) -> MockResponse:
        self.requests.append((method, url, kwargs))
        response = self.responses[(method, url.path)]
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture
def mock_session() -> MockSession:
    return MockSession()


@pytest.fixture
def client(mock_session: MockSession) -> SolyxEnergyLocalApiClient:
    return SolyxEnergyLocalApiClient(mock_session, HOST, TOKEN, CERT_SHA256)  # type: ignore[arg-type]


async def test_get_info_success(mock_session: MockSession, client: SolyxEnergyLocalApiClient) -> None:
    """A successful GET returns the info, pins the certificate and sends the token."""
    mock_session.add_response("GET", "/info", payload=INFO_PAYLOAD)
    assert await client.async_get_info() == LocalInfo(
        device_id="1020BAF5D988",
        model="nymo",
        esp_firmware_version="1.0.0",
        firmware_version="1.2.3",
        sensorbox_firmware_version="2.1.12",
    )

    _, url, request = mock_session.requests[-1]
    assert url == URL(f"https://{HOST}/info")
    assert request["headers"]["Authorization"] == f"Bearer {TOKEN}"
    assert isinstance(request["ssl"], aiohttp.Fingerprint)
    assert request["ssl"].fingerprint == bytes.fromhex(CERT_SHA256)


async def test_get_status_success(mock_session: MockSession, client: SolyxEnergyLocalApiClient) -> None:
    """A successful GET returns the status as typed values."""
    mock_session.add_response("GET", "/status", payload=STATUS_PAYLOAD)
    assert await client.async_get_status() == LocalStatus(
        control_source=ControlSource.LOCAL,
        command=Command(operation_mode=OperationMode.DIRECT, power_percent=75),
        nymo=NymoStatus(
            connected=True,
            mode="PWR_BOOST",
            control_value=74,
            boiler=Boiler(power=1450, voltage=231, current=6.3),
            grid=Grid(power=-320, line_voltages=(231, 229, 230), line_currents=(2, 1, 1)),
            temperatures=Temperatures(heat_sink=35, main_pcb=31, front_pcb=29),
            radio_signal=-38.5,
            age=4,
        ),
        savings=Savings(
            today=1200, yesterday=3400, this_week=9800, last_week=21000, this_month=41000,
            last_month=88000, this_year=512000, last_year=1100000, total=2300000, age=12,
        ),
        settings=Settings(
            threshold1=100,
            threshold2=0,
            power_limit=0,
            boost_minutes=30,
            legionella=Legionella(enabled=True, interval_days=7, days_since_max_temperature=3),
            age=12,
        ),
        wifi_signal=-51,
    )


async def test_get_status_before_first_read(
    mock_session: MockSession, client: SolyxEnergyLocalApiClient,
) -> None:
    """Values the Sensorbox has not read from the Nymo yet are None."""
    mock_session.add_response("GET", "/status", payload=EMPTY_STATUS_PAYLOAD)
    status = await client.async_get_status()
    assert status.control_source is ControlSource.CLOUD
    assert status.command == Command(operation_mode=None, power_percent=None)
    assert status.nymo == NymoStatus(
        connected=None, mode=None, control_value=None, boiler=None, grid=None,
        temperatures=None, radio_signal=None, age=None,
    )
    assert status.savings is None
    assert status.settings is None
    assert status.wifi_signal is None


@pytest.mark.parametrize("change", [
    {"controlSource": "SOMEWHERE"},
    {"command": {"operationMode": "TURBO"}},
    {"nymo": {"connected": "yes"}},
    {"nymo": {"boiler": {"power": "1450", "voltage": 231, "current": 6.3}}},
    {"nymo": {"boiler": {"power": True, "voltage": 231, "current": 6.3}}},
    {"nymo": {"boiler": {"voltage": 231, "current": 6.3}}},
    {"nymo": {"grid": {"power": 0, "lineVoltages": "231", "lineCurrents": []}}},
    {"savings": {"today": 1}},
    {"settings": {"threshold1": 1, "threshold2": 0, "powerLimit": 0, "boostMinutes": 30}},
    {"sensorbox": "strong"},
])
async def test_get_status_invalid(
    mock_session: MockSession, client: SolyxEnergyLocalApiClient, change: dict[str, object],
) -> None:
    """A status with wrong types or missing values raises SolyxEnergyDataError."""
    mock_session.add_response("GET", "/status", payload={**STATUS_PAYLOAD, **change})
    with pytest.raises(SolyxEnergyDataError):
        await client.async_get_status()


@pytest.mark.parametrize("payload", [{"model": "nymo"}, {"deviceId": ""}, {"deviceId": 42}])
async def test_get_info_invalid(
    mock_session: MockSession, client: SolyxEnergyLocalApiClient, payload: dict[str, object],
) -> None:
    """Info without a device ID raises SolyxEnergyDataError."""
    mock_session.add_response("GET", "/info", payload=payload)
    with pytest.raises(SolyxEnergyDataError):
        await client.async_get_info()


async def test_test_connection_returns_info(mock_session: MockSession, client: SolyxEnergyLocalApiClient) -> None:
    """Testing the connection returns the device info."""
    mock_session.add_response("GET", "/info", payload=INFO_PAYLOAD)
    assert (await client.async_test_connection()).device_id == "1020BAF5D988"


@pytest.mark.parametrize(("host", "port", "expected"), [
    ("solyx-f5d988.local", 443, "https://solyx-f5d988.local/status"),
    ("192.168.1.236", 8443, "https://192.168.1.236:8443/status"),
    ("fe80::1220:baff:fef5:d988", 443, "https://[fe80::1220:baff:fef5:d988]/status"),
    ("[fe80::1220:baff:fef5:d988]", 443, "https://[fe80::1220:baff:fef5:d988]/status"),
])
async def test_url(mock_session: MockSession, host: str, port: int, expected: str) -> None:
    """Host names, ports and IPv6 addresses form valid URLs."""
    client = SolyxEnergyLocalApiClient(mock_session, host, TOKEN, CERT_SHA256, port=port)  # type: ignore[arg-type]
    mock_session.add_response("GET", "/status", payload=STATUS_PAYLOAD)
    await client.async_get_status()
    assert str(mock_session.requests[-1][1]) == expected


@pytest.mark.parametrize(("status", "error"), [
    (401, SolyxEnergyAuthError),
    (429, SolyxEnergyDataError),
    (500, SolyxEnergyDataError),
])
async def test_get_status_http_errors(
    mock_session: MockSession, client: SolyxEnergyLocalApiClient, status: int, error: type[Exception],
) -> None:
    """HTTP errors while reading map to the matching exception."""
    mock_session.add_response("GET", "/status", status=status)
    with pytest.raises(error):
        await client.async_get_status()


async def test_get_status_certificate_mismatch(mock_session: MockSession, client: SolyxEnergyLocalApiClient) -> None:
    """A certificate that does not match the fingerprint raises SolyxEnergyCertificateError."""
    mock_session.add_error(
        "GET", "/status", aiohttp.ServerFingerprintMismatch(bytes(32), bytes.fromhex(CERT_SHA256), HOST, 443),
    )
    with pytest.raises(SolyxEnergyCertificateError):
        await client.async_get_status()


@pytest.mark.parametrize("error", [aiohttp.ClientConnectionError("refused"), TimeoutError()])
async def test_get_status_unreachable(
    mock_session: MockSession, client: SolyxEnergyLocalApiClient, error: Exception,
) -> None:
    """An unreachable device raises SolyxEnergyDataError."""
    mock_session.add_error("GET", "/status", error)
    with pytest.raises(SolyxEnergyDataError):
        await client.async_get_status()


@pytest.mark.parametrize("payload", [["not", "an", "object"], ValueError("bad json")])
async def test_get_status_invalid_response(
    mock_session: MockSession, client: SolyxEnergyLocalApiClient, payload: object,
) -> None:
    """A response that is not a JSON object raises SolyxEnergyDataError."""
    mock_session.add_response("GET", "/status", payload=payload)
    with pytest.raises(SolyxEnergyDataError):
        await client.async_get_status()


async def test_set_operation_mode_success(mock_session: MockSession, client: SolyxEnergyLocalApiClient) -> None:
    """Setting DIRECT sends the mode and power percentage."""
    mock_session.add_response("POST", "/operationMode", status=202)
    await client.async_set_operation_mode(OperationMode.DIRECT, 75)
    method, _, request = mock_session.requests[-1]
    assert method == "POST"
    assert request["json"] == {"mode": "DIRECT", "powerPercent": 75}


async def test_set_operation_mode_without_percent(
    mock_session: MockSession, client: SolyxEnergyLocalApiClient,
) -> None:
    """Modes other than DIRECT are sent without a power percentage."""
    mock_session.add_response("POST", "/operationMode", status=202)
    await client.async_set_operation_mode(OperationMode.MUTED)
    assert mock_session.requests[-1][2]["json"] == {"mode": "MUTED"}


@pytest.mark.parametrize(("status", "error"), [
    (403, SolyxEnergyLocalControlDisabledError),
    (422, SolyxEnergyWriteError),
    (429, SolyxEnergyWriteError),
])
async def test_set_operation_mode_errors(
    mock_session: MockSession, client: SolyxEnergyLocalApiClient, status: int, error: type[Exception],
) -> None:
    """Refused changes raise write errors; 403 means local control is turned off."""
    mock_session.add_response("POST", "/operationMode", status=status)
    with pytest.raises(error):
        await client.async_set_operation_mode(OperationMode.NORMAL)


def test_normalize_fingerprint() -> None:
    """Fingerprints are accepted with colons, in uppercase and with surrounding spaces."""
    pasted = " " + ":".join(CERT_SHA256[i:i + 2] for i in range(0, 64, 2)).upper() + " "
    assert normalize_fingerprint(pasted) == CERT_SHA256


@pytest.mark.parametrize("fingerprint", ["", "abc", CERT_SHA256[:-1], CERT_SHA256[:-1] + "g"])
def test_invalid_fingerprint(mock_session: MockSession, fingerprint: str) -> None:
    """A fingerprint that is not 64 hex characters is rejected when creating the client."""
    with pytest.raises(ValueError, match="64 hexadecimal"):
        SolyxEnergyLocalApiClient(mock_session, HOST, TOKEN, fingerprint)  # type: ignore[arg-type]
