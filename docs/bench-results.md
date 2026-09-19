# Bench results — AS50QDFHRA, 2026-09-16

Measurements taken against the real appliance, answering
[bench-plan.md](bench-plan.md). **Session incomplete** — Part 2 (power) and the
pin-order confirmation were not reached.

Instrument: Saleae Logic Pro 8 `5701262AE78884C9`, Logic 2.4.46, driven by the
scripts in [`bench/`](../bench/). Instrument characterisation and calibration
are recorded in the bench plan; the short version is that channel-to-channel
mismatch is `3.083 mV/V × V − 11.714 mV` and is corrected for.

---

## Answered

### Rail voltage — bench-plan 2.1

**5.0257 V open-circuit**, 5.1 mV pk-pk, measured at the pin identified below as
the supply.

**The `TPD4E05U06` ESD array stays.** Its 5.5 V standoff has only 0.5 V of
margin over 5 V logic, and 2.1 set a threshold of ~5.25 V for reconsidering it.
At 5.03 V there is 0.47 V of margin. No change.

### Logic levels — bench-plan 1.3

The active signal line swings **−0.17 V to 5.17 V**. Logic high is the 5 V rail,
not 3.3 V.

**Level translation is required.** That prediction was listed as one that could
have removed a whole block from the design; it does not.

### Baud and framing on the active line — bench-plan 1.3

**230400 baud, 8N1.** Not 9600 8E1.

Evidence, from 311 clean pulses across six bursts over 180 s:

| Baud | Pulses shorter than one bit time | Mean deviation from integer bits |
|---|---|---|
| 9600 | **306 of 311** | 0.286 |
| 115200 | 140 of 311 | 0.202 |
| **230400** | **0 of 311** | **0.031** |

9600 is not merely a worse fit, it is impossible: almost every pulse on this
line is shorter than a single 9600 bit time. 460800 fits comparably well
because it is the harmonic — but of 290 matching multiples, 289 are even and
one is odd, which is what a 230400 signal looks like measured against a 2.17 µs
ruler. Framing is 8N1: see the independent review below — **88 of 88 frames**
across all captures carry a valid start and stop bit at 10 bits per frame;
11-bit framings validate 2–4 of 9. (An earlier figure of "67%" was the first
decoder's failure to resync between frames, not a property of the signal.)

---

## Independent review of the capture

Re-analysed from the raw edge lists the same day, by a second pass that
reconstructed the bitstream itself rather than reusing either decoder.

**The capture is sound.** Three captures on two independent sample clocks
(500 MS/s and 6.25 MS/s), threshold 1.2 V on a 5 V line. Eight bursts. Refit
from raw edges, the bit period is **4.326 µs → 231,158 baud**, 0.33% from
230400 and inside the 160 ns sample resolution. At 8N1 every burst decodes to
exactly 11 frames, **all 88 with a valid start and stop bit**, same bytes each
time. 11-bit framings fail. And a structural check nobody designed in: every
burst spans exactly **106.0 bit-times**, which is precisely where the last edge
must fall if the final byte is `E3` (`11100011` LSB-first — bits 5–7 and the
stop bit are high and merge into idle, so the last edge sits at 100+1+5).

**230400 8N1 is verified and stands.**

**"Not hOn" is two claims with different truth values:**

- *This heartbeat is not an hOn frame* — **true, and sourced.** The hOn
  transport frame is `FF FF <len> <flags> <5 reserved> <type> <data>
  <checksum> <crc16>`
  ([paveldn, protocol_overview.rst](https://github.com/paveldn/haier-esphome/blob/master/docs/protocol_overview.rst)).
  Ours has no `FF FF`, and none of sum8 / xor8 / ten common CRC-8 variants
  produce the last byte. Independently, hOn is **controller-polled** — odd
  request types from the module, even responses from the appliance — whereas
  this appliance transmits *unsolicited* every 30.004 s. Two mismatches, not
  one.
- *This appliance does not speak hOn* — **not established.** A listen-only
  capture of the unpaired idle state cannot show what the appliance does when
  a controller addresses it. The earlier withdrawal of this claim was correct.

**Prior art:** every documented ESPHome-on-Haier success is a `KZW-W001/W002`
or an `ESP32-for-Haier` module
([goral.net.pl](https://goral.net.pl/post/replacing-haier-wifi-modules/),
[HA thread](https://community.home-assistant.io/t/esp-haier-haier-air-conditioner-esp-home-wemos-d1-mini/127880),
[esphaier](https://github.com/MiguelAngelLV/esphaier)). **Nothing was found
for the Realtek `WCATA008` / `Combo_RTK_PP` generation.** That absence is not
proof, but it means there is no one to copy.

**One unsourced number:** the SPDD states hOn as 8E1. The ESPHome doc page
does not state parity and the component inherits it from the `uart:` block.
It is probably 8N1 (ESPHome's default) and "8E1" appears never to have been
sourced. Irrelevant to the above; relevant before FR-3 is cited again.

## What the traffic actually is

The active line carries a **fixed 11-byte message every 30 seconds**:

```
burst 1 @  11.460s   E2 BF 0B C0 A0 01 60 03 29 5B E3
burst 2 @  41.464s   E2 BF 0B C0 A0 01 60 03 29 5B E3
   ... six bursts at 30.004 s intervals, byte-for-byte identical
```

Two facts establish what this is:

1. **The OEM Wi-Fi module was not connected.** It was on the bench, upstairs,
   throughout every capture in this session.
2. **The setpoint was changed about 22 times during the 180 s capture** — 27 °C
   down to 16 °C one degree at a time, then back up — and the traffic did not
   change at all.

So the appliance is **polling for a module that is not there**, and reporting
state to nobody. It has no reason to narrate the setpoint when nothing is
listening. The second signal line being silent for the full 180 s fits: nothing
drives the appliance's RX because nothing is plugged in.

This is the connector SerialTap plugs into, and that message is very probably
**the poll SerialTap will have to answer**. Recorded here because it is the
first concrete thing known about the protocol.

### Two useful consequences

**The appliance does not broadcast state unsolicited.** Twenty-two setpoint
changes produced no traffic beyond the heartbeat. Firmware cannot expect to
learn the appliance's state by listening; it will have to ask.

**The bytes are provisional.** They decode consistently at 230400 8N1, but they
do not match the `FF FF` preamble the hOn protocol is documented to use. Either
the framing is not quite right, or this poll is not an hOn frame. Do not build
anything on these eleven bytes yet.

### What this does *not* mean

An earlier draft of this document concluded "this is probably not the hOn bus".
**That was not supported and has been withdrawn.** It rested on the setpoint
changes not appearing in the traffic — which has a simpler explanation that
requires nothing to be wrong.

**No hardware change follows from the baud finding.** SPDD FR-3 already
requires the design to "impose no design ceiling below 1 Mbaud"; 230400 sits
well inside that and the TXU0204 handles it with room to spare.

## What this means for the project — the critical path has moved

The SPDD scopes firmware as "configuring ESPHome's existing `haier`
component" and puts protocol work **out of scope**. That was a bet that the
component works on this unit. Today produced the first evidence against the
bet — wrong baud, wrong framing, wrong direction on the only line that talks,
and no prior art for this module generation — and no evidence for it.

**If the protocol on this port cannot be learnt, the power gate and the board
are moot.** A UART bridge with nothing to say is not a product. So the order
of work changes:

1. **Establish that the protocol is knowable** — before any further hardware
   investment, including the load test.
2. Only then the power gate, and fabrication behind it.

The hardware is not wrong. It is, for the moment, unproven to be *useful*.

## Observed pin behaviour — provisional

Saleae channel *n* was clipped to connector pin *n+1*; connector pin 1 was used
as the ground reference.

| Pin | Ch | Behaviour | Reading |
|---|---|---|---|
| 1 | — | ground reference | — |
| 2 | 1 | floating | no contact, or a genuine no-connect |
| 3 | 2 | **active** — full-swing traffic | −0.17 to 5.17 V |
| 4 | 3 | idle high, zero transitions in 180 s | 5.0114 V |
| 5 | 4 | **supply** — dead steady | 5.0257 V, 5.1 mV pk-pk |

**Which end is pin 1 is unverified.** If the connector numbers from the other
end the whole table reverses. The shape — one ground, one spare, two signals,
one supply — matches SPDD §5.2's expectation, but the spare appears at position
2 rather than position 5, which may simply be the numbering running the other
way.

Settling this is [bench-plan 1.1](bench-plan.md): continuity from each
connector pin to the `GEATX` / `GEARX` test points on the OEM board's
underside, **with the unit powered off**. It was not done. Per the fabrication
gates it determines the cable, not a respin.

## DMM readings at the connector — partial

Taken with the unit switched off, at the end of the session.

**Ground is pin 1 of the JST XA**, confirmed by continuity. This is the one
piece of the pin map that is now measured rather than assumed, and it agrees
with how the Saleae was clipped (channel *n* to pin *n+1*), so the channel
mapping in the table above holds at least at that end.

**Pins 3 and 4 read approximately 1.387, drifting between 1.382 and 1.392**,
never settling.

### What is ambiguous about that, and must be re-checked first

Two things were not captured at the time and cannot be recovered from the
number:

1. **The units.** A four-digit "1.38x" on an auto-ranging meter is most likely
   **kΩ**, but MΩ is not excluded.
2. **What was measured against what.** Whether this was pin 3 to ground and
   pin 4 to ground, or pin 3 to pin 4, was not recorded.

Until both are pinned down this reading cannot be used for anything. Re-take it
as the first item of the next session.

### What it might mean

*This section is interpretation, not measurement.*

If it is **~1.4 kΩ from each signal pin to ground**, it sits squarely in the
range that matters for [bench-plan 2.5](bench-plan.md): the
[ADR 0001 amendment](adr/0001-fixed-direction-level-translation.md) worked the
R<sub>s</sub> problem against an assumed 1 kΩ pull-up and found that SPDD §5.6's
"100–330 Ω" range spans pass and fail. A real ~1.4 kΩ would let that resistor be
chosen rather than guessed — which is the whole point of test 2.5.

The instability is not necessarily a fault. A DMM measuring into an IC pin is
not measuring a resistor: it is driving a small test current into ESD
structures, input capacitance and whatever pull-up network is present, and the
reading reflects all of that. A ±0.4% wobble around 1.387 is mild. It is worth
noting, not worth worrying about yet.

**What would settle it:** with the unit off and the bulk capacitance given time
to discharge, measure each signal pin separately **to ground and to the 5 V
pin**, and in **both probe polarities** — a junction reads differently each way
and a resistor does not. That distinguishes a real pull-up from an ESD diode,
which is the difference between sizing R<sub>s</sub> and mis-sizing it.

## The test to run next

**Plug the `WCATA008` back into the appliance and sniff pins 3 and 4 with it
running.** That captures the real conversation, both directions, at its real
baud. It is the only test that answers the question that now matters:

- `FF FF …` at 9600 → ESPHome `haier` is viable; the 230400 heartbeat is an
  unrelated idle-mode behaviour, and the project resumes as planned.
- 230400 with no `FF FF` → the protocol is not hOn. Then the question is
  whether it can be learnt from the module's traffic, and the SPDD's scope
  needs an ADR before anything else is spent.

If piggybacking the connector with the module fitted is impractical, the
fallback is below.

### Fallback: the module on a bench PSU

**Power the OEM Realtek module on a bench PSU and watch its five pins.** It is
already off the appliance and on the desk, so this needs no ladder and no
dismantling. It answers more than the continuity check would:

- **The module's baud, independently.** Whatever it transmits must match the
  appliance. If it is 230400, this session's measurement is confirmed from the
  other direction; if it is 9600, the analysis here is wrong and that needs to
  be known.
- **Which pin is the module's TX**, and therefore the appliance's RX.
- **The module's real current draw** — see below.

### It also measures the number the power design rests on

The 300–370 mA requirement is derived, not measured: the RTL8720CM's datasheet
Table 20 gives 450 mA at 3.3 V, referred through the OEM buck to ≈330 mA at 5 V
([haier-oem-board.md](haier-oem-board.md)). **The actual module, powered on a
bench supply, measures that directly.** It is the assumption underneath the
fabrication gate.

**Identify the pins with a DMM before applying anything.** 5 V into a signal pin
destroys the module. Ground is whatever has continuity to the shield can; the
5 V pin reads through to the input side of the `C136/C138/C139` bulk group.
Set the PSU to 5.0 V with an **800 mA** limit — the documented inrush is ~590 mA,
and a limit set too low will brown the module into a reboot loop.

---

## Not reached

| | Why it matters |
|---|---|
| **Part 2 entirely — the V–I curve** | the fabrication gate — `RILIM`, `RAPP`, SPDD §12.1 step 2. **Now deferred behind the protocol question**; see above |
| Behaviour in current limit (2.3) | the one result that could still force a design change |
| Sag under pulsed load (2.4) | confirms `RAPP` dynamically |
| RX pull-up (2.5) | sizes R<sub>s</sub>, currently a 100–330 Ω guess. **Partially attempted** — see the DMM readings above |
| Pin order confirmation (1.1) | the harness and cable |
| Mechanical (Part 3) | mounting holes, connector placement |

The rail measurement needs the unit **powered on**; the continuity and pull-up
checks need it **off**. Doing power first and continuity last avoids a second
power cycle.

---

# Session 2 — 2026-09-19: two-way GEA3 confirmed

**The protocol is GE Appliances GEA3.** The heartbeat above decodes completely
against GE's public library, and an ESP32-S3 on the port, powered from pin 5,
received 64 ERDs in answer to a subscribe-all. Full decode, wiring, config,
ERD map and open items are in **[gea3.md](gea3.md)**. "Not hOn" is no longer
two claims: the appliance does not speak hOn, or smartAir2, at all.

Done this session, in order: heartbeat decoded (CRC seed `0x1021` over
destination..payload, ERD read request for `0x6003` from `0xC0` to `0xBF`);
smartAir2 and USB ruled out on the existing capture; TinyS3 + BSS138 shifter
wired to pins 1/3/4/5; flashed with esphome-gea; plugged in; discovery log
received over Wi-Fi.

Not done: the series-current measurement (bench-plan Part 2, still the
fabrication gate), the on-change publications, and the cold power-cycle test
for the boot anomaly recorded in gea3.md. The pin numbering is still
provisional; the roles are now confirmed by the fact that the conversation
worked.

**The critical path has moved back.** With the protocol known and public, the
power gate is once again the thing in front of fabrication.
