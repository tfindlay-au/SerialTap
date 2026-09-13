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

## Amendment, 2026-09-13: TXU0204, and optocouplers considered

The decision above named "two SN74LVC1T45, or a single dual-channel
fixed-direction part with independent per-channel direction". Looking for the
latter turned up something better, and ruled out the obvious candidates.

### The dual-channel part

**TXU0204** — 4-bit, dual-supply, fixed-direction, with two channels running
each way. TI names UART as an intended application. It improves on the original
choice in four ways:

- **Direction is fixed in silicon; there is no DIR pin at all.** This ADR asked
  for direction "hard-wired in copper" — a pin that cannot be mis-strapped is
  strictly better than one that must be strapped correctly.
- **Schmitt-trigger inputs**, which earn their keep on a metre of harness behind
  series resistors.
- **Integrated static pull-downs**, which retire this ADR's own consequence that
  "unused translator inputs must be tied off, never left floating" — the part
  does it.
- One component instead of two, and VCCA/VCCB span 1.1–5.5 V.

Two of its four channels go unused. That is the price, and the integrated
pull-downs make it a cheap one.

### The drive calculation this ADR asked for and never did

TXU0204 at a 4.5 V supply: **VOH 3.7 V at −12 mA, VOL 0.8 V at +12 mA.** Real
push-pull, against the ~4 kΩ of the TXB parts rejected above.

Driving *low* into an appliance that pulls up, through our series resistor:

| Appliance pull-up | Rs = 220 Ω | Rs = 100 Ω |
|---|---|---|
| 1 kΩ to 5 V | line reaches 1.1 V | line reaches 0.72 V |

A 5 V **CMOS** input (VIL ≈ 1.5 V) accepts both; a **TTL-threshold** input
(VIL = 0.8 V) accepts only the 100 Ω case. So SPDD §5.6's "100–330 Ω" range
spans pass and fail, and which end is safe depends on the appliance's pull-up.
**Measure that pull-up** before sizing Rs — it is on the bench list.

### Optocouplers: considered, rejected

Isolating the UART was raised — TLP2270 class, 20 Mbps, comfortably fast enough
for FR-3. Rejected, for reasons worth recording so the idea is not revisited:

1. **The isolation would not exist.** FR-2 powers the board from the appliance
   over the same connector, so ground is already common. A barrier across TX and
   RX with the 5 V and GND pins running past it is a barrier with a wire around
   it. Real isolation needs an isolated DC-DC to split the grounds, which
   contradicts the premise of the board.
2. **It loads the appliance's driver.** In the RX direction the LED is driven by
   the appliance's TX pin — milliamps, where a CMOS translator input draws
   microamps. That reintroduces from the other end exactly the unknown-load risk
   this ADR rejected the TXB parts for.
3. **Optocouplers invert**, and UART idles high. Correcting that needs ESP32
   UART signal inversion exposed through ESPHome, and SPDD §2 puts protocol work
   beyond configuring the existing `haier` component out of scope.
4. **Current**: 10–32 mA for two channels, 4–13% of the 5 V budget.

Isolation would be the right answer for an externally powered *diagnostic* tool
that only taps data. That is a different product from the one FR-2 describes.

### Decision

**TXU0204**, package still to be chosen. The reasoning above stands whichever
package is picked.
