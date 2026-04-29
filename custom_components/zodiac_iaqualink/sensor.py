"""Sensor entities for the Zodiac heat pump."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, HEATER_MODE_MAP, HEATER_STATUS_MAP
from .coordinator import ZodiacDataUpdateCoordinator
from .entity import ZodiacBaseEntity


@dataclass(frozen=True, kw_only=True)
class ZodiacSensorDescription(SensorEntityDescription):
    """Sensor description plus a value extractor against coordinator.data."""

    value_fn: Callable[[dict[str, Any]], Any]


SENSORS: tuple[ZodiacSensorDescription, ...] = (
    ZodiacSensorDescription(
        key="water_temperature",
        translation_key="water_temperature",
        name="Water temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.get("water_temp"),
    ),
    ZodiacSensorDescription(
        key="air_temperature",
        translation_key="air_temperature",
        name="Air temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.get("air_temp"),
    ),
    ZodiacSensorDescription(
        key="setpoint",
        translation_key="setpoint",
        name="Setpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.get("setpoint"),
    ),
    ZodiacSensorDescription(
        key="heater_status",
        translation_key="heater_status",
        name="Heater status",
        device_class=SensorDeviceClass.ENUM,
        options=["off", "temp_buffer", "heating", "unknown"],
        value_fn=lambda d: HEATER_STATUS_MAP.get(d.get("status"), "unknown"),
    ),
    ZodiacSensorDescription(
        key="heater_mode",
        translation_key="heater_mode",
        name="Heater mode",
        device_class=SensorDeviceClass.ENUM,
        options=["boost", "silent", "unknown"],
        value_fn=lambda d: HEATER_MODE_MAP.get(d.get("mode"), "unknown"),
    ),
    ZodiacSensorDescription(
        key="reason",
        translation_key="reason",
        name="Reason code",
        value_fn=lambda d: d.get("reason"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ZodiacDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(ZodiacSensor(coordinator, desc) for desc in SENSORS)


class ZodiacSensor(ZodiacBaseEntity, SensorEntity):
    """Generic sensor backed by an extractor function."""

    entity_description: ZodiacSensorDescription

    def __init__(
        self,
        coordinator: ZodiacDataUpdateCoordinator,
        description: ZodiacSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.serial}_{description.key}"

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data or {})
