"""Tests for controlling the Nymo: the operating mode select."""

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest
from solyx_energy_local_api.exceptions import (
    SolyxEnergyAuthError,
    SolyxEnergyLocalControlDisabledError,
    SolyxEnergyWriteError,
)
from solyx_energy_local_api.models import Command, OperationMode

from custom_components.solyx_energy_local.const import DOMAIN
from homeassistant.components.select import ATTR_OPTION, SERVICE_SELECT_OPTION
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNKNOWN
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .const import DEVICE_ID

if TYPE_CHECKING:
    from unittest.mock import AsyncMock

    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_registry import EntityRegistry


def entity_id(entity_registry: EntityRegistry, platform: str, key: str) -> str:
    entity = entity_registry.async_get_entity_id(platform, DOMAIN, f"{DEVICE_ID}-{key}")
    assert entity is not None
    return entity


async def select_mode(hass: HomeAssistant, entity: str, option: str) -> None:
    await hass.services.async_call(
        "select", SERVICE_SELECT_OPTION, {ATTR_ENTITY_ID: entity, ATTR_OPTION: option}, blocking=True,
    )


def command_status(client: AsyncMock, mode: OperationMode, percent: int | None) -> None:
    """Make the Sensorbox report the given mode as set locally."""
    status = client.async_get_status.return_value
    client.async_get_status.return_value = replace(
        status, command=Command(operation_mode=mode, power_percent=percent),
    )


async def test_initial_state(hass: HomeAssistant, entity_registry: EntityRegistry, init_integration: MockConfigEntry) -> None:
    """Before anything is set locally the mode is unknown; there is no power level to set."""
    mode = hass.states.get(entity_id(entity_registry, "select", "operating_mode"))
    assert mode is not None
    assert mode.state == STATE_UNKNOWN
    assert mode.attributes["options"] == ["normal", "muted", "direct"]

    assert entity_registry.async_get_entity_id("number", DOMAIN, f"{DEVICE_ID}-power_level") is None


async def test_state_follows_the_sensorbox(
    hass: HomeAssistant,
    entity_registry: EntityRegistry,
    mock_api_client_class: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The mode set locally, also by another client, is shown."""
    command_status(mock_api_client_class, OperationMode.DIRECT, 75)
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(entity_id(entity_registry, "select", "operating_mode")).state == "direct"


async def test_direct_mode_always_uses_half_power(
    hass: HomeAssistant,
    entity_registry: EntityRegistry,
    mock_api_client_class: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Direct mode is sent with 50 %, also when another client set the Nymo to another power."""
    command_status(mock_api_client_class, OperationMode.DIRECT, 75)
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await select_mode(hass, entity_id(entity_registry, "select", "operating_mode"), "direct")

    mock_api_client_class.async_set_operation_mode.assert_awaited_once_with(OperationMode.DIRECT, 50)


@pytest.mark.usefixtures("init_integration")
@pytest.mark.parametrize("case", [
    pytest.param(("normal", OperationMode.NORMAL, None), id="normal"),
    pytest.param(("muted", OperationMode.MUTED, None), id="muted"),
    pytest.param(("direct", OperationMode.DIRECT, 50), id="direct"),
])
async def test_select_mode(
    hass: HomeAssistant,
    entity_registry: EntityRegistry,
    mock_api_client_class: AsyncMock,
    case: tuple[str, OperationMode, int | None],
) -> None:
    """Selecting a mode sends it to the Sensorbox; direct mode is sent with 50 %."""
    option, mode, percent = case
    command_status(mock_api_client_class, mode, percent)
    await select_mode(hass, entity_id(entity_registry, "select", "operating_mode"), option)

    mock_api_client_class.async_set_operation_mode.assert_awaited_once_with(mode, percent)
    assert hass.states.get(entity_id(entity_registry, "select", "operating_mode")).state == option




@pytest.mark.usefixtures("init_integration")
@pytest.mark.parametrize("case", [
    pytest.param(
        (SolyxEnergyLocalControlDisabledError, ServiceValidationError, "local_control_disabled"),
        id="local_control_off",
    ),
    pytest.param((SolyxEnergyWriteError, HomeAssistantError, "set_operation_mode_failed"), id="refused"),
])
async def test_select_errors(
    hass: HomeAssistant,
    entity_registry: EntityRegistry,
    mock_api_client_class: AsyncMock,
    case: tuple[type[Exception],
    type[HomeAssistantError], str],
) -> None:
    """Refused changes show a translated error, such as local control being off."""
    api_error, error, translation_key = case
    mock_api_client_class.async_set_operation_mode.side_effect = api_error
    with pytest.raises(error) as raised:
        await select_mode(hass, entity_id(entity_registry, "select", "operating_mode"), "muted")
    assert raised.value.translation_key == translation_key


async def test_select_auth_error_starts_reauth(
    hass: HomeAssistant,
    entity_registry: EntityRegistry,
    init_integration: MockConfigEntry,
    mock_api_client_class: AsyncMock,
) -> None:
    """Rejected credentials while changing the mode start a reauth flow."""
    mock_api_client_class.async_set_operation_mode.side_effect = SolyxEnergyAuthError
    with pytest.raises(HomeAssistantError) as raised:
        await select_mode(hass, entity_id(entity_registry, "select", "operating_mode"), "muted")
    assert raised.value.translation_key == "authentication_failed"

    await hass.async_block_till_done()
    flows = hass.config_entries.flow.async_progress()
    assert [flow["step_id"] for flow in flows] == ["reauth_confirm"]
