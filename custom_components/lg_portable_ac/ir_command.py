"""IR command class for LG Portable AC.

Converts a 9-byte protocol frame into raw microsecond mark/space
timings suitable for the HA 2026.4 infrared platform.

Subclasses infrared_protocols.Command and implements get_raw_timings().
"""

from __future__ import annotations

from infrared_protocols.commands import Command

# Timing constants (microseconds), derived from Broadlink captures.
# See docs/protocol.md section 1 for derivation from 26.3 us ticks.
LEADER_MARK_US: int = 3604   # ~137 ticks * 26.3 us
LEADER_SPACE_US: int = 4392  # ~167 ticks * 26.3 us
BIT_MARK_US: int = 526       # ~20 ticks  * 26.3 us
BIT_ZERO_SPACE_US: int = 395 # ~15 ticks  * 26.3 us
BIT_ONE_SPACE_US: int = 1657 # ~63 ticks  * 26.3 us
TRAIL_MARK_US: int = 526     # Same as bit mark


class LGPortableACCommand(Command):
    """IR command for LG Portable AC (72-bit PDM, LSB-first, 38 kHz)."""

    def __init__(
        self,
        frame: list[int],
        repeat_count: int = 0,
    ) -> None:
        """Initialize with a 9-byte frame from protocol.encode().

        Args:
            frame: 9-byte list from protocol.encode().
            repeat_count: Number of times to repeat the frame (0 = send once).
        """
        super().__init__(modulation=38000, repeat_count=repeat_count)
        self._frame = frame

    def _encode_frame(self) -> list[int]:
        """Convert one 9-byte frame to mark/space timing list.

        Returns:
            List of ints: positive = mark (us), negative = space (us).
        """
        timings: list[int] = []

        # Leader pulse
        timings.append(LEADER_MARK_US)
        timings.append(-LEADER_SPACE_US)

        # Data: 9 bytes x 8 bits = 72 bits, transmitted LSB-first
        for byte_val in self._frame:
            for bit_pos in range(8):  # LSB first
                bit = (byte_val >> bit_pos) & 1
                timings.append(BIT_MARK_US)
                if bit:
                    timings.append(-BIT_ONE_SPACE_US)
                else:
                    timings.append(-BIT_ZERO_SPACE_US)

        # Trailing mark (signals end of frame)
        timings.append(TRAIL_MARK_US)

        return timings

    def get_raw_timings(self) -> list[int]:
        """Return raw IR timings for one frame transmission.

        Returns:
            List of ints: alternating mark (+) and space (-) durations
            in microseconds. Includes leader, 72 data bits, and trailer.
            The emitter handles repetition via self.repeat_count.
        """
        return self._encode_frame()
