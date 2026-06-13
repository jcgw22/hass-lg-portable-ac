"""Climate entity for LG Portable AC."""

from __future__ import annotations

import base64
import logging
from typing import Any

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
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import CONF_REMOTE_ENTITY_ID, DOMAIN, MAX_TEMP_F, MIN_TEMP_F, PRESET_AUTO_CLEAN
from .ir_command import LGPortableACCommand
from .protocol import encode

_LOGGER = logging.getLogger(__name__)

# Serialize IR sends -- don't blast commands simultaneously
PARALLEL_UPDATES = 1

# RM4 Pro captures use 26.3 µs ticks (1/38 kHz carrier period).
# We build the Broadlink packet ourselves to avoid the pulses_to_data
# 32.84 µs tick mismatch in the infrared entity.
_BROADLINK_TICK_US = 26.3

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


def _build_broadlink_packet(timings: list[int]) -> bytes:
    """Build a Broadlink RM4 Pro IR packet from signed µs timings.

    Uses 26.3 µs ticks to match the RM4 Pro's physical tick rate, producing
    a packet in the same format as learned codes replayed by the remote entity.
    """
    data = bytearray()
    for us in timings:
        ticks = round(abs(us) / _BROADLINK_TICK_US)
        if ticks > 255:
            data += bytes([0x00, ticks >> 8, ticks & 0xFF])
        else:
            data += bytes([ticks & 0xFF])
    data += bytes([0x00])  # end-of-signal sentinel

    preamble = bytes([0x00, 0x01])
    footer = bytes([0x0D, 0x05])
    length = len(preamble) + len(data) + len(footer)
    header = bytes([0x26, 0x00, length & 0xFF, (length >> 8) & 0xFF])
    return header + preamble + bytes(data) + footer


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up climate entity from a config entry."""
    remote_entity_id = entry.data[CONF_REMOTE_ENTITY_ID]
    async_add_entities([LGPortableACClimate(entry.entry_id, remote_entity_id)])


class LGPortableACClimate(RestoreEntity, ClimateEntity):
    """Climate entity for LG PL1215GXR portable AC via IR.

    Sends commands by building a raw Broadlink packet and calling
    remote.send_command with a b64: code, bypassing the infrared
    entity's pulses_to_data tick rate mismatch.
    """

    _attr_has_entity_name = True
    _attr_name = None
    _attr_assumed_state = True
    _attr_should_poll = False
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT

    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
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

    def __init__(self, entry_id: str, remote_entity_id: str) -> None:
        """Initialize the climate entity."""
        self._remote_entity_id = remote_entity_id
        self._attr_unique_id = f"{entry_id}_climate"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="LG Portable AC RM4 Pro",
            manufacturer="LG",
            model="PL1215GXR",
        )

        # Default assumed state
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_target_temperature = 68.0
        self._attr_fan_mode = FAN_LOW
        self._attr_swing_mode = SWING_OFF
        self._attr_preset_mode = PRESET_NONE

    async def async_added_to_hass(self) -> None:
        """Restore last known state on startup."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is None:
            return
        if last_state.state in [m.value for m in self._attr_hvac_modes]:
            self._attr_hvac_mode = HVACMode(last_state.state)
        attrs = last_state.attributes
        if (temp := attrs.get("temperature")) is not None:
            self._attr_target_temperature = float(temp)
        if (fan := attrs.get("fan_mode")) is not None:
            self._attr_fan_mode = fan
        if (swing := attrs.get("swing_mode")) is not None:
            self._attr_swing_mode = swing
        if (preset := attrs.get("preset_mode")) is not None:
            self._attr_preset_mode = preset

    async def _send_ir(self, power_on: bool = False, power_off: bool = False) -> None:
        """Encode state, build Broadlink packet, and send via remote.send_command."""
        mode = _MODE_TO_PROTOCOL.get(self._attr_hvac_mode, "cool")
        fan = _FAN_TO_PROTOCOL.get(self._attr_fan_mode, "low")

        _LOGGER.debug(
            "Sending IR: remote=%s mode=%s fan=%s temp=%s power_on=%s power_off=%s",
            self._remote_entity_id, mode, fan,
            int(self._attr_target_temperature), power_on, power_off,
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

        timings = LGPortableACCommand(frame).get_raw_timings()
        packet = _build_broadlink_packet(timings)
        raw_code = "b64:" + base64.b64encode(packet).decode()

        await self.hass.services.async_call(
            "remote",
            "send_command",
            {"command": [raw_code]},
            blocking=True,
            target={"entity_id": self._remote_entity_id},
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC operation mode."""
        if hvac_mode == HVACMode.OFF:
            await self._send_ir(power_off=True)
            self._attr_hvac_mode = HVACMode.OFF
            self.async_write_ha_state()
            return

        was_off = self._attr_hvac_mode == HVACMode.OFF
        self._attr_hvac_mode = hvac_mode
        await self._send_ir(power_on=was_off)
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        if (temp := kwargs.get("temperature")) is not None:
            self._attr_target_temperature = float(temp)
            if self._attr_hvac_mode != HVACMode.OFF:
                await self._send_ir()
            self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan speed."""
        self._attr_fan_mode = fan_mode
        if self._attr_hvac_mode != HVACMode.OFF:
            await self._send_ir()
        self.async_write_ha_state()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set swing mode."""
        self._attr_swing_mode = swing_mode
        if self._attr_hvac_mode != HVACMode.OFF:
            await self._send_ir()
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode."""
        self._attr_preset_mode = preset_mode
        if self._attr_hvac_mode != HVACMode.OFF:
            await self._send_ir()
        self.async_write_ha_state()
