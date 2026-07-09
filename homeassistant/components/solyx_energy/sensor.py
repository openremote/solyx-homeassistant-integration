"""Sensor entities for the Solyx Energy Nymo integration."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import (
    ATTRIBUTE_CONTROL_VALUE,
    ATTRIBUTE_ENERGY_BOILER,
    ATTRIBUTE_GRID_POWER,
    ATTRIBUTE_OPERATING_MODE,
    ATTRIBUTE_POWER_BOILER,
)
from .coordinator import SolyxEnergyCoordinator
from .entity import SolyxNymoEntity

PARALLEL_UPDATES = 0

SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key=ATTRIBUTE_POWER_BOILER,
        translation_key=ATTRIBUTE_POWER_BOILER,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        native_unit_of_measurement="W",
    ),
    SensorEntityDescription(
        key=ATTRIBUTE_ENERGY_BOILER,
        translation_key=ATTRIBUTE_ENERGY_BOILER,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        native_unit_of_measurement="Wh",
    ),
    SensorEntityDescription(
        key=ATTRIBUTE_OPERATING_MODE,
        translation_key=ATTRIBUTE_OPERATING_MODE,
        device_class=SensorDeviceClass.ENUM,
        options=["DIRECT", "MUTED"],
    ),
    SensorEntityDescription(
        key=ATTRIBUTE_GRID_POWER,
        translation_key=ATTRIBUTE_GRID_POWER,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        native_unit_of_measurement="W",
    ),
    SensorEntityDescription(
        key=ATTRIBUTE_CONTROL_VALUE,
        translation_key=ATTRIBUTE_CONTROL_VALUE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Solyx Energy sensors from a config entry."""
    coordinator: SolyxEnergyCoordinator = entry.runtime_data
    async_add_entities(
        SolyxSensorEntity(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    )


class SolyxSensorEntity(SolyxNymoEntity, SensorEntity):
    """A single Solyx Energy entity."""

    def __init__(
        self,
        coordinator: SolyxEnergyCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize a Solyx Energy entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device_id}-{description.key}"

    @property
    def native_value(self) -> StateType | None:
        """Function to retrieve the parsed (native) value of the sensor."""
        return getattr(self.coordinator.data, self.entity_description.key, None)
