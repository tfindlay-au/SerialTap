# SerialTap

An open-hardware board that puts an appliance's 5 V serial service port on Home
Assistant. ESP32-C3 plus bidirectional level translation, powered by the
appliance itself — one 4-wire cable carries 5 V, GND, TX and RX.

Reference target: Haier AS50QDFHRA. Service connector pin order is
**1 = 5 V, 2 = TX, 3 = RX, 4 = spare, 5 = GND**, TX being the pin the board
drives (corrected 2026-09-20 — earlier numbering ran the other way).
**GE Appliances GEA3** over UART, 230400 8N1,
confirmed two-way on 2026-09-19 — not hOn, not ESPHome `haier`. See
[docs/gea3.md](docs/gea3.md).
Intended to work with any appliance exposing 5 V and UART on a service port.

**Read [CONTEXT.md](CONTEXT.md) for terminology and [docs/SPDD.md](docs/SPDD.md)
for the design.** Decisions with lasting consequences are in
[docs/adr/](docs/adr/) — read them before contradicting one.

## Design principles

These are not negotiable defaults to be optimised away.

1. **Quality over cost.** Not a race to the bottom on part count or price. If a
   branded part yields a better product, use it. If extra decoupling makes it
   work better, add it. BOM cost on a five-board run is dwarfed by assembly
   setup, shipping and time; a marginal part that forces a respin costs more
   than it ever saved.

2. **Every part is chosen deliberately.** Pin every component by MPN on its
   schematic symbol, passives included. No automatic "cheapest in stock"
   picking — it is exactly the behaviour principle 1 rules out.

3. **The project carries its own library.** `lib/` holds symbols, footprints,
   3D models and datasheets for everything in the design, referenced with
   `${KIPRJMOD}`-relative paths. Source parts from SnapEDA or vendors as the
   design needs — do not limit the design to KiCad's stock libraries, and never
   reference a library outside the repo. The next person will not have this
   machine's global library.

## Tooling

| Tool | Role |
|---|---|
| KiCad **10** | **Source of truth.** Schematic → netlist → PCB, all of it in `pcb/serialtap-rNpM/` ([ADR 0005](docs/adr/0005-kicad-native-capture.md)) |
| `kicad-cli` | `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli` — ERC, DRC, gerber/drill/BOM/CPL export, STEP and image renders |
| LTspice | Power-path simulation only. `sim/` — standalone SPICE netlists, hand-written and outside the KiCad flow. Chosen because Homebrew cannot build ngspice on macOS 12 |
| kicad-happy | Installed plugin (v2.2.1, 11 skills). Design review over the generated `.kicad_sch` / `.kicad_pcb` — EMC, power, ESD, thermal, BOM lifecycle, PCBWay DFM |

### kicad-happy review gates

Run it at three points, not only before fabrication — its findings are cheapest
to act on early:

1. **After the schematic is captured** — regulator feedback network, decoupling
   adequacy, ESD coverage by connector, fuse sizing, temperature grade, EOL
   parts. Before any layout effort is invested.
2. **After layout** — thermal via adequacy, ground-plane voids, trace width vs
   current, impedance, DFM scoring.
3. **Before upload to PCBWay** — the `pcbway` skill and the pre-order checklist.

It is a **review aid, not a sign-off.** It does not replace `kicad-cli` ERC/DRC,
the [layout-rules checklist](docs/layout-rules.md), or human review — and it
cannot measure a real appliance. The risk it introduces is false confidence.

**The rule that keeps this honest:** nothing here is generated, so nothing can
be silently regenerated over. The schematic is drawn by hand and is the source
of truth; the PCB takes its netlist from it through KiCad. Both are checked
mechanically — `kicad-cli sch erc` and `kicad-cli pcb drc` — and neither
substitutes for reading the thing.

Do not reintroduce a code-generates-schematic tool without reading
[ADR 0005](docs/adr/0005-kicad-native-capture.md) first. Three were evaluated
and rejected on evidence, one of them for silently emitting a wrong netlist.

## Layout

Binding rules, DRC values and a pre-release checklist are in
[docs/layout-rules.md](docs/layout-rules.md). Priority order when rules conflict:

1. Antenna keepout (no copper, any layer)
2. Buck input hot loop (no vias inside it)
3. ESD path at the connector
4. USB pair integrity

And: **never split the ground plane.**

## Conventions

- Board and revision naming: `serialtap-r1p0`, `serialtap-r1p1`, …
  The revision is in the **filename**, not a folder: `pcb/serialtap-r1p0.kicad_sch`
- Say **level translator**, not "leveler" — the project was formerly
  `esp32leveler` and that name caused persistent confusion with spirit levels
- Fab class: PCBWay 5/5 mil, 0.25 mm drill, 4-layer, single-sided assembly
- Licence: CERN-OHL-P v2 (hardware), MIT (firmware and docs). Both permissive;
  see `NOTICE` for which files fall under which, and for the third-party
  material that is under neither

**Conventions here stand on their own reasoning.** `../daikin-esp` is an
unrelated board by another author (Greg Davill) that happens to sit on this
machine — not a standard. Cite it for *evidence* (what part it used, how that
worked out) and never as precedent for how this repo should be shaped. There
are thousands of KiCad projects and no canonical layout; if a convention cannot
be justified on its own terms, it is not a convention worth keeping.

## Current state

Design documented, nothing built — but the toolchain is now exercised rather
than assumed, and it cost a rewrite: see
[ADR 0005](docs/adr/0005-kicad-native-capture.md).

**Done**

- `sim/rail-sag` and `sim/inrush` (2026-09-12, **both re-run 2026-09-20**). The
  appliance rail must supply **300–370 mA**, not the 250 mA originally assumed;
  470 µF is the right bulk value and more capacitance would not rescue a weak
  rail. Both decks were found **unrunnable in a clean checkout** and are now
  fixed: `models/behavioral.lib` had been deleted by accident, and `rail-sag`
  set a 0 Ω resistor that LTspice rejects outright. No conclusion reversed. See
  [sim/README.md](sim/README.md)
- The service connector is a **5-pin JST XA**, not 4-pin (2026-09-12)
- KiCad project set up and verified: 4-layer stackup, DRC rules from
  [layout-rules.md](docs/layout-rules.md) confirmed *enforced*, ERC and DRC both
  clean and running
- **Every major active is pinned by MPN with reasoning** (SPDD §7.4): buck
  TPS62162, inductor XGL4020-222MEC, translator TXU0204, eFuse TPS2553,
  ideal-diode OR LM66200, ESD array TPD4E05U06QDQARQ1, module
  ESP32-C3-MINI-1-H4X, bulk PCL1A471MCL1GS, both connectors
- **The protocol is GE Appliances GEA3, not hOn** (2026-09-19). Decoded, then
  confirmed two-way on the appliance. Public, with a C library and an existing
  ESPHome component. No hardware consequence, and it *validates* ADR 0001.
  [ADR 0006](docs/adr/0006-gea3-not-hon.md), [docs/gea3.md](docs/gea3.md)
- **The rail load test no longer gates fabrication** (2026-09-19). Its only
  design output was one resistor. [ADR 0007](docs/adr/0007-rail-limit-inferred-not-measured.md)
- **The service connector was being read from the wrong end** (2026-09-20).
  Corrected everywhere: the order is 5 V, TX, RX, spare, GND, and old pin *n*
  is new pin *6 − n*. Nothing measured changed — the bench voltages and the
  5.84/4.62 kΩ bias readings were taken against physical pins — but every
  document that cited a pin number did. Direction is now settled by the working
  TinyS3 link rather than inference: TinyS3 TX drives pin 2, pin 3 drives
  TinyS3 RX. The schematic was rewired to match
- **The schematic exists** (2026-09-20). Drawn by hand into
  `pcb/serialtap-r1p0.kicad_sch` from
  [docs/schematic-capture.md](docs/schematic-capture.md), which Codex left as
  the wiring contract. ERC clean, netlist-checked against every invariant, and
  `RILIM` now has a value: **66.5 kΩ 1%**, a 351–449 mA limit once tolerance is
  counted — above the board's 250 mA peak, below the rail's OEM-implied
  capability. `FAULT`, `PG` and `ST` go to test pads, not GPIOs
- **Every pinned part is sourceable, and the eFuse blocker is retired**
  (2026-09-20). `TPS2553DBVR` — the plain non-latching part — is stocked at LCSC
  (44k) and Mouser (882); Digi-Key is out until 2026-10-26, which is what the
  2026-09-19 check actually saw. No single distributor can fill the board, and
  the thinnest line is now the Nichicon bulk cap at 69 pieces in one place.
  ~US$11.46/board. [bom/README.md](bom/README.md)

**Gates to fabrication**

1. **Project library.** ~~Gate~~ **Closed.** Complete for every pinned part as
   of 2026-09-19 and validating under `kicad-cli`: 10 footprints, a 3D model on
   every footprint, nothing referencing outside the repo. Grown to 23 symbols on
   2026-09-20 with the generics capture needed (R, C, LED, switch, test point,
   power symbols), all copied in from KiCad 10 rather than referenced
2. **Remaining part detail.** ~~Gate~~ **Now countable, and the last one before
   layout.** The schematic fixes it at **25 components over 12 unique lines** —
   ten resistors, ten ceramics, the LED and the two tact switches. Footprints
   follow the MPNs, so both land together. Packages for the pinned parts are
   settled (TPS62162 `DSG`, TXU0204 `RUT`) and the **distributor stock check is
   done for all ten** (2026-09-20, [bom/](bom/))
3. **Schematic capture.** ~~Gate~~ **Closed 2026-09-20.** 43 components, 57
   nets, one A3 sheet, KiCad 10 native. `kicad-cli sch erc --severity-all`: 0
   violations, and every review invariant checked against the *extracted
   netlist* rather than the drawing. `kicad-happy` review gate 1 run: 2 errors
   and 2 warnings, triaged in
   [docs/schematic-capture.md](docs/schematic-capture.md) — one is real (no TVS
   on USB VBUS, which reaches the LM66200's 6 V absolute maximum unclamped) and
   one is the passives above
4. **`sim/buck-load-step`** — corrected 2026-09-20 with fixed-output TPS62162
   `FB` tied to AGND. It passes the 40 → 335 mA load step with ≥285 mV margin.
5. Layout, then review gates 2 and 3

**Not gates, but cheap and still owed** ([ADR 0007](docs/adr/0007-rail-limit-inferred-not-measured.md))

- A meter in series with the TinyS3's 5 V lead. First measured current in the
  project. Needs no added load
- Cold power-cycle the appliance twice. The board needed a manual reset on its
  first power-up from the rail and that is unexplained. The one open item that
  could still change the design
- RX pull-up measurement **complete**: 5.84/5.80 kΩ to GND and 4.62 kΩ to 5 V;
  both UART series resistors are now 330 Ω, 1%
- ~~Connector pin-order direction~~ **Settled 2026-09-20.** The connector had
  been read from the wrong end: the order is **5 V, TX, RX, spare, GND**, and
  direction comes from the working TinyS3 link, not inference. Every document
  in the repo now uses the corrected numbers. What **pin 4** carries is still
  unknown, and still blocks only the harness
