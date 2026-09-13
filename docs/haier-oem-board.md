# The board SerialTap replaces

Notes from photographs of the OEM Wi-Fi board removed from the Haier
AS50QDFHRA, 2026-09-04. The photographs themselves are deliberately not carried
in this repository — they are a third-party board, examined to understand what
*this* design needs, not to reproduce it. SerialTap is an ESP32 design and
shares no circuitry with it.

Everything here is read off the silkscreen and component markings. It is
**evidence, not measurement** — it narrows what to expect, and does not replace
the bench work in [SPDD §12.1](SPDD.md).

## Identification

| | |
|---|---|
| Model | `WCATA008` |
| Board name | `Combo_RTK_PP_C.1` — Realtek combo (Wi-Fi + Bluetooth) |
| FCC ID | `ZKJ-WCATA008` |
| IC | `10229A-WCATA008` |
| Label | `V14429 **DC 5V**` |
| Outline | ≈22 × 54 mm — photo aspect ratio 2.41 against 2.45 for 22 × 54 |

## What it says about the 5 V rail

**The label reads DC 5V**, which confirms the supply voltage the whole design
assumes — previously an assumption, now corroborated.

More usefully, the board's own power architecture is *the same as SerialTap's*:

```
  5 V in (J103) ──► U108 + L104 + C136/C138/C139 ──► 3V3 ──► Realtek combo module
                    (SOP-8 + shielded inductor = a switching regulator, not an LDO)
```

So the appliance's service rail is **already designed to run a Wi-Fi radio,
through a buck converter, with a bursty transmit load** — the same shape of load
SerialTap presents, from the same connector. A Realtek Wi-Fi+BT combo draws
broadly what an ESP32-C3 draws during transmit.

### And it can be quantified

The FCC filing's internal photograph shows the part under the shield: **U101,
a Realtek `RTL8720CM`** — the Ameba-Z II Wi-Fi + BLE SoC. Its datasheet,
Table 20:

| Symbol | Parameter | Max |
|---|---|---|
| `IDD33` | 3.3 V rating current (internal regulator + integrated CMOS PA) | **450 mA** |
| `IRSH33` | 3.3 V inrush current | **800 mA** |

Referred through the OEM's own buck at ~90%, that is **≈330 mA at 5 V steady**
and **≈590 mA at 5 V inrush**.

Our ESP32-C3 peaks at 335 mA on 3.3 V — **less than the Realtek part's 450 mA
rating.** Its "ultra-low-power" billing refers to sleep states, not transmit;
the PA is subject to the same physics as everyone's.

So the appliance's service rail was specified to feed a load that peaks *higher*
than ours, and to survive an inrush larger than ours. Our requirement of
300–370 mA at 5 V sits inside that envelope, and the current-limited eFuse
(ADR 0004) makes SerialTap strictly better behaved at plug-in than the board it
replaces.

This is a chip *rating* rather than a measurement of the rail, so it is evidence
about what the OEM designed for, not proof of what the supply delivers. It says
nothing about what the rail does *in* current limit — which the decks assume is
a droop rather than a foldback or a reset. **Measure it anyway**
(SPDD §12.1 step 2). But the largest risk in this project just got
substantially smaller.

## The UART front end — independent validation

Around the service connector, on the back:

| Reference | Part | Role |
|---|---|---|
| `R141`, `R137` | resistors | series, in the signal lines |
| `D101` | SOT-23 marked `A7` = **BAV99** dual diode | clamp |
| `C122`, `C123` | capacitors | filtering |

That is *series resistor → clamp → filter cap*, which is the topology
[SPDD §5.6](SPDD.md) already specifies for SerialTap's port protection. The
OEM's own engineers, on the same bus in the same appliance, arrived at the same
answer.

Signals are silkscreened **`GEATX`** and **`GEARX`**. "GEA" is almost certainly
GE Appliances — Haier owns GEA, so this looks like a shared platform rather than
anything Haier-specific.

## Gold for the Wednesday probe

**`GEATX` and `GEARX` are exposed gold test points on the back of the board.**
That turns pin identification from inference into measurement: probe a test
point and a connector pin together and the mapping falls out directly, rather
than guessing which line is which from traffic direction.

Also present, and useful if the protocol ever needs decoding: `LOGTX`, `LOGRX`,
`SWDCLK`, `SWDATA`, `RESET` test points, and `J101`, an unpopulated 12-way
header — the Realtek SoC's debug and log interfaces.

## The antenna, and an inference that did not survive

The OEM board carries **`J102`, a U.FL / IPEX connector**, with `A102`, `L101`,
`C110` and `C111` forming a matching network at the far end from the service
connector.

I initially read that as evidence the chassis is RF-hostile and took it as an
argument for putting a U.FL on SerialTap. **That was wrong.** The connector was
never populated: nothing was ever plugged into it, and the unit ran on the
board's own antenna for its whole service life. An unpopulated U.FL is a
manufacturing option for other markets or installations — not evidence that the
on-board antenna was insufficient *here*.

The evidence in fact points the other way: in this exact appliance, in this
exact chassis, an on-board antenna was enough.

**Decision: ESP32-C3-MINI-1-H4X, with its PCB trace antenna.** Note the absence
of a `U`: `-1U` denotes a U.FL connector *instead of* an antenna, not as well as
one. The reference
installation has an access point about 3 m away with direct line of sight, so
the link budget is not demanding. The **-1U** variant remains the fallback if
bring-up shows poor RF — it is the same module with U.FL instead — but it is
not fitted on the strength of someone else's unused footprint.
