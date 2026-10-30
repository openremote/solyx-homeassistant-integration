"""Number entities for the Solyx Energy Local integration."""

from typing import TYPE_CHECKING, override

from solyx_energy_local_api.models import OperationMode

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.const import PERCENTAGE

from .entity import SolyxNymoEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import SolyxEnergyLocalConfigEntry

PARALLEL_UPDATES = 1

POWER_LEVEL_DESCRIPTION = NumberEntityDescription(
    key="power_level",
    translation_key="power_level",
    native_min_value=0,
    native_max_value=100,
    native_step=1,
    native_unit_of_measurement=PERCENTAGE,
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: SolyxEnergyLocalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the power level of a Nymo from a config entry."""
    async_add_entities([SolyxPowerLevelNumber(entry.runtime_data, POWER_LEVEL_DESCRIPTION)])


class SolyxPowerLevelNumber(SolyxNymoEntity, NumberEntity):
    """The power of direct mode, in percent of the boiler's power."""

    @property
    @override
    def native_value(self) -> float:
        """Return the power used for direct mode."""
        return self.coordinator.direct_percent

    @override
    async def async_set_native_value(self, value: float) -> None:
        """Set the power; it is sent right away while the Nymo is in or switching to direct mode."""
        percent = round(value)
        if self.coordinator.requested_mode is OperationMode.DIRECT:
            await self.coordinator.async_set_operation_mode(OperationMode.DIRECT, percent)
        else:
            self.coordinator.direct_percent = percent
            self.async_write_ha_state()
