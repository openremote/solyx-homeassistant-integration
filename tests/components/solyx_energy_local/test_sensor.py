"""Tests for the Solyx Energy Local sensor platform."""

from typing import TYPE_CHECKING

import pytest
from pytest_homeassistant_custom_component.common import async_fire_time_changed
from solyx_energy_local_api.exceptions import SolyxEnergyDataError
from solyx_energy_local_api.models import LocalStatus

from custom_components.solyx_energy_local.const import DATA_INTERVAL_SECONDS, DOMAIN
from custom_components.solyx_energy_local.coordinator import (
    SolyxEnergyData,
    to_cloud_values,
)
from homeassistant.const import STATE_UNAVAILABLE

from .const import DEVICE_ID

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_registry import EntityRegistry


@pytest.mark.parametrize(("key", "expected"), [
    ("boiler_current", ("6.0", "A", "current")),
    ("boiler_power", ("1380.0", "W", "power")),
    ("boiler_voltage", ("228.0", "V", "voltage")),
    ("days_since_maximum_temperature", ("3.0", "d", "duration")),
    ("grid_power", ("-320.0", "W", "power")),
    ("legionella_days", ("7.0", "d", "duration")),
    # Whole kWh, rounded down like the Sensorbox reports them to the cloud
    ("saved_this_month", ("41.0", "kWh", "energy")),
    ("saved_this_week", ("9.0", "kWh", "energy")),
    ("saved_today", ("1200.0", "Wh", "energy")),
])
async def test_sensor_states(
    hass: HomeAssistant,
    entity_registry: EntityRegistry,
    init_integration,
    key,
    expected,
) -> None:
    """Each sensor has the value, unit and device class of the cloud integration."""
    entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, f"{DEVICE_ID}-{key}")
    assert entity_id is not None

    state = hass.states.get(entity_id)
    assert state is not None
    value, unit, device_class = expected
    assert state.state == value
    assert state.attributes["unit_of_measurement"] == unit
    assert state.attributes["device_class"] == device_class


async def test_sensors_unavailable_when_unreachable(
    hass: HomeAssistant,
    entity_registry: EntityRegistry,
    init_integration,
    mock_api_client_class,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The sensors become unavailable when the Sensorbox stops answering."""
    mock_api_client_class.async_get_status.side_effect = SolyxEnergyDataError
    freezer.tick(DATA_INTERVAL_SECONDS)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, f"{DEVICE_ID}-boiler_power")
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_UNAVAILABLE


def test_values_before_first_read() -> None:
    """Right after a restart the Sensorbox has not read the Nymo yet, so all values are unknown."""
    status = LocalStatus.from_dict({
        "controlSource": "CLOUD",
        "nymo": {"connected": None, "boiler": None, "grid": None},
        "savings": None,
        "settings": None,
    })
    assert to_cloud_values(status) == SolyxEnergyData(
        boiler_current=None,
        boiler_power=None,
        boiler_voltage=None,
        days_since_maximum_temperature=None,
        grid_power=None,
        legionella_days=None,
        saved_this_month=None,
        saved_this_week=None,
        saved_today=None,
    )
