# Bench plan — the AS50QDFHRA session

Everything the design is waiting on from the appliance, in one place. These
requirements had accumulated across the SPDD, three ADRs, `sim/README.md` and
the OEM board notes; this is the consolidated list, so nothing is discovered
missing after the unit is closed up again.

**Results from the 2026-09-16 session are in [bench-results.md](bench-results.md)** — the rail voltage and the logic levels are answered; the power tests are not.

**Write the predictions down first.** Each test below states what we expect. A
measurement that can only confirm is decoration; one that can refute is
evidence.

---

## Part 1 — Signals (Saleae)

Answers the harness. Does **not** answer anything in Part 2.

### 1.1 Pin mapping — ~~do this first~~ settled 2026-09-20

**No longer required.** The numbering was being read from the wrong end of the
connector. Corrected, and naming the signals from the **appliance's** side as
this document does, the order is 5 V, appliance RX, appliance TX, spare,
ground — which is what SPDD §5.2 calls 5 V, TX, RX, spare, GND from the
**board's** side, TX being the pin the board drives. Direction is fixed by the
working TinyS3 link (pin 2 ← TinyS3 TX, pin 3 → TinyS3 RX), not by inference. The continuity check below would now
only re-confirm it, and is kept for anyone repeating the work on another unit.

#### The check, as originally written

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
| Threshold | a comparator level **between** the bus's low and high — **not 5.0 V**, which sits at the high rail and reads as all-low. Default 1.2 V; see `bench/capture_uart.py` |
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
| Pin 4 static, or a supply | if it carries traffic, it is not a spare and SPDD §5.2 needs revisiting |

### 1.4 What pin 4 is

Currently connected to nothing on SerialTap, deliberately. Determine whether it
is: a second supply, a ground, a static level, or an active signal. Until then
it stays unconnected.

---

## Part 2 — Power (multimeter and a load) — **no longer the fabrication gate**

> **Revised 2026-09-19 by
> [ADR 0007](adr/0007-rail-limit-inferred-not-measured.md).** Sections 2.2 and
> 2.3 below, the resistor-loaded current-voltage curve and the behaviour in
> limit, are **demoted to optional bring-up characterisation.** Their only
> design output is `RILIM`, one resistor, which ADR 0004 deliberately made
> independent of everything else on the board. Getting it wrong costs a resistor
> swap, not a revision, so it cannot gate fabrication. `RILIM` is now set from
> inference; read ADR 0007 for the reasoning, the three lines of evidence behind
> it, the rigour it gives up, and the conditions that would reinstate the test.
>
> **Still required, and all cheap:** a meter in series with the 5 V lead for the
> first measured current, and a cold
> power-cycle test for the unexplained manual reset of 2026-09-19. Section 2.4,
> sag under a pulsed load, should be done with the **ESP32 as its own load**
> rather than with resistors.
>
> The rest of Part 2 is kept verbatim: the method is sound and the wiring,
> Kelvin-sensing and safety notes all still apply if the test is reinstated.

A logic analyser cannot do any of this. This was SPDD §12.1 step 2.

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

A **120 Ω** resistor across 5 V draws 41.7 mA and dissipates **0.21 W** — 35% of
a 0.6 W part's rating. Parallel resistors share the current, so *each* part
still sees only 0.21 W however many are fitted. The array carries the watts; no
individual resistor is ever stressed.

| 120 Ω resistors | Load | Each dissipates | Array total |
|---|---|---|---|
| 3 | 125 mA | 0.21 W | 0.6 W |
| 6 | 250 mA | 0.21 W | 1.3 W |
| 9 | 375 mA | 0.21 W | 1.9 W |
| 11 | 458 mA | 0.21 W | 2.3 W |

**Never fit anything below ~100 Ω on its own** — at 5 V, 0.6 W is reached at
42 Ω, and a part run at its full rating is a part run too hot to touch. 120 Ω
sits at about a third of rating, which is where a resistor should live.

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
than bunching, since 0.21 W runs a part at 50–70 °C and breadboard plastic
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

#### Terminology: the resistors *are* the load

A "load" is anything that draws current from a supply. The resistors are not
connected *to* a load — they **are** it.

Resistors rather than an LED or a spare ESP32, because the method depends on
knowing the current without an ammeter. A resistor obeys `I = V/R` exactly; an
LED's non-linear forward curve does not, and draws only milliamps anyway. A real
ESP32 draws a realistic but uncontrolled and bursty profile that cannot be swept
or calculated — and would brown out under precisely the conditions being
measured, so the instrument would fail at the same moment as the subject.

The real board does become the load eventually. That is SPDD §12.1 step 4, bench
bring-up, and it happens after fabrication — which this test gates.

#### Step sequence

Work upward, adding one resistor at a time. Twenty 120 Ω parts make this a
single uniform staircase — **41.7 mA per step, all the way**. No swapping
between resistor values, and no step large enough to jump past a knee.

| Phase | Fitted | Load |
|---|---|---|
| A | 1 × 120 Ω | 42 mA |
| A | 2 × 120 Ω | 83 mA |
| A | 4 × 120 Ω | 167 mA |
| A | 6 × 120 Ω | 250 mA |
| B | 8 × 120 Ω | 333 mA |
| B | 9 × 120 Ω | 375 mA — nominally clears the pass condition |
| **C** | **10 × 120 Ω** | **417 mA — the pass condition, with margin** |
| C | 11 × 120 Ω | 458 mA |

Take the **pass at 10, not 9**. 375 mA is the figure at a stiff 5.00 V; the
actual current is lower, because the rail droops under load and the breadboard
drops its own share. Run the numbers through `analyse_rail.py` with a plausible
0.4 Ω source impedance and 0.15 Ω of rig resistance and nine resistors deliver
**365 mA — a fail**, on a rail that is in fact perfectly healthy. Ten delivers
404 mA and settles it.

This is the trap in reading the pass condition off the nominal table: 370 mA is
required *at the appliance*, and every millivolt of droop between the connector
and the resistors takes current out of the number. The `AN0`/`AN1` pair below
is what makes that visible rather than silent.

**Stop at the first sign of sag, or at 11.** Beyond that proves nothing the
design needs to know.

#### Resistor count

**Twenty 120 Ω 0.6 W parts are in hand, and that is comfortably enough** — the
whole sweep needs eleven. The surplus is useful anyway: the spares cover a
duff part, and let the pulsed-load test of §2.4 be built up separately without
dismantling this array.

| Fitted | Load | Note |
|---|---|---|
| 6 | 250 mA | the pulsed-load figure for §2.4 |
| 9 | 375 mA | nominal pass |
| 10 | 417 mA | **pass with margin — the target** |
| 11 | 458 mA | stop here |

No second resistor value is needed, and no 5 W wirewound. An earlier version of
this plan mixed 130 Ω with a single 15 Ω to reach the target; that was a
workaround for having only seven parts, and it cost the uniform step size.
Dropping it is a straight improvement — see [the slope note](#what-the-curve-yields).

#### The scripts that drive this

`bench/` holds the tooling, against Logic 2's automation server (2.4.46) and
the Logic Pro 8:

| Script | Does |
|---|---|
| `check.py` | pre-flight — is Logic 2 reachable, is the device present |
| `probe.py` | quick voltmeter on any channels; check probe placement before trusting a run |
| `calibrate.py` | measures the AN0/AN1 channel offset — **required before a rail run** |
| `capture_uart.py` | Part 1.2, five digital channels with an Async Serial decode |
| `capture_rail.py` | this test — a short capture per step, read out before you fit the next |
| `analyse_rail.py` | the summary pass — `RAPP`, the knee, the verdict |

Measured on the Logic Pro 8 (id `5701262AE78884C9`) on 2026-09-16, against a
bench PSU:

| | Value | Consequence |
|---|---|---|
| Analog rates accepted | **781.25 k, 1.5625 M, 3.125 M, 6.25 M, 12.5 M, 50 MS/s** — the same set for one or two channels, and 25 MS/s is *not* accepted | 781.25 kS/s is the floor and is already far more than the staircase needs, which is why each step is a separate short capture rather than one long recording. Go higher only for the transients of 2.3 and 2.4. Logic 2's UI offers slower rates via downsampling — **do not use them**: the precision here comes from taking a median over ~1.5 M samples, and it would also alias the appliance's own switching noise |
| CSV export precision | **3 decimals — 1 mV** | too coarse for a 6 mV rig drop, so the scripts export **binary** (float32) and parse it directly; also 6× smaller and 7× faster |
| Channel mismatch | **not a fixed offset** — `offset(V) = 3.083 mV/V × V − 11.714 mV`, perfectly linear over 4.5/5.0/5.5 V (worst residual 0.000 mV) | comparable to the rig drop itself, so `capture_rail.py` refuses to run without `calibrate.py`. A single-point correction at 5 V would leave up to 0.62 mV across a 200 mV droop; the linear form leaves ~0 |
| Noise | ~2.5 mV rms, averaged over ~1.5 M samples per step | negligible after the median; sub-millivolt resolution |
| AN0 absolute error | within ~3 mV of the PSU's dial across 4.5–5.5 V | that figure is PSU error and Saleae error combined and cannot be separated without a reference meter — which does not matter, because every quantity here is a *difference* |
| Repeatability | +3.701 mV measured twice, minutes apart, with an excursion to 4.5 V between — identical to the microvolt | the medians are trustworthy to well under a millivolt |

Two prerequisites, both one-time:

1. **Logic 2 → Preferences → Automation → "Enable automation server"**, then
   restart Logic 2. It is off by default and nothing here works without it.
2. The **`logic2-automation`** package, in `bench/.venv`. Note that the
   similarly named `saleae` package on PyPI is the *Logic 1.x* library and does
   not talk to Logic 2 at all.

`analyse_rail.py` was checked against synthetic staircases with a known source
impedance before the bench session — a healthy rail and one with a knee at a
known current. It recovers `RAPP` and the open-circuit intercept exactly in
both. The knee case earned its keep: the first version reported **PASS on a
rail that had collapsed**, because it judged the result on current alone. A rail
in foldback will happily push 370 mA through a resistor while being useless to
the buck. The pass condition is now **both** parts of `sim/README.md`'s
requirement — 370 mA *while the rail stays above `VBUCKREQ`, 4.0 V* — and
`RAPP` is fitted only over the linear region, since points past the knee
otherwise corrupt the very line they are judged against.

It is a tested instrument, not a first draft written at the appliance.

#### Record it with the Saleae's analog channel

Logic Pro 8 takes ±10 V on its analog inputs, so probe the 5 V rail directly —
no divider. Record continuously while adding resistors and the result is a
**voltage staircase**, one plateau per resistor.

No ammeter is needed. With N resistors of value R, the current is exactly:

```
I = V × N / R
```

so the measured voltage and the count give the current. **The analog trace is
the V–I curve.**

Measure the resistors with a meter first — and measure *all* of the ones going
in, not a sample. It costs a couple of minutes and buys two things. Use their
**mean** as `R`: parallel conductances add, so individual tolerance errors
average down rather than accumulating, and the array's effective value is known
far better than any single 5% part. And a resistor that reads wrong gets found
on the bench rather than as an unexplained kink in the curve.

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
- Resistors will be warm at 0.21 W. Hot enough to notice, not to damage
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

### 2.5 Pull-up on the RX line — sizes the UART series resistors

With the unit **powered down**, measure resistance from the appliance's RX pin
(the line SerialTap drives) to its 5 V rail and to ground.

The result is recorded in [bench-results.md](bench-results.md): RX pin 2 reads
5.84/5.80 kΩ to GND and 4.62 kΩ to 5 V, independent of probe polarity. Use
**330 Ω, 1%** for both UART series resistors. This is now a design input, not a
100–330 Ω guess.

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
| ~~Pin mapping~~ **done**; what pin 4 carries | the harness; `docs/harness/` |
| Baud, framing, idle level | the ESPHome config; confirms ADR 0001's premises |
| Logic high voltage | confirms level translation is needed at all |
| Open-circuit rail voltage | ESD array margin (TPD4E05U06's 5.5 V standoff) |
| Current limit | Optional bring-up characterisation; validates or revises the inferred `RILIM` under ADR 0007 |
| Source impedance `RAPP` | replaces the guess in `rail-sag.cir`; re-run the deck |
| Behaviour in limit | how conservatively `RILIM` must be set |
| RX pull-up | **Complete:** sets both UART series resistors to 330 Ω, 1% |
| Mechanical | mounting holes and connector placement in layout |
