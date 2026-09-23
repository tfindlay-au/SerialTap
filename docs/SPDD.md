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
- A firmware package that runs on the assembled board, ESPHome by default
- Harness documentation: cable pinouts per appliance, starting with the Haier

**Out of scope**

- Any enclosure. The board ships bare (§8).
- Reverse engineering an appliance protocol from scratch. The reference
  appliance speaks **GEA3**, which is public and has both a portable C library
  and an existing ESPHome component ([ADR 0006](adr/0006-gea3-not-hon.md)).
  Mapping which ERD carries which control is observation, and is in scope.
- Certification, EMC testing, or commercial production

## 3. Functional requirements

| # | Requirement |
|---|---|
| FR-1 | Provide one bidirectionally level-translated UART channel between the ESP32's 3.3 V logic and a target's 5 V logic |
| FR-2 | Accept 5 V from the target on the same connector as the data lines, and run the whole board from it |
| FR-3 | Operate reliably at 230400 8N1 (the reference target's measured rate, [ADR 0006](adr/0006-gea3-not-hon.md)) and impose no design ceiling below 1 Mbaud |
| FR-4 | Be flashable from a bare, unprogrammed state over USB-C with no jig or external adapter |
| FR-5 | Be recoverable by hand if firmware renders USB unusable |
| FR-6 | Never source current into a target appliance's rail from a bench supply, or vice versa |
| FR-7 | Survive ordinary installation faults on the port: ESD, hot-plug, a line shorted to 5 V or GND |
| FR-8 | Support ESPHome OTA as the normal update path once first-flashed |

## 4. Architecture

**Signal path**

```
  JST XA          ESD    series R  fixed-direction        ESP32-C3-MINI-1
  TX ------------[ ]-----[ Rs ]---[ B->A translator ]----> RX  (UART1)
  RX ------------[ ]-----[ Rs ]<--[ A->B translator ]----- TX  (UART1)
                                  VCCB=5V  VCCA=3V3

                                   USB-C  D+/D- <-------> GPIO18/19
                                                  (ROM USB Serial/JTAG:
                                                   flashing, CDC log, debug)
```

**Power path**

```
  JST XA 5V ---------[ eFuse ]--[ideal diode]--+
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

**Signal path.** Target ↔ ESD array ↔ series resistors ↔ fixed-direction
translators ↔ C3 UART1. Console and debug ride the C3's built-in USB
Serial/JTAG on GPIO18/19, out to USB-C, so the port's UART is never shared with
logging.

**Power path.** The JST 5 V and USB-C VBUS are each ideal-diode OR-ed onto a
common 5 V rail; a current-limited eFuse limits inrush; a synchronous buck
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
pin order **1 = 5 V, 2 = TX, 3 = RX, 4 = spare, 5 = GND**, silkscreened from
the board's point of view — TX is the pin the board drives, which is the
appliance's receiver.

**This order is corrected as of 2026-09-20.** Earlier revisions of this
document, the bench notes and `gea3.md` numbered the connector from the wrong
end and read 5 V, GND, TX, RX at pins 1–4. Nothing measured changed; the
labels did. Direction is not inferred: on the working TinyS3 rig the shifter
carries TinyS3 TX into pin 2 and pin 3 into TinyS3 RX
([gea3.md](gea3.md)).

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

**Pin 4's function is unknown** — it read as floating, either no contact or a
genuine spare — so nothing on the board connects to it: not the ESD array, not
a GPIO. Committing it to anything before it is known risks strapping an unknown
signal, possibly not a 5 V-logic one, to a net that matters.

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
| Fusing | **None.** TPS2553 provides constant-current limiting, thermal shutdown and reverse blocking, which is stronger and faster than a PTC's thermal trip. A PTC would only add cover for the eFuse itself failing short, and would cost 0.2–0.5 Ω in series — ~75 mV at 250 mA on a rail with no headroom to spare. Recorded as a deliberate removal, not an omission (ADR 0004 anticipated this) |

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

- **330 Ω, 1% series resistors** on TX and RX, selected from the powered-down
  appliance RX bias measurement. They limit fault current if a line meets 5 V
  or GND during install.
- The single four-channel ESD array protects the two JST UART signals and USB
  D+/D−. The interfaces are not used concurrently, but this assignment protects
  either interface from an accidental cable connection without another device.
- Port 5 V current limiting and reverse blocking are provided by TPS2553;
  source isolation is completed by the LM66200 ideal-diode OR.

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

`buck-load-step` uses the TPS62162 vendor model, because its question is about
the converter control loop and cannot be answered by a behavioural block. The
corrected 2026-09-20 deck ties the fixed-output part's `FB` pin to AGND and
passes the 40 → 335 mA load step with at least 285 mV margin to 3.0 V. Results
are in [sim/README.md](../sim/README.md).

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
| Bulk capacitor | Polymer or hybrid aluminium (Panasonic, Nichicon, Würth), not generic electrolytic. The reason is **no dry-out** in a warm appliance, *not* ESR — the load step needs only 185 mA, so even 200 mΩ would cost 37 mV. Do not pay for exotic ESR here |
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

### 7.4 Parts register

Filled in as parts are pinned. Every entry is a decision with a reason, not a
search result. Until the schematic exists this is the record; afterwards the
schematic symbols carry the MPNs and this table points at the reasoning.

| Function | MPN | Why this one |
|---|---|---|
| 3.3 V buck | **TPS62162DSGT** (WSON-8, 2×2 mm; `T` = 250-piece reel) | Fixed 3.3 V, so no feedback divider. `FB` is tied to AGND and `VOS` senses at the output capacitor, per the datasheet; the latter remains a control-loop-sensitive layout net. 1 A against a 335 mA peak. The only candidate with both a fixed output *and* an unencrypted SPICE model — TPS6282533 has no published model, TPS62901's is 74% Cadence-encrypted. Costs ~2 efficiency points against the TPS6282x, worth ~5 mA of appliance current, which is noise against a 300–370 mA requirement ([ADR 0003](adr/0003-buck-not-ldo.md), §5.8) |
| Buck inductor | **XGL4020-222MEC** (Coilcraft) | 2.2 µH, 19.5 mΩ DCR against the XFL3012's 97 mΩ — buys back ~0.8 of the ~2 points conceded above. Isat 2.7 A sits clear of the IC's ~1.6–2 A current limit, so the IC protects before the inductor saturates. Coilcraft publishes a `_sat` LTspice model, verified against the datasheet before use. 2.0 mm tall, confirmed to clear the enclosure |
| Port connector | **B05B-XASK-1-A(LF)(SN)** (JST XA, 5-pin, vertical, with boss) | Matches the appliance's XARR-05V panel housing, so the harness is straight-through (§5.2). Vertical entry confirmed against the enclosure. `-A` for the boss: this is the board's only permanent mechanical interface and takes every insertion force in a unit that vibrates, so the boss carries that into the board rather than the solder joints. Tin, not `-GU` gold — plating should match across a mating pair, and standard XA crimps are tin. **Through-hole**, so it needs a selective- or hand-solder step on an otherwise all-SMD board |

| Level translator | **TXU0204RUTR** (`RUT` UQFN-12, 2.0 × 1.7 mm) | 4-bit fixed-direction, two channels each way — TI names UART as the application. Direction fixed in *silicon*, so there is no DIR pin to mis-strap; Schmitt-trigger inputs for a metre of harness; integrated pull-downs, which retire ADR 0001's own warning about floating unused inputs. Push-pull ±12 mA at 4.5 V against the ~4 kΩ of the auto-direction parts ADR 0001 rejected. Two channels unused. See the 2026-09-13 amendment to [ADR 0001](adr/0001-fixed-direction-level-translation.md) |

| eFuse | **TPS2553DBVR** (SOT-23-6) — **not the `-1`** | ADR 0004's part. 75 mA–1.7 A adjustable limit, 2.5–6.5 V, 85 mΩ, active-high enable, **reverse blocking**, thermal shutdown, constant-current limiting rather than latch-off (the `-1` suffix latches; we do not want that). Unencrypted PSpice model exists, though ADR 0004's amendment means one is not required here. `R<sub>ILIM</sub>` is selected from the inferred rail envelope under ADR 0007, then checked at bring-up. |
| Ideal-diode OR | **LM66200DRLR** (SOT-5X3-8, its only package) | 1.6–5.5 V, 40 mΩ, 2.5 A, low I<sub>Q</sub>, **two ideal diodes in one package** — both OR branches in a single part instead of two LM66100s. Unencrypted PSpice model |

| ESD array | **TPD4E05U06QDQARQ1** (TI, AEC-Q101) | Quad, 0.5 pF, V<sub>RWM</sub> 5.5 V, min breakdown 6.5 V, ±12 kV, 2.5 A / 40 W surge. Channels protect JST TX/RX and USB D+/D−; the ports are mutually exclusive in normal use, but both remain protected against an accidental cable connection. The `-Q1` is taken for its temperature grade, not automotive compliance — this board lives in a warm appliance with no enclosure. **Caveat:** 5.5 V standoff against 5 V logic is 0.5 V of margin, so the Haier's open-circuit rail voltage must be confirmed (already on the bench list) |
| USB-C receptacle | **USB4085-GF-A** (GCT) | USB 2.0, 16 contacts, through-hole, horizontal top-mount, four PCB retention/grounding posts, 10 000 mating cycles, 3.46 mm profile. Through-hole retention is what §7.1 asked for, and it shares the selective-solder step the JST already needs. **KiCad 10 ships both a reviewed footprint and a STEP model** for it, which is not true of any vertical receptacle. Vertical was considered: it would free ~9 mm of long edge we do not need, in exchange for the cable levering perpendicular to the board and hand-sourced library assets |

| Bulk capacitor | **PCL1A471MCL1GS** (Nichicon) | 470 µF, 10 V ±20%, conductive polymer aluminium **solid** — no liquid electrolyte, so nothing to dry out, which is the entire reason for this class of part here. 8 × 10 mm SMD, ESR 17 mΩ, ripple 3.8 A, −55 to +105 °C. Double the voltage margin on a 5 V rail; the ±20% worst case of 376 µF is still comfortable, since `rail-sag` showed even 220 µF costs only 55 mA at light duty. ESR and ripple ratings are enormously in excess of what is asked of them, and deliberately not paid for |

| Module | **ESP32-C3-MINI-1-H4X** (Espressif) | 4 MB flash — ample for an ESPHome image plus OTA partitions, with no filesystem to speak of. **H = 105 °C** ambient rather than the N variant's 85 °C, for a bare board in an HVAC unit. **X = chip revision v1.1, and it is not optional: every non-X variant is NRND.** Plain `-1`, *not* `-1U` — the U denotes a U.FL connector and no antenna at all, whereas `-1` carries the PCB trace antenna this design settled on ([haier-oem-board.md](haier-oem-board.md)). Keeping the PCB antenna is what makes the antenna keepout layout priority #1; `-1U` has no keepout, but needs an external antenna and a pigtail inside the chassis |

**Passives pinned 2026-09-20**, once the schematic fixed how many of each there
are. Two families, chosen for consistency rather than per-line optimisation:

| Function | MPN | Why this one |
|---|---|---|
| All five resistor values — 330 Ω ×2, 5.1 kΩ ×3, 10 kΩ ×2, 66.5 kΩ, 100 kΩ ×2 | **KOA Speer RK73H 1J** series, 0603, ±1% | One series across every value: ±100 ppm/°C, −55…+155 °C, AEC-Q200. The 66.5 kΩ `RILIM` **has** to be 1% — the TPS2553 datasheet says so, it is not a preference — and running the same grade everywhere costs cents and removes a class of mistake. Size code `1J` = 0603 and tolerance code `F` = ±1% are confirmed from the ordering table in the datasheet |
| 100 nF ×4, 1 µF ×3, 10 µF ×2, 22 µF | **Samsung CL** series, **X7R only, ≥25 V** | X7R throughout, never X5R: TPS62162's LC stability table assumes variation stays within ±20% *including DC bias*, and 25 V parts on a 5 V rail keep the derating small enough to stay there. The 22 µF output value and its dielectric are the datasheet's own recommendation |
| Power LED | **LTST-C191KGKT** (Lite-On, 574 nm) | Vf 1.9–2.4 V puts ~0.6 mA through the 5.1 kΩ — dim on purpose (§5.7). Chosen over the 5× brighter emerald-green `LTST-C191TGKT` for temperature grade: −55…+85 °C against −20…+80 °C, consistent with the H-grade module and the `-Q1` ESD array |
| BOOT/RESET switches | **C&K KMR211NGLFS** | −40…+85 °C, 200 000 operations, 1.2 N. `NG` is the ordering key's **no ground pin** option, which is what picks the four-pad land pattern over the five-pad one. C&K's recommended layout — 0.9 × 1.0 mm pads at ±2.05, ±0.8 mm — matches KiCad's footprint exactly |

**The switch datasheet changed a resistor.** C&K specify a **minimum contact
current of 1 mA** for the standard silver contacts; the ULC option exists
precisely because 1 mA is a lot for a logic-level button, and it is not stocked
anywhere this project can check. With a 10 kΩ pull-up, SW1 would have switched
0.33 mA — a third of the vendor's minimum, in the dry-circuit region where
contact films do not get broken down.

- **R9 (BOOT) is therefore 2.2 kΩ, not 10 kΩ.** That puts 1.5 mA through SW1,
  50% above the minimum. GPIO9 is a strapping pin read once at reset, so the
  only cost is 1.5 mA while the button is physically held.
- **R10 (EN) stays 10 kΩ.** SW2 discharges C11's 1 µF through its contacts on
  every press, which is a far larger wetting pulse than any steady current would
  be, so the low steady current does not matter there. Shortening the EN time
  constant would also have been the wrong move while the manual-reset-on-first-
  power-up anomaly (§13) is unexplained. *The wetting-pulse argument is
  engineering judgement, not a vendor statement.*

The **two 5.1 kΩ CC pulldowns** the USB-C sink needs are R3 and R4, sharing a
line with the LED series resistor R8.

**Endurance resolved (2026-09-20).** The Nichicon datasheet, now in
[lib/datasheets](../lib/datasheets/), states **20 000 hours at 105 °C**, twice on
the same page. The 2 000 h figure some sources carry is wrong. That datasheet also
confirms this entry's 17 mΩ ESR and 3.8 A ripple, gives the case as 8 × 10 mm, and
adds leakage of 940 µA at rated voltage.

**Stock confirmed for every line above (2026-09-20).** All ten are obtainable,
but across three distributors — Digi-Key, LCSC and Mouser — and three of them
are single-source. The eFuse problem is resolved; see §13. Per-line stock,
distributor part numbers and cost are in [bom/](../bom/); the numbers go stale,
so re-check before ordering.

**`lib/` is started (2026-09-19).** Symbols and footprints exist for every part
above except three, 3D models for six, and datasheets for eight. It validates
under `kicad-cli` and references nothing outside the repo.
[lib/README.md](../lib/README.md) carries the per-asset provenance, the gap
list, and the pin tables extracted from the datasheets for the symbols still to
be authored. Gaps needing an external source: the `XGL4020` footprint and 3D
model, the `LM66200` DRL-8 footprint and 3D model, 3D models for the JST XA and
TI's DSG0008A, and the JST and Nichicon datasheets.

### 7.3 Project library

Every symbol, footprint and 3D model the design uses lives in `lib/` in this
repo, referenced with `${KIPRJMOD}`-relative paths in `fp-lib-table` and
`sym-lib-table`.

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
| Outline | **22 × 54 mm** — drop-in for the OEM Haier board. JST on one short edge, USB-C on an adjacent long edge, antenna at the far short edge |
| Fab class | PCBWay 5/5 mil, 0.2 mm drill (0.25 mm until 2026-09-24 — see layout-rules.md) |
| Impedance | Not controlled; USB pair geometry targeted from the stackup |
| Assembly | Single-sided, all parts on top. All SMD except the JST XA port connector, which is through-hole and needs a selective- or hand-solder step |
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

ESPHome, using the **`esphome-gea` external component in GEA3 mode at 230400
8N1** on the port's UART, with logging over USB CDC. OTA is the normal update
path after first flash. The YAML lives in an `esphome/` directory.

The reference appliance speaks GE Appliances GEA3, **not** Haier hOn, and
ESPHome's built-in `haier` component does not apply to it. Decoded 2026-09-18
and confirmed two-way on the appliance 2026-09-19; see
[ADR 0006](adr/0006-gea3-not-hon.md) and [gea3.md](gea3.md) for the evidence
and the ERD map. SerialTap takes bus address `0xBF`; the appliance is `0xC0`.

`esphome-gea` provides sensor, binary_sensor, switch, select, number and
text_sensor entities over ERDs. It has no climate entity, so that is the one
piece of firmware still to write. Control is writing ERDs `0x7A0F` power,
`0x7A01` mode, `0x7003` setpoint, `0x7A00` fan and `0x7B07`/`0x7B08` swing.

Because GEA3 also has a plain C implementation in GE's `tiny-gea-api`, nothing
in this design depends on ESPHome or on Home Assistant. Neither is load-bearing
for the hardware.

## 10. Deliverables

```
/
├── CONTEXT.md                  domain language
├── LICENSE                     CERN-OHL-P v2, verbatim
├── LICENSE-MIT                 firmware and docs
├── NOTICE                      which licence covers what, and third-party terms
├── docs/
│   ├── SPDD.md                 this document
│   ├── adr/                    decision records
│   ├── layout-rules.md         binding layout rules, DRC, DFM, checklist
│   └── harness/                cable pinouts per appliance
├── lib/                        project library: symbols, footprints, 3D, datasheets
├── sim/                        standalone LTspice decks (§5.8)
├── pcb/
│   ├── serialtap-rNpM.kicad_sch    source of truth
│   ├── serialtap-rNpM.kicad_pcb
│   ├── serialtap-rNpM.kicad_pro
│   ├── GERBER-serialtap-rNpM/      fab output, regenerated
│   ├── BOM-serialtap-rNpM.csv
│   ├── CPL-serialtap-rNpM.csv
│   ├── serialtap-rNpM-sch.pdf
│   └── serialtap-rNpM-ibom.html
├── esphome/                    ESPHome package, incl. loopback self-test build
└── test/                       loopback plug build notes, acceptance checklist
```

Board name is `serialtap`; revisions are `serialtap-r1p0`, `serialtap-r1p1`, …

**Flat.** Everything for the board lives directly in `pcb/`, with the revision
carried in the file name rather than in a folder. One board and a handful of
files do not need a directory tree, and freezing a revision is what version
control is already for — a folder per revision would only duplicate what a tag
does better.

## 11. Requirements traceability

| Req | Satisfied by |
|---|---|
| FR-1 | §5.1 fixed-direction translators |
| FR-2 | §5.2 JST XA carrying 5 V + data, §5.3 power path, §5.8 simulated against a weak source |
| FR-3 | §5.1 push-pull translation; §5.6 series R sized for it |
| FR-4 | §5.5 C3 ROM USB Serial/JTAG + esptool |
| FR-5 | §5.5 BOOT and RESET switches |
| FR-6 | §5.3 ideal-diode OR on both sources |
| FR-7 | §5.6 series R, ESD array, TPS2553 current limit and reverse blocking |
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
   *Complete. `buck-load-step` was re-run 2026-09-20 with fixed-output `FB`
   tied to AGND; it passes with ≥285 mV margin to 3.0 V.*
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
5. Scope both sides of both translator channels at **230400 8N1** against a
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
| Haier 5 V rail too weak for WiFi TX bursts | Board browns out on association; may reset the appliance | Buck over LDO, current-limited turn-on, ≥470 µF bulk. Simulated (§5.8): the rail must supply **300–370 mA**, and more bulk would not buy the shortfall back. **Risk substantially reduced:** the OEM board this replaces ran a Realtek RTL8720CM from the same rail, rated 450 mA at 3.3 V — more than our C3's 335 mA — through its own buck ([haier-oem-board.md](haier-oem-board.md)). Still **measure before committing to fab** (§12.1-2) |
| Haier connector pinout assumed, not confirmed | Cable is wrong; nothing communicates | Fixed board pinout makes this a cable fix, not a respin (§12.3) |
| Buck switching noise coupling into the antenna | Degraded WiFi range inside an appliance | Zoned floorplan (buck at the connector end, antenna at the far edge), minimised switch node, two ground planes — see layout-rules.md |
| Silent part substitution at assembly | A cheaper equivalent lands on the board and changes behaviour | Every part pinned by MPN (§7.2); substitutions proposed back, never applied silently |
| Bare board in an HVAC unit | Condensate, mains proximity, handling damage | Accepted for personal use; documented as unsuitable for distribution |
| No SPICE model for a chosen buck or eFuse | Power path cannot be simulated, removing the fab gate | Vendor SPICE model is a part-selection criterion (§7) |
| Direction frozen in copper | A future half-duplex target needs a new board | Accepted — explicitly a different product (ADR 0001) |
| Single UART, no spare | A second serial device needs a different module | Accepted (ADR 0002) |

**Open questions**

- ~~Actual current capability of the Haier 5 V service rail~~ **No longer a
  fabrication gate ([ADR 0007](adr/0007-rail-limit-inferred-not-measured.md)).**
  `RILIM` is set from inference instead: above SerialTap's worst-case draw and
  below the OEM-implied floor of the rail. The rail has been observed carrying a
  TinyS3 with Wi-Fi live (2026-09-19). Still unmeasured, and the cost of that is
  recorded in ADR 0007
- ~~Buck and eFuse MPNs~~ **Both pinned (§7.4):** TPS62162 and TPS2553.
  The corrected buck deck passes; `RILIM` is set per ADR 0007 and checked at
  bring-up.
- ~~**`TPS2553DBVR` availability.**~~ **Resolved 2026-09-20 by the first of the
  three escape routes: another distributor.** The plain non-latching part is
  stocked at **LCSC (C55266, 44,248)** and **Mouser (882)**. Digi-Key remains out
  until 2026-10-26 — the 2026-09-19 finding was correct about Digi-Key, and only
  the conclusion drawn from it was wrong. `TPS2552DBVR` and the
  `-1`-plus-auto-retry circuit of the datasheet's §10.2.2 are therefore both
  unnecessary; the reasoning for rejecting the `-1` (it latches off on
  overcurrent, and with 470 µF of bulk the plug-in charge time is the same order
  as its 8 ms fault deglitch, so it could latch at every plug-in inside an
  appliance) stands unchanged. No design or library change.
  **One check owed at goods-in:** LCSC's auto-generated listing text mentions
  latch protection, which is boilerplate for the whole TPS2553 family and says
  nothing about the suffix — verify the package marking on receipt.
- **`PCL1A471MCL1GS` depth.** Not a blocker, but the thinnest line on the BOM:
  **69 pieces at Mouser, and nowhere else.** Digi-Key is non-stock at 24-week
  lead and a 500-piece minimum; LCSC does not list it, and the sister
  `PCR1E471MCL1GS` shows 22-week lead and no stock at Arrow, so this is the
  series rather than the one part number. Buy spares in the same order. If that
  stock goes first, the fallback is a different 470 µF / 10 V polymer — a
  substitution, proposed back and never applied silently (CLAUDE.md, §13 risk
  table).
- **Which ERD carries which control** on the reference appliance. Firmware only,
  no hardware impact. Ten of the 64 ERDs are unnamed in GE's public definition
  set, and the appliance reads ERD `0x6003` from the module every 30 s for
  reasons unknown ([gea3.md](gea3.md))
- **Why the board needed a manual reset** on its first power-up from the
  appliance rail (2026-09-19). The one open item that could still change the
  design, because it concerns enable and reset timing on a rising rail
- ~~AS50QDFHRA service connector **pin order**~~ **Settled 2026-09-20**: the
  connector had been read from the wrong end. Corrected order is 5 V, TX, RX,
  spare, GND, with direction fixed by the working TinyS3 link (§5.2). What
  **pin 4** carries is still unknown, and still blocks nothing but the harness.
  Connector and mating part known since 2026-09-12: 5-pin JST XA, 2.5 mm pitch,
  XARR-05V panel housing
- Whether a board-mounted JST XA or a wire-to-board pigtail suits the install
- ~~PCB antenna or external?~~ **Settled: PCB antenna (ESP32-C3-MINI-1).** The
  OEM board provides a U.FL footprint but it was never populated — that unit ran
  on its own antenna inside this chassis for its service life. The reference
  install also has an access point ~3 m away with line of sight. The **-1U**
  variant is the fallback if bring-up shows poor RF
  ([haier-oem-board.md](haier-oem-board.md))

## 14. Decision log

| ADR | Decision |
|---|---|
| [0001](adr/0001-fixed-direction-level-translation.md) | Fixed-direction level translation, not auto-direction |
| [0002](adr/0002-c3-and-usb-only-programming.md) | ESP32-C3-MINI-1, programmed over USB only, no TC2050 |
| [0003](adr/0003-buck-not-ldo.md) | Synchronous buck, not an LDO, for the 3.3 V rail |
| [0004](adr/0004-current-limited-inrush.md) | Current-limited inrush protection, not slew-rate-limited |
| [0005](adr/0005-kicad-native-capture.md) | KiCad-native capture; atopile removed, and the code-to-schematic alternatives rejected on evidence |
| [0006](adr/0006-gea3-not-hon.md) | The appliance protocol is GE Appliances GEA3, not Haier hOn |
| [0007](adr/0007-rail-limit-inferred-not-measured.md) | The rail's current limit is inferred, not measured; the load test stops gating fabrication |
