"""Sensor entities for the Solyx Energy Nymo integration."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .coordinator import SolyxEnergyCoordinator
from .const import ATTRIBUTE_NOTES
from .entity import SolyxNymoEntity

SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key=ATTRIBUTE_NOTES,
        translation_key=ATTRIBUTE_NOTES,
    ),
)

async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Solyx Energy sensors from a config entry"""
    coordinator: SolyxEnergyCoordinator = entry.runtime_data
    async_add_entities(
        SolyxSensorEntity(coordinator, description) for description in SENSOR_DESCRIPTIONS
    )

class SolyxSensorEntity(SolyxNymoEntity, SensorEntity):
    """A single Solyx Energy entity"""

    def __init__(
            self,
            coordinator: SolyxEnergyCoordinator,
            description: SensorEntityDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.identifier}-{description.key}"

    @property
    def native_value(self) -> StateType | None:
        return getattr(self.coordinator.data, self.entity_description.key, None)