# Context: SerialTap

## What this project is

**SerialTap** is an open-hardware board that puts an appliance's 5 V serial
service port on Home Assistant. An ESP32 module plus bidirectional level
translation, powered by the appliance itself — one 4-wire cable carries 5 V,
GND, TX and RX.

Primarily a hardware design project: schematic and layout (KiCad 10),
gerbers, BOM, CPL and an assembly package for PCBWay. Scope also includes the
ESPHome package that runs on the returned boards and documented cable pinouts
per appliance, so that someone else can build one and fit it.

## Design principles

**1. Quality over cost.** This is not a race to the bottom on part count or
price. Where a branded part yields a better product, use it. Where extra
decoupling makes the circuit work better, add it. BOM cost on a five-board run
is dwarfed by assembly setup, shipping and time — and a marginal part that
forces one respin costs more than it ever saved.

Concretely: polymer or hybrid aluminium for bulk rather than generic
electrolytic; MLCCs chosen with DC-bias derating in mind, not just nameplate
capacitance; a shielded branded inductor with real saturation margin; genuine
JST parts, not clones.

**2. The design is not limited to KiCad's stock libraries.** Parts are chosen
for the design, and their symbols, footprints and 3D models are sourced from
SnapEDA or elsewhere as needed.

**3. The project carries its own library.** Everything the design depends on
lives in the repo, referenced with `${KIPRJMOD}`-relative paths, so the next
person can open it without having this machine's global library.

## Glossary

### SerialTap
The project and the board. Named for what it does: it taps an appliance's 5 V
serial service connector for **both data and power** over a single 4-wire cable.

Deliberately neutral about silicon and vendor — the module already changed once
mid-design (S3 → C3) and the reference appliance is only the first of many.

Previously named `esp32leveler`, where "leveler" meant *logic level translator*
and was routinely misread as a spirit level or inclinometer. That name is
retired; any surviving reference to it means this project.

### Level translator
The circuit that converts between the ESP32's 3.3 V logic and the target's 5 V
logic. Informally "level shifter"; use **translator** in schematic and doc text.
Never "leveler".

### Target device
The external equipment the board talks to over UART. It drives 5 V logic levels
and is the reason level translation exists at all.

### Board
One physical PCB design at a given revision, written `rNpM` — `r1p0`, `r1p1`,
and so on. The revision is part of the file name rather than a directory, so a
revision is a set of files in `pcb/`, not a folder.

### Port
The board's single level-translated UART channel, translated in both directions
with fixed-direction buffers.

Physically a **5-pin** JST XA connector (2.5 mm pitch), of which the design
uses four, in order **5 V, TX, RX, spare, GND**. It is simultaneously the data path to the
target device and the board's primary power source. There is exactly one port:
the board is a single-target adapter, not a multi-port gateway.

Five pins because that is what the reference target has. Confirmed 2026-09-12
on the AS50QDFHRA, mated with a JST **XARR-05V** panel housing — XA series,
2.5 mm pitch, contacts sold separately. The board therefore carries a 5-pin XA
header so the harness can be straight-through, which is the least error-prone
cable to build and to get wrong.

**What pin 4 does is unknown.** It read as floating on the capture — no
contact, or a genuine spare. Until that is settled it connects to nothing on
the board — not the ESD array, not a GPIO — because strapping an unknown signal
to a net that matters is a worse failure than losing a pin.

**The numbering was corrected on 2026-09-20**, having previously been read from
the wrong end of the connector: old pin *n* is new pin *6 − n*. Every document
in this repo now uses the corrected numbers.

### Primary supply
The 5 V arriving on the port's JST XA connector. The board is normally powered by
the target device it is controlling.

### Supply sources
Two, either of which may be live: the port's JST XA (primary) and USB-C (bench).
They are OR-ed with ideal diodes so neither can back-feed the other — in
particular so a laptop's USB cannot push 5 V into the target appliance's rail.

### Bench access
USB-C only. It carries first flashing (esptool over the C3's ROM USB
Serial/JTAG), ESPHome console logging over USB CDC, and OpenOCD debug. In
normal service the board is updated by ESPHome OTA and USB-C is unused.

### Recovery
BOOT (GPIO9) and RESET (EN) tact switches. Not needed for ordinary flashing —
esptool resets the chip into download mode over USB by itself — but the only
way back if firmware repurposes the USB pins, wedges the USB peripheral, or
boot-loops.

### Reference target
**Haier AS50QDFHRA** split-system HVAC. It speaks **GE Appliances GEA3** over
UART at 230400 8N1 — confirmed two-way on 2026-09-19 with an ESP32 running
the esphome-gea component, which returned 64 ERDs. It does *not* speak Haier
hOn or smartAir2, and ESPHome's built-in `haier` component does not apply.
The SPDD's firmware scope predates this and needs an ADR. See
[docs/gea3.md](docs/gea3.md).

It is the *reference* target, not the only one: it is what the first boards are
validated against and what the connector pinout is chosen to match.

### Generic use
The board is intended to work with any appliance exposing 5 V power and UART on
a service connector. Nothing in the hardware may assume Haier specifically — no
protocol-dependent circuitry, no reliance on a particular idle level, and no
assumption about how much current the appliance's 5 V rail can supply.

### Port pinout
Fixed, not selectable. Conventional order **5 V, GND, TX, RX**, silkscreened
from the *board's* point of view: TX is the pin the board drives, RX is the pin
the board listens on.

There is no crossover jumper. Because the translators are fixed-direction
(see ADR 0001), a polarity mistake cannot be corrected in firmware either —
remapping the C3's UART pins would drive a buffer backwards. Adapting to an
appliance that orders or labels its pins differently is a **cable** problem, and
each appliance gets a documented harness.

## Resolved design decisions

| Area | Decision |
|---|---|
| Module | ESP32-C3-MINI-1 (ADR 0002) |
| Port | One, JST XA **5-pin**, four used: 5 V, TX, RX, (spare), GND |
| Translation | Fixed-direction dual-supply buffers (ADR 0001) |
| Supply sources | JST XA 5 V (primary) and USB-C, ideal-diode OR-ed |
| Inrush / sag | Current-limited eFuse + ≥470 µF low-ESR bulk (ADR 0004) |
| 3.3 V rail | Synchronous buck, not an LDO (ADR 0003) |
| Port protection | Series resistors on TX/RX; one quad ESD array protects both UART lines and USB D+/D−; TPS2553 protects the port 5 V input |
| Programming | USB-C only; BOOT (GPIO9) and RESET (EN) tact switches |
| Source of truth | KiCad 10 schematic → netlist → PCB (ADR 0005) |
| Parts | Every component pinned by MPN; no automatic part picking |
| Library | Project-local `lib/`, `${KIPRJMOD}`-relative, nothing global |
| Mechanical | Bare board, mounting holes, no enclosure |
| Stackup | 4-layer: L1 sig+parts / L2 GND / L3 rails / L4 GND |
| Outline | 22 × 54 mm; JST on one short edge, USB-C on the adjacent long edge, antenna at the far short edge |
| Fab class | PCBWay 5/5 mil, 0.25 mm drill; impedance not controlled |
| Indicators | Power LED only; no status or activity LEDs |
| Test points | Pads on 5 V, 3V3, GND, and both sides of each translator channel |
| First run | 5 boards, single-sided assembly (all parts on top) |
| Scope | Hardware + ESPHome package + harness documentation |
| Licence | CERN-OHL-P for hardware, MIT for firmware and docs |
| Simulation | Power path only, LTspice decks in `sim/`, gates fabrication |
| Board acceptance | Loopback plug + ESPHome self-test, per board |

### Hot loop
The buck's input loop — input ceramic → high-side FET → low-side FET → ground →
back to the ceramic. It carries the fastest di/dt on the board and is the
dominant EMI source. Minimising its area outranks every other layout
consideration except the antenna keepout.

Distinct from the **switch node**, which is the dV/dt aggressor and is
deliberately kept small in *area* rather than poured.

### Project library
`lib/` at the repo root: symbols, footprints and 3D models for every part in the
design, plus datasheets. Referenced by the KiCad project in `pcb/` with
`${KIPRJMOD}`-relative paths.

Nothing in the design may depend on a library outside this directory.

### Simulation deck
A standalone LTspice netlist in `sim/`, hand-written and deliberately outside
the KiCad flow. Decks model the power path only; nothing else
on the board has a usable model or a question worth simulating.

### Loopback plug
A JST XA shell with TX bridged to RX. Turns the whole signal chain into a
self-test: firmware transmits a pattern and checks it returns, exercising both
translation directions, both series resistors and the connector, with no scope
and no appliance. It does not prove drive strength into a loaded line.

### Build artifact
Anything produced by `kicad-cli` from the design files: gerbers, drill files,
the BOM and CPL, the schematic PDF, STEP and image renders. These live under
`pcb/serialtap-rNpM/` and are never hand-edited — regenerate them instead.

The design files themselves — `.kicad_sch`, `.kicad_pcb`, `.kicad_pro` — are
**not** build artifacts. They are drawn and maintained by hand, and they are the
source of truth (ADR 0005). Nothing generates them, which is why there is no
rule against editing them.

## Known risks

- **Weak appliance rail.** The Haier 5 V service output is current-limited and
  its capability is not yet measured. Mitigated by the buck (≈250 mA peak draw
  versus ≈335 mA for an LDO), soft start, and bulk capacitance — but the actual rail must be
  measured during bring-up before the design is considered validated.
  Simulation (`sim/`, 2026-09-12) says it needs to supply **300–370 mA**, and
  that bulk capacitance cannot substitute for source current: sag is set by the
  *average* draw, so the capacitor rides out one transmit burst and nothing
  longer.
- **Bare board in an appliance.** No enclosure means exposed electronics near
  HVAC condensate and mains wiring. Accepted deliberately; the board is not
  weather- or touch-protected, and any production use would need one.
- **No SPICE model for the buck or eFuse.** Simulation gates fabrication, so a
  part without a usable vendor model cannot be used regardless of price or
  availability. This constrains selection before a part is committed.
- **Silent substitution at assembly.** Every part is pinned by MPN precisely so
  that a cheaper equivalent cannot reach the board unnoticed. Substitutions must
  be proposed back for a decision, never applied silently.
- **Protocol — resolved.** The port speaks GEA3, which GE publishes
  (tiny-gea-api) and for which an ESPHome component exists (esphome-gea).
  Decoded 2026-09-18, confirmed two-way 2026-09-19, recorded in
  [ADR 0006](docs/adr/0006-gea3-not-hon.md) with the ERD map in
  [docs/gea3.md](docs/gea3.md). No hardware consequence; it *validates*
  ADR 0001, because GEA3 is full duplex with a fixed direction per line.
  Remaining work is firmware only: which ERD carries which control, the ten
  ERDs GE's public set does not name, and ERD `0x6003`.
- **Rail capability — inferred, not measured.** The resistor load test no longer
  gates fabrication; `RILIM` is set from inference instead
  ([ADR 0007](docs/adr/0007-rail-limit-inferred-not-measured.md)). What that
  gives up is written down there, along with the conditions that reinstate the
  test. The unexplained manual reset on first power-up from the rail is the one
  open item that could still change the design.
- **Unverified Haier pinout.** ~~Partly resolved.~~ **Resolved 2026-09-20,
  except for one pin.** The *connector* was confirmed on 2026-09-12: a 5-pin
  JST XA, 2.5 mm pitch, mated with an XARR-05V panel housing. The *pin order*
  is now settled — 5 V, TX, RX, spare, GND — after the numbering was found to
  have been read from the wrong end; direction comes from the working TinyS3
  link rather than inference. **Pin 4's function remains unknown**, which holds
  up nothing but the harness documentation.
