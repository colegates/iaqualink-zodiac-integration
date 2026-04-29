"""DataUpdateCoordinator for the Zodiac iAquaLink heat pump."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ZodiacApiClient, ZodiacApiError, ZodiacAuthError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, EQUIPMENT_KEY

_LOGGER = logging.getLogger(__name__)


def _parse_number(value: Any) -> float | int | None:
    if value is None:
        return None
    try:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return value
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_shadow(shadow: dict[str, Any]) -> dict[str, Any]:
    """Flatten the relevant Z400iQ fields out of the raw shadow response."""
    reported = (shadow or {}).get("state", {}).get("reported", {}) or {}
    equipment = reported.get("equipment", {}) or {}
    hp = equipment.get(EQUIPMENT_KEY, {}) or {}

    sns_1 = hp.get("sns_1") or {}
    sns_2 = hp.get("sns_2") or {}

    raw_status = hp.get("status")
    raw_mode = hp.get("st")
    try:
        status = int(raw_status) if raw_status is not None else None
    except (TypeError, ValueError):
        status = None
    try:
        mode = int(raw_mode) if raw_mode is not None else None
    except (TypeError, ValueError):
        mode = None

    return {
        "device_id": shadow.get("deviceId"),
        "setpoint": _parse_number(hp.get("tsp")),
        "water_temp": _parse_number(sns_1.get("value")),
        "air_temp": _parse_number(sns_2.get("value")),
        "status": status,
        "mode": mode,
        "reason": hp.get("reason"),
        "fan": hp.get("fan"),
        "compressor_load": hp.get("cl"),
        "water_flow": hp.get("wf"),
        "led": hp.get("led"),
        "firmware": hp.get("vr"),
        "serial_number_internal": hp.get("sn"),
        "aws_status": (reported.get("aws") or {}).get("status"),
        "raw": shadow,
    }


class ZodiacDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls the device shadow on a schedule."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: ZodiacApiClient,
        serial: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{serial}",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client
        self.serial = serial

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            shadow = await self.client.async_get_shadow(self.serial)
        except ZodiacAuthError as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except ZodiacApiError as err:
            raise UpdateFailed(str(err)) from err
        return parse_shadow(shadow)

    async def async_set_setpoint(self, setpoint: int) -> None:
        await self.client.async_update_shadow(
            self.serial, {"equipment": {EQUIPMENT_KEY: {"tsp": int(setpoint)}}}
        )
        await self.async_request_refresh()

    async def async_set_mode(self, mode_int: int) -> None:
        await self.client.async_update_shadow(
            self.serial, {"equipment": {EQUIPMENT_KEY: {"st": int(mode_int)}}}
        )
        await self.async_request_refresh()
