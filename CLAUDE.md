# SerialTap

An open-hardware board that puts an appliance's 5 V serial service port on Home
Assistant. ESP32-C3 plus bidirectional level translation, powered by the
appliance itself — one 4-wire cable carries 5 V, GND, TX and RX.

Reference target: Haier AS50QDFHRA. **GE Appliances GEA3** over UART, 230400 8N1,
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

**Gates to fabrication**

1. **Project library.** Complete for every pinned part as of 2026-09-19 and
   validating under `kicad-cli`: 12 symbols, 10 footprints, a 3D model on every
   footprint, nothing referencing outside the repo. One open item in
   [lib/README.md](lib/README.md): the **`TXU0204` package** needs confirming.
   **`TPS2553DBVR` sourcing is a live problem** — only the `-1` latch-off variant
   had stock, and that variant is ruled out; see SPDD §13
2. **Remaining part detail.** Passives, the two 5.1 kΩ USB-C CC pulldowns,
   BOOT/RESET switches, power LED, packages for the TPS62162 and TXU0204, and a
   distributor stock check for every line. Selection is done; detail is not
3. **Schematic capture**, then `kicad-happy` review gate 1
4. **`sim/buck-load-step`** — the deck runs on TI's converted model but does not
   yet regulate at 3.3 V, so its results are marked untrusted. Not blocked on a
   part: the buck is pinned
5. Layout, then review gates 2 and 3

**Not gates, but cheap and still owed** ([ADR 0007](docs/adr/0007-rail-limit-inferred-not-measured.md))

- A meter in series with the TinyS3's 5 V lead. First measured current in the
  project. Needs no added load
- Cold power-cycle the appliance twice. The board needed a manual reset on its
  first power-up from the rail and that is unexplained. The one open item that
  could still change the design
- RX pull-up measurement, unit off. Sizes R<sub>s</sub>, currently a 100–330 Ω
  guess
- Connector pin-order direction. Roles are confirmed by a working conversation;
  the numbering is not. Determines the cable, not a respin
