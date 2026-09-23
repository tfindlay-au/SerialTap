# Layout rules — SerialTap

Binding rules for board layout in KiCad 10. Referenced by
[SPDD §8](SPDD.md). Numbers assume PCBWay's **5/5 mil, 0.2 mm drill** class (0.25 mm until
2026-09-24 — see *Design rules*).

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

**Replaced with PCBWay's published stackup, 2026-09-24.** From PCBWay's
[multi-layer laminated structure](https://www.pcbway.com/multi-layer-laminated-structure.html)
page, standard 4-layer 1.6 mm, 70 % inner residual copper (L2 is a near-solid
plane, so the high-residual variant fits): 0.5 oz outer base plated to 1 oz
(35 µm), **7628 RC46 % prepreg 0.1855 mm after lamination, Dk 4.74**, 1 oz
(35 µm) inner copper, **1.03 mm core, Dk 4.6**, symmetric. Finished
thickness 1.61 mm ±10 %. Loss tangent is not published; 0.02 is kept.
Encoded in the board file and confirmed as read back by the analyzer.
**Order with 1 oz inner copper** — the stackup assumes it.

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

- Antenna at one short edge, outline relieved so it overhangs. **Superseded
  2026-09-22:** the board keeps the OEM rectangle, so the antenna sits 0.25 mm
  inside the edge with a copper-free keepout on all four layers instead —
  checked 2026-09-23 under the pre-release checklist.
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
**Fixed** — every footprint on the board has a courtyard (checked 2026-09-23),
and the `missing_courtyard` DRC check, which had been set to *ignore*, is now
an *error* so a future footprint cannot slip in without one.

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
- Thermal pad: via array, 0.2 mm drill, tented with mask on L4. Windowpane the
  paste stencil to ~60–70 % coverage to limit wicking and voiding.
- Stitch L2–L4 with vias around the buck.

### Antenna

- **No copper on any layer** — L1, L2, L3, L4 — in the C3-MINI-1's antenna
  keepout. This includes ground pours. Follow Espressif's module datasheet
  keepout dimensions exactly.
- Module at the board edge with the antenna region overhanging the outline.
  **Superseded 2026-09-22** by the OEM outline: the antenna end sits 0.25 mm
  inside the edge, over the all-layer keepout (see *Floorplan*).
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

## Design rules (PCBWay 5/5 mil, 0.2 mm drill)

These are encoded in `pcb/serialtap-r1p0/serialtap-r1p0.kicad_pro` and enforced
by `kicad-cli pcb drc` — verified 2026-09-12 by feeding DRC a deliberately
undersized track and confirming it was rejected against the 0.127 mm minimum.
Net classes `Default` (0.20 mm), `Power` (0.50 mm) and `USB` (0.20 mm / 0.13 mm
gap) are defined there too.

| Rule | Value |
|---|---|
| Min trace width | 0.127 mm |
| Min clearance | 0.127 mm |
| Min drill | 0.2 mm |
| Default via | 0.2 mm drill / 0.50 mm pad |
| Min annular ring | 0.15 mm |
| Copper to board edge | 0.3 mm (0.5 mm preferred for planes) |
| Silkscreen to pad | 0.15 mm; no silk over pads |
| Silkscreen text | **0.8 mm high, 0.15 mm stroke minimum** |
| Solder mask dam | 0.1 mm min |

**Drill and annular ring changed 2026-09-24.** The rules had been 0.25 mm
drill with a 0.125 mm minimum annular ring, and every via was 0.25 / 0.5 mm.
PCBWay's capabilities page says "For pads with vias in the middle, Min width
for Annular Ring is 0.15mm(6mil)", so all 110 vias and U3's two thermal vias
were 0.025 mm short — and DRC could not catch it, because the rule itself
was 0.125 mm. Fixed by keeping the 0.5 mm pads and drilling 0.2 mm, which
moves no copper: the alternative, 0.55 mm pads on the 0.25 mm drill, left
U5's pin-3 GND via 0.004 mm too wide for its corridor between D− and
PORT_TX. PCBWay charges extra only below 0.2 mm, and 1.6 mm ÷ 0.2 mm is 8:1,
their standard aspect-ratio limit. The rules are now 0.2 mm minimum drill,
0.2 / 0.5 mm default via, 0.15 mm minimum annular ring — so DRC enforces the
fab's number from here on.

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
   below the checklist. The via is where D− has to cross D+: J2's pin order
   is the reverse of U6's, so the crossing is a matter of topology and cannot
   be designed out on L1 (2026-09-23). The only via-free route would move the
   layer change into J2's own A6–B6 link and cost ground reference and
   spacing. At USB Full Speed the via has no electrical effect.
   **Accepted 2026-09-23.**
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

Items checked 2026-09-23 were measured from the board file (KiCad Python API
and `kicad-cli`), not read off the render. Notes follow the list.

- [x] Antenna keepout clear on **all four** layers, including pours
- [x] L2 ground plane unbroken end to end
- [x] Buck input loop contains no vias; ceramic within 2 mm of the IC
- [x] Switch node area minimised, not poured
- [x] Feedback trace clear of SW node and inductor (rerouted 2026-09-24 — see note)
- [ ] USB pair: no vias, no plane gap beneath, matched within 5 mm (one via on D− excepted — *Recorded exceptions* 3)
- [x] TVS sits ahead of series resistors, at the connector (distance to J1 excepted — *Recorded exceptions* 1)
- [x] Both VCCA and VCCB decoupled on every translator
- [x] No floating translator inputs
- [x] All test points present, labelled, accessible
- [x] 3 fiducials placed asymmetrically (2026-09-22 — see *Recorded exceptions* 6)
- [x] Silkscreen: 0.8 mm / 0.15 mm text, clear of pads and board edge
- [x] DRC clean at 5/5 mil, 0.25 mm (`kicad-cli pcb drc`)
- [x] `kicad-happy` PCB review clean: thermal vias, plane voids, trace width,
      impedance, DFM score (gate 2, 2026-09-24 — no blockers; triage below)
- [x] `kicad-happy` `pcbway` pre-order checklist passed (gate 3, 2026-09-24 — see below)
- [ ] Gerbers rendered and visually inspected before upload

### Checklist notes — 2026-09-23

- **Antenna.** U6's keepout (102.2–107.6, 104.25–117.45; 5.4 × 13.2 mm,
  matching the antenna area in Espressif's land pattern, datasheet
  Fig. 11-1) has zero filled area from any of the three pours, and no track,
  via or pad in it. The board edge is 0.25 mm beyond the module end.
- **L2.** One connected fill, no tracks on the layer. The only large void is
  J2's pin field, ~6.5 × 2.7 mm: at 0.85 mm pitch the through-hole antipads
  in each row merge. That is inherent to a through-hole USB-C; nothing but
  J2's own nets and the last millimetre of the USB pair crosses it. U3's
  thermal-pad vias join L2 through thermal-relief spokes rather than solid —
  left for gate 2 to judge (dissipation at 335 mA is small).
- **Buck input.** C5 → VIN (pin 2) → PGND (pin 1) → C5 entirely on L1, no via
  on the loop; the GND and V5 vias nearby are branches off it. C5 is 1.48 mm
  from VIN and 0.65 mm from PGND, pad edge to pad edge.
- **Switch node.** One 0.40 × 2.15 mm track from pin 7 to L1. Not poured.
- **Feedback — failed 2026-09-23, rerouted 2026-09-24.** U3 is the
  fixed-output part, so FB is tied to AGND and the sense line is VOS (pin 6).
  As first routed, VOS ran down x = 135.4 and along y = 120.9 on L1 — on the
  edge of L1's body, 0.3 mm from the SW pad — to L1's *output pad*, 6.8 mm
  from C6. TI asks for the sense at the output capacitor, away from the
  inductor and SW (TPS62162 datasheet §11.1). Rerouted: pin 6 → via
  (135.4, 119.3) → L3 → via (143.1, 120.5) at C6's pad, which is the
  topology of TI's own layout example (Figure 42): VOS drops to another layer
  and comes up at the output capacitor, with L2 between it and SW. Two
  departures remain, both judged harmless. The L3 track also carries the
  3V3 rail west to the module — an estimated ~15 mΩ, ~5 mV at 335 mA, which
  the loop corrects toward the load. And pin 6's exit runs 0.15 mm from the
  SW track for ~0.75 mm, which adjacent pins make unavoidable; TI's example
  has the same. FB (pin 5) reaches GND through its own via: a DC tie, fine
  as it is. DRC unchanged at 0 / 0 / 0.
- **TVS order.** On both UART lines the path from J1 reaches U5's tap (at
  the vias at (139.3, 111.75) and (139.9, 112.6)) before it reaches R1/R2.
- **Translator.** C7 (VCCA) 0.86 mm and C8 (VCCB) 1.08 mm from U4. On the
  RUT package the unused inputs A2 (pin 3) and B4 (pin 7) are tied to GND,
  OE (pin 12) to VCCA; the unused outputs A4Y and B2Y are left open, as
  outputs should be.
- **Test points.** All ten on L4 with a 1.0 / 0.15 mm reference on
  B.Silkscreen; closest pair 2.6 mm centre to centre (TP6–TP7).
- **Silkscreen and DRC.** Text height, stroke, silk-to-pad and silk-to-edge
  are all DRC checks here; `kicad-cli pcb drc --severity-all
  --schematic-parity` reports 0 violations, 0 unconnected, 0 parity.

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
- **No plane gap beneath: fails in one place** (was two — see the
  2026-09-23 note below). From U5 to J2 the pair splits: D+ runs under the
  bottom pin row on L1, D− over the top row on L3, both across the pins'
  antipads and ~2.6 mm apart.
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

**Vertical legs moved clear of the shell tabs, 2026-09-23.** D+'s vertical leg
ran at x = 137.75 along the thermal reliefs of J2's two front shell tabs and
lost L2 for 3.15 mm of a 5.05 mm span (63 of 129 samples at 0.05 mm). Both legs
moved 0.95 mm west, to x = 136.80 (D+) and 136.40 (D−), keeping the 0.20 mm
gap. The GND stitching via at (136.5, 106.0) sat on the new path and moved to
(135.5, 106.0); it carries no track, only L2–L4. Re-measured with the same
scripts: every sample along both legs now has L2 beneath it, lengths are
unchanged (the top run shortens by what the bottom run gains), and DRC stays at
0 violations, 0 unconnected, 0 parity.

**Fix (b) as proposed does not work.** Checked 2026-09-23. The proposal was to
land D− on A7 on L1, beside D+. The problem is topology, not spacing. Heading
away from U6, the pair carries D+ on its left. J2 wants D− on the left, from
whichever side and direction the pair reaches either pin row: the receptacle
reverses U6's order. U5 is also a branch off the pair, and one line has to
pass the other to reach it. So a pair that stays together as far as J2 needs
one crossing. On one signal layer, a crossing is a via, and the via at
(138.6, 110.75) is that crossing.

**The only via-free route splits the pair at the connector.** D+ alone goes
through the 0.55 mm corridor between the shell tab at (138.45, 107.53) and A12, and along
the channel between the pin rows to B6. D− lands on A7 from below, and U5's
D+ is fed on a stub from A6. Measured on the board as it stands: this route
has no L2 under D+ for 1.60 of 6.20 mm, against 0.95 of 5.70 mm today. It runs
0.175–0.225 mm from GND, VBUS, SBU1 and CC2 pads. U5 would sit on a ~3.6 mm
stub. And in A-side orientation, D+ would still reach A6 through the A6–B6
link on L3. The layer change would move into J2's own pin barrels, not go
away. **Not made:** the via is kept, and accepted as *Recorded exceptions* 3.

## Review gate 2 — kicad-happy after layout, 2026-09-24

Run against `ec7624f`: schematic, PCB (`--full --proximity`), cross-domain,
EMC and thermal analyzers, kicad-happy 2.2.1, output in
`analysis/2026-09-24_0016/` (gitignored). SPICE not run by the skill: LTspice
is installed as an app but not on the path, and the power-path decks in `sim/`
already cover what the skill would simulate. Lifecycle audit not run (it was
not the question at this gate). **No blockers.** Every finding was checked
against the board file before it was kept; the triage:

**Real, and already known**
- USB pair over J2's pin-field void and the D− via without an adjacent stitch
  (RP-002, GP-001, RP-001) — *Recorded exceptions* 3 and the L2 note above.
- USB_VBUS, CC2 and PORT_5V at 91–94 % reference coverage (GP-001): all cross
  the same J2 pin field or J1's pins. DC or static nets.

**Real, new, and acted on or open**
- **Stackup.** PCBWay's published standard 4-layer 1.6 mm build is 7628
  prepreg at **0.1855 mm** after lamination, Dk 4.74, over a 1.03 mm core,
  Dk 4.6, with **1 oz inner copper**; the board encoded the provisional
  0.2104 mm and 17.5 µm inner. **Updated 2026-09-24** (see *Stackup*); DRC
  unchanged at 0 / 0 / 0. The analyzer's per-segment impedance reads
  49.7 Ω on every USB segment, L1 and L3 alike, with no width recorded — a
  placeholder, not a stackup calculation, and not used here.
- **USB impedance, estimated** (IPC-2141 microstrip formula, not a field
  solver; Hammerstad agrees within a few ohms): the as-routed 0.20 / 0.20 mm
  pair is **~101 Ω** on the PCBWay
  build, inside USB's 90 Ω ±15 % (76.5–103.5 Ω) but near its top; soldermask
  lowers it by a few ohms. The rule's 0.20 / 0.13 mm would give ~92 Ω. Not
  worth rerouting at Full Speed. An outside review's "76.5 Ω on PCBWay" used a
  0.1035 mm prepreg that PCBWay does not publish as standard.
- **Parts near the edge** (PM-002): C4 0.15 mm, L1 0.10 mm, SW1 and SW2
  0.35 mm, and the MLCCs C1, C9, C11 and R10 at 0.77–0.92 mm (courtyard to
  edge). Copper-to-edge is DRC-clean at 0.3 mm; the risk is depaneling
  stress, which is a gate 3 matter: ask PCBWay for routed rails, no V-score,
  and breakaway tabs away from those parts.

**Checked and dismissed**
- *GND plane split, 16 islands* (PS-002): an analyzer artefact. The
  "isolated" pads (U6's GND row, U2.4/5, U4.7) join through vias placed
  mid-track, which the analyzer's union-find does not merge. KiCad's own
  connectivity reports 0 unconnected with schematic parity.
- *U6 thermal vias insufficient, 1 of 5* (TV-001 ×8): the module's centre
  ground is nine 1.45 mm sub-pads with one via each, as Espressif's land
  pattern shows; the analyzer scores each sub-pad as a separate exposed pad.
- *Via in pad, untented* (VP-001): board vias are tented both sides by
  default. The flagged ones are inside U6's GND sub-pads (back still tented;
  0.25 mm holes) and inside the bare L4 test pads (nothing soldered).
- *Missing stitching via at layer change* (RP-001) on UART, BOOT, EN, PG,
  CC and V5: DC, static, or 230 kbaud signals.
- *Trace width below IPC-2221 at 10 °C rise* (on the provisional 17.5 µm
  inner copper): each thin L3 segment was traced to what it feeds. The V3V3
  0.3 / 0.4 mm branches feed pull-ups and U4's VCCA, the V5 0.3 mm branches
  the LED, U4's VCCB and TP1 — milliamps. The module's feed is 0.5 mm (0.44 A
  at 10 °C against 0.40 A needed), the buck's input is the V5 pour, and
  USB_VBUS's 0.4 mm (0.37 A) carries ~0.25–0.3 A only while flashing. With
  PCBWay's 1 oz inner copper every figure roughly doubles.
- *U3 harmonics in the 30–88 MHz band* (SW-001): generic to any 2.25 MHz
  buck; the layout mitigations (tight input loop, unpoured SW node) are in
  place.

**Thermal, by hand** (the analyzer skipped it for want of power data): U3
dissipates ~0.12–0.15 W at 335 mA, assuming 88–90 % efficiency. TI's θJA of
61.8 °C/W (DSG, datasheet §7.4) gives a 6–9 °C rise. U1 and U2 each dissipate
tens of milliwatts at most. **DFM** (PCBWay 5/5 mil, 0.25 mm): 0 violations,
0.161 mm minimum spacing, 0.125 mm annular ring — **which gate 3 found is
below PCBWay's via minimum**; see *Review gate 3*.

## Review gate 3 — PCBWay pre-order, 2026-09-24

Checked against PCBWay's published
[capabilities](https://www.pcbway.com/capabilities.html) (fetched
2026-09-24), not remembered figures. **One real defect, fixed:** every via's
annular ring was 0.125 mm against PCBWay's 0.15 mm via minimum. The drill is
now 0.2 mm (see *Design rules*). Everything else passes.

| PCBWay limit | This board | |
|---|---|---|
| Trace / space ≥ 4/4 mil (4-layer) | 5/5 mil rules; 0.2 mm narrowest track | pass |
| Via annular ring ≥ 0.15 mm | 0.15 mm (was 0.125) | **fixed** |
| Min drill 0.15 mm; extra charge below 0.2 mm | 0.2 mm | pass, standard price |
| Aspect ratio ≤ 8 (standard) | 1.6 / 0.2 = 8 | at the limit |
| Plated slot ≥ 0.5 mm | J2 shell tabs: four 0.6 mm routed slots | pass |
| Copper to edge ≥ 0.25 mm (CNC) | 0.3 mm DRC rule | pass |
| Inner isolation ring ≥ 7 mil | 0.25 mm hole clearance | pass |
| V-score needs a board ≥ 60–80 mm wide | 22 × 54 mm | **cannot V-score** — tab-route |

**Fab package** — `pcb/fab/serialtap-r1p0/`, regenerated from the board
and gitignored until release:
- Gerbers, X2 format: F/In1/In2/B copper, both masks, top paste, both
  silkscreens, Edge.Cuts, plus the `.gbrjob`. KiCad names inner files after
  the custom layer names (`GND (L2).g1` and so on); they are renamed to
  `In1_Cu` / `In2_Cu` / `B_Cu`, because spaces and brackets are a known way
  to trip fab upload parsers. The X2 `FileFunction` inside each file carries
  the layer order either way. There is no bottom paste file: nothing is
  assembled on L4.
- Excellon drill files in mm, PTH and NPTH separate, with PDF maps: 110 vias
  and U3's 2 thermal vias at 0.2 mm, J2 pins 0.4 mm, J2 slots 0.6 mm, J1
  pins 0.95 mm, J1's peg 1.25 mm NPTH.
- `serialtap-r1p0-top-pos.csv` — **top side only**. The ten L4 test pads are
  not flagged exclude-from-position in their footprint, so a both-sides
  export would list them and suggest bottom assembly. Coordinates are
  KiCad-absolute (negative Y), the same frame as the gerbers.
- `serialtap-r1p0-bom-pcbway.csv` — 22 lines, 33 parts, in PCBWay's column
  format, generated from the schematic. Every line has an MPN and a
  manufacturer; designators match the position file one for one.
- `serialtap-r1p0-assembly-top.pdf` — F.Fab, F.Silkscreen and the outline, for
  polarity and pin 1.

Gerber analyzer: all layers present, both drill files, 54.0 × 22.0 mm. Its
one warning, that layer extents differ, is expected: copper and mask stop
short of the outline.

### What to put on the order

| Field | Value |
|---|---|
| Layers | 4 |
| Size | 54 × 22 mm (single board; panel below) |
| Thickness | 1.6 mm |
| Stackup | PCBWay standard 4-layer, **1 oz inner, 1 oz outer** (see *Stackup*) |
| Min track / space | 5/5 mil |
| Min hole | 0.2 mm |
| Solder mask / silkscreen | Black (set in the board stackup) / white (assumed; not set in the file) |
| Surface finish | ENIG |
| Via process | Tented. The only exposed vias are the ones inside pads: U6's GND pads, U3's thermal pad and the L4 test pads |
| Impedance control | No. USB is Full Speed, and its geometry is estimated at ~101 Ω |
| Notes | Plated slots on J2 (four 0.6 mm, in the PTH drill file) |
| Assembly | Turnkey, **top side only**, 33 parts / 22 lines; **2 through-hole** parts (J1, J2) to be hand or selective soldered |

**Panel — ask PCBWay to panelise, tab-routed, not V-scored**, with rails on
the long edges for the SMT line. Put breakaway tabs only where no part is
within 1 mm of the edge. Measured from the antenna end: **top edge
x ≈ 1–5 and 47–53 mm, bottom edge x ≈ 1–6 and 48–53 mm**. Keep them off the
top edge from 5.8–17.3 mm (SW1 and SW2 at 0.3 mm) and 35.5–46.1 mm (J2,
flush). Keep them off the whole bottom edge from 7.6–46.2 mm (C4 at 0.1 mm,
L1 at 0.0 mm, and the MLCCs C1, C9, C11 and R10 at 0.7–0.9 mm, which crack
under break-out stress). Keep them off both short edges: the module
antenna is flush on the left, and J1 is flush on the right.

**Assembly notes for PCBWay:** C4 (polymer) and D1 are polarised. U6 is a
moisture-sensitive module; follow Espressif's storage and baking guidance.
The fiducials are FID1–FID3 on the board itself. Nothing goes on the bottom.

**Sourcing risk** (from [bom/README.md](../bom/README.md), stock as of
2026-09-20, now stale): C4 was single-source at 69 pieces; TPD4E05U06QDQARQ1
was sample-only at LCSC. PCBWay's turnkey buyers source by MPN worldwide,
but re-check these two before paying.

**Still open:** the last checklist item — render the gerbers themselves and
inspect them. PCBWay's own viewer, after upload and before paying, is the
check that matters, because it shows what their CAM actually read.
