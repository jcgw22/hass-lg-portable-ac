# LG Portable AC -- Home Assistant IR Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)

<p align="center">
	<img src="custom_components/lg_portable_ac/brand/icon.png" alt="LG Portable AC icon" width="160">
</p>

Control your **LG PL1215GXR** (and possibly other LG portable ACs) via
infrared using Home Assistant's native IR platform (2026.4+).

## Features

- Climate entity with thermostat card support
- Temperature control: 60-86 F / 16-30 C
- Modes: Cool, Dry, Fan Only, Energy Saver
- Fan speeds: Low, Medium, High
- Swing (louver oscillation): On/Off
- Auto-clean toggle
- Works with any HA infrared emitter (ESPHome IR proxy, Broadlink, etc.)

## Why This Exists

LG portable ACs use a **completely different IR protocol** from LG wall-mount
units. No existing library (IRremoteESP8266, ESPHome, Arduino-IRremote)
supports this protocol. This integration implements the protocol from scratch
based on reverse engineering of captured IR frames from the target unit.

See [docs/protocol.md](docs/protocol.md) for the full protocol specification.

## Installation

1. Install via HACS: Add this repo as a custom repository (category: Integration)
2. Restart Home Assistant
3. Go to Settings > Devices & Services > Add Integration > "LG Portable AC (IR)"
4. Select your IR transmitter entity
5. Done! A climate entity will appear.

## Tested Hardware

This integration has been developed and tested exclusively against the **LG PL1215GXR** portable air conditioner using a Broadlink RM4 Pro as the IR emitter. The protocol was reverse-engineered from captured IR frames on that specific unit.

Other LG portable AC models may or may not use the same IR protocol. If you try it on a different model and it works (or doesn't), please open an issue.

## Requirements

- Home Assistant 2026.4 or newer
- An IR emitter registered on the infrared platform (ESPHome IR proxy recommended)
- IR emitter pointed at the AC unit

## Status

- [x] Protocol fully decoded (9-byte frame, 72-bit PDM, LSB-first)
- [x] Encoder/decoder with checksum verification
- [x] Climate entity (cool, dry, fan, energy saver, temperature, swing, auto-clean)
- [x] Power on / power off commands
- [ ] Timer support (bytes B2/B4/B5 -- captures needed)
