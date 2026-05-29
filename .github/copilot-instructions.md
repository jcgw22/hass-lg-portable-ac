# LG Portable AC IR Integration -- Copilot Instructions

## Project Overview

This is a **Home Assistant HACS custom integration** that controls an
**LG PL1215GXR portable air conditioner** via infrared, using the
HA 2026.4+ native `infrared` platform.

The IR protocol was **fully reverse-engineered from scratch** -- it does NOT
match any publicly documented LG IR protocol. See `docs/protocol.md` for
the complete specification.

## Architecture

This is a **consumer integration** on the HA infrared platform:

```
ClimateEntity --> protocol.encode() --> LGPortableACCommand --> infrared.async_send_command() --> IR emitter hardware
```

- `protocol.py` -- encodes AC state into a 9-byte IR frame
- `ir_command.py` -- converts the 9-byte frame into raw microsecond mark/space timings by subclassing `infrared_protocols.Command`
- `climate.py` -- HA `ClimateEntity` with assumed state (IR is one-way)
- `config_flow.py` -- UI wizard to pick an IR emitter entity

## Protocol Summary (see docs/protocol.md for full details)

- **72-bit frame** (9 bytes), 38 kHz carrier, pulse-distance modulation, **LSB-first**
- Header: ~3604 us mark, ~4392 us space
- Bit encoding: ~526 us mark, ~395 us space (0), ~1657 us space (1)
- Frame always starts with 0xAA
- Temperature encoded TWICE: Fahrenheit in B3, Celsius in B1
- Both use bit-reversal: `rev8(temp_F - 59)` and `rev4(celsius - 16)`
- Checksum: `rev8(sum(rev8(B0..B7)) mod 256)`
- Verified against 26 captured samples, all 253 round-trip tests pass

### Frame layout

```
B0=0xAA  B1=SWING|CIDX  B2=0x00  B3=FIDX  B4=0x00  B5=0x00  B6=MODE|FAN  B7=FLAGS  B8=CHK
```

| Byte | Name | Description |
|------|------|-------------|
| B0 | ADDR | 0xAA fixed |
| B1 | SWING\|CIDX | bit7=auto-swing, bit6=1(fixed), bits[3:0]=rev4(celsius-16) |
| B2 | -- | 0x00 reserved (likely timer, not yet captured) |
| B3 | FIDX | rev8(temp_F - 59) |
| B4 | -- | 0x00 reserved (likely timer hours, not yet captured) |
| B5 | -- | 0x00 reserved |
| B6 | MODE\|FAN | bits[7:5]=mode (100=cool,001=energy_saver,110=fan), bits[3:2]=fan (10=low,01=med,11=hi) |
| B7 | FLAGS | bit0=celsius_display, bit4=power_on, bit5=auto_clean |
| B8 | CHK | rev8(sum(rev8(B0..B7)) & 0xFF) |

## What is DONE

- [x] Full protocol decode (9-byte frame structure)
- [x] Encoder function (`protocol.py` -- `encode()`)
- [x] Decoder function (`protocol.py` -- `decode()`)
- [x] IR command class (`ir_command.py` -- `LGPortableACCommand`)
- [x] Climate entity scaffold (`climate.py`)
- [x] Config flow scaffold (`config_flow.py`)
- [x] Integration init (`__init__.py`)
- [x] Manifest, strings, translations
- [x] 26 verified capture samples in `docs/verified_captures.md`

## What NEEDS WORK (TODO)

- [ ] **Timer functionality**: B2, B4, B5 are reserved bytes that likely carry timer data. No samples captured yet. See `docs/timer_analysis.md` for hypotheses and capture strategy.
- [ ] **Power OFF command**: Need to verify how the unit is turned off (dedicated command vs special flag vs just stop sending).
- [ ] **Energy saver mode mapping**: `energy_saver` doesn't map to a standard `HVACMode`. Currently not exposed. Options: preset_mode, HVACMode.AUTO, or separate switch entity.
- [ ] **Unit tests**: `tests/test_protocol.py` has the test structure but needs the full 26-sample verification table filled in.
- [ ] **Integration tests**: Mock `infrared.async_send_command` and test climate entity state transitions.
- [ ] **Broadlink fallback**: If the Broadlink integration doesn't expose InfraredEntity yet, add a fallback path that calls `broadlink.send_command` directly with Base64-encoded Broadlink packets.
- [ ] **Repeat frames**: Some IR protocols send the frame 2-3 times. Need to test if the AC needs repeats for reliability.
- [ ] **Sign convention verification**: Confirm whether `get_raw_timings()` should use negative spaces or all-positive values with the actual emitter hardware.

## Coding Conventions

- Python 3.12+, type hints everywhere
- Follow Home Assistant development guidelines: https://developers.home-assistant.io/
- Use `_attr_` pattern for entity attributes (not properties)
- All IR timing constants in microseconds
- Bit manipulation uses explicit masks and shifts, no magic numbers
- Every function that touches the protocol must reference the byte/bit it operates on

## Key Dependencies

- `homeassistant.components.infrared` (HA 2026.4+)
- `infrared_protocols` library (`Command` base class)
- No external pip packages

## Reference Implementations

- `lg_infrared` in HA core (LG TV via NEC protocol) -- same infrared platform, different protocol
- `hass_customir` by lischetzke -- community HACS example using the infrared platform
- `JanM321/esphome-lg-controller` -- LG wired protocol (uses 0xAA byte like ours)

## File Descriptions

| File | Purpose |
|------|---------|
| `custom_components/lg_portable_ac/__init__.py` | Integration entry point, forwards to climate platform |
| `custom_components/lg_portable_ac/manifest.json` | HA integration metadata, declares infrared dependency |
| `custom_components/lg_portable_ac/const.py` | Domain name, config keys, enums for modes/fan speeds |
| `custom_components/lg_portable_ac/protocol.py` | 9-byte frame encoder/decoder, checksum, bit-reversal |
| `custom_components/lg_portable_ac/ir_command.py` | Subclasses `Command`, converts bytes to IR timings |
| `custom_components/lg_portable_ac/climate.py` | `ClimateEntity` -- thermostat card in HA dashboard |
| `custom_components/lg_portable_ac/config_flow.py` | UI setup wizard -- pick an IR emitter entity |
| `custom_components/lg_portable_ac/strings.json` | UI strings for config flow |
| `docs/protocol.md` | Full protocol specification |
| `docs/timer_analysis.md` | Timer hypotheses and capture strategy |
| `docs/verified_captures.md` | All 26 verified IR captures with decoded values |
| `tests/test_protocol.py` | Unit tests for encoder/decoder/checksum |
