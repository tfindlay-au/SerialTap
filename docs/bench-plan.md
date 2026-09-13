# Bench plan — the AS50QDFHRA session

Everything the design is waiting on from the appliance, in one place. These
requirements had accumulated across the SPDD, three ADRs, `sim/README.md` and
the OEM board notes; this is the consolidated list, so nothing is discovered
missing after the unit is closed up again.

**Write the predictions down first.** Each test below states what we expect. A
measurement that can only confirm is decoration; one that can refute is
evidence.

---

## Part 1 — Signals (Saleae)

Answers the harness. Does **not** answer anything in Part 2.

### 1.1 Pin mapping — do this first, and with a meter

The OEM board exposes **gold test points marked `GEATX` and `GEARX`** on its
underside ([haier-oem-board.md](haier-oem-board.md)). With the unit powered
**off**, buzz continuity from each service-connector pin to those test points.

That turns pin identification from "infer it from which line talks first" into
a direct measurement, and takes two minutes.

Record: connector pin number → signal, for all five.

### 1.2 Capture all five pins

| Setting | Value |
|---|---|
| Channels | 5 |
| Sample rate | ≥ 2 MS/s (≈200× oversampled at 9600 baud) |
| Threshold | 5 V logic — **set it for 5 V, not 3.3 V** |
| Duration | long enough to catch idle *and* traffic; poll intervals may be seconds apart |

Capture through a state change — set the unit to heat or cool, change the
setpoint — so the bus is not merely idling.

### 1.3 Predictions to check the capture against

| Expectation | If it differs |
|---|---|
| **104.17 µs per bit** (9600 baud) | the assumed baud is wrong; measure the narrowest pulse and divide |
| **11 bits/frame** → ~1.146 ms (8E1: start + 8 + parity + stop) | framing is not 8E1; ESPHome's `haier` config changes |
| **Idle high (mark)** | an inverted or open-drain bus; ADR 0001's assumptions need revisiting |
| **Logic high ≈ 5 V** | if it is 3.3 V, the entire level-translation design is unnecessary |
| Pin 5 static, or a supply | if it carries traffic, it is not a spare and SPDD §5.2 needs revisiting |

### 1.4 What pin 5 is

Currently connected to nothing on SerialTap, deliberately. Determine whether it
is: a second supply, a ground, a static level, or an active signal. Until then
it stays unconnected.

---

## Part 2 — Power (multimeter and a load) — **this is the fabrication gate**

A logic analyser cannot do any of this. This is SPDD §12.1 step 2, and it is
the last thing standing between the design and ordering boards.

### 2.1 Open-circuit rail voltage

Meter across 5 V and GND on the service connector, nothing loaded.

**Expected ≈5.0 V.** This matters twice over: it sets the headroom for the buck,
and the ESD array (TPD4E05U06, 5.5 V standoff) has only 0.5 V of margin over
5 V logic. **If this reads above ~5.25 V, the ESD part needs reconsidering.**

### 2.2 The V–I curve — the number the whole project waits on

Load the rail in steps and record the voltage at each. Resistors are fine; an
electronic load is nicer.

| Target current | Resistor at 5 V | Dissipation — **rate the resistor for it** |
|---|---|---|
| 100 mA | 50 Ω | 0.5 W |
| 200 mA | 25 Ω | 1.0 W |
| 300 mA | 16.7 Ω | 1.5 W |
| 400 mA | 12.5 Ω | 2.0 W |
| 500 mA | 10 Ω | 2.5 W |

Use 5 W parts, or wirewounds, and do not leave them connected while you read the
meter and think.

From this curve fall out **two** numbers the simulations are parameterised on:

- the **current limit**, where the voltage collapses
- **`RAPP`**, the source impedance — currently a 0.5 Ω guess in `rail-sag.cir`,
  and simply the slope of the curve before the knee

**Pass condition:** holds up to **370 mA**. Between 250 and 300 mA means OTA and
association on appliance power are at risk. Below 250 mA the design needs
rethinking — and *not* with more capacitance, which `rail-sag` already ruled out.

**Expectation: it passes.** The OEM board ran a Realtek RTL8720CM from this rail,
rated 450 mA at 3.3 V through its own buck — about 330 mA at 5 V, with an
800 mA inrush rating. We are asking for less than the board it replaces.

### 2.3 Behaviour *in* limit — assumed, never verified

Push past the limit and watch what happens. Every deck in `sim/` assumes a
**droop**.

- Does it **fold back**, collapsing to near zero?
- Does it **latch off** and need a power cycle?
- **Does the appliance reset?** — the failure ADR 0004 exists to prevent

This changes how conservatively `RILIM` must be set, and is the one result that
could still force a design change.

### 2.4 Sag under a pulsed load

Switch a ~250 mA load on and off at a few hundred hertz and watch the rail.
A Saleae analog channel is ideal; a scope does fine.

Confirms `RAPP` dynamically and shows whether the rail has its own bulk
capacitance helping it — which `rail-sag` does not model.

### 2.5 Pull-up on the RX line — sizes a resistor we cannot otherwise choose

With the unit **powered down**, measure resistance from the appliance's RX pin
(the line SerialTap drives) to its 5 V rail and to ground.

The [ADR 0001 amendment](adr/0001-fixed-direction-level-translation.md) showed
that SPDD §5.6's "100–330 Ω" series-resistor range **spans pass and fail**: into
a 1 kΩ pull-up, 220 Ω leaves the line at 1.1 V and 100 Ω at 0.72 V — which a
TTL-threshold input accepts only in the second case. Without this measurement,
R<sub>s</sub> is a guess.

---

## Part 3 — Mechanical (calipers, and photographs with a ruler in frame)

For the replacement board to actually drop in:

- **Mounting hole positions**, from a datum corner, and their diameter
- **Board outline** confirmation against the 22 × 54 mm already in the KiCad file
- **Connector position** along the edge, and its orientation — vertical entry is
  already assumed, and the part pinned on that basis (B05B-XASK-1-A)
- **Anything that intrudes**: standoffs, ribs, clips, cable routes
- Height clearance is already confirmed (20 mm+), so the 2.0 mm inductor and the
  vertical JST are not at risk

---

## What each result unblocks

| Measurement | Unblocks |
|---|---|
| Pin mapping + pin 5 | the harness; `docs/harness/` |
| Baud, framing, idle level | the ESPHome config; confirms ADR 0001's premises |
| Logic high voltage | confirms level translation is needed at all |
| Open-circuit rail voltage | ESD array margin (TPD4E05U06's 5.5 V standoff) |
| **Current limit** | **`RILIM` for the eFuse; SPDD §12.1 step 2; the fabrication gate** |
| Source impedance `RAPP` | replaces the guess in `rail-sag.cir`; re-run the deck |
| Behaviour in limit | how conservatively `RILIM` must be set |
| RX pull-up | sizes R<sub>s</sub>, currently a 100–330 Ω range |
| Mechanical | mounting holes and connector placement in layout |
