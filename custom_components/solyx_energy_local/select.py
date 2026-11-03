"""Select entities for the Solyx Energy Local integration."""

from typing import TYPE_CHECKING, override

from solyx_energy_local_api.models import OperationMode

from homeassistant.components.select import SelectEntity, SelectEntityDescription

from .entity import SolyxNymoEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import SolyxEnergyLocalConfigEntry

PARALLEL_UPDATES = 1

OPERATING_MODE_DESCRIPTION = SelectEntityDescription(
    key="operating_mode",
    translation_key="operating_mode",
    options=[mode.lower() for mode in OperationMode],
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: SolyxEnergyLocalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the operating mode select of a Nymo from a config entry."""
    async_add_entities([SolyxOperatingModeSelect(entry.runtime_data, OPERATING_MODE_DESCRIPTION)])


class SolyxOperatingModeSelect(SolyxNymoEntity, SelectEntity):
    """The operating mode of the Nymo, which local clients may set while local control is on."""

    @property
    @override
    def current_option(self) -> str | None:
        """Return the mode last set locally, or None when none was set since the Sensorbox started."""
        mode = self.coordinator.data.status.command.operation_mode
        return mode.lower() if mode else None

    @override
    async def async_select_option(self, option: str) -> None:
        """Set the operating mode; direct mode uses the power of the power level."""
        await self.coordinator.async_set_operation_mode(OperationMode(option.upper()))
