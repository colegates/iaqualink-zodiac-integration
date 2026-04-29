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
        # power_state (equipment.hp_0.state) is the authoritative on/off field;
        # status reflects the operational result (off / buffer / heating).
        power = (self.coordinator.data or {}).get("power_state")
        if power == 0:
            return HVACMode.OFF
        if power == 1:
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
            "power_state": data.get("power_state"),
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
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.async_set_power(False)
        elif hvac_mode == HVACMode.HEAT:
            await self.coordinator.async_set_power(True)
        else:
            raise ValueError(f"Unsupported HVAC mode: {hvac_mode}")

    async def async_turn_on(self) -> None:
        await self.coordinator.async_set_power(True)

    async def async_turn_off(self) -> None:
        await self.coordinator.async_set_power(False)
