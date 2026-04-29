"""Config flow for Zodiac iAquaLink Heat Pump."""
from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ZodiacApiClient, ZodiacApiError, ZodiacAuthError
from .const import CONF_EMAIL, CONF_PASSWORD, CONF_SERIAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Placeholders rendered into the user-step description in strings.json so
# the URL is not embedded in the translation string (hassfest rejects raw
# URLs in translations).
_USER_PLACEHOLDERS = {
    "iaqualink_url": "https://iaqualink.net",
    "serial_example": "LB18475932",
}

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_SERIAL): str,
    }
)

STEP_REAUTH_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PASSWORD): str,
    }
)


class ZodiacConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Zodiac iAquaLink Heat Pump."""

    VERSION = 1

    def __init__(self) -> None:
        self._reauth_entry: ConfigEntry | None = None

    async def _async_validate(
        self, email: str, password: str, serial: str
    ) -> tuple[str | None, dict[str, Any]]:
        """Return (error_key, shadow) where error_key is one of {None, 'invalid_auth', 'cannot_connect'}."""
        session = async_get_clientsession(self.hass)
        client = ZodiacApiClient(session, email, password)
        try:
            await client.async_login()
            shadow = await client.async_get_shadow(serial)
        except ZodiacAuthError:
            return "invalid_auth", {}
        except ZodiacApiError as err:
            _LOGGER.warning("Cannot connect to iAquaLink API during config: %s", err)
            return "cannot_connect", {}
        return None, shadow

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

            err, shadow = await self._async_validate(email, password, serial)
            if err is not None:
                errors["base"] = err
            else:
                title = f"Zodiac {shadow.get('deviceId') or serial}"
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
            description_placeholders=_USER_PLACEHOLDERS,
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Triggered when an existing entry's credentials stop working."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._reauth_entry is not None
        errors: dict[str, str] = {}
        existing = self._reauth_entry.data
        if user_input is not None:
            err, _ = await self._async_validate(
                existing[CONF_EMAIL],
                user_input[CONF_PASSWORD],
                existing[CONF_SERIAL],
            )
            if err is not None:
                errors["base"] = err
            else:
                self.hass.config_entries.async_update_entry(
                    self._reauth_entry,
                    data={**existing, CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )
                await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_DATA_SCHEMA,
            description_placeholders={"email": existing[CONF_EMAIL]},
            errors=errors,
        )
