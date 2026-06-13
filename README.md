# LG Portable AC RM4 Pro -- Home Assistant IR Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)

<p align="center">
	<img src="custom_components/lg_portable_ac/brand/icon.png" alt="LG Portable AC icon" width="160">
</p>

Control your **LG PL1215GXR** (and possibly other LG portable ACs) via
infrared using a Broadlink RM4 Pro and Home Assistant.

## Features

- Climate entity with thermostat card support
- Temperature control: 60-86 F / 16-30 C
- Modes: Cool, Dry, Fan Only, Energy Saver
- Fan speeds: Low, Medium, High
- Swing (louver oscillation): On/Off
- Auto-clean toggle
- State restored across HA restarts

## Why This Exists

LG portable ACs use a **completely different IR protocol** from LG wall-mount
units. No existing library (IRremoteESP8266, ESPHome, Arduino-IRremote)
supports this protocol. This integration implements the protocol from scratch
based on reverse engineering of captured IR frames from the target unit.

See [docs/protocol.md](docs/protocol.md) for the full protocol specification.

## Installation

1. Install via HACS: Add this repo as a custom repository (category: Integration)
2. Restart Home Assistant
3. Go to **Settings → Devices & Services → Add Integration → "LG Portable AC RM4 Pro"**
4. Select your **Broadlink remote entity** (e.g. `remote.broadlink_rm4`)
5. Done — a climate entity will appear

## Tested Hardware

This integration has been developed and tested exclusively against the **LG PL1215GXR** portable air conditioner using a **Broadlink RM4 Pro** as the IR emitter. The protocol was reverse-engineered from captured IR frames on that specific unit.

Other LG portable AC models may or may not use the same IR protocol. If you try it on a different model and it works (or doesn't), please open an issue.

## Requirements

- Home Assistant **2026.4** or newer
- A **Broadlink RM4 Pro** (or compatible RM4) set up in HA with a working `remote.*` entity
- IR emitter pointed at the AC unit

> **Note:** This integration sends raw IR packets directly via the Broadlink `remote.send_command` service using `b64:` encoded codes. It does not use HA's infrared platform. This approach is used because the HA 2026.6 infrared platform has a tick-rate mismatch with the RM4 Pro that causes silent transmission failures; using the remote entity replays the packet in exactly the format the device expects.

## Status

- [x] Protocol fully decoded (9-byte frame, 72-bit PDM, LSB-first)
- [x] Encoder/decoder with checksum verification
- [x] Climate entity (cool, dry, fan, energy saver, temperature, swing, auto-clean)
- [x] Power on / power off commands
- [x] State restored across HA restarts
- [ ] Timer support (bytes B2/B4/B5 -- captures needed)
