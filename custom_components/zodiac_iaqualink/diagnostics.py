"""Diagnostics for the Zodiac iAquaLink integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_EMAIL, CONF_PASSWORD, CONF_SERIAL, DOMAIN
from .coordinator import ZodiacDataUpdateCoordinator

# Anything that could identify the user / their device gets redacted before
# the diagnostics file is offered for download.
TO_REDACT = {
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_SERIAL,
    "deviceId",
    "device_id",
    "session_id",
    "sn",
    "serial_number_internal",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    coordinator: ZodiacDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
            "version": entry.version,
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval_seconds": (
                coordinator.update_interval.total_seconds()
                if coordinator.update_interval
                else None
            ),
            "parsed": async_redact_data(coordinator.data or {}, TO_REDACT),
        },
    }
