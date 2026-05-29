# Timer Analysis

> Timer functionality has NOT been captured yet.
> This document contains hypotheses and a capture strategy.

## Unused Frame Space

| Location | Free Bits | Notes |
|----------|-----------|-------|
| B2 | 8 bits | Entire byte always 0x00 |
| B4 | 8 bits | Entire byte always 0x00 |
| B5 | 8 bits | Entire byte always 0x00 |
| B7 bits [7:6],[3:1] | 5 bits | Always 0 in all captures |
| B6 bit [4],[1:0] | 3 bits | Always 0 in all captures |

## Most Likely Hypothesis

Timer data is **embedded in the existing 9-byte frame** (like the LG wired
controller protocol), using B4/B5 for hours and B7 unused bits for flags.

## Predicted Timer Hour Values (bit-reversed)

| Hours | rev8(hours) |
|-------|-------------|
| 1 | 0x80 |
| 2 | 0x40 |
| 3 | 0xC0 |
| 4 | 0x20 |
| 5 | 0xA0 |
| 6 | 0x60 |
| 12 | 0x30 |
| 24 | 0x18 |

## Capture Strategy

1. Timer OFF 1 hour (baseline)
2. Timer OFF 2 hours (reveals encoding)
3. Timer ON 1 hour (reveals on/off flag)
4. Timer cancel (reveals reset)
5. Timer at different temp (confirms state embedding)

See `timer_analysis.txt` in this conversation for full details.
