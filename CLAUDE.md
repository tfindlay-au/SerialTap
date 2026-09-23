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
| KiCad **10** | **Source of truth.** Schematic → netlist → PCB, all of it in `pcb/serialtap.kicad_*` ([ADR 0005](docs/adr/0005-kicad-native-capture.md)) |
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

- The board is `serialtap`: `pcb/serialtap.kicad_sch`, `.kicad_pcb`, `.kicad_pro`.
  **No revision in file or folder names** — git is the version control. Tag the
  commit each fab order is built from, so a physical board traces back to its
  sources (renamed from `serialtap-r1p0` on 2026-09-24)
- Say **level translator**, not "leveler" — the project was formerly
  `esp32leveler` and that name caused persistent confusion with spirit levels
- Fab class: PCBWay 5/5 mil, 0.2 mm drill (vias 0.2 / 0.5 mm, 0.15 mm ring),
  4-layer, single-sided assembly — drill moved from 0.25 mm on 2026-09-24 to meet
  PCBWay's via annular-ring minimum; see [layout-rules.md](docs/layout-rules.md)
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

**The board is ready to order; nothing is built yet.** Every stage below is done and
recorded — the detail lives in the linked documents, not here.

| Stage | State | Record |
|---|---|---|
| Power-path simulation | `rail-sag`, `inrush` and `buck-load-step` pass. The appliance rail must supply **300–370 mA**; 470 µF bulk is right; the buck holds a 40 → 335 mA step with ≥285 mV margin | [sim/README.md](sim/README.md) |
| Protocol | **GEA3**, confirmed two-way 2026-09-19 — no hardware consequence | [ADR 0006](docs/adr/0006-gea3-not-hon.md), [docs/gea3.md](docs/gea3.md) |
| Parts | **All 22 BOM lines pinned** by MPN with footprint and datasheet; ~US$13.82/board; C4 is the thinnest line (single source) | [bom/README.md](bom/README.md), SPDD §7.4 |
| Library | Complete and in-repo: every footprint has a 3D model and a courtyard | [lib/README.md](lib/README.md) |
| Schematic | Hand-drawn, KiCad 10, ERC clean, netlist checked against every invariant. `RILIM` 66.5 kΩ (351–449 mA). No TVS on USB VBUS — **decided** | [docs/schematic-capture.md](docs/schematic-capture.md) |
| Layout | Placed and routed; DRC 0 / 0 / 0 with schematic parity; PCBWay stackup (1 oz inner); vias 0.2 / 0.5 mm. Departures recorded as exceptions — notably **one via on USB D−**, which topology forces | [docs/layout-rules.md](docs/layout-rules.md) |
| Review gates | kicad-happy gate 1 (schematic), gate 2 (layout — no blockers) and gate 3 (PCBWay pre-order — via ring fixed) all run | [schematic-capture.md](docs/schematic-capture.md), [layout-rules.md](docs/layout-rules.md) |
| Mechanical | 22 × 54 mm, **no mounting holes**; the board keeps the OEM outline and sits in its slot | [bench-plan Part 3](docs/bench-plan.md) |

**Next:** tag the commit, upload `pcb/fab/` to PCBWay, inspect their gerber
viewer, re-check C4 and U5 stock, and order with the specification in
[layout-rules.md § Review gate 3](docs/layout-rules.md#review-gate-3--pcbway-pre-order-2026-09-24).

**Still owed, not gating** ([ADR 0007](docs/adr/0007-rail-limit-inferred-not-measured.md)):

- A meter in series with the TinyS3's 5 V lead — the project's first measured
  current. Needs no added load
- Cold power-cycle the appliance twice. The board needed a manual reset on its
  first power-up from the rail, unexplained — **the one open item that could
  still change the design**
- What connector **pin 4** carries is unknown; it blocks only the harness
