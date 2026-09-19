# 7. The appliance rail's current limit is inferred, not measured

Date: 2026-09-19

## Status

Accepted

Amends [ADR 0004](0004-current-limited-inrush.md) and demotes Part 2.2 and 2.3
of [bench-plan.md](../bench-plan.md) from fabrication gate to optional
bring-up characterisation.

## Context

[bench-plan.md](../bench-plan.md) Part 2 specifies loading the appliance's 5 V
service rail with switched power resistors to plot its current-voltage curve,
find its current limit, and observe what it does in limit. It is labelled "the
fabrication gate" and SPDD §12.1 step 2 treats it the same way.

That framing predates [ADR 0004](0004-current-limited-inrush.md). ADR 0004
chose a current-limited eFuse over a slew-rate-limited load switch precisely so
that inrush would be bounded by a resistor rather than by the bulk capacitance,
making the two independent knobs. The consequence nobody followed through: the
only design output of the whole load test is `RILIM`, a single resistor. A test
whose output is one resistor value cannot gate fabrication, because getting it
wrong costs a resistor swap on an assembled board, not a revision.

The test also carries real cost. It means deliberately driving an appliance's
service rail into current limit, with dissipating resistors, at the top of a
ladder, with some risk to the appliance's control board.

Three independent lines of evidence now bear on whether the rail can carry
SerialTap:

1. **Design intent.** The rail was built to feed the OEM `WCATA008` module,
   whose `RTL8720CM` is rated 450 mA at 3.3 V and 800 mA inrush, referred
   through the OEM's own buck to roughly 330 mA steady and 590 mA inrush at
   5 V ([haier-oem-board.md](../haier-oem-board.md)). SerialTap's C3 peaks
   lower, and its eFuse makes it gentler at plug-in than the board it replaces.
2. **Direct observation, 2026-09-19.** A TinyS3 has run from the rail, with
   Wi-Fi associated and transmitting, powered from pin 5 with no USB
   ([gea3.md](../gea3.md)). Whatever regulator that board carries, it is not a
   gentler load than SerialTap: same job, larger SoC. If it is a linear
   regulator, its draw from the 5 V rail is roughly 40% higher than
   SerialTap's buck would be for the same 3.3 V work. **Worth confirming from
   the TinyS3 schematic, because it strengthens this argument.**
3. **Simulation.** `sim/rail-sag` already showed that more bulk capacitance
   would not rescue a weak rail, so there is no design lever being declined.

Each of these is weaker than a measurement. Point 1 is a datasheet rating read
as design intent, two inferences deep. Point 2 is qualitative: nobody has yet
put a meter in series, so "it works" is not a number.

## Decision

**Do not run the resistor load test as a precondition for fabrication.** Set
`RILIM` from inference: above SerialTap's worst-case steady draw so it cannot
nuisance-trip, and below the OEM-implied floor of the rail's capability so the
board still limits before the rail does. Account for the TPS2553's limit
accuracy at both ends of its tolerance, not just nominal.

Fit the resistor, and correct it during bring-up if the board misbehaves.

## Consequences

- **Fabrication is no longer gated on a bench measurement of the rail.** The
  remaining gates are the project library, the passives, schematic capture and
  layout.
- **ADR 0004's claim weakens, and this is the real cost.** "The limit can be
  set deliberately below a *measured* appliance capability, so the board is
  provably polite to the rail" becomes politely designed against inferred
  limits. That is a reduction in rigour and is recorded as such rather than
  quietly dropped.
- **ADR 0004's named fault mode becomes more likely to appear at bring-up.**
  Current-limit foldback on a genuinely weak rail must be distinguished from a
  brownout, and we now go into bring-up without having seen what this rail does
  in limit.
- `RILIM` remains a deliberately reasoned value, not a guess, but its
  justification is now documentary rather than empirical.

## Reversal condition

Reinstate the load test if bring-up shows any of: the board failing to start on
a rising rail, the eFuse tripping in normal operation, or the appliance
resetting or faulting when SerialTap is plugged in.

## Still required, because all three are free or nearly so

1. **Series current measurement.** A meter in series with the 5 V lead to the
   TinyS3, on the 10 A jack. Idle and Wi-Fi peak. This is the first measured
   current in the project and it needs no added load and no resistors.
2. **Cold power-cycle test, twice, at the isolator.** The board needed a manual
   reset on its first power-up from the appliance on 2026-09-19 and that is
   unexplained ([gea3.md](../gea3.md)). It is the one observed symptom
   consistent with a marginal rail, and unlike the current limit it could
   genuinely change the design, because it concerns enable and reset timing on
   a rising rail.
3. **Pull-up measurement on the RX line**, bench-plan 2.5, with the unit off.
   It sizes R<sub>s</sub>, currently a 100–330 Ω guess, and the 2026-09-16
   reading of roughly 1.387 of unrecorded units was never pinned down.

And when convenient, sag under a load step (bench-plan 2.4) **with the ESP32 as
its own load** rather than with resistors: Wi-Fi transmitting continuously,
both cores busy, LED at full brightness, stepped from idle, with the rail on
the calibrated Saleae analog channel and `bench/analyse_rail.py`. That answers
the pulsed-load question in firmware, with no dissipating parts and no rewiring
at the top of a ladder.
