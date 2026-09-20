# Sourcing and cost — checked 2026-09-20

Scope: **every line on the board**. The ten parts of SPDD §7.4 were checked on
2026-09-20; the passives were pinned and checked later the same day, once the
schematic fixed how many of each there are.

`bom.csv` is now **regenerated from the schematic**, so its `Reference` column
carries real designators instead of the old `U?`/`J?`/`C?` placeholders, and the
MPNs live in the symbol properties. The curated columns — distributor PNs,
stock, chosen distributor, notes — are merged forward by MPN, not regenerated.

**Every line now carries an MPN** — 22 lines, 33 components, **US$13.82/board**
at these prices. The switch line was settled on 2026-09-20 once the C&K
datasheet arrived by hand; it also forced R9 from 10 kΩ to 2.2 kΩ (SPDD §7.4).

## How this was checked

| Source | Method | Trust |
|---|---|---|
| LCSC | jlcsearch API, live query | Stock is live. **Price is indicative** — the API returns one figure, not a price ladder; LCSC's own ladder endpoint returned 404 |
| DigiKey | Product pages, live fetch | Stock and price ladder read directly off the product page |
| Mouser | **Checked by hand by the author** | Bot-blocked to automation. An API key was supplied 2026-09-20 and stored in `~/.config/secrets.env`, but Mouser rejects it as `Invalid unique identifier / API Key` — Search API keys sit in *pending authorization* after registration. Retry once it activates |
| Newark / element14 / Arrow | Not reached | All three refused automated access (403 / timeout) |

A `MOUSER_SEARCH_API_KEY` is now stored in `~/.config/secrets.env` (mode 0600,
outside this repo — it must never be committed), but is **not yet working**:
Mouser returns `Invalid unique identifier / API Key` on both the keyword and
part-number endpoints. The key is well-formed, so this is almost certainly
Mouser's registration approval still pending.

DigiKey has no credentials at all. Setting `DIGIKEY_CLIENT_ID` and
`DIGIKEY_CLIENT_SECRET` alongside a working Mouser key would make this whole
check a script rather than a one-off scrape — worth doing before the next
stock re-check, since stock data goes stale fast.

## The passives, pinned 2026-09-20

Searched by MPN against the jlcsearch API, because free-text search on that API
returns nothing — which suits this project anyway: the part is chosen first and
then checked for stock, never picked *because* it was in stock.

| Line | Refs | MPN | LCSC stock | US$ ea |
|---|---|---|---:|---:|
| 330 Ω 1% 0603 | R1, R2 | RK73H1JTTD3300F | 3,017 | 0.0051 |
| 5.1 kΩ 1% 0603 | R3, R4, R8 | RK73H1JTTD5101F | 13,741 | 0.0076 |
| 10 kΩ 1% 0603 | R9, R10 | RK73H1JTTD1002F | **1,192** | 0.0038 |
| 66.5 kΩ 1% 0603 | R5 | RK73H1JTTD6652F | 2,192 | 0.0154 |
| 100 kΩ 1% 0603 | R6, R7 | RK73H1JTTD1003F | 11,115 | 0.0043 |
| 100 nF 50 V X7R 0603 | C1, C7, C8, C9 | CL10B104KB8NNNC | 268,519 | 0.0115 |
| 1 µF 25 V X7R 0603 | C2, C3, C11 | CL10B105KA8NNNC | 178,930 | 0.0218 |
| 10 µF 25 V X7R 1206 | C5, C10 | CL31B106KAHNNNE | 30,509 | 0.2660 |
| 22 µF 25 V X7R 1210 | C6 | CL32B226KAJNNNE | 30,185 | 0.3599 |
| LED green 0603 | D1 | LTST-C191KGKT | 193,281 | 0.0217 |
| 2.2 kΩ 1% 0603 | R9 | RK73H1JTTD2201F | 1,033 | 0.0045 |
| Tact switch | SW1, SW2 | KMR211NGLFS | 8,125 | 0.6362 |

**The thinnest lines are the 2.2 kΩ at 1,033 and the 10 kΩ at 1,192** — about 100 boards' worth, and the
only passive under 2,000. Several other 10 kΩ 0603 1% parts showed absurdly low
stock in this index (Yageo RC0603FR-0710KL at 22, Panasonic ERJ-3EKF1002V at 2),
which is much more likely to be a partial index than the real LCSC position.
**Treat passive stock figures here as indicative only** — Mouser's API still
rejects its key, so there was no second source to cross-check against, and
DigiKey has no credentials at all.

**Datasheets are in [lib/datasheets](../lib/datasheets/)** for every pinned
passive. Samsung's own site and C&K's both refuse automated fetches; the Samsung
sheets came from a Future Electronics / Octopart mirror, and **the C&K one could
not be fetched at all**, which is why SW1/SW2 is still open.

## Every line is obtainable — but no single distributor can fill the board

| Part | DigiKey | Mouser | LCSC | Order from |
|---|---|---|---|---|
| TPS62162DSGT buck | 6,663 | — | 349 | LCSC |
| XGL4020-222MEC inductor | 3,876 | — | 5,408 | LCSC |
| B05B-XASK-1-A JST | 5,457 | — | 4,064 | DigiKey |
| TXU0204RUTR translator | 767 | — | 301 | DigiKey |
| **TPS2553DBVR eFuse** | **0** | **882** | **44,248** | **LCSC** |
| LM66200DRLR OR | 83,454 | — | 26,447 | DigiKey |
| TPD4E05U06QDQARQ1 ESD | 77,999 | — | **sample only** | DigiKey |
| USB4085-GF-A USB-C | 72,058 | — | 2,167 | DigiKey |
| **PCL1A471MCL1GS bulk** | **0** (24 wk, MOQ 500) | **69** | — | **Mouser** |
| ESP32-C3-MINI-1-H4X | **0** (4 wk, 3250 reel) | — | 911 | LCSC |

Three distributors, three shipments. **Three** lines are effectively
single-source — the eFuse is dual-sourced (LCSC and Mouser).

## The eFuse blocker is retired

SPDD §13 and CLAUDE.md both carry `TPS2553DBVR` availability as a live problem:
on 2026-09-19 only the `-1` latch-off variant — explicitly ruled out by ADR 0004
— could be found.

**The plain non-latching part is at LCSC as C55266, 44,248 in stock, ~$0.30.**
DigiKey is still out (3,000 arriving 2026-10-26), so the 2026-09-19 observation
was right about DigiKey and wrong only about the conclusion drawn from it.

**Mouser has it too: 882 in stock at A$1.60** (author-checked 2026-09-20). So
the part is genuinely dual-sourced, which matters more than the price gap —
LCSC is ~3× cheaper, but the Mouser order already has to happen for the bulk
capacitor, so the eFuse can ride along at no extra shipment if LCSC's stock
moves.

This takes the first of §13's three escape routes — *find the plain part at
another distributor* — so `TPS2552DBVR` and the `-1`-plus-auto-retry circuit are
both unnecessary. No design change, no library change.

One caveat: LCSC's auto-generated description for C55266 lists latch protection
among the features. That text is boilerplate for the whole TPS2553 family and is
not evidence about the suffix. **Check the package marking on receipt.**

## What is now the thinnest line

**PCL1A471MCL1GS, 69 pieces at one distributor.** Not a blocker, but it is the
only line with no second source and no depth:

- DigiKey stocks none — 24-week factory lead, 500-piece minimum (~US$456)
- LCSC does not list the part at all
- The sister part `PCR1E471MCL1GS` shows a 22-week lead and no stock at Arrow,
  so this is the series, not this one part number

Buy the spares in the same order. If that stock goes before the order does, the
fallback is a different 470 µF/10 V polymer — a substitution, which
[CLAUDE.md](../CLAUDE.md) says is proposed back and never applied silently.

Two other lines are single-source for reasons that are *choices*, not shortages:

- **TPD4E05U06QDQARQ1** — DigiKey only. LCSC has the `-Q1` solely as `-ES`
  engineering samples. The non-Q1 `TPD4E05U06DQAR` is everywhere and cheap, but
  §7.4 bought the `-Q1` for its temperature grade in a warm appliance
- **ESP32-C3-MINI-1-H4X** — LCSC only. The `H` (105 °C) and `X` (rev v1.1, since
  every non-X is NRND) are both mandatory; `-N4` is plentiful and is not a
  substitute

## Cost

Ten pinned parts, per board, cheapest in-stock source, USD:

| | Unit |
|---|---|
| ESP32-C3-MINI-1-H4X | 3.08 |
| PCL1A471MCL1GS | ~2.13 (A$3.25) |
| TPS62162DSGT | 1.50 |
| XGL4020-222MEC | 1.36 |
| TXU0204RUTR | 0.84 |
| TPD4E05U06QDQARQ1 | 0.79 |
| USB4085-GF-A | 0.77 |
| LM66200DRLR | 0.42 |
| TPS2553DBVR | 0.30 |
| B05B-XASK-1-A | 0.26 |
| **Total** | **≈ US$11.46** |

For 5 boards + 2 spares (7 pieces): **≈ US$80** in pinned parts — roughly
US$22 DigiKey, US$44 LCSC, US$15 Mouser.

Caveats, because these are estimates and not a quote:

- **Currency.** DigiKey and LCSC figures are USD as listed. The Nichicon is the
  author's Mouser AU figure, A$3.25, converted at an assumed ~0.66 — treat the
  conversion as approximate
- **Excludes** shipping, GST and duty. At this order size, shipping across three
  distributors to Australia will be a significant fraction of the parts cost,
  possibly more than it
- **Order 10, not 7, of the DigiKey lines.** DigiKey's qty-10 break means ten
  pieces cost about the same as seven at qty-1 pricing (≈US$31 vs ≈US$30). The
  extra spares are essentially free
- The Coilcraft inductor at DigiKey is a **Marketplace** listing: +US$10 flat
  shipping on its own. LCSC (5,408 in stock, cheaper) or Coilcraft direct avoids
  that — one reason it lands on LCSC above
- **Passives now counted** (2026-09-20): **US$1.09/board** at LCSC indicative
  pricing for the 21 pinned passive components (ten resistors, ten ceramics
  and the LED; the bulk capacitor is counted separately at US$2.13), of which the two 10 µF 1206 and
  the one 22 µF 1210 are US$0.89 — the ceramics dominate, and they dominate
  because they are 25 V X7R rather than the cheapest part that meets the value.
  The board total is **~US$12.55**, excluding the still-open switch line

The module and the bulk cap together are 45% of the board's parts cost. Nothing
here is worth optimising — [CLAUDE.md](../CLAUDE.md) principle 1 — it is
recorded because the number was asked for.

## For the PCBWay export

PCBWay turnkey sources by MPN, so `bom.csv` already carries what the quote
needs: MPN, manufacturer, and a distributor PN per line to disambiguate.

Two things to hand them explicitly, because they are the lines where a
well-meaning substitution would be wrong:

1. `TPS2553DBVR` — **not** `TPS2553DBVR-1`. The suffix is the whole decision
   (ADR 0004)
2. `ESP32-C3-MINI-1-H4X` — **not** `-N4`, **not** non-`X`, **not** `-1U`

Both belong in the order notes, not just the BOM.
