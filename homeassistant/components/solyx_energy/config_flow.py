"""Config flow for the Solyx Energy integration"""
from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SolyxEnergyApiClient, SolyxEnergyTokenError, SolyxEnergyDataError
from .const import (
    DOMAIN,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_NYMO_DEVICE_ID
)

# Schema definition for the required user inputs
STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CLIENT_ID): str,
        vol.Required(CONF_CLIENT_SECRET): str,
        vol.Required(CONF_NYMO_DEVICE_ID): str,
    }
)

class SolyxEnergyConfigFlow(ConfigFlow, domain=DOMAIN):

    VERSION = 1

    async def async_step_user(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial steps when setting up the integration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_CLIENT_ID])
            self._abort_if_unique_id_configured()

            try:
                await self._validate_input(user_input)
            except SolyxEnergyTokenError:
                errors["base"] = "invalid_auth"
            except SolyxEnergyDataError:
                errors["base"] = "data_error"
            else:
                return self.async_create_entry(
                    title="Nymo device",
                    data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors
        )

    async def _validate_input(self, user_input: dict[str, Any] | None) -> None:
        """Function that validates the user input, such as testing the connection to the Solyx Cloud environment"""
        session = async_get_clientsession(self.hass)
        client = SolyxEnergyApiClient(
            session=session,
            client_id=user_input[CONF_CLIENT_ID],
            client_secret=user_input[CONF_CLIENT_SECRET]
        )
        await client.async_test_connection(user_input[CONF_NYMO_DEVICE_ID])
