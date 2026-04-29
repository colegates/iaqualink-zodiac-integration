"""Config flow for Zodiac iAquaLink Heat Pump."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ZodiacApiClient, ZodiacApiError, ZodiacAuthError
from .const import CONF_EMAIL, CONF_PASSWORD, CONF_SERIAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_SERIAL): str,
    }
)


class ZodiacConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Zodiac iAquaLink Heat Pump."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            email = user_input[CONF_EMAIL].strip()
            password = user_input[CONF_PASSWORD]
            serial = user_input[CONF_SERIAL].strip()

            await self.async_set_unique_id(serial)
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            client = ZodiacApiClient(session, email, password)
            try:
                await client.async_login()
                # Validate the serial actually returns a shadow.
                shadow = await client.async_get_shadow(serial)
            except ZodiacAuthError:
                errors["base"] = "invalid_auth"
            except ZodiacApiError as err:
                _LOGGER.warning("Cannot connect to Zodiac API: %s", err)
                errors["base"] = "cannot_connect"
            else:
                title = f"Zodiac {serial}"
                if shadow.get("deviceId"):
                    title = f"Zodiac {shadow['deviceId']}"
                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_EMAIL: email,
                        CONF_PASSWORD: password,
                        CONF_SERIAL: serial,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
