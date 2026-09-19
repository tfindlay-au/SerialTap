# Sourcing and cost — checked 2026-09-20

Scope: the **ten pinned parts** of SPDD §7.4. Passives, the two 5.1 kΩ CC
pulldowns, BOOT/RESET switches and the power LED are still unpinned (gate 2)
and are not in [bom.csv](bom.csv).

`bom.csv` is the sourcing capture. Its `Reference` column is `U?`/`J?`/`C?`
because the schematic is still empty — **capture has not happened yet**
(gate 3). Once it has, these MPNs and distributor PNs become symbol properties,
and the CSV gets regenerated from the schematic rather than hand-kept.

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
- **Passives are not counted.** Rough allowance once pinned: ~US$2–4/board at
  DigiKey prototype pricing, well under US$1 at LCSC

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
