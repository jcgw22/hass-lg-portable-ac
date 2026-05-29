"""Pytest configuration for LG Portable AC tests.

Stubs out homeassistant and infrared_protocols with MagicMock so that the
pure-Python protocol module can be tested without a full HA installation.
Any attribute access on a MagicMock returns another MagicMock automatically,
so all `from homeassistant.x import Y` statements succeed without error.
"""

import sys
from unittest.mock import MagicMock

_HA_MODULES = [
    "homeassistant",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.components",
    "homeassistant.components.climate",
    "homeassistant.components.climate.const",
    "homeassistant.components.infrared",
    "homeassistant.helpers",
    "homeassistant.helpers.device_registry",
    "homeassistant.helpers.entity_platform",
    "homeassistant.helpers.selector",
    "infrared_protocols",
]

for _mod in _HA_MODULES:
    sys.modules[_mod] = MagicMock()
