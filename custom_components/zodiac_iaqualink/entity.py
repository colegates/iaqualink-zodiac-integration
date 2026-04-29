"""Base entity for the Zodiac iAquaLink integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_MODEL, DOMAIN, MANUFACTURER
from .coordinator import ZodiacDataUpdateCoordinator


class ZodiacBaseEntity(CoordinatorEntity[ZodiacDataUpdateCoordinator]):
    """Common bits for every entity tied to the heat pump."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ZodiacDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._serial = coordinator.serial

    @property
    def device_info(self) -> DeviceInfo:
        data = self.coordinator.data or {}
        return DeviceInfo(
            identifiers={(DOMAIN, self._serial)},
            manufacturer=MANUFACTURER,
            model=DEFAULT_MODEL,
            name=f"Zodiac {self._serial}",
            serial_number=data.get("serial_number_internal") or self._serial,
            sw_version=data.get("firmware"),
        )
