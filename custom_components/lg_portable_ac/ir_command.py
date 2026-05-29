"""IR command class for LG Portable AC.

Converts a 9-byte protocol frame into raw microsecond mark/space timings.
"""

from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)

# Timing constants (microseconds), derived from Broadlink RM4 Pro captures.
# Tick rate: 26.3 µs = 1/38 kHz carrier period.
LEADER_MARK_US: int = 3604   # ~137 ticks * 26.3 us
LEADER_SPACE_US: int = 4392  # ~167 ticks * 26.3 us
BIT_MARK_US: int = 526       # ~20 ticks  * 26.3 us
BIT_ZERO_SPACE_US: int = 395 # ~15 ticks  * 26.3 us
BIT_ONE_SPACE_US: int = 1657 # ~63 ticks  * 26.3 us
TRAIL_MARK_US: int = 526     # Same as bit mark


class LGPortableACCommand:
    """IR command for LG Portable AC (72-bit PDM, LSB-first, 38 kHz)."""

    def __init__(self, frame: list[int]) -> None:
        """Initialize with a 9-byte frame from protocol.encode()."""
        self._frame = frame

    def _encode_frame(self) -> list[int]:
        """Convert one 9-byte frame to mark/space timing list.

        Returns:
            Alternating list of signed µs durations:
            positive = mark (carrier on), negative = space (carrier off).
        """
        timings: list[int] = []

        # Leader pulse
        timings.append(LEADER_MARK_US)
        timings.append(-LEADER_SPACE_US)

        # Data: 9 bytes × 8 bits = 72 bits, LSB-first
        for byte_val in self._frame:
            for bit_pos in range(8):
                bit = (byte_val >> bit_pos) & 1
                timings.append(BIT_MARK_US)
                timings.append(-BIT_ONE_SPACE_US if bit else -BIT_ZERO_SPACE_US)

        # Trailing mark (end of frame)
        timings.append(TRAIL_MARK_US)

        return timings

    def get_raw_timings(self) -> list[int]:
        """Return signed µs timings for one frame."""
        timings = self._encode_frame()
        _LOGGER.debug("get_raw_timings: %s pulses, first 6: %s", len(timings), timings[:6])
        return timings
