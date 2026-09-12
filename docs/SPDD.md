# Software & Product Design Document — SerialTap

**Status:** draft, pre-schematic
**Date:** 2026-09-12
**Licence:** CERN-OHL-P v2 (hardware), MIT (firmware and documentation)

Terminology for this project is defined in [CONTEXT.md](../CONTEXT.md).
Decisions with lasting consequences are recorded in [docs/adr/](adr/).

---

## 1. Purpose

A small PCB that lets an ESP32 speak UART to appliances whose serial ports use
5 V logic, and be powered by those same appliances over the same connector.

The immediate motivation is putting a **Haier AS50QDFHRA** split-system HVAC on
Home Assistant via ESPHome's `haier` component. The board is deliberately not
specialised to it: any appliance exposing 5 V, GND, TX and RX on a service
connector is in scope.

The name describes the mechanism: one 4-wire cable **taps** the appliance's
service connector for both data and power. It is deliberately neutral about
silicon and vendor — the module changed once during design and the reference
appliance is only the first of many.

Formerly `esp32leveler`, where "leveler" meant *level translator* and was
consistently misread as a spirit level.

## 2. Scope

**In scope**

- Schematic and PCB design (KiCad 10)
- Fabrication and assembly package for PCBWay: gerbers, drill, BOM, CPL
- An ESPHome package that runs on the assembled board
- Harness documentation: cable pinouts per appliance, starting with the Haier

**Out of scope**

- Any enclosure. The board ships bare (§8).
- Protocol work beyond configuring ESPHome's existing `haier` component
- Certification, EMC testing, or commercial production

## 3. Functional requirements

| # | Requirement |
|---|---|
| FR-1 | Provide one bidirectionally level-translated UART channel between the ESP32's 3.3 V logic and a target's 5 V logic |
| FR-2 | Accept 5 V from the target on the same connector as the data lines, and run the whole board from it |
| FR-3 | Operate reliably at 9600 8E1 (the reference target's rate) and impose no design ceiling below 1 Mbaud |
| FR-4 | Be flashable from a bare, unprogrammed state over USB-C with no jig or external adapter |
| FR-5 | Be recoverable by hand if firmware renders USB unusable |
| FR-6 | Never source current into a target appliance's rail from a bench supply, or vice versa |
| FR-7 | Survive ordinary installation faults on the port: ESD, hot-plug, a line shorted to 5 V or GND |
| FR-8 | Support ESPHome OTA as the normal update path once first-flashed |

## 4. Architecture

**Signal path**

```
  JST XA        series R   ESD     fixed-direction        ESP32-C3-MINI-1
  TX ----------[ Rs ]-----[ ]----[ B->A translator ]----> RX  (UART1)
  RX ----------[ Rs ]-----[ ]<---[ A->B translator ]----- TX  (UART1)
                                  VCCB=5V  VCCA=3V3

                                   USB-C  D+/D- <-------> GPIO18/19
                                                  (ROM USB Serial/JTAG:
                                                   flashing, CDC log, debug)
```

**Power path**

```
  JST XA 5V --[fuse]--[ eFuse ]--[ideal diode]--+
               (current-limited, bounds inrush) |
                                                +-- 5V rail --+-- [470uF+]
  USB-C VBUS ---------------------[ideal diode]-+              |
                                                               +-- [PWR LED]
                                                               |
                                                               +-- VCCB
                                                               |
                                                        +------+------+
                                                        | sync buck   |
                                                        |  5V -> 3V3  |
                                                        +------+------+
                                                               |
                                                        3V3 rail --> C3, VCCA
```

**Signal path.** Target ↔ series resistors ↔ ESD array ↔ fixed-direction
translators ↔ C3 UART1. Console and debug ride the C3's built-in USB
Serial/JTAG on GPIO18/19, out to USB-C, so the port's UART is never shared with
logging.

**Power path.** The JST 5 V and USB-C VBUS are each ideal-diode OR-ed onto a
common 5 V rail; a slew-controlled load switch limits inrush; a synchronous buck
produces 3.3 V.

## 5. Detailed design

### 5.1 Level translation

Two fixed-direction dual-supply buffer channels — one 3.3 V → 5 V for TX, one
5 V → 3.3 V for RX — with direction hard-wired in copper. Rationale and the
rejection of auto-direction parts (TXB/TXS) is in
[ADR 0001](adr/0001-fixed-direction-level-translation.md).

VCCA is the 3.3 V rail; VCCB is the 5 V rail. Unused translator inputs are tied
off, never left floating.

Consequence to keep in mind: direction is frozen. Half-duplex or single-wire
buses are out of reach for this board without a revision.

### 5.2 Port and pinout

One JST XA **5-pin** connector (2.5 mm pitch), four of which are used, in fixed
pin order **5 V, GND, TX, RX**, silkscreened from the board's point of view —
TX is the pin the board drives.

The pin count follows the reference target: the AS50QDFHRA service connector
was confirmed on 2026-09-12 to be a 5-pin XA, mated with a JST XARR-05V panel
housing. Carrying five on the board keeps the harness straight-through.

Board-side candidates, all XA series, 2.5 mm pitch, 5 position:

| MPN | Entry |
|---|---|
| `B05B-XASK-1(LF)(SN)` | vertical, top entry, shrouded |
| `B05B-XASK-1-A(LF)(SN)` | vertical, with locating boss |
| `S05B-XASK-1(LF)(SN)` | right angle, side entry |

Not yet pinned: entry direction is a mechanical call about how the board sits in
the appliance, and the gender/mating relationship against XARR-05V should be
read off the JST XA datasheet rather than a distributor summary before an MPN
is committed.

**The fifth pin's function is unknown**, so nothing on the board connects to it
yet — not the ESD array, not a GPIO. It is captured with the other four during
the Wednesday probe. Committing it to anything before that risks strapping an
unknown signal, possibly not a 5 V-logic one, to a net that matters.

There is no crossover jumper, and the C3's GPIO matrix cannot substitute for
one: remapping UART pins would drive a fixed-direction buffer backwards.
Appliances that order or label their pins differently are accommodated by a
**cable**, documented per appliance.

### 5.3 Power

| Element | Choice |
|---|---|
| Sources | JST XA 5 V (primary), USB-C VBUS (bench) |
| Arbitration | Ideal-diode OR on each source (LM66100 / MAX40203 class) |
| Inrush | Current-limited switch / eFuse (TPS2553 class), programmable limit ([ADR 0004](adr/0004-current-limited-inrush.md)) |
| Bulk | ≥470 µF low-ESR on the 5 V rail, plus local ceramics |
| 3.3 V | Synchronous buck ([ADR 0003](adr/0003-buck-not-ldo.md)) |
| Fusing | Resettable fuse on the 5 V input, unless the chosen eFuse's own overcurrent protection makes it redundant |

Ideal diodes rather than Schottkys because ~20 mV of drop keeps the 5 V rail
genuinely at 5 V for the translators' VCCB, and because a laptop must never be
able to push current into an appliance's rail (FR-6).

### 5.4 Power budget

| Condition | 3.3 V draw | 5 V draw (buck, ~90%) |
|---|---|---|
| Idle, WiFi connected | ~40 mA | ~30 mA |
| WiFi RX / normal traffic | ~85 mA | ~65 mA |
| WiFi TX peak (20 dBm) | ~335 mA | ~250 mA |

The Haier's 5 V service rail capability is **not yet measured**. Simulation
(§5.8) establishes the minimum the design needs; measurement (§12) confirms the
appliance provides it. Both gate fabrication.

### 5.5 Programming and recovery

USB-C is the only programming, logging and debug interface
([ADR 0002](adr/0002-c3-and-usb-only-programming.md)). A virgin C3 enumerates on
its ROM USB Serial/JTAG and esptool drives it into download mode unaided, so
first flash needs no buttons.

BOOT (GPIO9) and RESET (EN) tact switches exist for the cases where that fails:
firmware repurposing GPIO18/19, a wedged USB peripheral, a hard boot-loop.

No TC2050 footprint. The ESP32-C3 has no external JTAG pins, so a pogo footprint
would carry the same USB pair as the USB-C connector and add nothing.

### 5.6 Protection

- Series resistors (100–330 Ω) on TX and RX. Free at 9600 baud; limits fault
  current if a line meets 5 V or GND during install.
- ESD diode array on the 5 V-side signals.
- Resettable fuse on the 5 V input.
- Reverse current on both supply inputs is already blocked by the ideal diodes.

### 5.7 Indicators and test access

One power LED, high-value resistor. No status LED and no TX/RX activity LEDs —
serial traffic is observable through ESPHome's own logging, which makes
dedicated hardware indicators redundant.

Test pads on 5 V, 3V3, GND, and **both the 3.3 V and 5 V side of each translator
channel**. These are bare copper at zero BOM cost and are what make ADR 0001's
"don't debug translation after assembly" argument actually hold.

### 5.8 Simulation

Simulation is scoped to the **power path only** and gates fabrication.

Nothing else on the board benefits. The C3-MINI-1 has no SPICE model — its
relevant behaviour is a pulsed current source. The translators ship as IBIS, not
SPICE, and answer signal-integrity questions that do not exist at 9600 baud over
a short harness; the translator question that does matter (drive strength into
an unknown appliance's pull-ups) is a DC calculation.

Three decks in `sim/`:

| Deck | Question it answers |
|---|---|
| `rail-sag` | Given a current-limited source, bulk capacitance and a 250 mA WiFi burst, does 3.3 V stay above the C3's brownout threshold? Swept across source current limit. |
| `inrush` | What does the appliance see at plug-in, with the eFuse limit set to a given value? |
| `buck-load-step` | Does the buck recover from a 30 → 250 mA step without undershooting brownout? |

`rail-sag` is the important one. Its output is not "it works" but a **number**:
the minimum source current this design tolerates. That converts the project's
largest unknown from a blocker into a specification to go and measure against,
and quantifies what extra bulk capacitance would buy if the Haier falls short.

**Status (2026-09-12).** `rail-sag` and `inrush` are written and run; results
and the numbers they produced are in [sim/README.md](../sim/README.md). In
short: sag is an average-current problem, so 470 µF is the right bulk value and
adding more would not rescue a weak rail; and the eFuse limit must sit strictly
below the appliance's own limit, which puts the appliance requirement at
**300–370 mA**, not the 250 mA of §5.4.

`buck-load-step` is **not** written. Its question is entirely about the
converter's control loop, which the behavioural blocks in `sim/models/` cannot
answer, so it is blocked on the buck MPN and its vendor SPICE model (§7.2)
rather than faked. Fabrication stays gated until it runs.

Simulation lives **outside** the KiCad flow. KiCad 10's built-in ngspice can
simulate a schematic, but the questions here are about a power path that spans
an appliance, a cable and a converter — most of which is not on the board and
has no symbol. The decks are standalone SPICE netlists, which also keeps them
readable and diffable on their own terms.

**Simulator: LTspice.** Homebrew cannot build ngspice on this machine — macOS
12.7.6 is past Homebrew's support window, and `brew install ngspice` fails
trying to compile gcc from source. KiCad bundles `libngspice` as a shared
library with no CLI. LTspice is a native macOS download, needs no toolchain, is
auto-detected by `kicad-happy`'s `spice` skill, and is the format many vendors
publish their models in — which matters given §7.1 requires parts with published
SPICE models.

## 6. Toolchain

**KiCad 10 is the single source of truth**: schematic → netlist → PCB, the
standard flow, with ERC built in. This reverses the original decision to make
atopile the source of truth and reduce KiCad to layout. The reasoning, the
evidence gathered by actually running the tools, and the three
code-to-schematic generators evaluated and rejected are in
[ADR 0005](adr/0005-kicad-native-capture.md).

| Artefact | Owner | Hand-edited? |
|---|---|---|
| `*.kicad_sch` | KiCad 10 | **Yes — this is the source.** Capture lives here |
| `*.kicad_pcb` | KiCad 10 | Yes — netlist updated from the schematic |
| `*.kicad_pro` | KiCad 10 | Yes — carries the DRC rules and net classes from [layout-rules.md](layout-rules.md) |
| netlist | `kicad-cli sch export netlist` | No |
| gerbers, drill | `kicad-cli` | No |
| BOM | `kicad-cli sch export bom` | No |
| `-sch.pdf` | `kicad-cli sch export pdf` | No |
| `sim/*.cir` | hand-written | Yes — standalone, outside the KiCad flow (§5.8) |

Nothing among the design files is generated, so nothing can be silently
regenerated over — which is why there is no "never hand-edit this" rule any
more. The checks are mechanical instead: `kicad-cli sch erc` and
`kicad-cli pcb drc`, both of which run today.

**Review tooling.** `kicad-happy` (v2.2.1, MIT) is installed as a Claude Code
plugin and reviews the `.kicad_sch` and `.kicad_pcb` directly. A hand-drawn
schematic is precisely the artifact it was built to read, and having one is what
makes the first review gate (§12.1) possible at all.

## 7. Components and sourcing

### 7.1 Component quality policy

The design optimises for a *balanced* product, not a minimal BOM. Where a
branded part yields a better result, it is used. Where extra decoupling improves
behaviour, it is added.

Specific consequences on this board:

| Part | Policy |
|---|---|
| Bulk capacitor | Polymer or hybrid aluminium (Panasonic, Nichicon, Würth), not generic electrolytic. Far lower ESR, no dry-out, and this board sits in a warm appliance |
| MLCCs | Chosen with **DC-bias derating** accounted for. A 10 µF 0603 6.3 V X5R can lose most of its capacitance at 5 V; use larger case sizes and 16–25 V ratings so the nameplate value is close to the real one |
| Inductor | Shielded, branded (Coilcraft, Würth, TDK, Bourns), with genuine saturation margin over the peak — and a published SPICE model (§5.8) |
| Buck, eFuse, ideal diodes | Branded silicon with vendor SPICE models and real datasheets |
| TVS array | Purpose-made ESD protection array (Nexperia, Semtech, onsemi), not a generic diode |
| Connectors | Genuine JST XA and a branded USB-C receptacle with through-hole retention |
| Decoupling | Added generously. Both VCCA and VCCB on every translator, multiple values at the module, bulk plus ceramics on every rail |

### 7.2 Sourcing

**Every component is pinned by MPN on its schematic symbol, passives included.**
There is no automatic part picker in this flow — removing atopile removed the
one that had to be suppressed anyway (ADR 0005). A substitution reaching the
board without a decision having been made is the failure mode being designed
against, and the defence is now review rather than configuration.

The exported BOM carries MPN plus LCSC and Digi-Key/Mouser numbers, and PCBWay
sources from whichever it can. Substitutions are proposed back, never applied
silently.

**Additional selection criterion:** because simulation gates fabrication (§5.8),
the **buck** must be a part whose vendor publishes a usable SPICE model. TI and
ADI generally do; several cheaper LCSC-catalogue alternatives do not — including
the AOZ1280CI on `daikin-esp`'s `esp-daikin-r1p1`, which is why that part is not
simply carried over. This applies before the buck is committed to the design.

The criterion does **not** extend to the eFuse. Its deck's question is answered
by the current limit alone, which a behavioural block models exactly; requiring
a vendor model there would narrow the field for nothing. Reasoning and
consequences are in the 2026-09-12 amendment to
[ADR 0004](adr/0004-current-limited-inrush.md) — in exchange, the eFuse's
current-limit *accuracy* becomes a first-order selection criterion, because it
is what sets the appliance requirement.

### 7.3 Project library

Every symbol, footprint and 3D model the design uses lives in `lib/` in this
repo, referenced with `${KIPRJMOD}`-relative paths in `fp-lib-table` and
`sym-lib-table`, following the `daikin-esp/pcb/lib/` convention.

The design is **not** limited to KiCad's stock libraries — parts are chosen for
the design and their library assets sourced from SnapEDA or the vendor as
needed. Datasheets for every non-passive are kept alongside.

Nothing in the design may reference a library outside this directory. A board
that only opens correctly on the author's machine is not reproducible, which
matters most for an open-hardware release.

## 8. Mechanical and fabrication

| Parameter | Value |
|---|---|
| Stackup | 4-layer: L1 signal+parts / L2 GND / L3 rails+escapes / L4 GND |
| Outline | ~40 × 25 mm, connectors one short edge, antenna the other |
| Fab class | PCBWay 5/5 mil, 0.25 mm drill |
| Impedance | Not controlled; USB pair geometry targeted from the stackup |
| Assembly | Single-sided, all parts on top |
| Quantity | 5 (first run) |
| Enclosure | None — bare board |
| Mounting | Mounting holes |
| Antenna | C3-MINI-1 placed at a board edge, keepout on all layers, buck switching node kept clear |

4 layers because the switcher and a PCB antenna share a small board; a solid
ground plane turns EMI and antenna reference from a layout puzzle into a
non-issue. With no components on the bottom, L4 is a second ground plane for
free — a return path and a shield under the buck.

Binding layout rules, DRC values, DFM constraints and a pre-release checklist
are in **[docs/layout-rules.md](layout-rules.md)**. The short version: three
circuits deserve real rules — the buck's input hot loop, the antenna keepout,
and the USB pair — and the ground plane is never split.

The C3's USB is Full Speed (12 Mbps), so controlled impedance is not ordered;
the pair is still routed as a proper pair with ~90 Ω geometry derived from
PCBWay's published stackup, because doing so costs nothing.

Bare board is a deliberate choice. It means exposed electronics near HVAC
condensate and mains wiring — acceptable for a personal install, not for
anything distributed.

## 9. Firmware

ESPHome, using the built-in `haier` climate component in hOn mode at 9600 8E1 on
the port's UART, with logging over USB CDC. OTA is the normal update path after
first flash. Repository layout follows `daikin-esp`: an `esphome/` directory
holding the YAML.

## 10. Deliverables

```
/
├── CONTEXT.md                  domain language
├── LICENSE                     CERN-OHL-P v2
├── LICENSE-MIT                 firmware and docs
├── docs/
│   ├── SPDD.md                 this document
│   ├── adr/                    decision records
│   ├── layout-rules.md         binding layout rules, DRC, DFM, checklist
│   └── harness/                cable pinouts per appliance
├── lib/                        project library: symbols, footprints, 3D, datasheets
├── sim/                        standalone LTspice decks (§5.8)
├── pcb/serialtap-rNpM/
│   ├── kicad-src/              schematic, PCB and project — the source of truth
│   ├── GERBER-serialtap-rNpM/  fab output
│   ├── BOM-serialtap-rNpM.csv
│   ├── CPL-serialtap-rNpM.csv
│   ├── serialtap-rNpM-sch.pdf
│   └── serialtap-rNpM-ibom.html
├── esphome/                    ESPHome package, incl. loopback self-test build
└── test/                       loopback plug build notes, acceptance checklist
```

Board name is `serialtap`; revision naming follows the `daikin-esp`
convention: `serialtap-r1p0`, `serialtap-r1p1`, …

## 11. Requirements traceability

| Req | Satisfied by |
|---|---|
| FR-1 | §5.1 fixed-direction translators |
| FR-2 | §5.2 JST XA carrying 5 V + data, §5.3 power path, §5.8 simulated against a weak source |
| FR-3 | §5.1 push-pull translation; §5.6 series R sized for it |
| FR-4 | §5.5 C3 ROM USB Serial/JTAG + esptool |
| FR-5 | §5.5 BOOT and RESET switches |
| FR-6 | §5.3 ideal-diode OR on both sources |
| FR-7 | §5.6 series R, ESD array, resettable fuse |
| FR-8 | §9 ESPHome OTA |

## 12. Validation

### 12.1 Design validation

Gating tasks, in order. The design is not validated until all pass.

Automated review by `kicad-happy` runs at three points alongside these: after
the schematic is captured (feedback network, decoupling, ESD coverage by
connector, fuse sizing, temperature grade, EOL parts), after layout (thermal
vias, plane voids, trace width, impedance, DFM score), and before upload to
PCBWay. It is a
review aid — it does not replace `kicad-cli` ERC/DRC, the layout-rules
checklist, or the physical measurements below.

1. **Simulate the power path** (§5.8). `rail-sag` yields the minimum source
   current the design tolerates; `inrush` sets the eFuse limit resistor;
   `buck-load-step` confirms no brownout on a 30 → 250 mA step.
   *Done for the first two; `buck-load-step` awaits the buck MPN.*
2. **Measure the Haier's 5 V rail** — open-circuit voltage, current limit, and
   sag under a 250 mA pulsed load — and confirm it exceeds the number from
   step 1. This is the single largest unknown in the design.
   The number to beat is now **≥ 370 mA** for full margin; 250–300 mA means
   OTA and association on appliance power are at risk; below 250 mA the design
   needs rethinking, and not with capacitors. Also record what the rail *does*
   in current limit — droop, foldback, or reset — which the decks assume is a
   droop. Detail in [sim/README.md](../sim/README.md).
3. **Confirm the AS50QDFHRA service connector pinout** by probing the unit. The
   board pinout is fixed and conventional, so this determines the *cable*, not a
   respin.
4. Bench bring-up: rails correct, current draw within §5.4, no brownout at
   plug-in.
5. Scope both sides of both translator channels at 9600 8E1 against a
   USB-serial adapter. Confirm clean push-pull levels, not RC-shaped edges.
6. ESPHome flashes over USB-C on a virgin board with no button presses.
7. Manual recovery works: hold BOOT, tap RESET, device enters download mode.
8. OTA update succeeds while powered **only** from the appliance rail — the
   worst-case current condition.
9. End to end: the board controls the Haier from Home Assistant.

### 12.2 Per-board acceptance test

Applied to each of the five assembled boards before it goes into service.

**Loopback plug.** A JST XA shell with TX bridged to RX. A test ESPHome build
transmits a pattern on the port and verifies it returns, which exercises the
whole chain in one step: 3.3 V → up-translator → connector → down-translator →
3.3 V, plus both series resistors and the solder joints on all of it.

It needs no scope and no appliance. VCCB derives from the OR-ed 5 V rail, so
USB-C alone powers the 5 V side — the test runs on a bench with one cable.

| Step | Pass condition |
|---|---|
| 1 | Board enumerates over USB-C and flashes with no button presses |
| 2 | 5 V and 3V3 test pads within tolerance; idle current within §5.4 |
| 3 | Loopback self-test returns the pattern intact |
| 4 | Joins WiFi and accepts an OTA update |

What the loopback does **not** prove: real push-pull drive strength into a
loaded 5 V line. The first board additionally gets a scope on the translator
test pads to confirm square edges rather than RC-shaped ones. Boards 2-5 inherit
that result.

## 13. Risks and open questions

| Risk | Impact | Mitigation |
|---|---|---|
| Haier 5 V rail too weak for WiFi TX bursts | Board browns out on association; may reset the appliance | Buck over LDO, current-limited turn-on, ≥470 µF bulk. Simulated (§5.8): the rail must supply **300–370 mA**, and more bulk would not buy the shortfall back. **Measure before committing to fab** (§12.1-2) |
| Haier connector pinout assumed, not confirmed | Cable is wrong; nothing communicates | Fixed board pinout makes this a cable fix, not a respin (§12.3) |
| Buck switching noise coupling into the antenna | Degraded WiFi range inside an appliance | Zoned floorplan (buck at the connector end, antenna at the far edge), minimised switch node, two ground planes — see layout-rules.md |
| Silent part substitution at assembly | A cheaper equivalent lands on the board and changes behaviour | Every part pinned by MPN (§7.2); substitutions proposed back, never applied silently |
| Bare board in an HVAC unit | Condensate, mains proximity, handling damage | Accepted for personal use; documented as unsuitable for distribution |
| No SPICE model for a chosen buck or eFuse | Power path cannot be simulated, removing the fab gate | Vendor SPICE model is a part-selection criterion (§7) |
| Direction frozen in copper | A future half-duplex target needs a new board | Accepted — explicitly a different product (ADR 0001) |
| Single UART, no spare | A second serial device needs a different module | Accepted (ADR 0002) |

**Open questions**

- Actual current capability of the Haier 5 V service rail — needs ≥ 370 mA
  (blocks §12.1 step 2)
- Buck and eFuse MPNs, both of which need vendor SPICE models (§7.2). The buck
  blocks `buck-load-step`; the eFuse's current-limit accuracy is what turns the
  300–370 mA range above into a single number
- AS50QDFHRA service connector **pin order**, and what the fifth pin carries
  (blocks the harness). The connector and mating part are now known: 5-pin JST
  XA, 2.5 mm pitch, XARR-05V panel housing (confirmed 2026-09-12)
- Whether a board-mounted JST XA or a wire-to-board pigtail suits the install

## 14. Decision log

| ADR | Decision |
|---|---|
| [0001](adr/0001-fixed-direction-level-translation.md) | Fixed-direction level translation, not auto-direction |
| [0002](adr/0002-c3-and-usb-only-programming.md) | ESP32-C3-MINI-1, programmed over USB only, no TC2050 |
| [0003](adr/0003-buck-not-ldo.md) | Synchronous buck, not an LDO, for the 3.3 V rail |
| [0004](adr/0004-current-limited-inrush.md) | Current-limited inrush protection, not slew-rate-limited |
| [0005](adr/0005-kicad-native-capture.md) | KiCad-native capture; atopile removed, and the code-to-schematic alternatives rejected on evidence |
