"""Coordinator file that handles data updates for Solyx Energy device entities."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    SolyxEnergyApiClient,
    SolyxEnergyAuthError,
    SolyxEnergyDataError,
    SolyxEnergyTokenError,
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

_LOGGER = logging.getLogger(__name__)


@dataclass
class SolyxEnergyData:
    """Snapshot of all Solyx Energy integration values."""

    powerBoiler: float | None
    energyBoiler: float | None
    operatingMode: str | None
    gridPower: float | None
    controlValue: float | None


class SolyxEnergyCoordinator(DataUpdateCoordinator[SolyxEnergyData]):
    """Coordinator that fetches and sends data over HTTPS using the SolyxEnergyApiClient class."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_client: SolyxEnergyApiClient,
        device_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initializes the main coordinator for the Solyx Energy integration."""
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
        """Function to update the device entities, by fetching data using the SolyxEnergyApiClient class."""
        try:
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
