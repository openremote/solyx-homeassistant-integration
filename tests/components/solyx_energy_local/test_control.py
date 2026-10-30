"""Tests for controlling the Nymo: the operating mode select and the power level number."""

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
from homeassistant.components.number import ATTR_VALUE, SERVICE_SET_VALUE
from homeassistant.components.select import ATTR_OPTION, SERVICE_SELECT_OPTION
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNKNOWN
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .const import DEVICE_ID

if TYPE_CHECKING:
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


async def set_value(hass: HomeAssistant, entity: str, value: float) -> None:
    await hass.services.async_call(
        "number", SERVICE_SET_VALUE, {ATTR_ENTITY_ID: entity, ATTR_VALUE: value}, blocking=True,
    )


def command_status(client, mode: OperationMode, percent: int | None) -> None:
    """Make the Sensorbox report the given mode as set locally."""
    status = client.async_get_status.return_value
    client.async_get_status.return_value = replace(
        status, command=Command(operation_mode=mode, power_percent=percent),
    )


async def test_initial_state(hass: HomeAssistant, entity_registry: EntityRegistry, init_integration) -> None:
    """Before anything is set locally the mode is unknown, and direct mode uses 50 %."""
    mode = hass.states.get(entity_id(entity_registry, "select", "operating_mode"))
    assert mode is not None
    assert mode.state == STATE_UNKNOWN
    assert mode.attributes["options"] == ["normal", "muted", "direct"]

    value = hass.states.get(entity_id(entity_registry, "number", "power_level"))
    assert value is not None
    assert value.state == "50"
    assert value.attributes["unit_of_measurement"] == "%"


async def test_state_follows_the_sensorbox(
    hass: HomeAssistant, entity_registry: EntityRegistry, mock_api_client_class, mock_config_entry,
) -> None:
    """The mode and power set locally, also by another client, are shown."""
    command_status(mock_api_client_class, OperationMode.DIRECT, 75)
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(entity_id(entity_registry, "select", "operating_mode")).state == "direct"
    assert hass.states.get(entity_id(entity_registry, "number", "power_level")).state == "75"


@pytest.mark.usefixtures("init_integration")
@pytest.mark.parametrize("case", [
    ("normal", OperationMode.NORMAL, None),
    ("muted", OperationMode.MUTED, None),
    ("direct", OperationMode.DIRECT, 50),
])
async def test_select_mode(
    hass: HomeAssistant, entity_registry: EntityRegistry, mock_api_client_class, case,
) -> None:
    """Selecting a mode sends it to the Sensorbox; direct mode sends the power level too."""
    option, mode, percent = case
    command_status(mock_api_client_class, mode, percent)
    await select_mode(hass, entity_id(entity_registry, "select", "operating_mode"), option)

    mock_api_client_class.async_set_operation_mode.assert_awaited_once_with(mode, percent)
    assert hass.states.get(entity_id(entity_registry, "select", "operating_mode")).state == option


async def test_power_level_is_kept_for_direct_mode(
    hass: HomeAssistant, entity_registry: EntityRegistry, init_integration, mock_api_client_class,
) -> None:
    """A power level set outside direct mode is not sent, but used when switching to direct."""
    await set_value(hass, entity_id(entity_registry, "number", "power_level"), 30)
    mock_api_client_class.async_set_operation_mode.assert_not_awaited()
    assert hass.states.get(entity_id(entity_registry, "number", "power_level")).state == "30"

    await select_mode(hass, entity_id(entity_registry, "select", "operating_mode"), "direct")
    mock_api_client_class.async_set_operation_mode.assert_awaited_once_with(OperationMode.DIRECT, 30)


async def test_power_level_in_direct_mode(
    hass: HomeAssistant, entity_registry: EntityRegistry, mock_api_client_class, mock_config_entry,
) -> None:
    """In direct mode a new power level is sent right away."""
    command_status(mock_api_client_class, OperationMode.DIRECT, 50)
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    command_status(mock_api_client_class, OperationMode.DIRECT, 80)
    await set_value(hass, entity_id(entity_registry, "number", "power_level"), 80)

    mock_api_client_class.async_set_operation_mode.assert_awaited_once_with(OperationMode.DIRECT, 80)
    assert hass.states.get(entity_id(entity_registry, "number", "power_level")).state == "80"


@pytest.mark.usefixtures("init_integration")
@pytest.mark.parametrize("case", [
    (SolyxEnergyLocalControlDisabledError, ServiceValidationError, "local_control_disabled"),
    (SolyxEnergyWriteError, HomeAssistantError, "set_operation_mode_failed"),
])
async def test_select_errors(
    hass: HomeAssistant, entity_registry: EntityRegistry, mock_api_client_class, case,
) -> None:
    """Refused changes show a translated error, such as local control being off."""
    api_error, error, translation_key = case
    mock_api_client_class.async_set_operation_mode.side_effect = api_error
    with pytest.raises(error) as raised:
        await select_mode(hass, entity_id(entity_registry, "select", "operating_mode"), "muted")
    assert raised.value.translation_key == translation_key


async def test_select_auth_error_starts_reauth(
    hass: HomeAssistant, entity_registry: EntityRegistry, init_integration, mock_api_client_class,
) -> None:
    """Rejected credentials while changing the mode start a reauth flow."""
    mock_api_client_class.async_set_operation_mode.side_effect = SolyxEnergyAuthError
    with pytest.raises(HomeAssistantError) as raised:
        await select_mode(hass, entity_id(entity_registry, "select", "operating_mode"), "muted")
    assert raised.value.translation_key == "authentication_failed"

    await hass.async_block_till_done()
    flows = hass.config_entries.flow.async_progress()
    assert [flow["step_id"] for flow in flows] == ["reauth_confirm"]


async def test_power_level_sent_before_direct_mode_is_confirmed(
    hass: HomeAssistant, entity_registry: EntityRegistry, init_integration, mock_api_client_class,
) -> None:
    """Right after selecting direct mode, a new power level is sent, also before the Nymo confirmed it."""
    await select_mode(hass, entity_id(entity_registry, "select", "operating_mode"), "direct")
    await set_value(hass, entity_id(entity_registry, "number", "power_level"), 70)

    assert mock_api_client_class.async_set_operation_mode.await_args_list[-1].args == (OperationMode.DIRECT, 70)
    assert hass.states.get(entity_id(entity_registry, "number", "power_level")).state == "70"
    # The Sensorbox has not reported the new mode yet.
    assert hass.states.get(entity_id(entity_registry, "select", "operating_mode")).state == STATE_UNKNOWN
