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

2. **Every part is chosen deliberately.** Pin every component by MPN in the
   `.ato`, passives included. No automatic "cheapest in stock" picking — it is
   exactly the behaviour principle 1 rules out.

3. **The project carries its own library.** `lib/` holds symbols, footprints,
   3D models and datasheets for everything in the design, referenced with
   `${KIPRJMOD}`-relative paths. Source parts from SnapEDA or vendors as the
   design needs — do not limit the design to KiCad's stock libraries, and never
   reference a library outside the repo. The next person will not have this
   machine's global library.

## Tooling

| Tool | Role |
|---|---|
| atopile (`ato`) | **Source of truth** for connectivity and parts. `elec/*.ato` |
| KiCad **10** | Layout only. `pcb/serialtap-rNpM/kicad-src/` |
| `kicad-cli` | `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli` — ERC, DRC, gerber/drill/BOM/CPL export, STEP and image renders |
| LTspice | Power-path simulation only. `sim/` — standalone SPICE netlists, outside the atopile flow. Chosen because Homebrew cannot build ngspice on macOS 12 |
| kicad-happy | Installed plugin (v2.2.1, 11 skills). Design review over the generated `.kicad_sch` / `.kicad_pcb` — EMC, power, ESD, thermal, BOM lifecycle, PCBWay DFM |

### kicad-happy review gates

Run it at three points, not only before fabrication — its findings are cheapest
to act on early:

1. **After the first `ato build`** — regulator feedback network, decoupling
   adequacy, ESD coverage by connector, fuse sizing, temperature grade, EOL
   parts. Before any layout effort is invested.
2. **After layout** — thermal via adequacy, ground-plane voids, trace width vs
   current, impedance, DFM scoring.
3. **Before upload to PCBWay** — the `pcbway` skill and the pre-order checklist.

It is a **review aid, not a sign-off.** It does not replace `kicad-cli` ERC/DRC,
the [layout-rules checklist](docs/layout-rules.md), or human review — and it
cannot measure a real appliance. The risk it introduces is false confidence.

**The rule that keeps this honest:** the KiCad *schematic* is a build artifact of
`ato build`. Never hand-edit it. If the schematic is wrong, fix the `.ato` and
rebuild. The `.kicad_pcb` is the exception — it is hand-maintained, and only its
netlist comes from atopile.

## Layout

Binding rules, DRC values and a pre-release checklist are in
[docs/layout-rules.md](docs/layout-rules.md). Priority order when rules conflict:

1. Antenna keepout (no copper, any layer)
2. Buck input hot loop (no vias inside it)
3. ESD path at the connector
4. USB pair integrity

And: **never split the ground plane.**

## Conventions

- Board and revision naming: `serialtap-r1p0`, `serialtap-r1p1`, … (follows
  `../daikin-esp`)
- Say **level translator**, not "leveler" — the project was formerly
  `esp32leveler` and that name caused persistent confusion with spirit levels
- Fab class: PCBWay 5/5 mil, 0.25 mm drill, 4-layer, single-sided assembly
- Licence: CERN-OHL-P v2 (hardware), MIT (firmware and docs)

## Current state

Design documented, nothing built. Three things gate fabrication:

1. Power-path simulation (`sim/`) — yields the minimum source current the design
   tolerates. **`rail-sag` and `inrush` done** (2026-09-12); they put the
   requirement at **300–370 mA** and confirm 470 µF is the right bulk value.
   `buck-load-step` is blocked on the buck MPN and its vendor SPICE model —
   a behavioural stand-in cannot answer a control-loop question. See
   [sim/README.md](sim/README.md)
2. Measuring the Haier's 5 V rail against that number
3. Confirming the AS50QDFHRA service connector pinout (determines the cable, not
   a respin)

Next decision up: buck and eFuse MPNs. Both need vendor SPICE models (SPDD
§7.2); the eFuse's current-limit accuracy is what collapses the 300–370 mA
range into one number.
