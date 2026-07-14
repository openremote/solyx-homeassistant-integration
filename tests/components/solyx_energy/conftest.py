"""Fixtures and helpers for the Solyx Energy tests."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,  # Change to tests.common when merging into home-assistant/core
)

from custom_components.solyx_energy.api import SolyxEnergyApiClient
from custom_components.solyx_energy.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_NYMO_DEVICE_ID,
    DOMAIN,
)
from homeassistant.util.json import json_loads

from .const import CLIENT_ID, CLIENT_SECRET, NYMO_DEVICE_ID

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a MockConfigEntry for the Solyx Energy integration."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=NYMO_DEVICE_ID,
        data={
            CONF_CLIENT_ID: CLIENT_ID,
            CONF_CLIENT_SECRET: CLIENT_SECRET,
            CONF_NYMO_DEVICE_ID: NYMO_DEVICE_ID,
        },
        title=f"Nymo {NYMO_DEVICE_ID}",
    )


@pytest.fixture
def mock_solyx_api_client():
    """Return a mocked SolyxEnergyApiClient instance."""
    data = json_loads((FIXTURES_DIR / "asset_data.json").read_text())
    client = AsyncMock(spec=SolyxEnergyApiClient)
    client.async_get_asset_data.return_value = data
    client.async_test_connection.return_value = None
    return client


@pytest.fixture
def mock_api_client_class(mock_solyx_api_client):
    """Patch SolyxEnergyApiClient so integration setup and config flow use the mock."""
    with (
        patch("custom_components.solyx_energy.SolyxEnergyApiClient", return_value=mock_solyx_api_client),
        patch("custom_components.solyx_energy.config_flow.SolyxEnergyApiClient", return_value=mock_solyx_api_client),
    ):
        yield mock_solyx_api_client


@pytest.fixture
def mock_setup_entry():
    """Mock setting up a config entry, preventing full integration setup."""
    with patch("custom_components.solyx_energy.async_setup_entry", return_value=True):
        yield


@pytest.fixture
async def init_integration(hass, mock_api_client_class, mock_config_entry):
    """Set up the Solyx Energy integration and return the config entry."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return mock_config_entry
