"""Constants for the LG Portable AC integration."""

from __future__ import annotations

from enum import StrEnum

DOMAIN = "lg_portable_ac"
CONF_REMOTE_ENTITY_ID = "remote_entity_id"


class ACMode(StrEnum):
    """LG Portable AC operating modes."""

    COOL = "cool"
    ENERGY_SAVER = "energy_saver"
    FAN = "fan"
    DRY = "dry"


class FanSpeed(StrEnum):
    """LG Portable AC fan speeds."""

    LOW = "low"
    MED = "med"
    HI = "hi"


# Temperature range (Fahrenheit)
MIN_TEMP_F: int = 60
MAX_TEMP_F: int = 86

# Temperature range (Celsius)
MIN_TEMP_C: int = 16
MAX_TEMP_C: int = 30

# Preset modes
PRESET_AUTO_CLEAN: str = "auto_clean"
