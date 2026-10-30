"""Tests for the Solyx Energy Local config flow.

Covers setup by address, setup after mDNS discovery, and reauthentication. The
API client is mocked at the class level, so no network calls are made.
"""

from dataclasses import replace
from ipaddress import ip_address
from typing import TYPE_CHECKING

import pytest
from solyx_energy_local_api.exceptions import (
    SolyxEnergyAuthError,
    SolyxEnergyCertificateError,
    SolyxEnergyDataError,
)

from custom_components.solyx_energy_local.const import CONF_CERT_SHA256, DOMAIN
from homeassistant.config_entries import SOURCE_USER, SOURCE_ZEROCONF
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TOKEN
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import CERT_SHA256, DEVICE_ID, HOST, TOKEN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

# Prevent the flow from actually setting up the full integration when an entry is created
pytestmark = pytest.mark.usefixtures("mock_setup_entry")

CREDENTIALS = {CONF_TOKEN: TOKEN, CONF_CERT_SHA256: CERT_SHA256}
USER_INPUT = {CONF_HOST: HOST, **CREDENTIALS}
ENTRY_DATA = {CONF_HOST: HOST, CONF_PORT: 443, **CREDENTIALS}


def zeroconf_info(host: str = HOST, properties: dict[str, str] | None = None) -> ZeroconfServiceInfo:
    """Return the mDNS advertisement of the Sensorbox."""
    return ZeroconfServiceInfo(
        ip_address=ip_address(host),
        ip_addresses=[ip_address(host)],
        hostname="solyx-f5d988.local.",
        name="Solyx Nymo F5D988._solyx._tcp.local.",
        port=443,
        type="_solyx._tcp.local.",
        properties={"deviceId": DEVICE_ID} if properties is None else properties,
    )


@pytest.mark.usefixtures("mock_api_client_class")
async def test_user_flow(hass: HomeAssistant) -> None:
    """The happy path: a valid address, token and fingerprint create an entry."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"Nymo {DEVICE_ID}"
    assert result["data"] == ENTRY_DATA
    assert result["result"].unique_id == DEVICE_ID


@pytest.mark.usefixtures("mock_api_client_class")
async def test_user_flow_normalizes_fingerprint(hass: HomeAssistant) -> None:
    """A fingerprint pasted with colons and in uppercase is stored in the canonical form."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    pasted = ":".join(CERT_SHA256[i:i + 2] for i in range(0, 64, 2)).upper()
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={**USER_INPUT, CONF_CERT_SHA256: pasted},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_CERT_SHA256] == CERT_SHA256


@pytest.mark.parametrize(("api_error", "error"), [
    (SolyxEnergyAuthError, "invalid_auth"),
    (SolyxEnergyCertificateError, "certificate_mismatch"),
    (SolyxEnergyDataError, "cannot_connect"),
])
async def test_user_flow_errors(hass: HomeAssistant, mock_api_client_class, api_error, error) -> None:
    """Connection errors are shown on the form, and the flow recovers once they are fixed."""
    mock_api_client_class.async_test_connection.side_effect = api_error
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=USER_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    mock_api_client_class.async_test_connection.side_effect = None
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_invalid_fingerprint(hass: HomeAssistant, mock_api_client_class) -> None:
    """A fingerprint that is not 64 hex characters is reported on its field."""
    mock_api_client_class.config_flow_class.side_effect = ValueError
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={**USER_INPUT, CONF_CERT_SHA256: "not-a-fingerprint"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_CERT_SHA256: "invalid_fingerprint"}


@pytest.mark.usefixtures("mock_api_client_class")
async def test_user_flow_already_configured(hass: HomeAssistant, mock_config_entry) -> None:
    """Setting up the same Nymo again aborts and updates its address."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={**USER_INPUT, CONF_HOST: "solyx-f5d988.local"},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert mock_config_entry.data[CONF_HOST] == "solyx-f5d988.local"


@pytest.mark.usefixtures("mock_api_client_class")
async def test_zeroconf_flow(hass: HomeAssistant) -> None:
    """A discovered Nymo only asks for the token and fingerprint."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=zeroconf_info(),
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "zeroconf_confirm"
    assert result["description_placeholders"] == {"device_id": DEVICE_ID, "host": HOST}

    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=CREDENTIALS)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == ENTRY_DATA
    assert result["result"].unique_id == DEVICE_ID


async def test_zeroconf_flow_error(hass: HomeAssistant, mock_api_client_class) -> None:
    """A rejected token is shown on the confirm form."""
    mock_api_client_class.async_test_connection.side_effect = SolyxEnergyAuthError
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=zeroconf_info(),
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=CREDENTIALS)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_zeroconf_flow_wrong_device(hass: HomeAssistant, mock_api_client_class) -> None:
    """The flow aborts when another Nymo answers at the discovered address."""
    mock_api_client_class.async_test_connection.return_value = replace(
        mock_api_client_class.async_test_connection.return_value, device_id="AABBCCDDEEFF",
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=zeroconf_info(),
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=CREDENTIALS)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_device"


async def test_zeroconf_updates_address(hass: HomeAssistant, mock_config_entry) -> None:
    """A Nymo that is already set up and shows up at a new address gets its address updated."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=zeroconf_info(host="192.168.1.50"),
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert mock_config_entry.data[CONF_HOST] == "192.168.1.50"


async def test_zeroconf_without_device_id(hass: HomeAssistant) -> None:
    """An advertisement without a device ID is not a Nymo."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=zeroconf_info(properties={}),
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_solyx_device"


@pytest.mark.usefixtures("mock_api_client_class")
async def test_reauth_flow(hass: HomeAssistant, mock_config_entry) -> None:
    """New credentials are stored and the entry is reloaded."""
    mock_config_entry.add_to_hass(hass)
    result = await mock_config_entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    new_fingerprint = "ab" * 32
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_TOKEN: "new-token", CONF_CERT_SHA256: new_fingerprint},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data == {
        CONF_HOST: HOST, CONF_PORT: 443, CONF_TOKEN: "new-token", CONF_CERT_SHA256: new_fingerprint,
    }


async def test_reauth_flow_error(hass: HomeAssistant, mock_config_entry, mock_api_client_class) -> None:
    """A rejected token during reauthentication is shown on the form."""
    mock_config_entry.add_to_hass(hass)
    mock_api_client_class.async_test_connection.side_effect = SolyxEnergyAuthError
    result = await mock_config_entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=CREDENTIALS)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_reauth_flow_wrong_device(hass: HomeAssistant, mock_config_entry, mock_api_client_class) -> None:
    """Reauthentication aborts when another Nymo answers at the stored address."""
    mock_config_entry.add_to_hass(hass)
    mock_api_client_class.async_test_connection.return_value = replace(
        mock_api_client_class.async_test_connection.return_value, device_id="AABBCCDDEEFF",
    )
    result = await mock_config_entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=CREDENTIALS)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_device"
