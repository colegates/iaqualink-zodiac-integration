"""Climate entity exposing the Zodiac heat pump as a thermostat."""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MAX_TEMP_C, MIN_TEMP_C
from .coordinator import ZodiacDataUpdateCoordinator
from .entity import ZodiacBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ZodiacDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ZodiacHeatPumpClimate(coordinator)])


class ZodiacHeatPumpClimate(ZodiacBaseEntity, ClimateEntity):
    """A thermostat-style entity for the heat pump."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
    )
    _attr_min_temp = MIN_TEMP_C
    _attr_max_temp = MAX_TEMP_C
    _attr_target_temperature_step = 1
    _attr_translation_key = "heat_pump"
    _attr_name = None  # use device name

    def __init__(self, coordinator: ZodiacDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.serial}_climate"

    @property
    def current_temperature(self) -> float | None:
        return (self.coordinator.data or {}).get("water_temp")

    @property
    def target_temperature(self) -> float | None:
        return (self.coordinator.data or {}).get("setpoint")

    @property
    def hvac_mode(self) -> HVACMode | None:
        status = (self.coordinator.data or {}).get("status")
        # status 0 = off; 1 = at-target buffer; 2 = actively heating
        if status == 0:
            return HVACMode.OFF
        if status in (1, 2):
            return HVACMode.HEAT
        return None

    @property
    def hvac_action(self) -> HVACAction | None:
        status = (self.coordinator.data or {}).get("status")
        if status == 0:
            return HVACAction.OFF
        if status == 1:
            return HVACAction.IDLE
        if status == 2:
            return HVACAction.HEATING
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return {
            "air_temperature": data.get("air_temp"),
            "reason_code": data.get("reason"),
            "status_code": data.get("status"),
            "mode_code": data.get("mode"),
            "fan": data.get("fan"),
            "compressor_load": data.get("compressor_load"),
            "water_flow": data.get("water_flow"),
        }

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        clamped = max(MIN_TEMP_C, min(MAX_TEMP_C, int(round(float(temp)))))
        await self.coordinator.async_set_setpoint(clamped)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        # The Z400iQ shadow doesn't expose a clean "off" toggle separate from the wall HMI;
        # writing tsp is the only well-understood control. We surface HEAT/OFF read-only
        # via status, but reject mode writes for now to avoid sending unsupported commands.
        raise NotImplementedError("Use the iAquaLink app or the heater's HMI to power on/off")
