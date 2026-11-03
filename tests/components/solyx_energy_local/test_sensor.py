"""Tests for the Solyx Energy Local sensor platform."""

from typing import TYPE_CHECKING

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from solyx_energy_local_api.exceptions import SolyxEnergyDataError
from solyx_energy_local_api.models import LocalStatus

from custom_components.solyx_energy_local.const import (
    DATA_INTERVAL_SECONDS,
    DOMAIN,
    STALE_AFTER_SECONDS,
)
from custom_components.solyx_energy_local.coordinator import (
    SolyxEnergyData,
    to_cloud_values,
)
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.util.json import json_loads

from .conftest import FIXTURES_DIR
from .const import DEVICE_ID

if TYPE_CHECKING:
    from unittest.mock import AsyncMock

    from freezegun.api import FrozenDateTimeFactory

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_registry import EntityRegistry


@pytest.mark.parametrize(("key", "expected"), [
    pytest.param("boiler_current", ("6.0", "A", "current"), id="boiler_current"),
    pytest.param("boiler_power", ("1380.0", "W", "power"), id="boiler_power"),
    pytest.param("boiler_voltage", ("228.0", "V", "voltage"), id="boiler_voltage"),
    pytest.param("days_since_maximum_temperature", ("3.0", "d", "duration"), id="days_since_maximum_temperature"),
    pytest.param("grid_power", ("-320.0", "W", "power"), id="grid_power"),
    pytest.param("legionella_days", ("7.0", "d", "duration"), id="legionella_days"),
    # Whole kWh, rounded down like the Sensorbox reports them to the cloud
    pytest.param("saved_this_month", ("41.0", "kWh", "energy"), id="saved_this_month"),
    pytest.param("saved_this_week", ("9.0", "kWh", "energy"), id="saved_this_week"),
    pytest.param("saved_today", ("1200.0", "Wh", "energy"), id="saved_today"),
])
async def test_sensor_states(
    hass: HomeAssistant,
    entity_registry: EntityRegistry,
    init_integration: MockConfigEntry,
    key: str,
    expected: tuple[str, str, str],
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
    init_integration: MockConfigEntry,
    mock_api_client_class: AsyncMock,
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


def _status(*, connected: bool | None = True, nymo_age: int = 11, savings_age: int = 11,
            settings_age: int = 11) -> LocalStatus:
    """Return the fixture status with the given connection and ages."""
    data = json_loads((FIXTURES_DIR / "status.json").read_text())
    data["nymo"]["connected"] = connected
    data["nymo"]["age"] = nymo_age
    data["savings"]["age"] = savings_age
    data["settings"]["age"] = settings_age
    return LocalStatus.from_dict(data)


NYMO_FIELDS = ("boiler_current", "boiler_power", "boiler_voltage", "grid_power")
SAVINGS_FIELDS = ("saved_this_month", "saved_this_week", "saved_today")
SETTINGS_FIELDS = ("days_since_maximum_temperature", "legionella_days")
ALL_FIELDS = NYMO_FIELDS + SAVINGS_FIELDS + SETTINGS_FIELDS


@pytest.mark.parametrize(("status", "stale_fields"), [
    pytest.param(_status(), (), id="fresh"),
    pytest.param(_status(connected=None), (), id="connection_unknown"),
    pytest.param(
        _status(nymo_age=STALE_AFTER_SECONDS, savings_age=STALE_AFTER_SECONDS,
                settings_age=STALE_AFTER_SECONDS),
        (), id="at_the_limit",
    ),
    pytest.param(_status(nymo_age=STALE_AFTER_SECONDS + 1), NYMO_FIELDS, id="nymo_stale"),
    pytest.param(_status(savings_age=STALE_AFTER_SECONDS + 1), SAVINGS_FIELDS, id="savings_stale"),
    pytest.param(_status(settings_age=STALE_AFTER_SECONDS + 1), SETTINGS_FIELDS, id="settings_stale"),
    pytest.param(_status(connected=False), ALL_FIELDS, id="disconnected"),
])
def test_stale_values(status: LocalStatus, stale_fields: tuple[str, ...]) -> None:
    """Values the Sensorbox read too long ago, or from a disconnected Nymo, are left out."""
    values = to_cloud_values(status)
    for field in ALL_FIELDS:
        assert (getattr(values, field) is None) == (field in stale_fields), field


async def test_sensors_unavailable_when_stale(
    hass: HomeAssistant,
    entity_registry: EntityRegistry,
    init_integration: MockConfigEntry,
    mock_api_client_class: AsyncMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Sensors with stale values become unavailable, while the others keep their values."""
    mock_api_client_class.async_get_status.return_value = _status(nymo_age=STALE_AFTER_SECONDS + 1)
    freezer.tick(DATA_INTERVAL_SECONDS)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    states = {}
    for key in ("boiler_power", "saved_today"):
        entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, f"{DEVICE_ID}-{key}")
        assert entity_id is not None
        state = hass.states.get(entity_id)
        assert state is not None
        states[key] = state.state
    assert states == {"boiler_power": STATE_UNAVAILABLE, "saved_today": "1200.0"}
