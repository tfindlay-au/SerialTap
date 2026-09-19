# Project library

Every symbol, footprint and 3D model this design uses lives here, referenced
with `${KIPRJMOD}`-relative paths from `pcb/sym-lib-table` and
`pcb/fp-lib-table`. Those two tables list **only** this library. Nothing in the
design may reference a library outside this directory (SPDD §7.3, CLAUDE.md
principle 3).

```
lib/
├── serialtap.kicad_sym      one symbol library, all parts
├── serialtap.pretty/        one footprint library, all parts
├── 3dmodels/                STEP and WRL, referenced as ${KIPRJMOD}/../lib/3dmodels/…
├── datasheets/              vendor PDFs for every non-passive
└── README.md                this file: provenance and gaps
```

**Started 2026-09-19.** Validated with `kicad-cli sym export svg` and
`kicad-cli fp export svg`: all symbols and all footprints parse and render.
`kicad-cli sch erc` still reports 0 violations.

## Verify after any change

```sh
CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
"$CLI" sym export svg --output /tmp/s lib/serialtap.kicad_sym   # mkdir the output dir first
"$CLI" fp  export svg --output /tmp/f lib/serialtap.pretty
# 3D refs: catches bare/unquoted paths too, which a quoted-only grep misses
grep -rhoE '\(model[[:space:]]+("[^"]*"|[^[:space:]")]+)' lib/serialtap.pretty/ | sort -u
# footprint links must all be serialtap:
grep -o '(property "Footprint" "[^"]*"' lib/serialtap.kicad_sym | grep -v '"serialtap:'
```

That last grep is the rule that matters. Imported assets arrive with paths into
the installing machine's global library; every one must be rewritten to
`${KIPRJMOD}/../lib/3dmodels/…` or the board will not open correctly for
anyone else.

## Provenance

`KiCad 10` = this machine's KiCad installation. `Espressif` = the vendor's own
KiCad library. `UltraLibrarian` / `SamacSys` = supplied 2026-09-19 via
componentsearchengine and UltraLibrarian. All are CC-BY-SA 4.0 with a design
exception, or vendor-supplied; see [NOTICE](../NOTICE).

Every footprint carries a 3D model, every referenced model file is present, and
no reference points outside this directory. Validated 2026-09-19: 12 symbols and
10 footprints render under `kicad-cli`, `sch erc` reports 0 violations.

| Part | Symbol | Footprint | 3D |
|---|---|---|---|
| **ESP32-C3-MINI-1-H4X** | Espressif | Espressif | Espressif STEP + WRL |
| **TPS62162DSGT** buck | KiCad (extends `TPS62170DSG`) | KiCad `Texas_DSG0008A…ThermalVias` ✅ **matches TI** | SamacSys |
| **TPD4E05U06QDQARQ1** ESD | KiCad (extends `TPD4EUSB30`) | KiCad `USON-10_2.5x1.0mm` | KiCad |
| **TPS2553DBVR** eFuse | UltraLibrarian | KiCad `SOT-23-6` | KiCad |
| **TXU0204PWR** translator | SamacSys | KiCad `TSSOP-14_4.4x5mm` | KiCad |
| **LM66200DRLR** ideal-diode OR | SamacSys | **`SOT8`, repaired** ✅ **matches TI** | vendor STEP |
| **XGL4020-222MEC** inductor | SamacSys | **SamacSys** ✅ **matches Coilcraft** | vendor STEP |
| **B05B-XASK-1-A(LF)(SN)** JST | KiCad generic 1x05 | KiCad, exact part, **boss hole present** | vendor STEP |
| **USB4085-GF-A** USB-C | KiCad generic 16P | KiCad, exact part | KiCad STEP |
| **PCL1A471MCL1GS** bulk | KiCad generic polarised | KiCad `CP_Elec_8x10` — **decided, see below** | KiCad |

Symbol names are the part, not a generic type, so an MPN cannot be silently
inherited by a second part of the same class later. Each carries `MPN` and
`Manufacturer` properties and points at its footprint in this library.

**Pin electrical types were set from the datasheet I/O columns** on all three
imported IC symbols. The supplied symbols had every pin as `passive`, which
makes ERC blind to undriven power nets and output conflicts — unacceptable when
`kicad-cli sch erc` is a release gate. 26 pins corrected.

## Footprints adjudicated against vendor land patterns

Where two sources disagreed, the vendor's own published land pattern decided it.
This is why two supplied footprints were rejected and one was repaired.

**LM66200 — the supplied "unofficial" one won.** TI's DRL0008A drawing specifies
pads 0.3 × 0.67 mm, 0.5 mm pitch, rows 1.48 mm apart.

| Candidate | Pad | Row separation | Verdict |
|---|---|---|---|
| `SOT8` (unofficial) | 0.3 × 0.67 | 1.48 | **exact match** |
| `SOTFL50P160X60-8N` (SamacSys) | 0.3 × 0.475 | 1.676 | rejected: 29% short, rows 0.2 mm too far apart |

`SOT8` had two defects, both repaired: pad 5 sat 20 µm out of line with the rest
of its row, and all eight pads carried an inherited 0.102 mm solder-mask margin.
At 0.5 mm pitch with 0.3 mm pads there is only 0.2 mm between pads, so a 0.102 mm
expansion each side would have erased the mask bridge entirely and invited
bridging. Removed, so the board's own mask settings govern. **Flag for DFM
review:** TI asks for 0.05 mm mask around, which is a 0.1 mm bridge — at or below
PCBWay's minimum. Confirm at review gate 3.

**XGL4020 — SamacSys won.** Coilcraft's four land-pattern figures are mutually
consistent only one way: pad 0.98 mm wide, centres 2.37 mm apart, pad 3.25 mm
across, overall 3.35 mm.

| Candidate | Pad width | Centre spacing | Verdict |
|---|---|---|---|
| SamacSys | 0.98 | 2.37 | **matches**; pad 3.4 across vs 3.25 typ, benign, extra solder outward |
| UltraLibrarian | 0.864 | 2.692 | rejected: pads 0.32 mm too far apart, under the terminal |

Spacing matters most here: this is the buck's hot loop, and misplaced pads move
the termination relative to the land.

**TPS62162 — KiCad won.** TI's DSG0008A drawing: signal pads 0.25 mm wide, rows
1.9 mm apart, thermal pad 0.9 × 1.6 mm.

| Candidate | Rows apart | Thermal pad | Verdict |
|---|---|---|---|
| KiCad | 1.9 | 0.9 × 1.6 | **exact match**, and ships thermal vias |
| SamacSys | 2.1 | 1.0 × 1.7 | rejected |

**JST B05B-XASK-1-A — KiCad won, and the boss is there.** SPDD §7.4 chose the
`-A` specifically for its boss. KiCad's footprint carries an unnamed non-plated
hole for it, and its plain variant has 5 pads against this one's 6. It also has
larger annular rings than the supplied alternative, which is what a through-hole
connector taking insertion force wants. No alternative needed.

## The bulk capacitor land pattern, decided

**Nichicon publishes no recommended land pattern for this part.** The part spec
sheet and the series datasheet both defer to the *Guidelines for Aluminum
Electrolytic Capacitors*, and that document does not contain one either — it
defers in turn to the catalogue. So neither candidate is vendor-specified; both
are IPC derivations.

| Candidate | Pad | Centres | Inner edge | Outer edge |
|---|---|---|---|---|
| **KiCad `CP_Elec_8x10`** (chosen) | 3.5 × 2.5 | ±3.25 | ±1.5 | ±5.0 |
| SamacSys `CAPAE830X1040N` | 3.8 × 2.15 | ±3.4 | ±1.5 | ±5.3 |

**They agree exactly on the inner pad edge at ±1.5 mm**, which is what sets where
the terminal lands. They differ only in how far each pad extends outward and how
wide it is. Either would solder.

KiCad's is chosen for wider pads — 2.5 mm against 2.15 mm, so more solder area
and more tolerance to placement rotation on a part 10 mm tall with a high centre
of mass — and for a tighter courtyard on a 22 mm-wide board. It also comes from a
library with a documented review process, where the alternative's origin proved
unreliable: the same source was wrong on the LM66200 and right on the XGL4020.

**Confirm two ways:** at DFM review, and against the real capacitor when it
arrives, by checking the terminals sit inside the pads with fillet showing.

## Still open

1. **JST XA series datasheet.** No direct URL found. The footprint is KiCad's for
   the exact part, so nothing is blocked; this is for completeness.

2. **Package confirmation for `TXU0204`**: TSSOP-14 (`PW`) is in the library. The
   alternatives are WQFN-14, UQFN-12 and X2QFN-12. TSSOP is the only leaded
   option and area is not scarce. Confirm before capture.

## Notes for schematic capture

From the datasheets read while building this library. All three bear on §5.3 and
are recorded so they are not rediscovered late.

- **`TPS62162` has a `VOS` pin** that the datasheet calls the "output voltage
  sense pin and connection for the control loop circuitry". SPDD §7.4 says the
  fixed-output part means "no feedback divider **and no sense trace for layout to
  special-case**". The first half is right, the second is not: `VOS` must run
  back to the output capacitor and it is in the control loop, so layout does have
  to treat it carefully. Worth a rule in
  [layout-rules.md](layout-rules.md).
- **`TPS62162` `FB` should be tied to `AGND`** on fixed-output versions, per the
  datasheet, for thermal performance. It is not a no-connect.
- **`LM66200` `ON` gates both channels together**, so it cannot be used to prefer
  one source over the other. Its `ST` pin reports which input is live, which is
  free diagnostics for a GPIO or an LED.
- **`TPS2553` `EN` is active high** (the TPS2552 is active low), `FAULT` is
  active-low open drain, and `RILIM` must be between 15 kΩ and 232 kΩ — which
  bounds [ADR 0007](adr/0007-rail-limit-inferred-not-measured.md)'s sizing.

## Pin tables extracted from the datasheets here

Recorded so the missing symbols can be authored without re-reading the PDFs.
All three are verbatim from the vendor tables in `datasheets/`.

**TXU0204** — and this **confirms SPDD §7.4's "two channels each way"**:
channels 1 and 2 run A to B, channels 3 and 4 run B to A.

| Pin name | PW / BQA | RUT / DTR | I/O |
|---|---|---|---|
| VCCA | 1 | 1 | supply, A port, 1.1–5.5 V |
| A1 | 2 | 2 | in |
| A2 | 3 | 3 | in |
| A3Y | 4 | 4 | out |
| A4Y | 5 | 5 | out |
| NC | 6, 9 | — | — |
| GND | 7 | 6 | — |
| OE | 8 | 12 | in, low = all outputs Hi-Z |
| B4 | 10 | 7 | in |
| B3 | 11 | 8 | in |
| B2Y | 12 | 9 | out |
| B1Y | 13 | 10 | out |
| VCCB | 14 | 11 | supply, B port, 1.1–5.5 V |
| PAD | — | — | thermal, grounding recommended |

**TPS2553** (`DBV` = SOT-23-6). Enable is **active high** on the 2553; the 2552
is active low. `RILIM` range is **15 kΩ to 232 kΩ**, which bounds ADR 0007's
sizing.

| Pin | Name | I/O |
|---|---|---|
| 1 | IN | in, needs ≥0.1 µF to GND right at the IC |
| 2 | GND | — |
| 3 | EN | in, logic **high** turns the switch on |
| 4 | FAULT | out, active-low open drain |
| 5 | ILIM | sets the current limit |
| 6 | OUT | out |

**LM66200** (`DRL` = SOT-5X3, 8-pin, its only package).

| Pin | Name | I/O |
|---|---|---|
| 1, 5 | GND | — |
| 2, 7 | VOUT | out |
| 3 | VIN1 | in, channel 1 |
| 4 | ON | in, **active low**; high turns off **both** channels |
| 6 | VIN2 | in, channel 2 |
| 8 | ST | out, high when VIN1 is the source, low when VIN2 is |

Two things there matter at capture and are noted for §5.3: `ON` gates both
inputs together, so it cannot be used to prefer one source; and `ST` reports
which source is live, which is free diagnostics for a GPIO or an LED.
