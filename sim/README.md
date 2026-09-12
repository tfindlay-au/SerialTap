# Power-path simulation

Standalone LTspice decks, deliberately outside the KiCad flow
([SPDD §5.8](../docs/SPDD.md)). They model the **power path only**; nothing
else on the board has a usable model or a question worth simulating.

Simulation **gates fabrication** ([SPDD §12.1](../docs/SPDD.md) step 1). The
point is not a pass mark — it is a *number* to go and measure the appliance
against.

## Running

```sh
./models/fetch-models.sh   # once - vendor SPICE models (see below)
./run.py                   # every deck
./run.py rail-sag          # one deck
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
| `buck-load-step.cir` | Does the buck recover from a 40 → 335 mA step without undershooting brownout? | runs, **result not yet trusted** — see below |

SPDD §5.4 quotes the step as 30 → 250 mA. Those are the **5 V-side** figures;
seen from the buck's output, where a load step actually happens, the same event
is 40 → 335 mA, which is what `buck-load-step` applies.

## The vendor model

`buck-load-step` is the one deck a behavioural block cannot answer — overshoot,
undershoot and settling belong to the control loop, the inductor and the output
capacitor together. It runs on TI's own model for the **TPS6282x** family.

`models/fetch-models.sh` downloads TI's *unencrypted* PSpice transient model
(literature number SLVMCV3) and converts it. Four things are worth knowing:

- **The vendor file is not committed.** TI ships it "as an aid for customers of
  Texas Instruments" with no redistribution grant, so the repo carries the fetch
  step and the converter instead of the file. This is the one exception to
  CLAUDE.md's "the project carries its own library" rule, and it is a licensing
  exception, not a convenience one — `lib/` still carries every KiCad asset.
- **One construct needed converting.** LTspice already understands PSpice's
  `VSWITCH` models, `TABLE {} = () ()` and `VALUE { IF(...) }` — all verified
  against this build before the converter was written. What defeats it is
  PSpice bracing a parameter reference *inside* a braced expression
  (`VALUE {{IF(V(A) > {VTHRESH}, {VDD},{VSS})}}`): the braces end up nested and
  LTspice reports "Questionable use of curly braces". `pspice2ltspice.py`
  strips the inner braces and passes everything else through untouched — 29
  expressions in this model.
- **`startup` on the `.tran` line is mandatory.** TI wrote the model for PSpice,
  which always solves an operating point first, so its internal latches and
  references need one. Plain `.tran` sends LTspice into minutes of Gmin
  stepping; `.tran ... uic` skips the operating point and the model sits dead,
  never switching. `startup` solves the operating point with the sources at
  zero — which converges immediately — then ramps them.
- **It is slow.** The model's soft-start runs about 1.5 ms and has to complete
  before a load step means anything, and a 2.2 MHz switcher is resolved
  throughout. Budget minutes per run and do not add sweeps casually. The `SS`
  subcircuit parameter looks like a way to skip soft-start — it is the initial
  condition on the ramp node — but setting it stops the model starting at all.
  Because a run is expensive, prefer `./run.py --keep-raw buck-load-step` when
  you might want to look at the waveform afterwards; the default throws the
  `.raw` away once the measurements are parsed out.

### Open issue: the deck does not yet regulate at 3.3 V

`results/buck-load-step.md` currently reports `vo_ss = 1.55 V` against a 3.3 V
target, so **its undershoot and overshoot numbers mean nothing yet** and the
`ok` column should be ignored. The rail is steady at 1.55 V from 2.0 ms to
2.65 ms, so this is not an unfinished soft-start — the loop is holding the
wrong level. Implied reference is 0.28 V, where the divider and TI's own
testbench both say 0.6 V.

What is known so far:

- The model itself is fine: on TI's own component values it comes up and
  switches.
- It is not the `SS` parameter. Setting `SS=1` to skip soft-start stops the
  model starting at all, with or without `startup`, so full soft-start has to
  run every time.
- Most likely suspects, in order: feedback-node bias current the model applies
  but the datasheet divider ignores (the deck's 180k/40k is a higher impedance
  than TI's 200k/100k), or the loop being unstable with 47 µF where TI used
  100 µF.

Next step is one run on TI's exact divider and output capacitor at a 3.3 V
target, to separate "wrong divider impedance" from "wrong compensation". Each
run is minutes, which is why this is not resolved yet.

**The passives in that deck are placeholders.** TPS62827 is the 4 A member of
the family and is oversized for this board; the family member, the inductor and
the output capacitors are still unpinned. The values are scaled from TI's own
testbench for this model (1.8 V at 4 A, L = 470 nH, COUT = 100 µF). Re-running
after the real parts are chosen is one command.

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
- **No control loop.** The behavioural buck is a constant-power load with a
  UVLO, which is right for `rail-sag` and `inrush` and useless for a load-step
  question — hence `buck-load-step` running on the vendor model instead.
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

**And the answer barely depends on the buck.** `VBUCKREQ` is a reporting
threshold, not a modelling one, so the same results can be re-judged against a
different minimum input voltage without re-running. Dropping it from 4.0 V to
3.5 V — roughly dropout for a TPS6282x at this current, and well under any
candidate's UVLO — moves exactly one corner of the table (220 µF at 20% duty,
175 → 130 mA) and leaves every other figure unchanged. That is because the
failure mode is average-current starvation, which collapses the rail entirely
rather than dipping it marginally below a threshold. So the 300–370 mA
requirement stands whichever family member is finally chosen.

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
