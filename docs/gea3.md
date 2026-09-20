# The protocol is GEA3

**Established 2026-09-18/19.** The Haier AS50QDFHRA's service port speaks
**GE Appliances GEA3**, not Haier hOn and not smartAir2. ESPHome's `haier`
component does not apply to this unit. The SPDD's firmware scope and
[CONTEXT.md](../CONTEXT.md) still describe the old assumption; an ADR should
replace it and cite this file.

Measurement and inference are labelled separately throughout.

## How it was found

The 2026-09-16 capture ([bench-results.md](bench-results.md)) showed an
11-byte message every 30.004 s at 230400 8N1 with no `FF FF` preamble:

```
E2 BF 0B C0 A0 01 60 03 29 5B E3
```

The OEM board's silkscreen labels the signal lines `GEATX` / `GEARX`. GE
Appliances publishes its serial protocol library,
[tiny-gea-api](https://github.com/geappliances/tiny-gea-api), whose constants
(`include/tiny_gea_constants.h`, `include/tiny_gea_packet.h`,
`include/tiny_gea3_erd_api.h`, `src/tiny_gea3_interface.c`) decode the message
field by field:

| Bytes | Field | Source |
|---|---|---|
| `E2` | STX | `tiny_gea_stx = 0xE2` |
| `BF` | destination address | packet layout |
| `0B` | length = 11, the whole packet including STX and ETX | receiver checks `payload_length == receive_count + 2` |
| `C0` | source address | packet layout |
| `A0 01 60 03` | ERD read request (`0xA0`), request id 1, ERD `0x6003` | `tiny_gea3_erd_api_read_request_payload_t` |
| `29 5B` | CRC-16, poly `0x1021`, seed `0x1021`, over destination..payload, MSB first | `tiny_gea_crc_seed = 0x1021`, receiver valid when running CRC == 0 |
| `E3` | ETX | `tiny_gea_etx = 0xE3` |

The CRC was found by brute-forcing all 65536 seeds over several byte ranges
(`bench/`-style scratch script, not kept). The only seed that produces
`29 5B` over destination..payload is `0x1021`, GE's documented seed. A chance
match on exactly the documented seed is a 1-in-65536 event. Seed `0xE300`
over STX..payload also matches; it is the same computation, since feeding
`E2` into a seed of `E300` yields `1021`.

Everything else in the earlier capture fits GEA3 as documented by
[esphome-gea](https://github.com/mguaylam/esphome-gea): 230400 baud, 8N1,
full duplex, and the appliance polling the module rather than broadcasting.
The earlier search for an 8-bit checksum failed because `E3` is not a
checksum, it is the end-of-frame byte.

**Also ruled out on the way:**

- *smartAir2* shares hOn's `FF FF` transport (paveldn's README: "compatible on
  the transport level"), runs at 9600 in both of paveldn's example configs,
  and is controller-polled. Same three mismatches as hOn, plus it belongs to
  the older `KZW-W002` module generation, not this unit's Realtek `WCATA008`.
- *USB on the signal pins* (another `WCATA008` host reportedly has a USB-A
  socket). The line swings 0–5 V (USB signals at 3.3 V), the bit period is
  4.34 µs (no USB speed is near 230 kbit/s), only one line toggles (USB is
  differential), and the framing decodes as clean 8N1. paveldn's README says
  of Haier's USB-shaped ports: "It is a UART port that just uses a USB
  connector." The USB-A report is the same UART behind a different shell.

## Address conventions

| Address | Role | Status |
|---|---|---|
| `0xC0` | the appliance's control board | **supported**: esphome-gea's GE configs use `dest_address: 0xC0`; the appliance answered at it (below) |
| `0xBF` | the Wi-Fi module | **inferred**: it is the destination the appliance polls on the module's own connector. Claiming it worked (below) |
| `0xFF` | broadcast | GE constant |

ERD `0x6003`, the one the appliance reads from the module every 30 s, is
**not identified**. It is module-hosted, so it is probably a connection or
status word the appliance shows on its Wi-Fi indicator. That is a guess. The
firmware dump (below) should settle it.

## Live confirmation, 2026-09-19

An ESP32-S3 (Unexpected Maker TinyS3) running ESPHome 2025.11.2 with the
esphome-gea external component, wired through a BSS138 level shifter and
**powered from the appliance's own 5 V pin with no USB**, sent a GEA3
subscribe-all and the appliance answered with **64 ERDs**. The 30 s heartbeat
kept arriving, now addressed to `0xBF` = us, and the appliance answered every
periodic re-subscription (`cmd=0xA5`). Bus reported `CONNECTED`, RSSI −46 dB.

Config: [bench/esphome/as50qdfhra.yaml](../bench/esphome/as50qdfhra.yaml).
Component config that mattered: `protocol: gea3`, `src_address: 0xBF`,
`dest_address: 0xC0`, `erd_lookup: true`, UART on GPIO43/44 at 230400 with the
logger moved to `USB_SERIAL_JTAG` so it does not claim those pins.

### Wiring used

| Service port pin | Measured as | Went to |
|---|---|---|
| 1 | 5.0257 V supply | TinyS3 5V pin, and from there to shifter HV |
| 2 | idle high, silent = appliance RX | shifter HV2 ← LV2 ← TinyS3 GPIO43 (TX) |
| 3 | carries the heartbeat = appliance TX | shifter HV1 → LV1 → TinyS3 GPIO44 (RX) |
| 4 | no contact | — |
| 5 | ground | TinyS3 GND, and from there to the shifter GND (both shifter GND pins are one net) |

**Numbering corrected 2026-09-20.** This session read the connector from the
wrong end; the physical wiring above is what was built and what worked, only
the pin numbers were reversed. Old number *n* is new number *6 − n*. This table
is also the evidence that settles UART direction: the TinyS3's TX drives pin 2,
so pin 2 is the appliance's receiver, and pin 3 is its transmitter.

TinyS3 3V3 → shifter LV. The TinyS3 5V pin shares a net with USB VBUS, so
appliance power and USB are never connected at the same time.

### One anomaly

On the first power-up from the appliance the board associated with Wi-Fi but
was unreachable (connect to port 6053 returned errno 113, host unreachable,
i.e. the gateway could not ARP it). A press of the TinyS3 reset button fixed
it and it then ran stably. **Not diagnosed.** Candidates: power-on sequencing
on a rising rail, or a one-off. Test: cold power-cycle the appliance twice and
see whether the board comes up unaided. If it does not, that is a finding
about enable/reset timing that SerialTap's own design must handle.

### The ERD map, as discovered

Names are from GE's public ERD definition set via `erd_lookup`. Values are as
read with the unit **off**. GE ERDs carry temperatures in **Fahrenheit**; that
is an inference from the values (target range 60–86 = 16–30 °C, the Haier's
advertised range), not something the protocol states.

**The climate entity** (inference from names and values; to be confirmed by
changing each from the remote and watching `cmd=0xA6` publications):

| ERD | Name | Type | Raw | Value | Note |
|---|---|---|---|---|---|
| `0x7A0F` | WAC Power On/Off State | bool | 00 | off | |
| `0x7A01` | WAC Operation Mode | enum | 00 | 0 | |
| `0x7003` | Target Cooling Temperature | i16 | 0050 | 80 | °F; 26.7 °C |
| `0x7A00` | WAC Fan Setting | enum | 01 | 1 | |
| `0x7B07` | Up-down Air Swing | bool | 00 | false | |
| `0x7B08` | Left-right Air Swing | bool | 00 | false | |
| `0x7B05` | Sleep Mode | enum | 00 | 0 | |
| `0x7A02` | WAC Ambient Temperature | u8 | 4F | 79 | °F; 26.1 °C |
| `0x7100` | Inside ambient temperature | i16 | 0314 | 788 | tenths °F |
| `0x7101` | Inside coil temperature | i16 | 02F0 | 752 | tenths °F |
| `0x7261` | Compressor state | bool | 00 | false | |
| `0x7130` | Inside fan speed | u16 | 0000 | 0 | |
| `0x7132` | Inside target fan speed | u16 | 0000 | 0 | |
| `0x7B00` | Available AC Modes | enum×8 | 03 | 3 | |
| `0x7B0B` | Available AC Fan Speeds | enum×5,u8 | 0F | 15 | |
| `0x7B06` | Target Temperature Range | u8/u8 | 3C56 | 60/86 | °F = 16–30 °C |
| `0x7B09` | Air Swing Availability | enum/enum | 0101 | 1/1 | |
| `0x0007` | Temperature Display Units | enum | 01 | 1 | the unit displays °C |

**Everything else reported:**

| ERD | Name | Type | Raw |
|---|---|---|---|
| `0x0030` | Ready to Enter Boot Loader | enum | 03 |
| `0x0036` | Service Mode State Request | enum | 00 |
| `0x0037` | Service Mode State | enum | 00 |
| `0x008D` | *(unknown)* | | 00000029 |
| `0x7049` | Capacity in BTU/h | enum | 04 |
| `0x721F` | Sealed system diagnostic | enum | 00 |
| `0x7240` | *(unknown)* | | 00 |
| `0x724F` | Inside fan diagnostic | enum | 00 |
| `0x7503` | *(unknown)* | | 00 |
| `0x7960` | IDU DIP Switch Status | bool×9 | F1000000 |
| `0x7961` | *(unknown)* | | 01 |
| `0x7962` | *(unknown)* | | 01 |
| `0x7963` | Turbo/Quiet Mode Modifier Status | enum | 00 |
| `0x7964` | *(unknown)* | 32 bytes | all zero |
| `0x7965` | *(unknown)* | 32 bytes | all zero |
| `0x7966` | Electric Room Heater Presence | enum | 00 |
| `0x7967` | Electric Room Heater Status | bool | 00 |
| `0x7968` | Most Recent Fault Code Displayed | u32/u32/u16/u16/enum/u8/u8/u8 | 00000000000000000000000000100000 |
| `0x796A` | Outdoor temperature permits Self Clean operation | bool | 00 |
| `0x796B` | *(unknown)* | | 00 |
| `0x796C` | Communication Quality read from IDU | u8 | 00 |
| `0x796D` | Self Clean Mode Support | enum | 01 |
| `0x796E` | Self Clean Mode Status and Control | bool | 00 |
| `0x796F` | Cassette IDU DIP Switch Status | bool×18 | 00000000 |
| `0x7970` | Mid-Static IDU DIP Switch Status | bool×18 | 00000000 |
| `0x7971` | Console IDU DIP Switch Status | bool×18 | 00000000 |
| `0x7972` | External Damper Presence | enum | 00 |
| `0x7973` | External Damper Status | bool | 00 |
| `0x7974` | External Damper Request | bool | 00 |
| `0x7975` | Vacation Mode (10C Heating Mode) Status | bool | 00 |
| `0x7976` | Vacation Mode (10C Heating Mode) Control | bool | 00 |
| `0x7977` | Service Mode Electric Room Heater Request | bool | 00 |
| `0x7978` | Self Clean Request | enum | 00 |
| `0x7979` | Self Clean Reminder Timer Duration Selection | enum | 01 |
| `0x797A` | Self Clean Alert Countdown | u32 | 00007507 (29959) |
| `0x797B` | Alerts | bool×4,u8,u8 | 0000 |
| `0x797C` | Ready To Enter Vacation Mode | bool | 00 |
| `0x797D` | Static Pressure Setting Status | u16 | 0000 |
| `0x797E` | Float Switch Status | enum | 00 |
| `0x7980` | Temperature Display Mode Selection Request | enum | 00 |
| `0x7981` | Temperature Display Mode Selection Status | enum | 00 |
| `0x7982` | Motion Sensing Mode Selection Request | u8/u8/enum | 000000 |
| `0x7983` | Motion Sensing Mode Selection Status | u8/u8/enum | 000000 |
| `0x7A04` | WAC Filter Notification | enum | 00 |
| `0x7B04` | *(unknown)* | | 002D |
| `0x7B0A` | *(unknown)* | | 01 |

Ten ERDs are unnamed in GE's public set: `0x008D`, `0x7240`, `0x7503`,
`0x7961`, `0x7962`, `0x7964`, `0x7965`, `0x796B`, `0x7B04`, `0x7B0A`.

## What this changes

- **Firmware.** No protocol to learn. Control is writing `0x7A0F`, `0x7A01`,
  `0x7003`, `0x7A00`, `0x7B07`/`0x7B08`. esphome-gea already has switch,
  number and select entities that write ERDs; it has no climate entity, so
  that is the one piece of firmware work. The SPDD's "configure ESPHome's
  `haier` component" scope needs an ADR.
- **Hardware.** Unchanged. The bus is 5 V (level translation stays), 230400
  is inside FR-3, the connector and pin roles are as SPDD §5.2 expected.
  SerialTap claims address `0xBF`.
- **The 30 s heartbeat** is the appliance reading ERD `0x6003` from the
  module. Whether SerialTap must host an answer, and what it means, is open.

## Open items

1. **Publications on change.** From the remote: power, setpoint ±1, mode, fan,
   swing, one at a time, watching for `cmd=0xA6` and which ERD moved. Confirms
   the climate-entity table above and the enum values.
2. **Current draw from the rail.** DMM in series on the 5 V lead (10 A jack).
   Idle and Wi-Fi peaks. First measured value for the number the power design
   assumes. Not done 2026-09-19: one person on a ladder has no hands left.
3. **Cold power-cycle test** for the boot anomaly above.
4. **Firmware dump** of the `WCATA008` (Segger J-Link EDU Mini ordered
   2026-09-18, due the week of 2026-09-21). Now confirmation and completeness:
   the ten unnamed ERDs, ERD `0x6003`, and whatever the module writes.
   Procedure in the 2026-09-18 conversation; summary: LOGTX at 115200 first,
   then SWD on the `SWDCLK`/`SWDATA`/`RESET` test points, VTref from the
   board's 3V3, `savebin` through the XIP window (verify the base with
   `mem32` first; `0x98000000` is unverified recollection), dump twice and
   compare. Reading through XIP defeats AmebaZ2's execute-in-place
   encryption if it is enabled; a flash-clip read would not.
5. **ADR**: firmware scope from Haier `haier` component to GEA3 + esphome-gea +
   a climate entity. Update CONTEXT.md's reference-target paragraph.
