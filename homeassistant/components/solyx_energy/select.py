"""Select entities for the Solyx Energy Nymo integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity

from .entity import SolyxNymoEntity
from .entity_descriptions import SELECT_DESCRIPTIONS

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import SolyxEnergyCoordinator

PARALLEL_UPDATES = 1


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Solyx Energy select entities from a config entry."""
    coordinator: SolyxEnergyCoordinator = entry.runtime_data
    async_add_entities(
        SolyxSelectEntity(coordinator, description)
        for description in SELECT_DESCRIPTIONS
    )


class SolyxSelectEntity(SolyxNymoEntity, SelectEntity):
    """A single Solyx Energy select entity, writable by the user."""

    @property
    def current_option(self) -> str | None:
        """Return the currently selected option from the coordinator data."""
        return getattr(self.coordinator.data, self.entity_description.key, None)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option and push it to the Solyx cloud platform."""
        await self.coordinator.async_set_attribute(self.entity_description.key, option)
