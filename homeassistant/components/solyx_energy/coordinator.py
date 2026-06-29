"""Coordinator file that handles data updates for Solyx Energy device entities"""
from __future__ import annotations

import logging

from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SolyxEnergyApiClient, SolyxEnergyTokenError, SolyxEnergyDataError
from .const import (
    ATTRIBUTE_NOTES,
    DATA_INTERVAL_SECONDS,
    DOMAIN
)
from .util import _parse_attr_value

_LOGGER = logging.getLogger(__name__)

@dataclass
class SolyxEnergyData:
    """Snapshot of all Solyx Energy integration values."""
    notes: str | None

class SolyxEnergyCoordinator(DataUpdateCoordinator[SolyxEnergyData]):
    """Coordinator that fetches and sends data over HTTPS"""

    def __init__(
            self,
            hass: HomeAssistant,
            api_client: SolyxEnergyApiClient,
            device_id: str,
            config_entry: ConfigEntry
    ):
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=DATA_INTERVAL_SECONDS)
        )
        self.api_client = api_client
        self.identifier = device_id


    async def _async_update_data(self) -> None:
        """Function to update the device entities, by fetching data using the SolyxEnergyApiClient class"""
        try:
            nymo_data = await self.api_client.async_get_asset_data(self.identifier)
        except SolyxEnergyTokenError as err:
            raise ConfigEntryAuthFailed from err
        except SolyxEnergyDataError as err:
            raise UpdateFailed(f"API error: {err}") from err

        # _LOGGER.debug(f"Device data: ${nymo_data}")
        return SolyxEnergyData(
            notes=_parse_attr_value(nymo_data, ATTRIBUTE_NOTES)
        )
