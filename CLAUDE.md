# SerialTap

An open-hardware board that puts an appliance's 5 V serial service port on Home
Assistant. ESP32-C3 plus bidirectional level translation, powered by the
appliance itself — one 4-wire cable carries 5 V, GND, TX and RX.

Reference target: Haier AS50QDFHRA (hOn over UART, 9600 8E1, ESPHome `haier`).
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

- `sim/rail-sag` and `sim/inrush` (2026-09-12). The appliance rail must supply
  **300–370 mA**, not the 250 mA originally assumed; 470 µF is the right bulk
  value and more capacitance would not rescue a weak rail. See
  [sim/README.md](sim/README.md)
- The service connector is a **5-pin JST XA**, not 4-pin (2026-09-12)
- KiCad project set up and verified: 4-layer stackup, DRC rules from
  [layout-rules.md](docs/layout-rules.md) confirmed *enforced*, ERC and DRC both
  clean and running

**Gates to fabrication**

1. **Part selection.** Nothing is pinned. Blocks almost everything else: the
   schematic, `buck-load-step`, and the BOM. The buck needs a vendor SPICE
   model (SPDD §7.2); the eFuse does not (ADR 0004 amendment), but its
   current-limit accuracy is what collapses 300–370 mA into one number
2. **Schematic capture**, then `kicad-happy` review gate 1
3. **`sim/buck-load-step`** — the deck runs on TI's converted model but does not
   yet regulate at 3.3 V, so its results are marked untrusted. Blocked on the
   buck MPN anyway
4. **Measure the Haier's 5 V rail** against the 300–370 mA figure — open-circuit
   voltage, current limit, sag under a 250 mA pulsed load, and what it *does* in
   current limit
5. **Confirm the connector pin order** and what the fifth pin carries (Saleae
   capture on all five). Determines the cable, not a respin
6. Layout, then review gates 2 and 3
