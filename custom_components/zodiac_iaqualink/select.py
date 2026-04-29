"""Select entity for Boost / Silent mode."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    HEATER_MODE_BOOST,
    HEATER_MODE_MAP,
    HEATER_MODE_REVERSE,
    HEATER_MODE_SILENT,
)
from .coordinator import ZodiacDataUpdateCoordinator
from .entity import ZodiacBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ZodiacDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ZodiacModeSelect(coordinator)])


class ZodiacModeSelect(ZodiacBaseEntity, SelectEntity):
    """Boost / Silent mode selector."""

    _attr_translation_key = "heater_mode"
    _attr_name = "Mode"
    _attr_options = [HEATER_MODE_BOOST, HEATER_MODE_SILENT]

    def __init__(self, coordinator: ZodiacDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.serial}_mode_select"

    @property
    def current_option(self) -> str | None:
        mode = (self.coordinator.data or {}).get("mode")
        return HEATER_MODE_MAP.get(mode)

    async def async_select_option(self, option: str) -> None:
        if option not in HEATER_MODE_REVERSE:
            raise ValueError(f"Unsupported mode: {option}")
        await self.coordinator.async_set_mode(HEATER_MODE_REVERSE[option])
