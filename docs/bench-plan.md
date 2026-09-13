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

**You do not have to find the current limit.** The requirement is that the rail
holds up past **370 mA**. Proving that is a pass/fail, and much safer than
hunting for the cliff edge.

#### Method: add one resistor at a time

Do not build a heavy load and plug it in. Build it up in place, watching the
voltage, and stop the moment it starts to fall.

A **130 Ω** resistor across 5 V draws 38.5 mA and dissipates **0.19 W** — 38% of
a 0.5 W part's rating. Parallel resistors share the current, so *each* part
still sees only 0.19 W however many are fitted. The array carries the watts; no
individual resistor is ever stressed.

| 130 Ω resistors | Load | Each dissipates | Array total |
|---|---|---|---|
| 3 | 115 mA | 0.19 W | 0.6 W |
| 5 | 192 mA | 0.19 W | 1.0 W |
| 8 | 308 mA | 0.19 W | 1.5 W |
| 11 | 423 mA | 0.19 W | 2.1 W |

**Never fit anything below ~130 Ω on its own** — at 5 V a 50 Ω part would be at
its full 0.5 W rating, and anything lower exceeds it.

#### Wiring — both across the rail, never in series

The load and the probe both connect **across** 5 V and ground. The Saleae is a
voltmeter with 1 MΩ inputs; nothing passes through it.

```
  appliance 5V ──┬───────────────┬── Saleae AN0 (+)
                 │               │
            [resistors]          │        <- load: 5 V to GND
                 │               │
  appliance GND ─┴───────────────┴── Saleae GND
```

Load the pin that **test 1.1 confirmed is the 5 V supply** — not connector pin
5, which is the unknown one this design deliberately leaves unconnected.

A small breadboard is a good way to hold the array: resistors go in one at a
time with no hot parts held by hand. Two cautions — **spread them out** rather
than bunching, since 0.19 W runs a part at 50–70 °C and breadboard plastic
softens around 80 °C; and keep each step to seconds.

#### Use two analog channels, because breadboard resistance would corrupt this

Breadboard contacts and rails come to perhaps 50–200 mΩ. At 400 mA that is
20–80 mV — against an expected droop of only 100–200 mV, so it would land
squarely on top of the measurement. Logic Pro 8 has eight analog channels;
spend two:

| Channel | Where | Gives |
|---|---|---|
| `AN0` | at the appliance connector pins | what the appliance actually delivers |
| `AN1` | at the breadboard rails, by the resistors | what the load actually sees |

Then:

- **current** is `I = V_AN1 × N / R` — accurate, because AN1 is the voltage
  genuinely across the resistors
- the **appliance's curve** is that current against `AN0`
- `AN0 − AN1` is the test rig's own drop, now measured and subtractable rather
  than silently folded into `RAPP`

#### Resistor count

7 × 130 Ω reaches 269 mA — short of the 370 mA pass condition. Options:

| Combination | Load | Parts |
|---|---|---|
| 7 × 130 Ω | 269 mA | 7 |
| 7 × 130 + 8 × 390 Ω | **372 mA** | 15 |
| 7 × 130 + 12 × 390 Ω | 423 mA | 19 |
| one 15 Ω 5 W | 333 mA | 1 |
| one 12 Ω 10 W | 417 mA | 1 |

390 Ω contributes 12.8 mA at 0.064 W each — very safe, just small steps.

Even if only 269 mA is reached, the result is not wasted: if the curve is still
straight and stiff there, with no sign of bending, the limit is comfortably
above — which, with the OEM module's 450 mA rating, is strong evidence though
not proof.

#### Record it with the Saleae's analog channel

Logic Pro 8 takes ±10 V on its analog inputs, so probe the 5 V rail directly —
no divider. Record continuously while adding resistors and the result is a
**voltage staircase**, one plateau per resistor.

No ammeter is needed. With N resistors of value R, the current is exactly:

```
I = V × N / R
```

so the measured voltage and the count give the current. **The analog trace is
the V–I curve.** Measure two or three of the resistors with a meter first to
confirm their actual value.

#### What the curve yields

- the **slope before the knee** is `RAPP`, the source impedance — currently a
  0.5 Ω guess in `rail-sag.cir`
- the **knee**, if reached, is the current limit
- **holding ≥370 mA is the pass condition**, and is enough on its own

**Expectation: it passes.** The OEM board ran a Realtek RTL8720CM from this
rail, rated 450 mA at 3.3 V through its own buck — about 330 mA at 5 V, with an
800 mA inrush rating. We are asking for less than the board being replaced.

#### Safety

- Work up from light to heavy. Never start with the biggest load
- **Stop as soon as the voltage begins to sag** — that is the answer, not a
  problem to push through
- Check polarity twice before connecting. 5 V and GND, nothing else
- Keep the load connected for seconds at a time, not minutes
- Resistors will be warm at 0.19 W. Hot enough to notice, not to damage
- Have a way to kill power quickly
- Never short the rail. A dead short is the one thing that could damage the
  appliance's supply, and it proves nothing

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
