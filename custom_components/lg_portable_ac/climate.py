"""Climate entity for LG Portable AC."""

from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.climate.const import (
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    PRESET_NONE,
    SWING_OFF,
    SWING_ON,
)
from homeassistant.components.infrared import InfraredEmitterConsumerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_INFRARED_ENTITY_ID, DOMAIN, MAX_TEMP_F, MIN_TEMP_F, PRESET_AUTO_CLEAN
from .ir_command import LGPortableACCommand
from .protocol import encode

# Serialize IR sends -- don't blast commands simultaneously
PARALLEL_UPDATES = 1

# Map HA constants to protocol strings
_MODE_TO_PROTOCOL: dict[HVACMode, str] = {
    HVACMode.COOL: "cool",
    HVACMode.DRY: "dry",
    HVACMode.FAN_ONLY: "fan",
    HVACMode.AUTO: "energy_saver",
}

_FAN_TO_PROTOCOL: dict[str, str] = {
    FAN_LOW: "low",
    FAN_MEDIUM: "med",
    FAN_HIGH: "hi",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up climate entity from a config entry."""
    ir_entity_id = entry.data[CONF_INFRARED_ENTITY_ID]
    async_add_entities([LGPortableACClimate(entry, ir_entity_id)])


class LGPortableACClimate(InfraredEmitterConsumerEntity, ClimateEntity):
    """Climate entity for LG PL1215GXR portable AC via IR.

    This is an assumed_state entity because IR is one-way --
    we cannot read the AC's actual state back.
    """

    _attr_has_entity_name = True
    _attr_name = None
    _attr_assumed_state = True
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT

    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.PRESET_MODE
    )

    _attr_min_temp = MIN_TEMP_F
    _attr_max_temp = MAX_TEMP_F
    _attr_target_temperature_step = 1.0

    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.COOL,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
        HVACMode.AUTO,
    ]
    _attr_fan_modes = [FAN_LOW, FAN_MEDIUM, FAN_HIGH]
    _attr_swing_modes = [SWING_ON, SWING_OFF]
    _attr_preset_modes = [PRESET_NONE, PRESET_AUTO_CLEAN]

    def __init__(
        self,
        entry: ConfigEntry,
        infrared_entity_id: str,
    ) -> None:
        """Initialize the climate entity."""
        self._infrared_emitter_entity_id = infrared_entity_id
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_climate"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="LG Portable AC",
            manufacturer="LG",
            model="PL1215GXR",
        )

        # Default assumed state
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_target_temperature = 68.0
        self._attr_fan_mode = FAN_LOW
        self._attr_swing_mode = SWING_OFF
        self._attr_preset_mode = PRESET_NONE

        _LOGGER.debug("LGPortableACClimate initialized, emitter=%s", infrared_entity_id)

    async def async_added_to_hass(self) -> None:
        """Log availability after entity is added."""
        await super().async_added_to_hass()
        _LOGGER.debug(
            "Entity added to hass, available=%s, emitter=%s",
            self.available,
            self._infrared_emitter_entity_id,
        )

    async def _send_state(
        self, power_on: bool = False, power_off: bool = False
    ) -> None:
        """Encode the current state and send it via IR."""
        mode = _MODE_TO_PROTOCOL.get(self._attr_hvac_mode, "cool")
        fan = _FAN_TO_PROTOCOL.get(self._attr_fan_mode, "low")

        _LOGGER.debug(
            "Sending IR: emitter=%s mode=%s fan=%s temp=%s power_on=%s power_off=%s",
            self._infrared_emitter_entity_id,
            mode, fan,
            int(self._attr_target_temperature),
            power_on, power_off,
        )

        frame = encode(
            temp_f=int(self._attr_target_temperature),
            mode=mode,
            fan=fan,
            power_on=power_on,
            power_off=power_off,
            auto_swing=(self._attr_swing_mode == SWING_ON),
            auto_clean=(self._attr_preset_mode == PRESET_AUTO_CLEAN),
        )

        _LOGGER.debug("IR frame: %s", [f"0x{b:02X}" for b in frame])

        command = LGPortableACCommand(frame)
        try:
            await self._send_command(command)
            _LOGGER.debug("IR command sent successfully")
        except Exception:
            _LOGGER.exception("Failed to send IR command to %s", self._infrared_emitter_entity_id)
            raise

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC operation mode."""
        _LOGGER.debug("async_set_hvac_mode called: %s (was %s)", hvac_mode, self._attr_hvac_mode)
        if hvac_mode == HVACMode.OFF:
            await self._send_state(power_off=True)
            self._attr_hvac_mode = HVACMode.OFF
            self.async_write_ha_state()
            return

        was_off = self._attr_hvac_mode == HVACMode.OFF
        self._attr_hvac_mode = hvac_mode
        await self._send_state(power_on=was_off)
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        _LOGGER.debug("async_set_temperature called: %s", kwargs)
        if (temp := kwargs.get("temperature")) is not None:
            self._attr_target_temperature = float(temp)
            if self._attr_hvac_mode != HVACMode.OFF:
                await self._send_state()
            self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan speed."""
        _LOGGER.debug("async_set_fan_mode called: %s", fan_mode)
        self._attr_fan_mode = fan_mode
        if self._attr_hvac_mode != HVACMode.OFF:
            await self._send_state()
        self.async_write_ha_state()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set swing (louver oscillation) mode."""
        _LOGGER.debug("async_set_swing_mode called: %s", swing_mode)
        self._attr_swing_mode = swing_mode
        if self._attr_hvac_mode != HVACMode.OFF:
            await self._send_state()
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode (none or auto_clean)."""
        _LOGGER.debug("async_set_preset_mode called: %s", preset_mode)
        self._attr_preset_mode = preset_mode
        if self._attr_hvac_mode != HVACMode.OFF:
            await self._send_state()
        self.async_write_ha_state()
