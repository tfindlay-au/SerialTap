# 5. KiCad-native capture, not atopile

Date: 2026-09-13

## Status

Accepted

Supersedes the toolchain decision in SPDD §6, which made atopile the source of
truth for connectivity and parts and reduced KiCad to layout only.

## Context

The original toolchain was chosen on paper, before any of it was run. Exercising
it on 2026-09-12 produced four findings, each verified rather than assumed.

**atopile does not generate a schematic.** Its full build-target registry was
enumerated: `bom`, `pinout`, `power-tree`, `stackup`, `datasheets`, 2D/3D
renders, manufacturing data — and no schematic step. The only mentions of
"schematic" in its source are in its KiCad *PCB* plugin. This is not a gap in
the tool, it is its philosophy: the `.ato` source replaces schematic capture,
and visualisation is block diagrams (it emits `power_tree.md` as mermaid).

The consequences for this project were larger than a missing file:

- **No ERC at all.** KiCad's electrical rules check runs on a schematic.
- **No `serialtap-rNpM-sch.pdf`**, a stated deliverable (SPDD §10).
- **`kicad-happy`'s review gate 1 is stranded.** Its primary input is a
  `.kicad_sch`; the gate was specified to run "after the first `ato build`,
  before any layout effort is invested", and there was nothing for it to read.

**The atopile CLI is end-of-life.** It announces that 0.15.8 was the last CLI
release and is in maintenance mode only, replaced by a hosted app at 0.16+.
Building an open-hardware project's source of truth on a dead branch, with the
successor being someone else's cloud service, sits badly with the principle that
the project carries everything it depends on.

**It targets KiCad 9, not 10.** It installed its plugin into `KiCad/9.0/` and
writes the KiCad 9 file format, while this project mandates KiCad 10.

**Its headline feature is one we forbid.** Automatic part picking resolves to
the cheapest in-stock LCSC part meeting a value, which is exactly what design
principle 2 rules out. It was disabled by policy from the start.

### What was left

Strip out part picking (forbidden), the package registry (unused) and schematic
generation (absent), and atopile's remaining contribution is a text netlist
source, some reports, and solver assertions.

That would still be worth something — except that **no tool can generate the
schematic**, so it has to be drawn by hand either way. At that point atopile
stops being a generator and becomes a checker: a second, independent expression
of the same connectivity, in a second language, to cross-check the drawing.
Every connection would be stated twice, forever. That is a standing invitation
to drift.

### Alternatives evaluated

| Tool | Result |
|---|---|
| **SKiDL** | Netlist generation works for KiCad 5–10, but `generate_schematic()` is fully implemented only for **KiCad 5**; on 6–9 it logs a warning and returns without output. Same position as atopile. |
| **circuit-synth** 0.12.1 (beta) | Does generate a `.kicad_sch` that KiCad 10 opens, and PDF export works. **But the generated schematic does not represent the described circuit.** |
| **kicad-sch-api** | The library underneath circuit-synth; targets KiCad 7/8, and is the engine that produced the failure below. |

The circuit-synth trial is worth recording, because the failure is silent. A
three-component slice of this board's port protection — a 5-pin connector and
two series resistors — was described using the project's documented hierarchical
pattern. The netlist KiCad extracts from the schematic it generated:

```
/port_protection/PORT_RX     <- J1.4, R2.1
/port_protection/PORT_TX     <- J1.3, R1.1
unconnected-(R1-Pad2)        <- R1.2
unconnected-(R2-Pad2)        <- R2.2
```

Both series resistors dangle, and the nets on their far side are absent. Also
six `hier_label_mismatch` errors — child-sheet labels with no matching parent
sheet pins, so the hierarchy is not connected — its own netlist emits
`(pin (num "?"))`, and it draws no wires at all, expressing connectivity purely
through labels.

A tool that silently produces a wrong netlist on three components cannot hold
the source of truth for a board that will be paid for and fabricated.

## Decision

**Remove atopile. KiCad 10 is the source of truth**: schematic → netlist → PCB,
the standard flow, with ERC built in.

The schematic is drawn by hand and committed. It is **not** a build artifact,
and the rule forbidding hand-editing it is withdrawn — there is nothing
generating it to be overwritten by.

Generators may still be used as *scaffolding* — to bulk-place symbols, say — but
the committed `.kicad_sch` is the artifact, and KiCad's own ERC and extracted
netlist are the check on it.

## Consequences

- **ERC exists.** `kicad-cli sch erc`, which the project previously had no
  access to at all.
- **`kicad-happy` review gate 1 works**, on the artifact it was designed to read.
- The `-sch.pdf` deliverable is producible again (`kicad-cli sch export pdf`),
  as is the BOM (`sch export bom`).
- One toolchain, one KiCad version, no EOL dependency, and no hosted service.
- **Reproducible by anyone with KiCad** — which matters most for an open-hardware
  release. `.ato` was an extra language to learn before the board could be
  rebuilt.
- Connectivity authoring moves into the schematic. `.kicad_sch` is a poorer
  authoring surface than a text netlist language: it carries coordinates, and
  symbols must be placed as well as connected. This is the real cost, and it is
  accepted deliberately.
- Lost with atopile: its solver assertions, and its generated power-tree and
  pinout reports. The assertions are the genuine loss. In practice this board's
  hard engineering questions were answered by LTspice and will be settled by
  measurement (`sim/`, SPDD §5.8), not by a netlist solver — and `kicad-happy`
  derives power-tree analysis from the schematic.
- `elec/` is removed. The block structure its stub recorded is already in
  SPDD §4.
- Part selection discipline is unchanged and now rests entirely on review:
  every component pinned by MPN, no automatic picking. Removing atopile removes
  the picker that had to be suppressed anyway.
