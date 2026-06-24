"""Config flow for the Solyx Energy integration"""
from __future__ import annotations
from homeassistant import config_entries
from .const import DOMAIN


class SolyxEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Example config flow."""