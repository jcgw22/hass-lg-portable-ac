"""Unit tests for the LG Portable AC IR protocol encoder/decoder."""

import pytest

from custom_components.lg_portable_ac.protocol import (
    _bit_reverse_byte,
    _bit_reverse_nibble,
    checksum,
    decode,
    decode_broadlink,
    encode,
)

# ---------------------------------------------------------------
# Verified captures from Broadlink RM4 Pro
# Each tuple: (name, [B0, B1, B2, B3, B4, B5, B6, B7, B8])
# ---------------------------------------------------------------
VERIFIED_CAPTURES = [
    ("cool_60",
     [0xAA, 0x40, 0x00, 0x80, 0x00, 0x00, 0x88, 0x00, 0x96]),
    ("cool_68",
     [0xAA, 0x42, 0x00, 0x90, 0x00, 0x00, 0x88, 0x00, 0x8D]),
    ("cool_75",
     [0xAA, 0x41, 0x00, 0x08, 0x00, 0x00, 0x88, 0x00, 0x1F]),
    ("cool_80",
     [0xAA, 0x4D, 0x00, 0xA8, 0x00, 0x00, 0x88, 0x00, 0xB4]),
    ("on_68",
     [0xAA, 0x42, 0x00, 0x90, 0x00, 0x00, 0x88, 0x10, 0x9D]),
    ("energy_saver_68",
     [0xAA, 0x42, 0x00, 0x90, 0x00, 0x00, 0x28, 0x00, 0x2D]),
    ("fan_80",
     [0xAA, 0x4D, 0x00, 0xA8, 0x00, 0x00, 0xC8, 0x00, 0xF4]),
    ("cool_c_19_fanlow",
     [0xAA, 0x4C, 0x00, 0xE0, 0x00, 0x00, 0x88, 0x01, 0xF8]),
    ("cool_c_19_fanmed",
     [0xAA, 0x4C, 0x00, 0xE0, 0x00, 0x00, 0x84, 0x01, 0xF4]),
    ("cool_c_19_fanhi",
     [0xAA, 0x4C, 0x00, 0xE0, 0x00, 0x00, 0x8C, 0x01, 0xFC]),
    ("cool_c_19_fanhi_autocleanOn",
     [0xAA, 0x4C, 0x00, 0xE0, 0x00, 0x00, 0x8C, 0x21, 0xC2]),
    ("cool_c_19_fanhi_autocleanOff",
     [0xAA, 0x4C, 0x00, 0xE0, 0x00, 0x00, 0x8C, 0x01, 0xFC]),
    ("cool_c_19_fanhi_autoSwingOn",
     [0xAA, 0xCC, 0x00, 0xE0, 0x00, 0x00, 0x8C, 0x01, 0x02]),
    ("cool_c_19_fanhi_autoSwingOff",
     [0xAA, 0x4C, 0x00, 0xE0, 0x00, 0x00, 0x8C, 0x01, 0xFC]),
    ("cool_f_66_fanhi",
     [0xAA, 0x4C, 0x00, 0xE0, 0x00, 0x00, 0x8C, 0x00, 0xFD]),
    # power_off frame: B1[6]=0 (unit off), B7[4]=1 (power_action)
    # Computed: encode(68, 'cool', 'low', power_off=True)
    ("power_off_68_cool_low",
     [0xAA, 0x02, 0x00, 0x90, 0x00, 0x00, 0x88, 0x10, 0xED]),
    # dry mode: B6[7:5]=010=0x40
    # Computed: encode(68, 'dry', 'low')
    ("dry_68_fanlow",
     [0xAA, 0x42, 0x00, 0x90, 0x00, 0x00, 0x48, 0x00, 0x4D]),
]


class TestBitReversal:
    """Test bit-reversal helper functions."""

    def test_reverse_byte_0x01(self):
        assert _bit_reverse_byte(0x01) == 0x80

    def test_reverse_byte_0x80(self):
        assert _bit_reverse_byte(0x80) == 0x01

    def test_reverse_byte_0xAA(self):
        assert _bit_reverse_byte(0xAA) == 0x55

    def test_reverse_byte_round_trip(self):
        for i in range(256):
            assert _bit_reverse_byte(_bit_reverse_byte(i)) == i

    def test_reverse_nibble_0x1(self):
        assert _bit_reverse_nibble(0x1) == 0x8

    def test_reverse_nibble_round_trip(self):
        for i in range(16):
            assert _bit_reverse_nibble(_bit_reverse_nibble(i)) == i


class TestChecksum:
    """Test checksum computation against verified captures."""

    @pytest.mark.parametrize("name,frame", VERIFIED_CAPTURES)
    def test_checksum_matches_capture(self, name, frame):
        computed = checksum(frame[:8])
        assert computed == frame[8], (
            f"{name}: checksum 0x{computed:02X} != expected 0x{frame[8]:02X}"
        )


class TestDecode:
    """Test frame decoding against verified captures."""

    @pytest.mark.parametrize("name,frame", VERIFIED_CAPTURES)
    def test_decode_does_not_raise(self, name, frame):
        result = decode(frame)
        assert result["temp_f"] >= 60
        assert result["temp_f"] <= 86


class TestEncode:
    """Test encoding and round-trip consistency."""

    def test_encode_cool_68_fanlow(self):
        frame = encode(temp_f=68, mode="cool", fan="low")
        assert frame == [0xAA, 0x42, 0x00, 0x90, 0x00, 0x00, 0x88, 0x00, 0x8D]

    def test_encode_cool_60(self):
        frame = encode(temp_f=60, mode="cool", fan="low")
        assert frame == [0xAA, 0x40, 0x00, 0x80, 0x00, 0x00, 0x88, 0x00, 0x96]

    def test_encode_power_on_68(self):
        frame = encode(temp_f=68, mode="cool", fan="low", power_on=True)
        assert frame == [0xAA, 0x42, 0x00, 0x90, 0x00, 0x00, 0x88, 0x10, 0x9D]

    def test_encode_energy_saver_68(self):
        frame = encode(temp_f=68, mode="energy_saver", fan="low")
        assert frame == [0xAA, 0x42, 0x00, 0x90, 0x00, 0x00, 0x28, 0x00, 0x2D]

    def test_encode_fan_80(self):
        frame = encode(temp_f=80, mode="fan", fan="low")
        assert frame == [0xAA, 0x4D, 0x00, 0xA8, 0x00, 0x00, 0xC8, 0x00, 0xF4]

    def test_encode_swing_on(self):
        frame = encode(
            temp_f=66, mode="cool", fan="hi",
            auto_swing=True, celsius_display=True,
        )
        assert frame == [0xAA, 0xCC, 0x00, 0xE0, 0x00, 0x00, 0x8C, 0x01, 0x02]

    def test_encode_auto_clean_on(self):
        frame = encode(
            temp_f=66, mode="cool", fan="hi",
            auto_clean=True, celsius_display=True,
        )
        assert frame == [0xAA, 0x4C, 0x00, 0xE0, 0x00, 0x00, 0x8C, 0x21, 0xC2]

    def test_power_off_clears_b1_bit6(self):
        """power_off must clear B1[6] (unit-on bit)."""
        frame = encode(temp_f=68, mode="cool", fan="low", power_off=True)
        assert frame[1] & 0x40 == 0, "B1[6] must be 0 for power-off"
        assert frame[7] & 0x10 != 0, "B7[4] (power_action) must be 1 for power-off"

    def test_power_on_sets_b1_bit6(self):
        """power_on must set both B1[6] and B7[4]."""
        frame = encode(temp_f=68, mode="cool", fan="low", power_on=True)
        assert frame[1] & 0x40 != 0, "B1[6] must be 1 for power-on"
        assert frame[7] & 0x10 != 0, "B7[4] (power_action) must be 1 for power-on"

    def test_normal_command_b7_bit4_clear(self):
        """Regular (non-transition) command must not set B7[4]."""
        frame = encode(temp_f=68, mode="cool", fan="low")
        assert frame[1] & 0x40 != 0, "B1[6] must be 1 for normal command"
        assert frame[7] & 0x10 == 0, "B7[4] must be 0 for normal command"

    def test_encode_dry_mode_b6_bits(self):
        """Dry mode must set B6[7:5]=0b010."""
        frame = encode(temp_f=68, mode="dry", fan="low")
        assert (frame[6] >> 5) & 0x07 == 0b010

    def test_encode_decode_round_trip(self):
        """Every encode() output should decode() cleanly."""
        for temp in range(60, 87):
            for mode in ("cool", "energy_saver", "fan", "dry"):
                for fan in ("low", "med", "hi"):
                    frame = encode(temp_f=temp, mode=mode, fan=fan)
                    result = decode(frame)
                    assert result["temp_f"] == temp, f"{mode}@{temp}°F: wrong temp"
                    assert result["mode"] == mode, f"{mode}@{temp}°F: wrong mode"
                    assert result["fan"] == fan, f"{mode}@{temp}°F: wrong fan"
                    assert result["unit_on"] is True
                    assert result["power_on"] is False
                    assert result["power_off"] is False

    def test_decode_power_off_frame(self):
        """Decoded power-off frame must have unit_on=False, power_off=True."""
        frame = encode(temp_f=68, mode="cool", fan="low", power_off=True)
        result = decode(frame)
        assert result["unit_on"] is False
        assert result["power_off"] is True
        assert result["power_on"] is False

    def test_decode_power_on_frame(self):
        """Decoded power-on frame must have unit_on=True, power_on=True."""
        frame = encode(temp_f=68, mode="cool", fan="low", power_on=True)
        result = decode(frame)
        assert result["unit_on"] is True
        assert result["power_on"] is True
        assert result["power_off"] is False


# ---------------------------------------------------------------------------
# Known hardware captures from Broadlink RM4 Pro
#
# Columns: (name, b64, temp_f, mode, fan, celsius_display,
#           auto_swing, auto_clean, power_on, power_off)
# All expected values were validated against knowninfo.decode_broadlink().
# ---------------------------------------------------------------------------
_KNOWN_CAPTURES = [
    # ── Cool mode, Fahrenheit display, fan=low ───────────────────────────────
    ("60",  "JgCYAAABiacUDhU/Ew8UPxQPFD8UDxQ/Ew8TDxQPEw8TDxMPFD8UDxMPEw8TEBMPEw8TDxMPExATDxMPEw8TDxMQEw8TDxJBFA8TDxMPEw8TDxQPEw8TDxMPEw8UDxMPEw8TDxMPFA8TDxMPEw8VPxMPEw8TDxRAEw8TDxMPFA8TDxMPEw8TDxQPFD8UPxQPFD8TDxQPFD8TAA0F",  60, "cool",         "low", False, False, False, False, False),
    ("61",  "JgCYAAABhqoSEBJCEBISQRMPE0ESEBJBExASEBMPEw8TDxMQEkETDxMQEhATDxMPEw8TEBIQEhATDxMPExASEBMPEw8TQRIQEw8TDxMQEhATDxMPEw8TEBIQEw8TDxMPExASEBMPEw8TDxMQEhASQRMQEhASEBJBERISEBEREw8RERESEBITDxMPE0ESQRERE0ESEBJBExASAA0F",  61, "cool",         "low", False, False, False, False, False),
    ("62",  "JgCYAAABh6oTDxJBExASQRQOEkEUDxJBExATDxMPEkEUDxMPEkETDxQPEw8TDxMPExATDxMPEw8TDxMQEw8TDxMPEw8TQRJBEw8UDxMPEw8TDxMQEw8TDxMPEw8TEBMPEw8TDxMPExATDxMPEw8SQRQPEw8TDxJCEw8TDxMPExATDxMPEw8TDxMQEkESQRNBEkEUDxJBEkEUAA0F",  62, "cool",         "low", False, False, False, False, False),
    ("63",  "JgCYAAABh6kTDxNBEw8SQRQPFD8TDxNBEw8TDxMQEkETDxMPE0ETDxMPExASEBMPEw8TDxMPFA8TDxMPEw8TEBMPEkETDxMQEw8TDxMPEw8TEBMPEw8TDxMPExATDxMPEw8TDxMQEw8TDxMPExASQRMPEw8TEBJBEw8TDxMQEw8TDxMPEw8TEBMPEkESQhJBEkETQRMPEw8UAA0F",  63, "cool",         "low", False, False, False, False, False),
    ("64",  "JgCYAAABh6kTEBJBEw8SQhMPFD8TEBJBEw8TEBJBEw8TDxMQEkETDxMPExATDxMPEw8TDxMQEw8TDxMPEw8TEBMPEkETDxNBEw8TDxMQEw8TDxMPEw8TEBMPEw8TDxMPExATDxMPEw8TDxMQEw8SQRMPExATDxJBEw8TEBMPEw8TDxMQEw8TDxJBEw8UDxMPEkETQRMPEkEUAA0F",  64, "cool",         "low", False, False, False, False, False),
    ("65",  "JgCYAAABiKgTDxNBEw8SQRQPFD8TDxNBEw8TDxJCEw8TDxMPE0ETDxMPEw8TEBMPEw8TDxMPExATDxMPEw8TDxMQEkESQRQPEw8TDxMPFA8TDxMPEw8TDxQPEw8TDxMPExATDxMPEw8TDxMQEw8UPxMPFA8TDxJBEw8UDxMPEw8TDxMQEw8TDxJBFA8TDxMPEkETQRJBFA8TAA0F",  65, "cool",         "low", False, False, False, False, False),
    ("66",  "JgCYAAABh6kUDhNBEw8SQRQPEkETDxNBEw8TDxJCFD8TDxMQEkETDxMPFA8TDxMPEw8TDxQPEw8TDxMPEw8UDxMPEkEUQBQ/Ew8UDxMPEw8TDxMPFA8TDxMPEw8TEBMPEw8TDxMPFA8TDxMPEw8UQBMPEw8TDxRAEw8TDxMPExATDxMPEw8TDxRAEw8TDxRAFD8SQRRAFD8UAA0F",  66, "cool",         "low", False, False, False, False, False),
    ("67",  "JgCYAAABhqoTDxJBFA8SQRMQEkETDxJBFA8TDxJBE0ETDxMPEkITDxMPEw8TEBMPEw8TDxMPExATDxMPEw8TEBJBEw8TDxMQEw8TDxMPEw8TEBMPEw8TDxMPExATDxMPEw8TDxQPEw8TDxMPExASQRMPEw8TEBJBEw8TDxMQEw8TDxMPEw8UDxJBEw8SQhMPEw8TDxMQEw8TAA0F",  67, "cool",         "low", False, False, False, False, False),
    ("68",  "JgCYAAABiKcUDxJBFA8SQRMPFD8UDxJBFA8SQRMPEw8TEBMPFD8TDxQPEw8TDxMPEw8UDxMPEw8TDxMPFA8TDxJBFA8TDxQ/Ew8UDxMPEw8TDxMPFA8TDxMPEw8TDxQPEw8TDxMPExATDxMPEw8SQRQPEw8TDxQ/FA8TDxMPExATDxMPEw8TDxJCEw8SQRNBEw8TDxMQEkETAA0F",  68, "cool",         "low", False, False, False, False, False),
    ("69",  "JgCYAAABiKgUDhRAEw8SQRQPEkETDxJCEw8UPxQPEkETDxMQEkAUDxMPExATDxMPEw8TDxMQEw8TDxMPEw8UDxJBEw8SQhMPEw8TDxMQEw8TDxMPEw8TEBMPEw8TDxMQEw8TDxMPEw0VEBMPEw8UPxMQEw8TDxQ/FA8TDxMPEw8TEBMPEw8TDxQ/E0ETDxMPFA8TDxJBExATAA0F",  69, "cool",         "low", False, False, False, False, False),
    ("70",  "JgCYAAABhqoTDxJBFA8SQRQOEkITDxJBFA8SQRMPEkITDxMPEkEUDxMPEw8TDxMQEw8TDxMPEw8TEBMPEw8TDxJBFA8SQRJCEw8TDxMPExATDxMPEw8TDxMQEw8TDxMPEw8TEBMPEw8TDxMPExASQRMPEw8UDxJBEw8TEBMPEw8TDxMPExATDxJBEkEUDxMPEw8TDxNBEkEUAA0F",  70, "cool",         "low", False, False, False, False, False),
    ("71",  "JgCYAAABiKgUDhJBFA8SQRMPFT8TDxJBFA8SQRRAEw8TDxMPFEATDxMPEw8UDxMPEw8TDxMPFA8TDxMPEw8TEBJBEkESEBQPEw8TDxMPFA8TDxMPEw8TDxQPEw8TDxMPEw8UDxMPEw8TDxMPFA8UPxMPEw8UDxJBEw8TEBMPEw8TDxMPFA8TDxJBFD8UDxJBFA8SQRMPEw8UAA0F",  71, "cool",         "low", False, False, False, False, False),
    ("72",  "JgCYAAABiKgTDxJBExASQRMPEkEUDxJBExASQRJBFA8TDxMPEkETEBMPEw8TDxMQEw8TDxMPEw8TEBMPEw8TDxJBE0ETDxJCEw8TDxMPExATDxMPEw8TDxMQEw8TDxMPEw8TEBMPEw8TDxMPExASQRMPEw8TEBI/FQ8TDxMQEw8TDxMPExASEBJBEkEUDxJBExASQRMPEkEUAA0F",  72, "cool",         "low", False, False, False, False, False),
    ("73",  "JgCYAAABh6kTDxNBEw8SQRMQEkETDxJCEw8SQRNBEkETDxMQEkETDxMQEhATDxMPEw8TEBMPEw8TDxMPExATDxJBE0ESQRMPExATDxMPEw8TEBMPEw8TDxMPEw8UDxMPEw8TDxMQEw8TDxMPEw8UQBMPEw8TDxU/Ew8TDxMPFA8TDxMPEw8TDxNBEkETQRERERESQRNBERERAA0F",  73, "cool",         "low", False, False, False, False, False),
    ("74",  "JgCYAAABh6oTDxJBEw8TQRMPEkEUDxJBEw8TQRJBEkITDxMPEkEUDxMPEw8TDxMQEw8TDxMPEw8TEBMPEw8TDxJCEkESQRNBEw8TEBIQEw8TDxMPExASDhUPEw8TDxMQEw8TDxMPEw8TEBIQEw8SQRMQEw8TDxJBExATDxMPEw8TEBIQEw8TDxJBE0ESQRMQEw8SQRNBEkETAA0F",  74, "cool",         "low", False, False, False, False, False),
    ("75",  "JgCYAAABiacTDxU/Ew8UPxQPFD8TDxRAFD8UDxMPEw8TDxMPFEATDxMPExATDxMPEw8TDxMQEw8TDxMPEw8UQBMPEw8TDxQPEw8TDxMPExATDxMPEw8TDxQPEw8TDxMPEw8TEBMPEw8TDxMPFA8UPxMPEw8UDxQ/Ew8TDxQPEw8TDxMPExATDxQ/FD8VPxQ/FT8TDxMPExATAA0F",  75, "cool",         "low", False, False, False, False, False),
    ("76",  "JgCYAAABh6kTDxNBEw8SQRQPEkETEBJBEkETEBMPEw8TDxMPE0ETDxMPEw8UDxMPEw8TDxMQEw8TDxMPEw8SQhMPEw8TDxNBEw8TDxMPFA8TDxMPEw8TEBMPEw8TDxMPExATDxMPEw8TDxMQEw8SQRMPExATDxJBEw8UDxMPEw8TDxMQEw8TDxJBE0ESQRJCEkETDxMQEkETAA0F",  76, "cool",         "low", False, False, False, False, False),
    ("77",  "JgCYAAABiKgTDxJBFA8SQRMPFT8TDxQ/FT8TDxMPFEATDxMPFD8UDxMPEw8TDxQPEw8TDxMPEw8UDxMPEw8UPxQPEw8UPxMQEw8TDxMPEw8UDxMPEw8TDxMPFA8TDxMPEw8TDxMQEw8TDxMPFA8TQBMPEw8TEBNAEw8TDxMQEw8TDxMPEw8UDxMPEw8TDxMPFEATDxQ/FA8TAA0F",  77, "cool",         "low", False, False, False, False, False),
    ("78",  "JgCYAAABhqoTDxJBFA8SQRMQEkETDxJBE0ETDxJCEw8TDxMPE0ETDxMPEw8UDxMPEw8TDxMQEw8TDxMPEw8SQhMPEw8SQRNBEw8TDxQPEw8TDxMPEw8UDxMPEw8TDxMPFA8TDxMPEw8TDxQPEw8SQRQPEw8TDxJBFA8TDxMPEw8TDxQPEw8TDxMPExATDxJBEkEUDxJBEkEUAA0F",  78, "cool",         "low", False, False, False, False, False),
    ("79",  "JgCYAAABiKgTDxQ/FA8UPxMPFT8TDxJBE0ETDxJBFA8TDxMPEkEUDxMPEw8TDxQPEw8TDxMPFA4UDxMPEw8SQRQPEkETDxMQEw8TDxMPEw8UDxMPEw8TDxMPFA8TDxMPEw8TDxQPEw8TDxMPExASQRMPEw8UDxJBEw8TDxMQEw8TDxMPEw8TEBMPEw8TDxJCEkESQRQPEw8TAA0F",  79, "cool",         "low", False, False, False, False, False),
    ("80",  "JgCYAAABiKgTDxJCEw8SQRQPEkETDxJCEkETDxRAEkETDxQPEkETDxMQEw8TDxMPEw8TEBMPEw8TDxMPExATQBMPEkITDxJBFA8TDxMPEw8TDxQPEw8TDxMPEw8UDxMPEw8TDxMQEw8TDxMPEw8TQRMPEw8TDxNBEw8TDxMPFA8TDxMPEw8TEBMPEw8UPxQPEkEUPxQPFD8TAA0F",  80, "cool",         "low", False, False, False, False, False),
    # ── Power-on command ─────────────────────────────────────────────────────
    ("on_68", "JgCYAAABhqoRERJCEBISQRERE0ERERJBEhESQREREhEQEhEREkEREhATEBERERIQERIQEhESERASERERERERERJBEhERERJBEhEREREREhASEBIRERERERIQEhASERERERESEBIRFA4QEhERERETQRERERESEBNBERERERIQERISQRIQERIRERJBEw8TQRJBE0ESEBASEkETAA0F", 68, "cool",         "low", False, False, False, True,  False),
    # ── Energy-saver mode, fan=low ───────────────────────────────────────────
    ("energy_saver_68", "JgCYAAABiKgTDxQ/FA8UPxQOFT8TDxQ/FA8UPxMPFA8TDxMPFD8UDxMPEw8TDxQPEw8TDxMPEw8UDxMPEw8TDxQ/FA8TDxJBFA8TDxMPEw8UDxMPEw8TDxMPFA8TDxMPEw8TDxQPEw8TDxMPEw8TQRMPEkEUDxMPEw8TDxQPEw8TDxMPEw8UDxJBEw8SQRNBEw8SQRQPEw8TAA0F", 68, "energy_saver", "low", False, False, False, False, False),
    ("energy_saver_70", "JgCYAAABh6kTDxJCEhASQRMQEkETDxJCEhASQRIQE0ERERIQE0ERERERERESEREREBIRERIQEhERERERERESEBNBERESQhJBEhASEBESEREREREREhASERERERERERERERIRERERERESERERERESQRIREkESEBIQEhEREREREhASEBIRERERERJBE0ESEBIQEhESQRJBEhERAA0F", 70, "energy_saver", "low", False, False, False, False, False),
    ("energy_saver_71", "JgCYAAABiacTDxRAEw8UPxQPFD8TDxU/Ew8UPxU/Ew8TDxQPEkETDxMPFA8TDxMPEw8TDxQPEw8TDxMPEw8UDxJBEkEUDxMPEw8TDxQPEw8TEBIQEg8UDxMPEw8TDxMPFA8TDxMPEw8TDxQPEw8UPxQOFT8TDxMPFA8TDxMPEw8TDxMQEw8TDxQ/FT8TDxQ/FA8UPxQ/FT8TAA0F", 71, "energy_saver", "low", False, False, False, False, False),
    ("energy_saver_72", "JgCYAAABiacUDxJBEw8TQRMPEkEUDxJBEw8TQRJBEw8UDxMPEkEUDxMPEw8TDxMPExATDxMPEw8TDxMQEw8TDxJBE0ETDxJBFA8TDxMPEw8TEBMPEw8TDxMPFA8TDxMPEw8TDxQPEw8TDxMPExASQRMPEkEUDxMPEw8TDxQPEw8TDxMPExATDxJBEkEUDxJBEkITDxMPEw8TAA0F", 72, "energy_saver", "low", False, False, False, False, False),
    ("energy_saver_73", "JgCYAAABiKgTDxQ/FA8UPxMPFEATDxQ/ExAUPxQ/FT8TDxMPFEATDxMPFA8TDxMPEw8TDxQPEw8TDxMPEw8TEBNAFD8TQRMPEw8UDxMPEw8TDxMPFA8TDxMPEw8TDxQPEw8TDxMPEw8UDxMPEw8SQRQPEkETDxMQEw8TDxMPEw8TEBMPEw8TDxJCFD8UPxQPFD8TDxQPEkETAA0F", 73, "energy_saver", "low", False, False, False, False, False),
    ("energy_saver_74", "JgCYAAABiacUDxJBEw8SQhMPEkEUDxNAEw8UQBQ/FD8UDxMPFD8UDxMPEw8TDxMPFA8TDxMPEw8TDxQPEw8TDxQ/FT8UPxU/Ew8TDxMPExATDxMPEw8TDxQPEw8TDxMPExATDxMPEw8TDxQPEw8UPxMPFT8TDxMPEw8UDxMPEw8TDxMPFA8TDxQ/FT8UPxMPFT8TDxQ/FA8TAA0F", 74, "energy_saver", "low", False, False, False, False, False),
    ("energy_saver_75", "JgCYAAABiKgTDxJBFA8SQRMPE0ETDxJBE0ETDxMPFA8TDxMPEkEUDxMPEw8TDxMPFA8TDxMPEw8TDxQPEw8SQRQPEw8TDxMPEw8UDxMPEw8TDxMPFA8TDxMPEw8TDxMQEgsXEBMPEw8UDxMPEw8UPxQPFD8TDxMQEw8TDxMPEw8UDxMPEw8TDxQ/FT8UPxNBFD8UDxQ/FD8UAA0F", 75, "energy_saver", "low", False, False, False, False, False),
    ("energy_saver_76", "JgCYAAABhqkUDxJBExASQRMPEkEUDxJBEkITDxMPEw8TEBMPEkETDxQPEw8TDxMPExATDxMPEw8TDxMQEw8SQRMPExATDxJBEw8UDxMPEw8TDxMQEw8TDxMPEw8TEBMPEw8TDxMPFA8TDxMPEw8SQhMPEkETEBMPEw8TDxMPExATDxMPEw8TDxNBEkETQRJBEkETQRMPExATAA0F", 76, "energy_saver", "low", False, False, False, False, False),
    ("energy_saver_77", "JgCYAAABiacTDxRAEw8UPxQPFD8TDxRAFD8UDhQPFD8TDxMQE0ATDxMPExATDxMPEw8TDxQPEw8TDxMPEw8UQBMPEw8UQBMPEw8TDxMQEw8TDxMPEw8TEBMPEw8TDxMPFA8TDxMPEw8TDxQPEw8UPxMPFEATDxMPExATDxMPEw8TDxMQEw8TDxMPEw8TEBMPFD8UPxQPFD8UAA0F", 77, "energy_saver", "low", False, False, False, False, False),
    ("energy_saver_78", "JgCYAAABiKgTDxQ/FA8UPxMPFEATDxQ/FEATDxQ/FA8TDxMPFD8UDxMPEw8TDxMQEw8TDxMPEw8UDxMPEw8UPxQPEw8UPxRAEw8TDxMPExATDxMPEw8TDxQPEw8TDxMPEw8TEBMPEw8TDxMPFA8UPxMOFUATDxMNFQ8UDxMPEw8TDxMPExATDxMPEw8TDxRAFD8UQBQ/Ew8UAA0F", 78, "energy_saver", "low", False, False, False, False, False),
    ("energy_saver_79", "JgCYAAABhqoTDxJBExASQRMPEkITDxJBE0ETDxJBExATDxMPEkEUDxMPEw8TDxMQEw8TDxMPEw8TEBMPEw8SQRMQEkETDxMQEw8TDxMPEw8TEBMPEw8TDxMQEhATDxMPEw8TEBIQEw8TDxMPExASQRMPE0ETDxMPEw8TDxMQEw8TDxMPEw8TEBMPEw8TDxJCEkESQRNBEkEUAA0F", 79, "energy_saver", "low", False, False, False, False, False),
    ("energy_saver_80", "JgCYAAABhqoTDxJBFA8SQRMQEkETDxJCEkETDxJCEkETDxMQEkETDxMPExATDxMPEw8TEBMPEw8TDxMPExASQRMPEkITDxJBExATDxMPEw8TDxMQEw8TDxMPEw8TEBMPEw8TDxMPExATDxMPEw8SQxIPEkETEBMPEw8TDxMPExATDxMPEw8TDxMQEw8SQRJCEw8TDxMPExATAA0F", 80, "energy_saver", "low", False, False, False, False, False),
    # ── Fan-only mode ────────────────────────────────────────────────────────
    ("fan",   "JgCYAAABhqoTDxJBExASQRMPEkITDxJBE0ETDxJBE0ETDxMPE0ETDxMPExASEBMPEw8TDxMQEhATDxMPEw8SQhMPEkETEBJBEw8TEBIQEw8TDxMPExASEBMPEw8TDxMQEhATDxMPEw8TEBIQEw8SQRMQEw8SQRNBEw8TDxMPExATDxMPEw8TEBIQEw8SQRMPE0ESQRNBEkETAA0F",  80, "fan",          "low", False, False, False, False, False),
    # ── Cool mode, Celsius display, various fan speeds ────────────────────────
    ("cool_c_19_fanlow",  "JgCYAAABhqoRERJBEhESQRIQE0ERERJBEhERERJBE0EREREREkESERERERERERIRERERERIQEhASERERERESEBIQE0ESQRNBERESEBIQERIREREREhARERIRERERERIQEhASERERERESEBEREhESQRIQEhERERJBE0ERERERERESEBIRERERERIQEhASERJBEkISQRJBE0ERAA0F", 66, "cool", "low", True, False, False, False, False),
    ("cool_c_19_fanmed",  "JgCYAAABh6gSERJBEhATQREREkESERJBEhAREhJBEkESEREREkESERERERERERERERIRERERERESEBIREREQEhIQEkISQRJBEhEQEhEREhERERIQEBISEhAQEhERERERERESEBIRERERERIQE0EREREREhAREhJBE0ASERIQEhASEBIREREREREREhATQRIQEkETQRJBE0ESAA0F", 66, "cool", "med", True, False, False, False, False),
    ("cool_c_19_fanhi",   "JgCYAAABhqkSERJBEhATQREREkESERJBEhASEBNBEkESEREREkESEBIRERERERIQEhASERERERESEBIQEhEREREREkETQRJBEhEQEhERERESEBIREREREREREhASERERERESEBIQEhEREREREkETQRIQEhAREhJBEkESEREREhARERIRERERERIQEhATQRJBE0ESQRNBEkESAA0F", 66, "cool", "hi",  True, False, False, False, False),
    ("cool_c_19_fanhi_autocleanOn",  "JgCYAAABh6kSEBNBERESQRIREkESEBJCERERERJBE0ESEBIQE0ERERIQEhASEREREhASEBEREhEREREREhASEREREkETQRJBEhASEBIREREQEhIQEhERERASEhASEBIRERERERIQEhASEREREkETQREREhARERNBEkESEBIRERERERJBEhEREREREkIRERERERESEBNBEkESAA0F", 66, "cool", "hi",  True, False, True,  False, False),
    ("cool_c_19_fanhi_autocleanOff", "JgCYAAABh6kSEBNBEhASQRIREkESEBNBERESEBJCEkESEBIREkESEBIQEhERERERERESEBIREREREREREhASEREREkETQRJBEhASEREREREQEhEREhEREREREhASEBIRERERERIQEhASEREREkETQRERERESEBNBEkESEBIRERERERIQEhERERERERESQhJBEkETQRJBE0ESAA0F", 66, "cool", "hi",  True, False, False, False, False),
    ("cool_c_19_fanhi_autoSwingOn",  "JgCYAAABhqoSEBJBEhESQRIQEkIRERJBEhASERJBEkIREREREkETQRIQEhASERERERERERERERIRERERERESEBESEkESQhJBEhASEBIRERERERIQEhASERERERESEBIQEhEREREREhASEBIREkESQhERERESEBJCEkERERIREREREREREhASEREREkESEBIREREREREREhASAA0F", 66, "cool", "hi",  True, True,  False, False, False),
    ("cool_c_19_fanhi_autoSwingOff", "JgCYAAABhqoRERJBEhESQRIQEkIRERJBEhERERJBEkIREREREkESERERERESEBIQEhERERIQERESERERERERERIQE0ESQRNBERERERIQEhERERERERESEBIREREREREREhASERERERERERIQE0ESQRIQEhERERJBE0ERERERERESERERERERERIQEhESQRJBE0ESQRNBEkESAA0F", 66, "cool", "hi",  True, False, False, False, False),
    # ── Cool mode, Fahrenheit display, fan=hi ────────────────────────────────
    ("cool_f_66_fanhi", "JgCYAAABhqkSERJBEhATQw8RE0ASERJBEhASERJBEkESEREREkESERERERESEBIQEhEREREREhASEBIRERERERIQE0ESQRJCERERERIQEhASERERERESEBEREhEREREREhASEBESERERERIQE0ESQRIQEhEQEhJBEhASERERERESEBESERERERJBEhESQRJBE0ESQRNBEkESAA0F", 66, "cool", "hi",  False, False, False, False, False),
    # ── Power-off command ────────────────────────────────────────────────────
    ("Poweroff", "JgCYAAABh6kSERFCEhERQRIREkERERNBEREREhFCEkEREhIQEBIREg8TEBIQEhATDxMPEhESEBIREhEREBIQERIREkESQRNBEBIREhERERIPEhERERIRERATDxMQEhASEREREg8TEBEREhASEkESQRIREBIREhFBEhEQEw8SERISQRASEBMREBNBEkEREhATEBESQRIREkERAA0F", 66, "cool", "hi",  False, False, False, False, True),
    # ── Dry mode ─────────────────────────────────────────────────────────────
    ("Dry_f_67_fanlow",   "JgCYAAABiKgSEBNBEhASQRISEUESEBNBERESEBNBEkESEBIREkESEBIQEhERERERERESEBIRERERERIQEhASERJBEhASERERERERERIQEhERERERERESEBIRERERERIQEhAREhERERESEBIQERISQRIQEhESQRIQEhASERASERERERIQEhERERJBEhATQREREhASEBIREkESAA0F", 67, "dry",  "low", False, False, False, False, False),
    ("Dry_f_68_fanlow",   "JgCYAAABiKgSEBNBERESQRIREkESEBNBERESQRIRERERERIQE0EREREREhASERERERERERIQEhEREREREhASEBNBERERERNBEREQEhIQEhASERERERESEBIQEhEREREREhASEBIRERERERIQEhESQREREhATQRIQEhASEBIREBIRERIQEhAREhJBEhATQRJBEhASERJBEhARAA0F", 68, "dry",  "low", False, False, False, False, False),
    ("Dry_f_68_fanlow_autocleanOn",            "JgCYAAABh6kSEBNBERESQRIREkESEBNBERESQRIRERESEBIQE0ERERIQERESERERERESEA8TERIPFA8SEhUNFQ5BEhASEBNBERESEBIQEhEREREREhASEBIRERERERIQEhASERERERESEBIQEhESQRIQEhATQREREhASERERERESEBNBERERERJCERESQRJCERESQRNBERESAA0F", 68, "dry",  "low", False, False, True,  False, False),
    ("Dry_f_68_fanlow_autocleanOn_autoswingOn", "JgCYAAABhqoSEBJBEhESQRIQE0ESEBJBEhESQRIQEhEREREREkETQRIQEhASERASERERERIQEhERERERERESEBNBERERERJCERERERERERESERERERERERIREREREREREREUDxERERERERIQEhESQRIQERETQRIQEhARERIRERERERJCERERERJBEhESQRNAEhESQRJCEkESAA0F", 68, "dry",  "low", False, True,  True,  False, False),
    # ── Power-on + dry mode ───────────────────────────────────────────────────
    ("Poweron_Dry_f_66_fanlow_autocleanOn_autoswingOn", "JgCYAAABhqkSERJBERETQREREkESERJBEhASEBNBEkESEREREkETQRERERESEBIREREREREREhASERERERERERIQE0ESQRNBERESEBIQEhEREREREhASEBESERERERIQEhASERERERESEBIRERESQRIQEhESQRIQEhASERERERESQRNBEhASEBNBERESQRIREkESQhEREkESAA0F", 66, "dry",  "low", False, True,  True,  True,  False),
]


class TestKnownCaptures:
    """Decode all real Broadlink RM4 Pro captures and verify every field.

    The expected values were obtained by running knowninfo.decode_broadlink()
    against the same base64 strings and confirmed with checksum validation.
    """

    @pytest.mark.parametrize(
        "name,b64,temp_f,mode,fan,celsius_display,auto_swing,auto_clean,power_on,power_off",
        _KNOWN_CAPTURES,
        ids=[c[0] for c in _KNOWN_CAPTURES],
    )
    def test_decode_broadlink_fields(
        self,
        name: str,
        b64: str,
        temp_f: int,
        mode: str,
        fan: str,
        celsius_display: bool,
        auto_swing: bool,
        auto_clean: bool,
        power_on: bool,
        power_off: bool,
    ) -> None:
        """Each capture must decode to the expected field values."""
        result = decode_broadlink(b64)

        assert result["temp_f"] == temp_f, f"{name}: temp_f"
        assert result["mode"] == mode, f"{name}: mode"
        assert result["fan"] == fan, f"{name}: fan"
        assert result["celsius_display"] is celsius_display, f"{name}: celsius_display"
        assert result["auto_swing"] is auto_swing, f"{name}: auto_swing"
        assert result["auto_clean"] is auto_clean, f"{name}: auto_clean"
        assert result["power_on"] is power_on, f"{name}: power_on"
        assert result["power_off"] is power_off, f"{name}: power_off"
        assert result["unit_on"] is (not power_off), f"{name}: unit_on"
