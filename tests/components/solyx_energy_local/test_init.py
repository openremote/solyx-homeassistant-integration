"""Tests for the Solyx Energy Local integration setup and unload.

These drive the real HA config-entry lifecycle (setup, unload, retry, reauth)
with the API client mocked at the class level, so no network calls are made.
"""

from typing import TYPE_CHECKING

import pytest
from solyx_energy_local_api.exceptions import (
    SolyxEnergyAuthError,
    SolyxEnergyCertificateError,
    SolyxEnergyDataError,
)

from custom_components.solyx_energy_local.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC

from .const import DEVICE_ID

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceRegistry


async def test_load_unload_config_entry(hass: HomeAssistant, init_integration) -> None:
    """The integration loads and can be unloaded cleanly."""
    assert init_integration.state is ConfigEntryState.LOADED
    assert init_integration.runtime_data.device_id == DEVICE_ID

    assert await hass.config_entries.async_unload(init_integration.entry_id)
    await hass.async_block_till_done()
    assert init_integration.state is ConfigEntryState.NOT_LOADED


@pytest.mark.parametrize("api_error", [SolyxEnergyAuthError, SolyxEnergyCertificateError])
async def test_config_entry_auth_failure(
    hass: HomeAssistant, mock_config_entry, mock_api_client_class, api_error,
) -> None:
    """A rejected token or changed certificate fails setup and starts a reauth flow."""
    mock_api_client_class.async_get_status.side_effect = api_error

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert len(flows) == 1
    assert flows[0]["step_id"] == "reauth_confirm"
    assert flows[0]["handler"] == DOMAIN


async def test_config_entry_not_ready(hass: HomeAssistant, mock_config_entry, mock_api_client_class) -> None:
    """An unreachable Sensorbox schedules a retry instead of hard-failing the entry."""
    mock_api_client_class.async_get_status.side_effect = SolyxEnergyDataError

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_device_info(device_registry: DeviceRegistry, init_integration) -> None:
    """Setup registers the Nymo with the same info as the cloud integration, plus its MAC address."""
    device = device_registry.async_get_device_by_identifier((DOMAIN, DEVICE_ID), init_integration.entry_id)
    assert device is not None
    assert device.manufacturer == "Solyx Energy"
    assert device.model == "Nymo"
    assert device.name == "Nymo"
    assert device.serial_number == DEVICE_ID
    assert device.connections == {(CONNECTION_NETWORK_MAC, "10:20:ba:f5:d9:88")}
