"""The Zodiac iAquaLink Heat Pump integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ZodiacApiClient, ZodiacApiError, ZodiacAuthError
from .const import CONF_EMAIL, CONF_PASSWORD, CONF_SERIAL, DOMAIN
from .coordinator import ZodiacDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CLIMATE, Platform.SENSOR, Platform.SELECT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Zodiac iAquaLink Heat Pump from a config entry."""
    session = async_get_clientsession(hass)
    client = ZodiacApiClient(
        session=session,
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
    )
    try:
        await client.async_login()
    except ZodiacAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except ZodiacApiError as err:
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = ZodiacDataUpdateCoordinator(hass, client, entry.data[CONF_SERIAL])
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
