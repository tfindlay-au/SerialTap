# 3. Synchronous buck, not an LDO, for the 3.3 V rail

Date: 2026-09-12

## Status

Accepted

## Context

The board is normally powered from the target appliance's 5 V service rail. On
the reference target — a Haier AS50QDFHRA — that rail is current-limited and its
actual capability has not been measured. Assume it is weak.

An ESP32-C3 peaks around **335 mA** during RF transmit. The two ways to get
3.3 V from 5 V behave differently against a weak source:

| | Draw from 5 V at peak | Heat dissipated |
|---|---|---|
| LDO | ~335 mA | ~0.57 W |
| Buck at ~90% | ~250 mA | ~0.12 W |

The current saving is about 25% — real, but not dramatic. The heat difference
is the larger factor: an LDO turning 0.57 W into heat in a small package, on a
bare board with no enclosure, mounted inside an HVAC unit, is an unattractive
combination.

An LDO is otherwise the easier choice: one part, two capacitors, no inductor,
no switching noise near a PCB antenna, trivial layout.

`daikin-esp`'s `esp-daikin-r1.0` — the closest prior board in this codebase —
already uses a DC-DC rather than an LDO on an ESP32-C3.

## Decision

Use a synchronous buck converter for the 3.3 V rail.

## Consequences

- Roughly 85 mA less peak draw on an appliance rail whose limits are unknown,
  and ~0.45 W less heat on a board with no enclosure to conduct it away.
- Switching node and inductor must be kept away from the C3-MINI-1's PCB
  antenna, and the input loop kept tight. This is the main reason the board is
  4-layer with a continuous ground plane on L2.
- Higher part count and a component — the inductor — whose choice is
  performance-critical and must therefore be pinned by hand rather than left to
  atopile's automatic part picker.
- Switching ripple on the 3.3 V rail. Acceptable: there is nothing analogue on
  this board, and the ESP32's own supply rejection is designed for it.
