"""Fixtures and helpers for the Solyx Energy Local tests."""

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,  # Change to tests.common when merging into home-assistant/core
)
from solyx_energy_local_api.client import SolyxEnergyLocalApiClient
from solyx_energy_local_api.models import LocalInfo, LocalStatus

from custom_components.solyx_energy_local.const import CONF_CERT_SHA256, DOMAIN
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TOKEN
from homeassistant.util.json import json_loads

from .const import CERT_SHA256, DEVICE_ID, HOST, TOKEN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for Home Assistant component tests."""


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a MockConfigEntry for the Solyx Energy Local integration."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=DEVICE_ID,
        data={
            CONF_HOST: HOST,
            CONF_PORT: 443,
            CONF_TOKEN: TOKEN,
            CONF_CERT_SHA256: CERT_SHA256,
        },
        title=f"Nymo {DEVICE_ID}",
    )


@pytest.fixture
def mock_local_api_client():
    """Return a mocked SolyxEnergyLocalApiClient instance."""
    client = AsyncMock(spec=SolyxEnergyLocalApiClient)
    client.async_get_status.return_value = LocalStatus.from_dict(json_loads((FIXTURES_DIR / "status.json").read_text()))
    client.async_test_connection.return_value = LocalInfo.from_dict(json_loads((FIXTURES_DIR / "info.json").read_text()))
    return client


@pytest.fixture
def mock_api_client_class(mock_local_api_client):
    """Patch SolyxEnergyLocalApiClient so integration setup and config flow use the mock."""
    with (
        patch(
            "custom_components.solyx_energy_local.SolyxEnergyLocalApiClient",
            return_value=mock_local_api_client,
        ),
        patch(
            "custom_components.solyx_energy_local.config_flow.SolyxEnergyLocalApiClient",
            return_value=mock_local_api_client,
        ) as config_flow_class,
    ):
        mock_local_api_client.config_flow_class = config_flow_class
        yield mock_local_api_client


@pytest.fixture
def mock_setup_entry():
    """Mock setting up a config entry, preventing full integration setup."""
    with patch("custom_components.solyx_energy_local.async_setup_entry", return_value=True):
        yield


@pytest.fixture
async def init_integration(hass: HomeAssistant, mock_api_client_class, mock_config_entry):
    """Set up the Solyx Energy Local integration and return the config entry."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return mock_config_entry
