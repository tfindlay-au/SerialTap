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
grep -rn 'KICAD[0-9]*_3DMODEL_DIR\|KICAD[0-9]*_3RD_PARTY' lib/   # must return nothing
```

That last grep is the rule that matters. Imported assets arrive with paths into
the installing machine's global library; every one must be rewritten to
`${KIPRJMOD}/../lib/3dmodels/…` or the board will not open correctly for
anyone else.

## Provenance

`KiCad 10` means copied from this machine's KiCad 10 installation.
`Espressif` means the vendor's own KiCad library. Both are CC-BY-SA 4.0 with a
design exception; see [NOTICE](../NOTICE).

| Part (MPN) | Symbol | Footprint | 3D |
|---|---|---|---|
| **ESP32-C3-MINI-1-H4X** | ✅ Espressif | ✅ Espressif | ✅ Espressif STEP + WRL |
| **TPS62162DSG** buck | ✅ KiCad `Regulator_Switching` (+ parent `TPS62170DSG`) | ✅ KiCad `Texas_DSG0008A_WSON-8…ThermalVias` | ❌ **gap** |
| **TPD4E05U06QDQARQ1** ESD | ✅ KiCad `Power_Protection` (+ parent `TPD4EUSB30`) | ✅ KiCad `USON-10_2.5x1.0mm` | ✅ KiCad |
| **TPS2553DBV** eFuse | ❌ **gap** (pin table below) | ✅ KiCad `SOT-23-6` | ✅ KiCad |
| **TXU0204PW** translator | ❌ **gap** (pin table below) | ✅ KiCad `TSSOP-14_4.4x5mm` *(package pending, see below)* | ✅ KiCad |
| **LM66200DRL** ideal-diode OR | ❌ **gap** (pin table below) | ❌ **gap** — KiCad has DRL-5 and DRL-6, not DRL-8 | ❌ **gap** |
| **XGL4020-222MEC** inductor | generic `L` ✅ | ❌ **gap** | ❌ **gap** |
| **B05B-XASK-1-A(LF)(SN)** JST | generic `Conn_01x05_Pin` ✅ | ✅ KiCad, **exact part incl. the `-A` boss** | ❌ **gap** |
| **USB4085-GF-A** USB-C | generic `USB_C_Receptacle_USB2.0_16P` ✅ | ✅ KiCad, **exact part** | ✅ KiCad STEP |
| **PCL1A471MCL1GS** bulk | generic `C_Polarized` ✅ | ⚠️ KiCad `CP_Elec_8x10` — **land pattern unverified against the Nichicon drawing** | ✅ KiCad |

Generic symbols are used where the part needs no special pin semantics. Per
CLAUDE.md principle 2 each instance still carries its MPN as a symbol property;
that happens at schematic capture, not here.

**SPDD §7.4's claim about the USB-C receptacle is confirmed:** KiCad 10 ships
both a reviewed footprint and a STEP model for the USB4085. That was the stated
reason for choosing it over a vertical part, and it holds.

## Gaps

**Needs sourcing — SnapEDA, UltraLibrarian or the vendor:**

1. `XGL4020` footprint and 3D model. Coilcraft distributes CAD through
   UltraLibrarian. The datasheet is in `datasheets/` but its land-pattern
   drawing does not survive text extraction well enough to author from: the
   numbers are recoverable, which number belongs to which dimension is not.
   **Not authored deliberately** rather than guessed.
2. `LM66200` DRL-8 footprint and 3D model. SOT-5X3, 8-pin, 2.1 × 1.6 mm. KiCad
   has DRL-5 and DRL-6 only.
3. 3D model for the JST `B05B-XASK-1-A`. KiCad ships the footprint but no STEP.
4. 3D model for TI's `DSG0008A` WSON-8 2 × 2 mm.
5. Datasheets not retrievable by direct URL: **JST XA series** and **Nichicon
   PCL series**. The Nichicon one also settles the two open questions in
   SPDD §7.4 — the land pattern above, and the endurance figure that sources
   disagree on.

**Two package decisions still open (SPDD §7.4 says "package TBD"):**

- **TXU0204** has four: TSSOP-14 `PW` 5 × 6.4 mm, WQFN-14 `BQA` 3 × 2.5 mm,
  UQFN-12 `RUT` 2 × 1.7 mm, X2QFN-12 `DTR` 1 × 1.7 mm. TSSOP-14 is provisionally
  in the library as the only leaded option: visible, inspectable, reworkable
  joints, and area is not scarce on a 22 × 54 mm board. **Confirm before
  capture.** KiCad has footprints for all four.
- **TPS62162** resolves to `DSG` = WSON-8 2 × 2 mm, the package KiCad's own
  symbol targets. Treat as settled unless there is a reason not to.

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
