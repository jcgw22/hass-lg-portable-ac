"""LG PL1215GXR IR protocol encoder and decoder.

Protocol: 72-bit (9-byte) PDM frame, 38 kHz, LSB-first.
See docs/protocol.md for the full specification.

Frame layout:
  B0=ADDR  B1=SWING|CIDX  B2=RSVD  B3=FIDX  B4=RSVD  B5=RSVD  B6=MODE|FAN  B7=FLAGS  B8=CHK
"""

from __future__ import annotations

import base64 as _base64


def _bit_reverse_byte(b: int) -> int:
    """Reverse all 8 bits of a byte.

    Example: 0b00000001 -> 0b10000000 (0x01 -> 0x80)
    """
    return int(f"{b:08b}"[::-1], 2)


def _bit_reverse_nibble(n: int) -> int:
    """Reverse the lower 4 bits of a nibble.

    Example: 0b0001 -> 0b1000 (1 -> 8)
    """
    return int(f"{n & 0x0F:04b}"[::-1], 2)


def checksum(payload: list[int]) -> int:
    """Compute the checksum for bytes B0-B7.

    Formula: rev8( sum( rev8(Bn) for Bn in B0..B7 ) mod 256 )
    """
    wire_sum = sum(_bit_reverse_byte(b) for b in payload[:8]) & 0xFF
    return _bit_reverse_byte(wire_sum)


def encode(
    temp_f: int,
    mode: str = "cool",
    fan: str = "low",
    power_on: bool = False,
    power_off: bool = False,
    auto_swing: bool = False,
    auto_clean: bool = False,
    celsius_display: bool = False,
) -> list[int]:
    """Encode AC state into a 9-byte IR frame.

    Args:
        temp_f: Setpoint in Fahrenheit (60-86).
        mode: Operating mode ("cool", "energy_saver", "fan", "dry").
        fan: Fan speed ("low", "med", "hi").
        power_on: Power-ON command: B1[6]=1, B7[4]=1. Mutually exclusive with power_off.
        power_off: Power-OFF command: B1[6]=0, B7[4]=1. Mutually exclusive with power_on.
        auto_swing: If True, enable louver oscillation (B1[7]=1).
        auto_clean: If True, activate auto-clean cycle (B7[5]=1).
        celsius_display: If True, remote shows Celsius (B7[0]=1).

    Returns:
        List of 9 integers (0x00-0xFF).
    """
    temp_f = max(60, min(86, temp_f))

    # B0: Address byte (always 0xAA)
    b0 = 0xAA

    # B1: Celsius index + auto-swing flag
    #   celsius = round((temp_f - 32) * 5 / 9)
    #   B1 = [swing][1][0][0][rev4(celsius - 16)]
    celsius = round((temp_f - 32) * 5 / 9)
    celsius = max(16, min(30, celsius))
    cidx = _bit_reverse_nibble(celsius - 16)
    # B1[6]=1 when unit is on, B1[6]=0 for power-off command
    b1 = (0x80 if auto_swing else 0x00) | (0x00 if power_off else 0x40) | cidx

    # B2: Reserved (0x00) -- likely timer field, not yet decoded
    b2 = 0x00

    # B3: Fahrenheit index = rev8(temp_f - 59)
    b3 = _bit_reverse_byte(temp_f - 59)

    # B4: Reserved (0x00) -- likely timer hours, not yet decoded
    b4 = 0x00

    # B5: Reserved (0x00)
    b5 = 0x00

    # B6: Mode (bits 7:5) | Fan speed (bits 3:2)
    mode_bits = {"cool": 0x80, "energy_saver": 0x20, "fan": 0xC0, "dry": 0x40}
    fan_bits = {"low": 0x08, "med": 0x04, "hi": 0x0C}
    b6 = mode_bits.get(mode, 0x80) | fan_bits.get(fan, 0x08)

    # B7: Flags
    b7 = 0x00
    if celsius_display:
        b7 |= 0x01  # bit 0
    if power_on or power_off:  # power_action flag: set for both ON and OFF transitions
        b7 |= 0x10  # bit 4
    if auto_clean:
        b7 |= 0x20  # bit 5

    # B8: Checksum
    payload = [b0, b1, b2, b3, b4, b5, b6, b7]
    b8 = checksum(payload)

    return [b0, b1, b2, b3, b4, b5, b6, b7, b8]


def decode(frame: list[int]) -> dict:
    """Decode a 9-byte IR frame into human-readable fields.

    Args:
        frame: List of 9 integers.

    Returns:
        Dictionary with decoded field values.

    Raises:
        ValueError: If frame length is wrong or checksum fails.
    """
    if len(frame) != 9:
        raise ValueError(f"Expected 9 bytes, got {len(frame)}")

    if frame[0] != 0xAA:
        raise ValueError(f"Expected B0=0xAA, got 0x{frame[0]:02X}")

    expected_chk = checksum(frame[:8])
    if frame[8] != expected_chk:
        raise ValueError(
            f"Checksum mismatch: B8=0x{frame[8]:02X}, "
            f"expected 0x{expected_chk:02X}"
        )

    # B1: swing + power-state + celsius index
    auto_swing = bool(frame[1] & 0x80)
    unit_on = bool(frame[1] & 0x40)   # B1[6]: 1=on, 0=off (power-off command)
    cidx = _bit_reverse_nibble(frame[1] & 0x0F)
    celsius = cidx + 16

    # B3: fahrenheit index
    temp_f = _bit_reverse_byte(frame[3]) + 59

    # B6: mode + fan
    mode_val = (frame[6] >> 5) & 0x07
    mode_map = {0b100: "cool", 0b001: "energy_saver", 0b110: "fan", 0b010: "dry"}
    mode = mode_map.get(mode_val, f"unknown(0b{mode_val:03b})")

    fan_val = (frame[6] >> 2) & 0x03
    fan_map = {0b10: "low", 0b01: "med", 0b11: "hi", 0b00: "auto"}
    fan = fan_map.get(fan_val, f"unknown(0b{fan_val:02b})")

    # B7: flags
    celsius_display = bool(frame[7] & 0x01)
    power_action = bool(frame[7] & 0x10)       # set for both on and off transitions
    power_on = power_action and unit_on        # True only for power-ON command
    power_off = power_action and not unit_on   # True only for power-OFF command
    auto_clean = bool(frame[7] & 0x20)

    return {
        "temp_f": temp_f,
        "temp_c": celsius,
        "mode": mode,
        "fan": fan,
        "auto_swing": auto_swing,
        "unit_on": unit_on,
        "power_action": power_action,
        "power_on": power_on,
        "power_off": power_off,
        "auto_clean": auto_clean,
        "celsius_display": celsius_display,
        "raw": [f"0x{b:02X}" for b in frame],
    }


def decode_broadlink(b64_string: str) -> dict:
    """Decode a Broadlink RM4 Pro base64 packet into AC state.

    Wire format:
      Bytes 0-3: header (0x26 0x00 + 2-byte length)
      Bytes 4-5: preamble (0x00 0x01)
      Bytes 6-7: leader mark + leader space (in 26.3 µs ticks)
      Bytes 8+:  N pairs of (mark_ticks, space_ticks), one per data bit
      Last:      trailing mark byte followed by 0x00 sentinel

    Bits are decoded from space duration (>40 ticks → 1, else 0) and
    reassembled LSB-first into bytes before calling decode().

    Args:
        b64_string: Base64-encoded Broadlink RM4 packet.

    Returns:
        Same dict as decode().

    Raises:
        ValueError: If the embedded frame has a bad checksum.
    """
    raw = _base64.b64decode(b64_string)
    data = list(raw[8:])  # skip 4-byte header + 2-byte preamble + 2-byte leader

    bits: list[int] = []
    i = 0
    while i + 1 < len(data):
        space_ticks = data[i + 1]
        if space_ticks == 0:  # end sentinel
            break
        bits.append(1 if space_ticks > 40 else 0)
        i += 2

    logical_frame: list[int] = []
    for byte_idx in range(len(bits) // 8):
        byte_val = 0
        for bit_pos in range(8):
            byte_val |= bits[byte_idx * 8 + bit_pos] << bit_pos
        logical_frame.append(byte_val)

    return decode(logical_frame[:9])
