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
| 2 | `GND` | common return |
| 3 | `PORT_TX` | board output to appliance |
| 4 | `PORT_RX` | appliance output to board |
| 5 | `PORT_NC` | deliberately unconnected until the harness investigation assigns it |

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

- J1 pin 5 has no copper connection other than its own pad.
- No USB VBUS path can reach `PORT_5V` except through the LM66200 ideal-diode OR.
- The ESD array is ahead of both UART series resistors.
- `FB` is not floating; `VOS` senses at the output capacitor.
- Every unused TXU input is tied off and every unused output is explicitly no-connect.
- Every passive has an MPN before ERC/BOM review; values above are design values, not distributor substitutions.
