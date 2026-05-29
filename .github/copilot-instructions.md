# LG Portable AC IR Integration -- Copilot Instructions

## Project Overview

This is a **Home Assistant HACS custom integration** that controls an
**LG PL1215GXR portable air conditioner** via infrared using a **Broadlink RM4 Pro**.

The IR protocol was **fully reverse-engineered from scratch** -- it does NOT
match any publicly documented LG IR protocol. See `docs/protocol.md` for
the complete specification.

## Architecture

```
ClimateEntity --> protocol.encode() --> LGPortableACCommand.get_raw_timings()
    --> _build_broadlink_packet() --> remote.send_command(b64:<packet>)
    --> Broadlink RM4 Pro --> IR signal
```

- `protocol.py` — encodes AC state into a 9-byte IR frame
- `ir_command.py` — converts the 9-byte frame into raw signed µs mark/space timings
- `climate.py` — HA `ClimateEntity` with assumed state; builds a Broadlink packet at 26.3 µs/tick and calls `remote.send_command` with a `b64:` code
- `config_flow.py` — UI wizard to pick a Broadlink `remote` entity

### Why not the HA infrared platform?

HA 2026.6 introduced `InfraredEmitterConsumerEntity` which the integration originally used. The Broadlink RM4 Pro's `infrared` entity uses `pulses_to_data` which generates packets with a 32.84 µs tick rate, but the RM4 Pro physically operates at 26.3 µs (1/38 kHz carrier period). This causes all timings to transmit at ~80% of the correct duration, which the AC does not recognize. Using `remote.send_command` with a self-built `b64:` packet bypasses this and matches the exact format of learned codes that the device replays correctly.

Issue filed: https://github.com/home-assistant/core/issues/172524

## Protocol Summary (see docs/protocol.md for full details)

- **72-bit frame** (9 bytes), 38 kHz carrier, pulse-distance modulation, **LSB-first**
- Header: ~3604 µs mark (~137 ticks), ~4392 µs space (~167 ticks)
- Bit encoding: ~526 µs mark (~20 ticks), ~395 µs space/0-bit (~15 ticks), ~1657 µs space/1-bit (~63 ticks)
- Frame always starts with 0xAA
- Temperature encoded TWICE: Fahrenheit in B3, Celsius in B1
- Both use bit-reversal: `rev8(temp_F - 59)` and `rev4(celsius - 16)`
- Checksum: `rev8(sum(rev8(B0..B7)) mod 256)`
- Verified against 103 test cases; all round-trip tests pass

### Frame layout

```
B0=0xAA  B1=SWING|CIDX  B2=0x00  B3=FIDX  B4=0x00  B5=0x00  B6=MODE|FAN  B7=FLAGS  B8=CHK
```

| Byte | Name | Description |
|------|------|-------------|
| B0 | ADDR | 0xAA fixed |
| B1 | SWING\|CIDX | bit7=auto-swing, bit6=1(on)/0(power-off), bits[3:0]=rev4(celsius-16) |
| B2 | -- | 0x00 reserved (likely timer, not yet captured) |
| B3 | FIDX | rev8(temp_F - 59) |
| B4 | -- | 0x00 reserved (likely timer hours, not yet captured) |
| B5 | -- | 0x00 reserved |
| B6 | MODE\|FAN | bits[7:5]=mode (100=cool,001=energy_saver,110=fan,010=dry), bits[3:2]=fan (10=low,01=med,11=hi) |
| B7 | FLAGS | bit0=celsius_display, bit4=power_action, bit5=auto_clean |
| B8 | CHK | rev8(sum(rev8(B0..B7)) & 0xFF) |

## What is DONE

- [x] Full protocol decode (9-byte frame structure)
- [x] Encoder function (`protocol.py` — `encode()`)
- [x] Decoder function (`protocol.py` — `decode()`)
- [x] IR command class (`ir_command.py` — `LGPortableACCommand`, plain Python class, no external deps)
- [x] Broadlink packet builder (`climate.py` — `_build_broadlink_packet()`, 26.3 µs tick)
- [x] Climate entity with full state machine (`climate.py`)
- [x] State restoration across HA restarts (`RestoreEntity`)
- [x] Config flow — select Broadlink `remote` entity (`config_flow.py`)
- [x] Integration init (`__init__.py`)
- [x] Manifest, strings, translations (EN + ES)
- [x] Verified capture table in `docs/verified_captures.md`
- [x] 103 passing tests covering encode/decode/checksum and all known captures

## What NEEDS WORK (TODO)

- [ ] **Timer functionality**: B2, B4, B5 are reserved bytes that likely carry timer data. No samples captured yet. See `docs/timer_analysis.md` for hypotheses and capture strategy.
- [ ] **Non-Broadlink emitters**: The integration currently only supports Broadlink RM4 Pro. Once the HA infrared platform tick-rate bug is fixed, add an option to use a generic `infrared` entity instead.

## Coding Conventions

- Python 3.12+, type hints everywhere
- Follow Home Assistant development guidelines: https://developers.home-assistant.io/
- Use `_attr_` pattern for entity attributes (not properties)
- All IR timing constants in microseconds (26.3 µs = 1 carrier tick at 38 kHz)
- Bit manipulation uses explicit masks and shifts, no magic numbers
- The captures in `tests/test_protocol.py` (`_KNOWN_CAPTURES`) are the source of truth — never change expected values without a new hardware capture

## Key Dependencies

- `homeassistant.components.remote` — `remote.send_command` service
- `homeassistant.helpers.restore_state` — `RestoreEntity` for state persistence
- No external pip packages

## File Descriptions

| File | Purpose |
|------|---------|
| `custom_components/lg_portable_ac/__init__.py` | Integration entry point, forwards to climate platform |
| `custom_components/lg_portable_ac/manifest.json` | HA integration metadata (requires HA 2026.6+) |
| `custom_components/lg_portable_ac/const.py` | Domain name, config keys, enums for modes/fan speeds |
| `custom_components/lg_portable_ac/protocol.py` | 9-byte frame encoder/decoder, checksum, bit-reversal |
| `custom_components/lg_portable_ac/ir_command.py` | Converts bytes to signed µs mark/space timings |
| `custom_components/lg_portable_ac/climate.py` | `ClimateEntity` + Broadlink packet builder |
| `custom_components/lg_portable_ac/config_flow.py` | UI setup wizard — pick a Broadlink remote entity |
| `custom_components/lg_portable_ac/strings.json` | UI strings for config flow |
| `docs/protocol.md` | Full protocol specification |
| `docs/timer_analysis.md` | Timer hypotheses and capture strategy |
| `docs/verified_captures.md` | Verified IR captures with decoded frame bytes |
| `tests/test_protocol.py` | 103 unit tests — encoder, decoder, checksum, all known captures |
