"""Coordinator file that handles data updates for Solyx Energy device entities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import TYPE_CHECKING

from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    SolyxEnergyApiClient,
    SolyxEnergyAuthError,
    SolyxEnergyDataError,
    SolyxEnergyTokenError,
    SolyxEnergyWriteError,
)
from .const import (
    ATTRIBUTE_CONTROL_VALUE,
    ATTRIBUTE_ENERGY_BOILER,
    ATTRIBUTE_GRID_POWER,
    ATTRIBUTE_OPERATING_MODE,
    ATTRIBUTE_POWER_BOILER,
    DATA_INTERVAL_SECONDS,
    DOMAIN,
)
from .util import parse_attr_value, parse_float

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SolyxEnergyData:
    """Hold a snapshot of all Solyx Energy integration values, using the internal Solyx platform name."""

    powerBoiler: float | None     # noqa: N815
    energyBoiler: float | None    # noqa: N815
    operatingMode: str | None          # noqa: N815
    gridPower: float | None       # noqa: N815
    controlValue: float | None    # noqa: N815


class SolyxEnergyCoordinator(DataUpdateCoordinator[SolyxEnergyData]):
    """Coordinator that fetches and sends data over HTTPS using the SolyxEnergyApiClient class."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_client: SolyxEnergyApiClient,
        device_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the main coordinator for the Solyx Energy integration."""
        super().__init__(
            hass,
            logger=_LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=DATA_INTERVAL_SECONDS),
        )
        self.api_client = api_client
        self.device_id = device_id

    async def _async_update_data(self) -> SolyxEnergyData:
        """Fetch data with the SolyxEnergyApiClient class and update the device entities accordingly."""
        try:
            _LOGGER.debug("Retrieving data from Solyx Energy API...")
            nymo_data = await self.api_client.async_get_asset_data(self.device_id)
        except SolyxEnergyAuthError as err:
            raise ConfigEntryAuthFailed from err
        except (SolyxEnergyTokenError, SolyxEnergyDataError) as err:
            raise UpdateFailed(f"API error: {err}") from err

        return SolyxEnergyData(
            powerBoiler=parse_float(nymo_data, ATTRIBUTE_POWER_BOILER),
            energyBoiler=parse_float(nymo_data, ATTRIBUTE_ENERGY_BOILER),
            operatingMode=parse_attr_value(nymo_data, ATTRIBUTE_OPERATING_MODE),
            gridPower=parse_float(nymo_data, ATTRIBUTE_GRID_POWER),
            controlValue=parse_float(nymo_data, ATTRIBUTE_CONTROL_VALUE),
        )

    async def async_set_attribute(self, attribute_name: str, value: object) -> None:
        """Push data from device entities to the Solyx cloud platform with the SolyxEnergyApiClient class."""
        try:
            _LOGGER.debug(f"Updating entity {attribute_name} in the Solyx cloud platform to {value}...")
            await self.api_client.async_set_asset_attribute(self.device_id, attribute_name, value)
        except SolyxEnergyAuthError as err:
            raise ConfigEntryAuthFailed from err
        except (SolyxEnergyTokenError, SolyxEnergyWriteError) as err:
            raise HomeAssistantError(f"API error: {err}") from err
