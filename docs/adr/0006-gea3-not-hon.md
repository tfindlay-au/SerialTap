# 6. The appliance protocol is GE Appliances GEA3, not Haier hOn

Date: 2026-09-19

## Status

Accepted

Replaces the firmware scope in SPDD §2 and §9, which assumed Haier hOn over
ESPHome's built-in `haier` climate component.

## Context

The project was scoped on the assumption that the reference appliance, a Haier
AS50QDFHRA, speaks the hOn protocol at 9600 8E1, and that firmware therefore
reduces to configuring ESPHome's existing `haier` component. Protocol work was
explicitly out of scope. That assumption was never sourced; it was inherited
from the fact that the appliance is a Haier.

The 2026-09-16 Saleae session found the service port transmitting an 11-byte
message every 30.004 s at 230400 8N1, with no `FF FF` preamble, unsolicited,
with the OEM module disconnected. That was evidence against hOn but did not
identify what the protocol was, and for two days the project's critical path
was "establish that the protocol is knowable at all" ahead of any further
hardware investment.

The OEM board's silkscreen labels its signal lines `GEATX` and `GEARX`. GE
Appliances owns GE Appliances-branded Haier product lines and publishes its
serial protocol library. Decoded against that library, the message is a
complete, valid GEA3 frame:

```
E2            STX
BF            destination, the Wi-Fi module
0B            length, 11, the whole packet including STX and ETX
C0            source, the appliance control board
A0 01 60 03   ERD read request, request id 1, ERD 0x6003
29 5B         CRC-16, poly 0x1021, seed 0x1021, over destination..payload
E3            ETX
```

Every field matches GE's published constants. The CRC seed was found by
exhaustive search over all 65536 seeds and the only one that fits is GE's
documented value. The earlier failed search for an 8-bit checksum failed
because `E3` is not a checksum, it is the end-of-frame byte.

Confirmed live on 2026-09-19: an ESP32-S3 running ESPHome with the esphome-gea
external component, through a level shifter, powered from the appliance's own
5 V pin, sent a GEA3 subscribe-all and the appliance answered with 64 ERDs.
Over the following fourteen minutes it answered 28 of 28 subscribe-all
requests with no CRC error, at a latency of 12 to 25 ms.

hOn, smartAir2 and USB-on-the-signal-pins were each ruled out; see
[gea3.md](../gea3.md) for the evidence on all three.

## Decision

**The reference appliance speaks GEA3.** Firmware is built on GEA3, not on
ESPHome's `haier` component, which does not apply to this unit at all.

GEA3 is public. GE publishes `tiny-gea-api` in portable C, and an ESPHome
external component, `esphome-gea`, already implements the transport, address
detection and the ERD read, write and subscribe layers. The remaining firmware
work is a climate entity over known ERDs, not protocol reverse engineering.

Protocol work stays out of scope in the sense that matters: nothing has to be
discovered from scratch. Mapping which ERD carries which control is
observation, done by changing a setting and watching which ERD publishes.

## Consequences

- **No hardware change.** This is the point of recording it. The bus is 5 V
  single-ended, ground-referenced, full duplex, 8N1, one line each way. Every
  hardware decision the protocol could touch is unaffected or confirmed.
- **[ADR 0001](0001-fixed-direction-level-translation.md) is validated rather
  than merely unbroken.** GEA3 is full duplex with a permanent direction per
  line, which is exactly what a fixed-direction translator wants. GEA2, the
  older protocol in the same family, is half duplex at 19200; had this been
  GEA2, fixed-direction translation would have been the wrong topology.
- **FR-3 is satisfied with room to spare.** 230400 against a requirement of no
  ceiling below 1 Mbaud.
- **Firmware is no longer coupled to ESPHome or to Home Assistant.** Because
  GEA3 has a plain C implementation, the board is viable with ESPHome, bare
  ESP-IDF, or anything else. Nothing in the schematic assumes either.
- **SerialTap claims bus address `0xBF`**, the address the appliance polls. The
  appliance is `0xC0`.
- **One new firmware question, no hardware impact:** the appliance reads ERD
  `0x6003` from the module every 30 s. Whether SerialTap must host an answer,
  and what the value means, is unknown. It kept talking when we answered
  nothing.
- The SPDD's claim that hOn is 8E1 was never sourced and is now moot. Do not
  cite it.

## What is deferred, and is now cheap

The ERD semantic map, the ten ERDs that GE's public definition set does not
name, and the meaning of ERD `0x6003`. The OEM module firmware dump, planned
for the week of 2026-09-21, becomes a completeness exercise rather than
discovery, and can slip without blocking anything.
