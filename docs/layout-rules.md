# Layout rules — SerialTap

Binding rules for board layout in KiCad 10. Referenced by
[SPDD §8](SPDD.md). Numbers assume PCBWay's **5/5 mil, 0.25 mm drill** class.

## Priority order

When rules conflict, this is the order they win in:

1. **Antenna keepout.** Non-negotiable, set by Espressif.
2. **Buck input hot loop.** The fastest di/dt on the board.
3. **ESD path at the connector.**
4. **USB pair integrity.**
5. Everything else.

Place in that order too. The module and the buck are placed first; the rest
fills in around them.

## Stackup

| Layer | Assignment |
|---|---|
| L1 | Signal + all components (single-sided assembly) |
| L2 | **Solid ground.** Unbroken. Reference for every L1 signal and the antenna. |
| L3 | 5 V and 3V3 pours, plus escape routing |
| L4 | **Ground.** Second return path and shield under the buck. No components. |

Dielectric thicknesses are **not** symmetric on a standard 1.6 mm 4-layer —
typically a thin prepreg L1–L2 and a thick core L2–L3. Obtain PCBWay's published
stackup before computing any trace geometry; the L1–L2 height sets the USB pair
dimensions.

**Encoded as of 2026-09-12** in `pcb/serialtap-r1p0/serialtap-r1p0.kicad_pcb`:
four copper layers named per the table above, on a **provisional** asymmetric
stackup of 0.2104 mm prepreg / 1.065 mm core / 0.2104 mm prepreg, 35 µm outer
and 17.5 µm inner copper. Those dielectric figures are the usual nominal values
for a 1.6 mm four-layer board, **not** PCBWay's published stackup — they are
placed so KiCad has a physically sensible board to work with, and the rule above
still stands: get the real numbers before computing the USB geometry.

## Floorplan

Board outline **22 × 54 mm**, chosen to drop into the OEM Haier board's place.
Zones run along the 54 mm axis:

```
  |<--------------------------- 54 mm --------------------------->|
  +----------------------------------------------------------------+
  | ANTENNA  |  C3-MINI-1  | translators  |   power    |    JST     |  22
  | overhang |   module     | + TVS + Rs   | OR/eFuse   |  5-pin XA  |  mm
  | no copper|              |              | bulk, buck |            |
  +-------------------------------------------[ USB-C ]-------------+
                                               long edge
```

- Antenna at one short edge, outline relieved so it overhangs.
- **JST on the far short edge; USB-C on a long edge beside it.** They do not
  both fit across 22 mm: a 5-position XA header is ~14.6 mm and a USB-C
  receptacle ~8.9 mm, which needs ~26 mm with edge clearance between them.
  The JST keeps the short edge because it is the permanent harness and wants a
  clean cable exit; USB-C is bench-only and unused after first flash (ADR 0002).
  Both still land at the same end, so the two 5 V sources still meet at the
  ideal-diode OR without crossing the board.
- Buck biased toward the connector end — maximum distance from the antenna.
- TVS and series resistors **at the JST**, not at the translators. The
  unprotected side of the ESD devices must be as short as possible; the 3.3 V
  side takes the long run to the module, where it is harmless.

## Area budget — measured from the footprints, 2026-09-20

The board is **1188 mm²** (22 × 54). The courtyards of all 33 components total
**774 mm², or 65%** of that. Tight but routable on four layers; the usual pain
threshold is 70–80%.

It is less crowded than "33 components" sounds, because four parts are 71% of
the area and the other 29 share what is left:

| Part | Courtyard | mm² |
|---|---|---:|
| U6 ESP32-C3-MINI-1 | 13.6 × 17.0 | 231 |
| J1 JST XA 5-pin | 16.0 × 7.4 | 118 |
| J2 USB-C | 10.6 × 10.2 | 107 |
| C4 bulk 470 µF | 10.5 × 8.8 | 92 |
| **those four** | | **548** |
| the other 29 (5 ICs, inductor, 2 switches, 20 passives, LED) | | **226** |

So placement is really "fit four large objects to the floorplan, then fill".
The module's 231 mm² already includes its antenna end, which is where the
keepout lives — the keepout does not cost additional area, it constrains what
may sit *near* it.

**One library gap this exposed:** the `LM66200` footprint has **no courtyard**
on `F.CrtYd`. Every other footprint has one. KiCad's courtyard-overlap DRC
check therefore cannot protect U2 during placement — fix before laying out.

## Per-circuit rules

### Buck converter

The critical net is not the switch node — it is the **input loop**:
`input ceramic → high-side FET → low-side FET → ground → back to ceramic`.

- Input ceramic capacitor on L1, within 1–2 mm of VIN/PGND. **No vias inside
  this loop.** Via inductance is comparable to the loop being minimised.
- The 470 µF bulk sits *behind* the ceramic. Bulk handles millisecond WiFi
  bursts; the ceramic handles nanosecond switching edges. Do not swap them.
- **Switch node: minimum copper area** consistent with current. This is the one
  net that is deliberately not poured — it is the dV/dt aggressor radiating at
  the antenna.
- Inductor immediately at the SW pin. Short, direct.
- Feedback: 0.127–0.2 mm, sensed at the **output** capacitor, routed away from
  SW and never beneath the inductor. Ground-guard if space allows.
- Thermal pad: via array, 0.25 mm drill, tented with mask on L4. Windowpane the
  paste stencil to ~60–70 % coverage to limit wicking and voiding.
- Stitch L2–L4 with vias around the buck.

### Antenna

- **No copper on any layer** — L1, L2, L3, L4 — in the C3-MINI-1's antenna
  keepout. This includes ground pours. Follow Espressif's module datasheet
  keepout dimensions exactly.
- Module at the board edge with the antenna region overhanging the outline.
- Nothing routed on L3 beneath the antenna either.
- Ring the keepout boundary with ground stitching vias.
- Installation note for the harness docs: keep ≥15 mm clear of metal.

### USB

The C3's USB Serial/JTAG is **USB 1.1 Full Speed (12 Mbps)**. Transmission-line
effects are negligible over ~20 mm, which is why controlled impedance is not
ordered. Route it properly anyway — it costs nothing:

- Same layer (L1), tightly coupled, **no vias, no stubs**.
- Continuous L2 ground reference along the entire run. Never cross a plane gap.
- Length matched within 5 mm.
- Target ~90 Ω differential geometry computed from PCBWay's actual stackup.
  Starting point for a thin L1–L2 prepreg: ~0.20 mm width, ~0.13 mm gap —
  **confirm with KiCad's impedance calculator against the real stackup.**
- Keep ≥0.6 mm from other signals.

### Port protection and translation

Order along the path, nearest connector first:

```
JST pin --> TVS array --> 330 Ω series R --> translator B-side
```

- TVS ground via directly into L2, short and wide. The ESD return path matters
  more than the clamp.
- The TPD4E05U06's other two channels protect USB D+/D− at USB-C. Both ports
  are normally mutually exclusive, but both connector-facing data paths are
  protected against accidental connection.
- 100 nF on **both** VCCA and VCCB of each translator, within 2 mm.
- Tie off unused translator inputs. Never leave them floating.

### Module

- 10 µF + 100 nF at the C3-MINI-1's 3V3 pin.
- Ground stitching under the module's thermal pad into L2.

## Global rules

- **Never split the ground plane.** One solid L2. The instinct to isolate
  "noisy" switcher ground from "quiet" RF ground with a split or star point
  makes things worse — it forces return currents to detour around the gap and
  become loop antennas. Return current is controlled by *placement and zoning*,
  not by copper splits.
- Perimeter ground stitching every ~5 mm.
- No unstitched copper islands.

## Design rules (PCBWay 5/5 mil, 0.25 mm drill)

These are encoded in `pcb/serialtap-r1p0/serialtap-r1p0.kicad_pro` and enforced
by `kicad-cli pcb drc` — verified 2026-09-12 by feeding DRC a deliberately
undersized track and confirming it was rejected against the 0.127 mm minimum.
Net classes `Default` (0.20 mm), `Power` (0.50 mm) and `USB` (0.20 mm / 0.13 mm
gap) are defined there too.

| Rule | Value |
|---|---|
| Min trace width | 0.127 mm |
| Min clearance | 0.127 mm |
| Min drill | 0.25 mm |
| Default via | 0.25 mm drill / 0.50 mm pad |
| Min annular ring | 0.125 mm |
| Copper to board edge | 0.3 mm (0.5 mm preferred for planes) |
| Silkscreen to pad | 0.15 mm; no silk over pads |
| Silkscreen text | **0.8 mm high, 0.15 mm stroke minimum** |
| Solder mask dam | 0.1 mm min |

**Silkscreen values checked against PCBWay, 2026-09-22.** PCBWay's
capabilities page gives a minimum legend height of 0.8 mm and a minimum
character width (stroke) of 0.15 mm; their engineering FAQ asks for 0.2 mm
silk-to-pad and accepts 0.1 mm where space is tight, and says silk left on a
pad is clipped off at fabrication. The board's DRC stroke minimum was 0.12 mm —
**looser than the fab**, so it was raised to 0.15 mm. Height already matched.
There is no slack to gain by matching PCBWay: their numbers are the floor.

Default widths for non-critical nets:

| Net class | Width |
|---|---|
| Signal | 0.20 mm |
| 3V3 | 0.50 mm or pour |
| 5 V | 0.50 mm or pour |
| GND | plane |

0.5 mm on 1 oz outer copper carries ~1 A at a 10 °C rise — comfortably above the
eFuse limit, so current capacity is never the binding constraint here.

## DFM — single-sided assembly

- All components on L1. L4 carries no parts.
- **3 global fiducials** on L1: 1 mm copper dot, 2 mm mask opening, placed
  asymmetrically. No local fiducials needed — nothing is fine-pitch BGA.
- Passives **0603 by default**; 0402 permitted only where loop area demands it
  (buck input ceramics, translator decoupling).
- Pin-1 and polarity markers on silkscreen, still visible after assembly.
- Designators readable and unambiguous; none hidden under parts.
- Keep components ≥3 mm from the board edge where possible.
- ~~Mounting holes with keepout~~ **N/A — there are none** (measured
  2026-09-20). Retention is **not an open question** (decided 2026-09-22): the
  board keeps the OEM board's 22 × 54 mm outline and sits in the same slot.
- Test points: 1 mm exposed copper, labelled on silkscreen, reachable with a
  probe without removing the board.

## Recorded exceptions — r1p0 as routed, 2026-09-22

Where the routed board departs from a rule above, the departure is recorded
here, with the reason, rather than left for a reviewer to rediscover.

1. **The ESD array is not at the JST.** U5 (TPD4E05U06) sits 12.2 mm from
   J1 and 5.5 mm from J2, footprint centre to centre (measured from the board
   file 2026-09-22; the `a80c933` note's 9 mm / 3 mm is the gap between
   parts). One four-channel array serves both connectors, so it cannot sit at
   both. The order *connector → TVS → 330 Ω → translator* still holds on the
   UART lines. **Accepted 2026-09-22.**
2. **The UART from J1 runs on L3, with L1 hops.** Permitted by the stackup
   (*L3: escape routing*). On this stackup L3 sits 0.21 mm above L4 and
   1.065 mm below L2, so its return reference is **L4**, not L2 (corrected
   2026-09-22 — first recorded the wrong way round). The lines carve a
   channel through the L3 V5 pour, not a ground plane.
3. **USB D− reaches J2 on L3, through one via.** The U5 channel assignment
   (USB on pins 1/2, UART on pins 4/5, swapped in the schematic in
   `a80c933`) lets the pair reach the array without a crossing. From there D+
   runs to J2 on L1, but D− drops through a via at (138.6, 110.75) and reaches
   B7 on L3 (corrected 2026-09-22 — first recorded as "a TVS stub on L3"; both
   TVS stubs are on L1, 2.0 mm on D− and 1.5 mm on D+). See the USB check
   below the checklist.
4. **CC2 passes under the USB-C body.** Three segments, all on L1, no vias
   (checked 2026-09-22). The USB4085 shell is metal and grounded, so
   soldermask is the only insulation between it and the trace. CC2 is a
   static pull-down strap, not a signal, and USB is used only for setup
   flashing. Confirm at gate 2 that the trace clears the shell's contact
   points.
5. **L4 carries the ten test pads.** They are bare copper with no BOM line —
   nothing is assembled on L4, so *single-sided assembly* holds — but each pad
   is a void in the L4 ground pour. L2 remains the unbroken plane the rules
   require, and L4 is the second return path, so this is accepted.
6. **Fiducials sit in the right-hand two-thirds only.** FID1 (151.6, 101.3)
   and FID2 (152.9, 120.5) either side of J1, FID3 (132.6, 111.1) mid-board:
   an asymmetric triangle ~20 × 19 mm. The only free L1 space at the left end
   is directly beside the antenna, and antenna keepout outranks fiducial
   spread. They are `serialtap:Fiducial_1mm_Mask2mm` (KiCad stock, copied
   in), board-only, and excluded from the BOM and the placement file.
7. **Two library footprints were trimmed to fit.** Silkscreen only, pads and
   keepouts untouched: three outline segments off `ESP32-C3-MINI-1` and four
   off `USB_C_Receptacle_GCT_USB4085`, to clear silk DRC. Made on the board,
   then written back to `lib/` so the library and the board agree.

## Pre-release review checklist

- [ ] Antenna keepout clear on **all four** layers, including pours
- [ ] L2 ground plane unbroken end to end
- [ ] Buck input loop contains no vias; ceramic within 2 mm of the IC
- [ ] Switch node area minimised, not poured
- [ ] Feedback trace clear of SW node and inductor
- [ ] USB pair: no vias, no plane gap beneath, matched within 5 mm
- [ ] TVS sits ahead of series resistors, at the connector (distance to J1 excepted — *Recorded exceptions* 1)
- [ ] Both VCCA and VCCB decoupled on every translator
- [ ] No floating translator inputs
- [ ] All test points present, labelled, accessible
- [x] 3 fiducials placed asymmetrically (2026-09-22 — see *Recorded exceptions* 6)
- [ ] Silkscreen: 0.8 mm / 0.15 mm text, clear of pads and board edge
- [ ] DRC clean at 5/5 mil, 0.25 mm (`kicad-cli pcb drc`)
- [ ] `kicad-happy` PCB review clean: thermal vias, plane voids, trace width,
      impedance, DFM score
- [ ] `kicad-happy` `pcbway` pre-order checklist passed
- [ ] Gerbers rendered and visually inspected before upload

### USB pair as routed — measured 2026-09-22

Measured from the board file with KiCad's Python API, not read off the
drawing. Path: U6 → U5 (ESD, on 2.0 / 1.5 mm stubs) → J2. The main run is L1,
0.20 mm wide at a 0.20 mm gap, ~30 mm long and tightly coupled.

| Plug orientation | D+ | D− | Mismatch |
|---|---|---|---|
| A-side (A6/A7) | 36.84 mm | 40.18 mm + via | 3.34 mm (≈4.7 mm counting the via's 1.33 mm barrel) |
| B-side (B6/B7) | 38.44 mm | 38.59 mm + via | 0.15 mm (≈1.5 mm with via) |

Against the checklist:

- **Matched within 5 mm: passes**, narrowly, in the worst orientation.
- **No vias: fails.** One, on D−, at (138.6, 110.75).
- **No plane gap beneath: fails in two places.** D+'s vertical leg at
  x = 137.75 runs along the edge of the thermal reliefs of J2's two front
  shell tabs, losing L2 for roughly 3 mm. And from U5 to J2 the pair splits:
  D+ runs under the bottom pin row on L1, D− over the top row on L3, both
  across the pins' antipads and ~2.6 mm apart.
- **≥0.6 mm from other signals: fails.** The closest aggressors are VBUS pad
  A9 (0.14 mm), a CC1 trace (0.20 mm) and the BOOT pad (0.45 mm). All three
  are DC or static nets.
- **~90 Ω geometry: not met.** An estimate, not a measurement: 0.20/0.20 mm
  on the provisional 0.21 mm prepreg works out to roughly 105–110 Ω by the
  IPC-2141 microstrip formula. The rule's 0.13 mm gap was not used.

**What it means electrically:** little. This is USB 1.1 Full Speed. Its
4–20 ns edges make a 40 mm line electrically short, and a 4.7 mm skew is
~30 ps against an 83 ns bit. The failures are against the rule as written,
not against a working link.
