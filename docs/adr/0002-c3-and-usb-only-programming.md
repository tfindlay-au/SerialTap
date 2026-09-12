# 2. ESP32-C3-MINI-1, programmed over USB only

Date: 2026-09-12

## Status

Accepted

Supersedes an earlier working assumption of ESP32-S3-WROOM-1 with a
Tag-Connect TC2050 JTAG footprint.

## Context

The board started out with two level-translated UART ports, which argued for an
S3: three UART controllers, spare GPIO, and — importantly — JTAG brought out on
GPIO39-42, which a TC2050 pogo footprint could reach.

The port count then dropped to one. That removed the UART and GPIO pressure
entirely: one port needs one UART, and the console rides the built-in USB
Serial/JTAG controller.

It also exposed a hardware fact that invalidated the TC2050 plan. **The ESP32-C3
has no external JTAG pins.** Its only JTAG access is the built-in USB
Serial/JTAG controller on GPIO18/19. A TC2050 on a C3 board would carry the same
USB D+/D- pair as the USB-C connector — identical flashing, identical OpenOCD
debug, no additional capability.

The remaining argument for TC2050 was the inverse one: its footprint is bare
pads with zero BOM cost, whereas USB-C is a real connector, the hardest joint to
inspect, and the most mechanically abused part on a board that otherwise lives
sealed inside an appliance and updates over OTA.

## Decision

Use **ESP32-C3-MINI-1**. Provide **USB-C as the sole programming, logging and
debug interface**. Add **BOOT (GPIO9) and RESET (EN) tact switches** as the
recovery path. Do not fit a TC2050 footprint.

## Consequences

- Continuity with `daikin-esp`, which already runs ESPHome on a C3.
- Roughly half the module cost of an S3-WROOM-1 and a notably smaller footprint.
- No spare UART. A second port, or any future device needing its own serial
  channel, means a different module and a board revision.
- Ordinary flashing needs no buttons: esptool drives the C3's ROM USB
  Serial/JTAG into download mode over the CDC link on a virgin chip.
- The buttons exist for the cases where that fails — firmware repurposing
  GPIO18/19, a wedged USB peripheral, a hard boot-loop. Without them the board
  could become unrecoverable in the field.
- One programming path to document and test, not two.
- Production programming requires plugging a USB-C cable, so the enclosure must
  either expose the connector or be openable.
