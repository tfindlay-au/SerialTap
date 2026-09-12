# 1. Fixed-direction level translation

Date: 2026-09-12

## Status

Accepted

## Context

The board exposes one 5 V UART port, needing translation in both directions:
3.3 V → 5 V on TX, 5 V → 3.3 V on RX.

The obvious part for this job is an auto-direction translator (TXB0104,
TXS0104). One 4-channel chip covers the whole port, there is no direction pin to
route, and every hobby breakout board uses them.

Auto-direction parts achieve their bidirectionality with deliberately weak
output drivers (~4 kΩ) plus edge-accelerating one-shots. That works only when
nothing else on the line has comparable drive strength. Target devices in the
field routinely have pull-ups, series resistors, long cable runs, or
open-drain-ish outputs. The failure mode is not a clean failure: the board
works on the bench against a USB-serial adapter and then glitches or latches
against the real appliance. Diagnosing that after boards are assembled and
installed is expensive.

UART direction is fixed and known at design time. Nothing about this
application requires direction to be discovered at runtime.

## Decision

Use fixed-direction dual-supply buffers, with direction hard-wired per channel
— two SN74LVC1T45 (one A→B for TX, one B→A for RX), or a single dual-channel
fixed-direction part with independent per-channel direction.

## Consequences

- Push-pull drive on both sides. Tolerant of pull-ups, cable capacitance, and
  higher baud rates than an auto-direction part would survive.
- No auto-direction failure modes to debug during bring-up.
- Slightly higher part count and BOM line count than a single auto-direction chip.
- Direction is frozen in copper. A future target needing a half-duplex or
  single-wire bus on this port would need a board revision, not a firmware
  change. Accepted: that is a different product.
- Unused translator inputs must be tied off, not left floating.
