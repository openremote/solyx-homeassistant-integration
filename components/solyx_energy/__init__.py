"""Solyx Nymo integration."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

DOMAIN = "solyx_energy"

def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up a skeleton component"""
    hass.states.set("solyx_energy.Hello_World", "Works!")

    return True

