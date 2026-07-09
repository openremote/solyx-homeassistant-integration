"""Config flow for the Solyx Energy integration."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .api import (
    SolyxEnergyApiClient,
    SolyxEnergyAuthError,
    SolyxEnergyDataError,
    SolyxEnergyTokenError,
)
from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_NYMO_DEVICE_ID,
    DOMAIN,
)

# Schema definition for the initial user setup
STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CLIENT_ID): TextSelector(),
        vol.Required(CONF_CLIENT_SECRET): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
        vol.Required(CONF_NYMO_DEVICE_ID): TextSelector(),
    },
)

# Schema definition for the reauthentication flow — only credentials are re-entered;
# the device ID stays bound to the existing entry's unique ID.
# When an incorrect device ID was given, we'd recommend users to reconfigure the device.
STEP_REAUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CLIENT_ID): TextSelector(),
        vol.Required(CONF_CLIENT_SECRET): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
    },
)

class SolyxEnergyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the main config flow for the Solyx Energy integration."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step when setting up the integration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_NYMO_DEVICE_ID])
            self._abort_if_unique_id_configured()

            try:
                await self._validate_input(user_input)
            except SolyxEnergyAuthError:
                errors["base"] = "invalid_auth"
            except (SolyxEnergyTokenError, SolyxEnergyDataError):
                errors["base"] = "data_error"
            else:
                return self.async_create_entry(
                    title=f"Nymo {user_input[CONF_NYMO_DEVICE_ID]}",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )


    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Handle the reauthentication step when users provide incorrect credentials."""
        self._reauth_entry = self._get_reauth_entry()
        return await self.async_step_reauth_confirm()


    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Prompts a dialog that asks the user to re-enter credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            merged_input = {
                CONF_CLIENT_ID: user_input[CONF_CLIENT_ID],
                CONF_CLIENT_SECRET: user_input[CONF_CLIENT_SECRET],
                CONF_NYMO_DEVICE_ID: self._reauth_entry.data[CONF_NYMO_DEVICE_ID],
            }
            try:
                await self._validate_input(merged_input)
            except SolyxEnergyAuthError:
                errors["base"] = "invalid_auth"
            except (SolyxEnergyTokenError, SolyxEnergyDataError):
                errors["base"] = "data_error"
            else:
                return self.async_update_reload_and_abort(
                    self._reauth_entry,
                    data=merged_input,
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_SCHEMA,
            description_placeholders={
                "device_id": self._reauth_entry.data[CONF_NYMO_DEVICE_ID],
            },
            errors=errors,
        )

    async def _validate_input(self, user_input: dict[str, Any]) -> None:
        """Validate user input by testing the connection to the Solyx Cloud."""
        session = async_get_clientsession(self.hass)
        client = SolyxEnergyApiClient(
            session=session,
            client_id=user_input[CONF_CLIENT_ID],
            client_secret=user_input[CONF_CLIENT_SECRET],
        )
        await client.async_test_connection(user_input[CONF_NYMO_DEVICE_ID])
