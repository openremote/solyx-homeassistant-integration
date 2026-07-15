"""Tests for the Solyx Energy select platform."""
import pytest

from custom_components.solyx_energy.api import SolyxEnergyWriteError
from custom_components.solyx_energy.const import DOMAIN
from homeassistant.components.select import (
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_OPTION
from homeassistant.exceptions import HomeAssistantError

from .const import NYMO_DEVICE_ID


async def test_select_state_and_write(hass, entity_registry, mock_solyx_api_client, init_integration) -> None:
    """Test the select entity state, options, and write path."""
    entity_id = entity_registry.async_get_entity_id("select", DOMAIN, f"{NYMO_DEVICE_ID}-operatingMode")
    assert entity_id is not None

    # Validate the selected option, and the list of available options.
    state = hass.states.get(entity_id)
    assert state.state == "DIRECT"
    assert state.attributes["options"] == ["DIRECT", "MUTED"]

    # Pick a new option and check if it is sent to the (mock) API.
    await hass.services.async_call(
        SELECT_DOMAIN, SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: entity_id, ATTR_OPTION: "MUTED"},
        blocking=True,
    )
    mock_solyx_api_client.async_set_asset_attribute.assert_called_once_with(
        NYMO_DEVICE_ID, "operatingMode", "MUTED",
    )
    # The state should have updated to the new option.
    assert hass.states.get(entity_id).state == "MUTED"


async def test_select_api_failure(hass, mock_solyx_api_client, init_integration) -> None:
    """Test that an API error (SolyxEnergyWriteError) during a write raises HomeAssistantError."""
    mock_solyx_api_client.async_set_asset_attribute.side_effect = SolyxEnergyWriteError

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            SELECT_DOMAIN, SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: "select.nymo_operating_mode", ATTR_OPTION: "MUTED"},
            blocking=True,
        )
