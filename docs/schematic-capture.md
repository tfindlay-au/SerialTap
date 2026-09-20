# Schematic capture contract — SerialTap r1p0

This is the wiring target for `pcb/serialtap-r1p0.kicad_sch`. It records the
settled connectivity so schematic capture is a transcription and review task,
not another architecture discussion.

## Connector roles

J1 is the board-mounted JST XA service connector. The labels are from the
board's point of view:

| J1 pin | Net | Function |
|---:|---|---|
| 1 | `PORT_5V` | appliance 5 V input |
| 2 | `PORT_TX` | board output to appliance — the appliance's receiver |
| 3 | `PORT_RX` | appliance output to board — the appliance's transmitter |
| 4 | `PORT_NC` | deliberately unconnected until the harness investigation assigns it |
| 5 | `GND` | common return |

**Corrected 2026-09-20.** This table originally read 5 V, GND, TX, RX, spare at
pins 1–5, from a connector that was being read from the wrong end. Old pin *n*
is new pin *6 − n*. Direction is settled by the working TinyS3 rig, not
inferred: TinyS3 TX drives pin 2, pin 3 drives TinyS3 RX
([gea3.md](gea3.md)).

J2 is USB-C. All VBUS pins join `USB_VBUS`; all GND pins and shield join
`GND`; D+ and D− go through the USB ESD array to C3 GPIO19 and GPIO18.
CC1 and CC2 each receive a 5.1 kΩ pulldown to GND.

## Power tree

```text
PORT_5V ── TPS2553 IN
             TPS2553 OUT ── LM66200 IN1
USB_VBUS ────────────────── LM66200 IN2
                              LM66200 OUT ── V5
V5 ── TXU VCCB, bulk capacitor, buck VIN, power LED
TPS62162 VOUT ── V3V3 ── C3 VDD, TXU VCCA
```

TPS2553 `EN` is tied high to its input supply so the appliance branch is always
enabled. `FAULT` is brought to a labelled test pad or left as an explicitly
marked no-connect; `ILIM` receives the selected resistor to GND. There is no
PTC/resettable fuse. LM66200 provides the source isolation and TPS2553 provides
the port current limit and reverse blocking.

TPS62162 support wiring is fixed:

- `FB` → `AGND`
- `VOS` → `V3V3` at the output-capacitor positive terminal
- `AGND`, `PGND`, and exposed pad → `GND`
- `EN` → `V5`
- `PG` → labelled test pad (or explicit no-connect if not used by firmware)
- `SW` → XGL4020-222MEC → `V3V3`
- 10 µF ceramic from VIN to GND, 22 µF ceramic from V3V3 to GND, plus the 470 µF bulk on V5

## UART translation

The selected TXU0204RUTR is used as follows:

| TXU pin/function | Net |
|---|---|
| VCCA | `V3V3` |
| VCCB | `V5` |
| OE | `V3V3` |
| A1 input | C3 UART TX |
| B1Y output | `PORT_TX` through 330 Ω, 1% |
| B3 input | `PORT_RX` through 330 Ω, 1% |
| A3Y output | C3 UART RX |
| A2 and B4 inputs | tied to GND |
| A4Y and B2Y outputs | no-connect |
| GND and exposed pad | GND |

The TPD4E05U06QDQARQ1 channels are assigned to `PORT_TX`, `PORT_RX`, USB D+,
and USB D−. Its ground pin connects directly to GND. Each connector-facing
line reaches its ESD channel before the UART series resistor or USB trace.

## C3 support and recovery

- GPIO18 → USB D−; GPIO19 → USB D+
- GPIO9 has a 10 kΩ pull-up to V3V3 and BOOT switch to GND
- EN has a 10 kΩ pull-up to V3V3, RESET switch to GND, and reset capacitor to GND
- C3 receives local 100 nF and 10 µF V3V3 decoupling
- UART1 uses GPIO4 as TX and GPIO5 as RX; these are assigned to the TXU A-side nets

## Review invariants

- J1 pin 4 has no copper connection other than its own pad.
- No USB VBUS path can reach `PORT_5V` except through the LM66200 ideal-diode OR.
- The ESD array is ahead of both UART series resistors.
- `FB` is not floating; `VOS` senses at the output capacitor.
- Every unused TXU input is tied off and every unused output is explicitly no-connect.
- Every passive has an MPN before ERC/BOM review; values above are design values, not distributor substitutions.

## Capture record — 2026-09-20

Captured into [`pcb/serialtap-r1p0.kicad_sch`](../pcb/serialtap-r1p0.kicad_sch),
KiCad 10 native format (`version 20260306`), one A3 sheet in seven labelled
blocks: service port, USB-C, power path, level translation, ESP32-C3, test
access, ERC power sources. **43 components, 57 nets.**

`kicad-cli sch erc --severity-all` reports **0 violations**.

The connectivity above was transcribed and then checked against the *extracted
netlist*, not against the drawing — a drawing can look right and still be
wrong. Every review invariant, as `kicad-cli sch export netlist` reports it:

| Invariant | Netlist evidence |
|---|---|
| J1 pin 4 has no copper other than its own pad | `unconnected-(J1-Pin_4-Pad4)`, one node |
| No USB VBUS path to `PORT_5V` except through the OR | `USB_VBUS` = J2 VBUS ×4, C3, U2.VIN2. `PORT_5V` = J1.1, U1.IN, U1.EN, C1. They meet only at U2's output |
| ESD array ahead of both UART series resistors | `PORT_TX` = J1.3, **U5.D1+**, R1.1 — and `TX_BUF` = R1.2, U4.B1Y, TP4. Same shape for RX |
| `FB` not floating; `VOS` senses at the output capacitor | U3.5 (`FB`) is in `GND`; U3.6 (`VOS`) is in `V3V3` with C6 |
| Every unused translator pin handled | A2, B4 tied to `GND`; A4Y, B2Y carry explicit no-connects |
| Every passive has an MPN | **Not met** — see "Still open" below |

### Decisions taken at capture

- **`RILIM` = 66.5 kΩ 1% (R5).** TI's Table 2 row for a 400 mA nominal limit;
  with part and resistor tolerance the limit lands **351–449 mA**. That is
  ~100 mA above the board's 250 mA worst-case 5 V draw, so a Wi-Fi TX burst
  cannot nuisance-trip it, and below the ~590 mA inrush the rail demonstrably
  sources for the OEM module it was built to feed
  ([ADR 0007](adr/0007-rail-limit-inferred-not-measured.md)). The 88.7 kΩ /
  300 mA alternative was rejected: its 262 mA minimum leaves only 12 mA over
  the board's own estimated peak. Still an inferred value, to be confirmed at
  bring-up.
- **`FAULT`, `PG` and `ST` go to test pads** (TP8, TP9, TP10), not to GPIOs.
  Zero BOM cost, no firmware coupling. `FAULT` and `PG` are open-drain and
  carry pull-ups (R6 to `V5`, R7 to `V3V3`). The cost is that neither fault
  state is visible to Home Assistant; routing them to GPIO6/GPIO7 later is a
  respin, so this is the decision to revisit if remote fault reporting matters.
- **Drawing style: rails and cross-block signals by symbol and label, local
  topology by wire.** Power symbols (`PORT_5V`, `USB_VBUS`, `V5`, `V3V3`,
  `GND`) carry the rails; labels carry signals between blocks; wires are drawn
  where the topology is the point — the J1 → ESD → series resistor chain, the
  buck's SW node through L1, the BOOT and RESET networks, each pull-up. This
  keeps a 43-part board on one readable sheet. The netlist, not the drawing, is
  what was checked.
- **`LM66200` `VOUT_2` pin type changed to passive** in the project library.
  `VOUT_1` and `VOUT_2` are the same internal node, and two `power_out` pins on
  one net is an ERC conflict. The datasheet I/O column still says output; the
  library note records why the symbol departs from it.
- **Eleven generic symbols added to the project library** (R, C, LED, SW_Push,
  TestPoint, PWR_FLAG, GND, V5, V3V3, PORT_5V, USB_VBUS), copied from KiCad 10's
  own libraries so nothing references outside the repo. See
  [lib/README.md](../lib/README.md).

### Review gate 1 — kicad-happy, 2026-09-20

Run on the schematic alone; no PCB exists yet, so the cross-domain, EMC,
thermal and gerber analyses were **not run** and neither was the lifecycle
audit. 28 findings: 2 errors, 2 warnings, 24 informational.

| Finding | Verdict |
|---|---|
| `PP-001` U2.VIN1 has no DC path to a rail | **False positive.** `EFUSE_OUT` holds U1.OUT (`power_out`), U2.VIN1 and C2. The DC path runs through U1's pass FET; the rule walks the net graph only and cannot traverse an IC. A current-limited switch between two rails always trips it |
| `SS-001` BOM under 50% MPN coverage (9/21) | **True, and expected.** The passives are the open gate below |
| `DS-002` no `datasheets/` directory | **Path convention.** This project keeps vendor PDFs in `lib/datasheets/` beside the symbols that cite them |
| `UC-002` no ESD/TVS on VBUS at J2 | **Genuine, and open.** See below |
| `PR-004` no series resistors on USB D+/D− | **Expected.** The C3's USB Serial/JTAG PHY needs none; Espressif's own boards fit none |

**The VBUS finding is worth a decision.** All four ESD channels are committed
(`PORT_TX`, `PORT_RX`, USB D+, D−), so VBUS is unprotected. `PORT_5V` is
covered by a different mechanism — the TPS2553 is rated 15 kV IEC 61000-4-2
*with external capacitance*, which C1 provides. VBUS has no equivalent: it
reaches the LM66200 directly, whose inputs are **6 V absolute maximum**
(datasheet §6.1) against a hot-plug transient that can overshoot well past
5.5 V. C3 (1 µF) damps it; nothing clamps it. A single-channel TVS on VBUS
would close this. Not fitted, because it is a new part and this project pins
parts deliberately rather than by reflex.

### Amended 2026-09-20: J1 pin numbering corrected

Captured first against the original table, then rewired when the connector was
found to have been read from the wrong end. The board-side nets are unchanged
— `PORT_TX` is still what the board drives — but they move pads: J1.2 now
carries `PORT_TX` through R1, J1.3 carries `PORT_RX` through R2, J1.4 is the
no-connect and J1.5 is ground. Confirmed in the netlist:

```
PORT_5V    J1.1 + C1.1 U1.1 U1.3
PORT_TX    J1.2 + R1.1 U5.1          TX_BUF  R1.2 + U4.10 (B1Y, output)
PORT_RX    J1.3 + R2.1 U5.2          RX_BUF  R2.2 + U4.8  (B3,  input)
unconnected-(J1-Pin_4-Pad4)
GND        J1.5 + ...
```

`TX_BUF` lands on the translator's B-side **output** and `RX_BUF` on its
B-side **input**, so the direction through the fixed-direction buffer matches
the rig that works.

### Still open after capture

1. ~~**Passive MPNs.**~~ **Done 2026-09-20**, except SW1/SW2 — see
   [bom/README.md](../bom/README.md) and SPDD §7.4. Two capture defects surfaced
   while pinning them, both fixed: **C4 had been drawn with the generic `C`
   symbol** instead of its own `PCL1A471MCL1GS` symbol, which cost it an MPN, a
   footprint and — on a polarised polymer capacitor — its polarity marking; and
   **the ten test pads were appearing as a BOM line**, now excluded from the BOM
   while staying on the board as copper. Pinning the switches then changed a
   third thing: **R9 is 2.2 kΩ, not 10 kΩ**, so SW1's contacts carry 1.5 mA
   against C&K's 1 mA minimum (SPDD §7.4). R10 stays 10 kΩ.
2. ~~**VBUS TVS**~~ **Accepted, not fitted** (2026-09-20). The USB port is a
   one-off setup interface — the operational path is J1 — so the exposure is
   closer to a debug header's than to a permanently cabled port. The risk is
   real and recorded; the decision is to carry it.
3. **Reference designators are functional, not positional.** Re-annotate in
   KiCad if left-to-right ordering matters for the assembly drawing.
