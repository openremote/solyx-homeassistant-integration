"""Solyx Energy integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SolyxEnergyApiClient
from .coordinator import SolyxEnergyCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

type SolyxEnergyConfigEntry = ConfigEntry[SolyxEnergyCoordinator]

async def async_setup_entry(hass: HomeAssistant, entry: SolyxEnergyConfigEntry) -> bool:
    """Set up Solyx Energy device from a config entry."""
    session = async_get_clientsession(hass)
    apiClient = SolyxEnergyApiClient()

    return True

async def async_unload_entry(hass: HomeAssistant, entry: SolyxEnergyConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        return True

    return False


