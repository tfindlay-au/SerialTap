# 4. Current-limited inrush protection, not slew-rate-limited

Date: 2026-09-12

## Status

Accepted

Amends the power-path decision that originally specified a slew-controlled load
switch.

## Context

The board is powered from an appliance's 5 V service rail whose current
capability is unknown and assumed weak. It carries ≥470 µF of bulk capacitance,
which exists to ride out the C3's ~335 mA WiFi transmit bursts.

That bulk capacitor is also a problem at plug-in. A large discharged capacitor
across a weak rail looks like a short, and can trip or reset the appliance
supplying it.

The idiomatic answer is a slew-rate-limited load switch (TPS22918 class), which
ramps the output and so bounds inrush as `I = C × dV/dt`. With 470 µF:

| Rise time | Inrush |
|---|---|
| 1 ms | 2.35 A |
| 10 ms | 235 mA |
| 50 ms | 47 mA |

Two problems. First, tens of milliseconds are needed, and many slew-limited
switches top out around 10 ms. Second and more fundamental: **the bound depends
on the bulk capacitance.** Increasing the cap later — a likely response if the
Haier rail turns out marginal — would silently raise inrush, coupling two
mitigations that should be independent.

A current-limited switch or eFuse bounds the draw directly. The limit is set by
a resistor, holds regardless of what capacitance sits behind it, and can be set
below whatever the appliance is known to supply.

## Decision

Use a current-limited switch / eFuse (TPS2553 class) with a programmable current
limit on the 5 V input, placed between the input fuse and the ideal-diode OR.

## Consequences

- Inrush is bounded by a resistor, not by a capacitor value. Bulk capacitance
  and inrush protection become independent knobs.
- The limit can be set deliberately below a measured appliance capability, so
  the board is provably polite to the rail it is plugged into.
- Many parts in this class also provide overcurrent, overvoltage and reverse
  protection, potentially making the separate resettable fuse redundant. Decided
  at part selection.
- The limit resistor cannot be chosen until the `inrush` simulation deck and the
  Haier rail measurement are done. It is a gated value, not a guess.
- Slightly more expensive than a plain slew-limited load switch, and it
  introduces a fault mode — current-limit foldback on a genuinely weak rail —
  that must be distinguished from a brownout during bring-up.
