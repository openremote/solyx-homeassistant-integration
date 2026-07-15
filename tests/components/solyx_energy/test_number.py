"""Tests for the Solyx Energy number platform."""

import pytest

from custom_components.solyx_energy.api import SolyxEnergyWriteError
from custom_components.solyx_energy.const import DOMAIN
from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
from homeassistant.components.number.const import SERVICE_SET_VALUE
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.exceptions import HomeAssistantError

from .const import NYMO_DEVICE_ID


async def test_number_state_and_write(hass, entity_registry, mock_solyx_api_client, init_integration) -> None:
    """Test the number entity state, attributes, and write path."""
    entity_id = entity_registry.async_get_entity_id("number", DOMAIN, f"{NYMO_DEVICE_ID}-controlValue")
    assert entity_id is not None

    # Check the starting value, min/max, and unit are correct.
    state = hass.states.get(entity_id)
    assert float(state.state) == 60.0
    assert state.attributes["min"] == 0
    assert state.attributes["max"] == 100
    assert state.attributes["unit_of_measurement"] == "%"

    # Set a new value and check it is sent to the (mock) API.
    await hass.services.async_call(
        NUMBER_DOMAIN, SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, "value": 25},
        blocking=True,
    )
    mock_solyx_api_client.async_set_asset_attribute.assert_called_once_with(
        NYMO_DEVICE_ID, "controlValue", 25.0,
    )
    # The state should update to the new value.
    assert float(hass.states.get(entity_id).state) == 25.0


async def test_number_api_failure(hass, mock_solyx_api_client, init_integration) -> None:
    """Test that an API error during a write raises HomeAssistantError."""
    mock_solyx_api_client.async_set_asset_attribute.side_effect = SolyxEnergyWriteError

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            NUMBER_DOMAIN, SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: "number.nymo_control_value", "value": 25},
            blocking=True,
        )
