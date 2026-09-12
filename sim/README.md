# Power-path simulation

Standalone LTspice decks, deliberately outside the atopile → KiCad flow
([SPDD §5.8](../docs/SPDD.md)). They model the **power path only**; nothing
else on the board has a usable model or a question worth simulating.

Simulation **gates fabrication** ([SPDD §12.1](../docs/SPDD.md) step 1). The
point is not a pass mark — it is a *number* to go and measure the appliance
against.

## Running

```sh
./run.py            # every deck
./run.py rail-sag   # one deck
```

`run.py` drives `LTspice -b`, decodes the UTF-16 log it leaves behind, joins
each `.step` line to its `.meas` results and writes a table to
`results/<deck>.md`. Everything in `results/` is generated — re-run, never
edit. Stdlib Python only; no dependency outside this repo.

LTspice lives at `/Applications/LTspice.app/Contents/MacOS/LTspice`.

## The decks

| Deck | Question | State |
|---|---|---|
| `rail-sag.cir` | Given a current-limited source, bulk capacitance and WiFi transmit bursts, does the 5 V rail stay high enough for the buck to hold 3V3? | runs |
| `inrush.cir` | What does the appliance see at plug-in, with the eFuse limit set to a given value? | runs |
| `buck-load-step.cir` | Does the buck recover from a 30 → 250 mA step without undershooting brownout? | **blocked** — see below |

### buck-load-step is blocked, deliberately

Its question is entirely about the converter's **control loop**: overshoot,
undershoot and settling on a load step are properties of the compensation, the
inductor and the output capacitance together. A behavioural constant-power
block cannot answer it, and a deck that appeared to answer it would be worse
than no deck at all — it would manufacture exactly the false confidence
[CLAUDE.md](../CLAUDE.md) warns about.

It needs, in this order:

1. the buck MPN chosen (SPDD §7.2 requires one whose vendor publishes a SPICE
   model — a selection criterion, not a preference);
2. that vendor model dropped into `models/`;
3. the inductor and output capacitors pinned, because they are half the loop.

## Model fidelity

`models/behavioral.lib` holds **behavioural** blocks, not vendor models. They
describe the terminal behaviour the datasheets promise over the timescales
these decks care about (~µs to ~1 s). Where a vendor model exists for the part
finally chosen, it replaces the block.

What they deliberately do not contain, and what therefore cannot be concluded
from these decks:

- **No switching.** The buck is a constant-power load, not a converter. Ripple,
  switching harmonics and EMI are not simulated here — EMC is
  `kicad-happy`'s job after layout.
- **No control loop.** Hence `buck-load-step` being blocked.
- **Instant limiter response.** `CLIM` reaches its limit in one timestep. A
  real TPS2553-class eFuse takes microseconds, so `inrush`'s `ispike` column
  understates the true contact event. Connector and cable inductance are not
  modelled either.
- **No temperature, no tolerance.** Every value is nominal at 27 °C. Tolerance
  is applied by hand when reading the results (see the eFuse arithmetic below).
- **Capacitance is a constant.** DC-bias derating is applied when choosing the
  parameter value (SPDD §7.1), not modelled as a function of voltage.

## What the decks found

Run 2026-09-12, against the design values in
[SPDD §5.3](../docs/SPDD.md) — 470 µF bulk, ideal-diode OR, 0.95 Ω total series
resistance from appliance to rail.

### The number: minimum appliance supply current

Minimum source current at which the 5 V rail stays above 4.0 V — the
placeholder for the buck's minimum input, `VBUCKREQ` in the deck:

| Radio duty | 220 µF | **470 µF** | 1000 µF |
|---|---|---|---|
| 20% — steady ESPHome traffic | 175 mA | **120 mA** | 110 mA |
| 50% — busy link | 200 mA | **175 mA** | 175 mA |
| 91% — association / OTA | 250 mA | **250 mA** | 250 mA |

**Sag is an average-current problem, not a peak-current one.** The knee sits
within ~10% of the mean draw in every case. Bulk capacitance rides out an
individual transmit burst; it cannot manufacture average current.

**This settles how much bulk is worth fitting.** Going 470 µF → 1000 µF buys
10 mA at light duty and nothing at all under sustained transmit. Dropping to
220 µF costs 55 mA. 470 µF (SPDD §5.3) is the right size, and "add more bulk"
is *not* the answer if the Haier turns out marginal — more source current is.

### The eFuse limit

`inrush` is unambiguous: the eFuse limit must sit **strictly below** the
appliance's own limit. Above it, the appliance is driven into its own current
limit and its rail is dragged down to follow the charging capacitor for the
whole ramp — 8–17 ms of an undefined state that may reset the appliance, which
is the failure [ADR 0004](../docs/adr/0004-current-limited-inrush.md) exists to
prevent.

Ramp time is just Q/I: 9.4 ms at 250 mA into 492 µF, and the appliance is asked
for a flat current for that whole time — no peak beyond the limit itself.

Sizing, with `TOL` the chosen part's current-limit accuracy:

```
IEF_nom  ≥  sustained average draw / (1 - TOL)     so it never limits in service
IEF_nom  ≤  appliance limit / (1 + TOL)            so it always limits before
                                                    the appliance does
```

Taking the 246 mA sustained-transmit average from `rail-sag`:

| Limit accuracy | IEF nominal | Appliance must supply |
|---|---|---|
| ±10% | ≥ 273 mA | > 300 mA |
| ±20% | ≥ 308 mA | > 370 mA |

Which is the real headline: **the appliance needs 300–370 mA, not 250 mA**, if
the board is to both survive sustained transmit and stay polite at plug-in. The
figure firms up once the eFuse MPN — and with it `TOL` — is chosen.

### What to measure on the Haier

[SPDD §12.1 step 2](../docs/SPDD.md) now has numbers to test against:

1. Open-circuit voltage of the 5 V service rail.
2. **Current limit** — the one that matters. Pass is ≥ 370 mA; 250–300 mA means
   OTA and association on appliance power are at risk and the eFuse must be set
   below whatever the rail actually gives; under 250 mA the design needs
   rethinking, and not by adding capacitors.
3. Sag under a 250 mA pulsed load, to get `RAPP` — currently a 0.5 Ω guess.
4. Behaviour *in* current limit: does it fold back, latch off, or reset the
   appliance? The decks assume it merely droops.

## Parameters worth revisiting

| Parameter | Current value | Why it is a guess |
|---|---|---|
| `RAPP` | 0.5 Ω | Appliance source impedance. Measurement, item 3 above. |
| `RCABLE` | 0.25 Ω | ~1 m of 26 AWG out and back. Depends on the harness finally built. |
| `VBUCKREQ` | 4.0 V | Placeholder for the buck's minimum input. `margin` is `v5min - VBUCKREQ`, so results can be re-judged without re-running. |
| `RFUSE` | 0.20 Ω | PTC hold resistance. Set to 0 if the eFuse makes the fuse redundant (ADR 0004). |
| `TON` / duty | 2 ms, 20–91% | Transmit burst shape. Worst case is asserted, not measured. Worth a current probe during bring-up. |
