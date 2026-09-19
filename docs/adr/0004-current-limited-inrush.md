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

## Amendment, 2026-09-12: the eFuse is modelled behaviourally

SPDD §7.2 made a published vendor SPICE model a *selection criterion* for both
the buck and the eFuse, on the grounds that simulation gates fabrication.

Running [`sim/inrush.cir`](../../sim/inrush.cir) showed that criterion does no
real work for the eFuse. The deck's question — what the appliance sees at
plug-in — is answered by the current limit alone: a flat current into the bulk
capacitor for Q/I seconds, with success or failure turning entirely on whether
that current sits below the appliance's own limit. A behavioural constant-current
block answers it exactly. What a vendor model would add is response time, in
microseconds, and soft-start shape — neither of which moves the sizing.

That is *not* true of the buck. `buck-load-step` asks a control-loop question,
and overshoot, undershoot and settling are properties of the compensation, the
inductor and the output capacitor together. Only a vendor model answers it.

### Decision

The vendor-SPICE-model criterion of SPDD §7.2 applies to the **buck only**. The
eFuse is chosen on its behaviour — programmable limit, limit accuracy, package,
what else it protects against — and modelled behaviourally in
[`sim/models/behavioral.lib`](../../sim/models/behavioral.lib). TPS2553-class
remains the target.

### Consequences

- The eFuse field is no longer narrowed to parts picked for their model.
- **Current-limit accuracy becomes the specification that matters most.** It is
  what collapses the 300–370 mA appliance requirement into a single number; see
  [sim/README.md](../../sim/README.md).
- The deck cannot see a real part's response time, so the contact-event current
  it reports (`ispike`) is indicative only, and is documented as such.

## Amendment, 2026-09-19: `RILIM` is set from inference

See [ADR 0007](0007-rail-limit-inferred-not-measured.md). The rail measurement
this ADR made `RILIM` conditional on is not being taken, because the only design
output of that measurement is `RILIM` itself, and this ADR's own decision made
that a single resistor rather than a layout or part commitment.

The consequence above — "the limit can be set deliberately below a *measured*
appliance capability, so the board is provably polite to the rail it is plugged
into" — no longer holds as written. It weakens to politely designed against
inferred limits, and the named foldback fault mode becomes more likely to be met
for the first time at bring-up rather than on the bench. ADR 0007 records the
evidence, the residual risk and the reversal condition.
