# LG PL1215GXR IR Protocol Specification

> This protocol was reverse-engineered from 26 Broadlink RM4 Pro captures.
> It does NOT match any publicly documented LG IR protocol.
> See the README for the full comparison against known implementations.

## Quick Reference

- **Carrier:** 38 kHz
- **Modulation:** Pulse-distance (PDM), LSB-first
- **Frame:** 72 bits (9 bytes)
- **Header:** ~3604 us mark, ~4392 us space
- **Bit mark:** ~526 us (always)
- **Bit-0 space:** ~395 us
- **Bit-1 space:** ~1657 us
- **Address byte:** 0xAA (fixed)

## Frame Layout

```
B0=ADDR  B1=SWING|CIDX  B2=RSVD  B3=FIDX  B4=RSVD  B5=RSVD  B6=MODE|FAN  B7=FLAGS  B8=CHK
```

| Byte | Name | Description |
|------|------|-------------|
| B0 | ADDR | 0xAA fixed device address |
| B1 | SWING\|CIDX | bit7=auto-swing, bit6=1(fixed), bits[3:0]=rev4(celsius-16) |
| B2 | -- | 0x00 reserved (timer -- not yet captured) |
| B3 | FIDX | rev8(temp_F - 59) |
| B4 | -- | 0x00 reserved (timer hours -- not yet captured) |
| B5 | -- | 0x00 reserved |
| B6 | MODE\|FAN | bits[7:5]=mode, bits[3:2]=fan speed |
| B7 | FLAGS | bit0=celsius_display, bit4=power_on, bit5=auto_clean |
| B8 | CHK | rev8(sum(rev8(B0..B7)) & 0xFF) |

## Temperature Encoding

Temperature is encoded TWICE in every frame:

- **B3 (Fahrenheit):** `B3 = rev8(temp_F - 59)` -- authoritative setpoint
- **B1 (Celsius):** `B1[3:0] = rev4(round((temp_F-32)*5/9) - 16)` -- redundancy

## Mode Encoding (B6 bits 7:5)

| Bits | Hex | Mode |
|------|-----|------|
| 100 | 0x80 | Cool |
| 001 | 0x20 | Energy Saver |
| 110 | 0xC0 | Fan Only |

## Fan Speed (B6 bits 3:2)

| Bits | Hex | Speed |
|------|-----|-------|
| 10 | 0x08 | Low |
| 01 | 0x04 | Medium |
| 11 | 0x0C | High |

## Checksum

```
B8 = rev8( sum( rev8(Bn) for Bn in [B0..B7] ) mod 256 )
```

Verified against all 26 captured samples.
