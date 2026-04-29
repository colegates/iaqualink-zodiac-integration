"""Constants for the Zodiac iAquaLink Heat Pump integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "zodiac_iaqualink"
MANUFACTURER = "Zodiac"
DEFAULT_MODEL = "Z400iQ Heat Pump"

# API
API_KEY = "EOOEMOW4YR6QNB11"
LOGIN_URL = "https://prod.zodiac-io.com/users/v1/login"
SHADOW_URL_TEMPLATE = "https://prod.zodiac-io.com/devices/v1/{serial}/shadow"
USER_AGENT = "okhttp/3.12.0"

# Polling — keep conservative; the API throttles on excessive requests.
DEFAULT_SCAN_INTERVAL = timedelta(seconds=120)

# Config entry keys
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_SERIAL = "serial"

# Heat-pump shadow keys
EQUIPMENT_KEY = "hp_0"

# Heater status (from shadow `equipment.hp_0.status`)
HEATER_STATUS_MAP = {
    0: "off",
    1: "temp_buffer",
    2: "heating",
}

# Heater mode (from shadow `equipment.hp_0.st`)
HEATER_MODE_BOOST = "boost"
HEATER_MODE_SILENT = "silent"
HEATER_MODE_MAP = {
    0: HEATER_MODE_BOOST,
    1: HEATER_MODE_SILENT,
}
HEATER_MODE_REVERSE = {v: k for k, v in HEATER_MODE_MAP.items()}

# Setpoint bounds (Zodiac Z400iQ supports 8 - 32 °C)
MIN_TEMP_C = 8
MAX_TEMP_C = 32
