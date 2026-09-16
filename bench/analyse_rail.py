#!/usr/bin/env python
"""Turn a rail staircase into the numbers docs/bench-plan.md asks for.

  python analyse_rail.py captures/rail-YYYYmmdd-HHMMSS

capture_rail.py already reports each step live; this is the summary pass —
it fits the source impedance RAPP over the whole sweep, looks for a knee, and
states the pass/fail against the 370 mA requirement.
"""
import json
import pathlib
import sys

import numpy as np

PASS_MA = 370.0        # sim/README.md: the appliance must supply 300-370 mA
VBUCKREQ = 4.0         # sim/README.md: the buck's minimum input. The pass
                       # condition is BOTH - 370 mA *while above 4.0 V*.
RAIL_SAG_GUESS = 0.5   # what sim/rail-sag.cir currently assumes for RAPP

if len(sys.argv) != 2:
    sys.exit(__doc__)
run = pathlib.Path(sys.argv[1])
meta = json.loads((run / "steps.json").read_text())
R = meta["resistance_ohm"]
v_oc = meta["v_open_circuit"]
loaded = [s for s in meta["steps"] if s["n"] > 0]
if len(loaded) < 2:
    sys.exit("Need at least two loaded steps to fit anything.")

print(f"{run.name}: {len(loaded)} loaded steps, R = {R} ohm, "
      f"{meta['seconds_per_step']:g} s per step at "
      f"{meta['analog_sample_rate']:,} S/s\n")

print(f"Open-circuit rail: {v_oc:.4f} V")
if v_oc > 5.25:
    print("  *** above 5.25 V - TPD4E05U06 (5.5 V standoff) needs "
          "reconsidering (bench-plan 2.1)")
else:
    print("  within the ESD array's margin (bench-plan 2.1)")

print(f"\n{'N':>3} {'I (mA)':>9} {'AN0 (V)':>9} {'sag':>9} {'rig drop':>10} "
      f"{'ripple':>9} {'R_inc':>8}")
print("-" * 64)
prev = None
for s in loaded:
    sag = (v_oc - s["v_src"]) * 1000
    drop = (s["v_src"] - s["v_load"]) * 1000
    r_inc = ""
    if prev:
        di = (s["i_ma"] - prev["i_ma"]) / 1000.0
        if di > 1e-6:
            r_inc = f"{(prev['v_src'] - s['v_src']) / di:8.3f}"
    print(f"{s['n']:>3} {s['i_ma']:>9.1f} {s['v_src']:>9.4f} {sag:>7.1f} mV "
          f"{drop:>8.1f} mV {s['ripple_mv']:>7.1f} mV {r_inc:>8}")
    prev = s

# ---------------------------------------------------------------- knee
# Find where the curve stops being straight, using the step-to-step incremental
# resistance. Fitting a line to everything and looking at the last point does
# not work: once past the knee there are usually SEVERAL bad points, and they
# corrupt the very line they are being judged against.
inc = []
for a, b in zip(loaded, loaded[1:]):
    di = (b["i_ma"] - a["i_ma"]) / 1000.0
    inc.append((a["v_src"] - b["v_src"]) / di if di > 1e-6 else float("nan"))

knee_at = None
if len(inc) >= 3:
    for k in range(2, len(inc)):
        early = np.array(inc[:k], dtype=float)
        early = early[np.isfinite(early)]
        if early.size < 2:
            continue
        base = float(np.median(early))
        if np.isfinite(inc[k]) and inc[k] > max(3 * base, base + 0.3):
            knee_at = k + 1          # index into `loaded` of the first bad step
            break

linear = loaded[:knee_at] if knee_at else loaded

# ---------------------------------------------------------------- RAPP
i_a = np.array([s["i_ma"] for s in linear]) / 1000.0
v_a = np.array([s["v_src"] for s in linear])
if len(linear) >= 2:
    slope, intercept = np.polyfit(i_a, v_a, 1)
    resid = v_a - (slope * i_a + intercept)
    rapp = -slope
    scope = "the linear region" if knee_at else "the whole sweep"
    print(f"\nSource impedance RAPP = {rapp:.4f} ohm, fitted over {scope} "
          f"({len(linear)} steps)")
    print(f"  fitted open-circuit intercept {intercept:.4f} V "
          f"(measured {v_oc:.4f} V - {abs(intercept-v_oc)*1000:.1f} mV apart)")
    print(f"  worst fit residual {np.abs(resid).max()*1000:.1f} mV")
    if abs(rapp - RAIL_SAG_GUESS) > 0.05:
        print(f"  sim/rail-sag.cir guesses {RAIL_SAG_GUESS} ohm - replace it "
              f"with {rapp:.3f} and re-run the deck")
    else:
        print(f"  sim/rail-sag.cir's {RAIL_SAG_GUESS} ohm guess holds")
else:
    rapp = float("nan")
    print("\nToo few linear steps to fit RAPP.")

if knee_at:
    k = loaded[knee_at]
    prev = loaded[knee_at - 1]
    print(f"\n*** KNEE between {prev['i_ma']:.0f} mA and {k['i_ma']:.0f} mA: "
          f"the rail fell {(prev['v_src']-k['v_src'])*1000:.0f} mV over a step "
          f"that should have cost {rapp*(k['i_ma']-prev['i_ma']):.0f} mV.")
    print(f"    The appliance's current limit is about {prev['i_ma']:.0f} mA.")
    print("    Record what it DOES there - droop, foldback, latch-off, or a")
    print("    reset of the appliance. That is bench-plan 2.3, and it is the")
    print("    one result that could still force a design change.")

# ---------------------------------------------------------------- verdict
# Two conditions, not one. Current alone is not a pass: a rail that has folded
# back can still pass 370 mA through a resistor while being entirely unusable.
usable = [s for s in linear if s["v_src"] >= VBUCKREQ]
i_usable = max((s["i_ma"] for s in usable), default=0.0)
i_any = max(s["i_ma"] for s in loaded)
v_min = min(s["v_src"] for s in loaded)

print(f"\nHighest load on the linear region, above {VBUCKREQ} V: "
      f"{i_usable:.1f} mA")
if i_any > i_usable:
    print(f"  (the sweep reached {i_any:.1f} mA in total, and the rail got "
          f"down to {v_min:.4f} V - not usable current)")

if i_usable >= PASS_MA and not knee_at:
    print(f"\nPASS - the rail held {PASS_MA:.0f} mA above {VBUCKREQ} V with no "
          f"knee in sight.")
    print("       Clears SPDD 12.1 step 2, the fabrication gate.")
elif i_usable >= PASS_MA and knee_at:
    headroom = (loaded[knee_at - 1]["i_ma"] / PASS_MA - 1) * 100
    print(f"\nMARGINAL - {PASS_MA:.0f} mA is met, but the limit is only "
          f"{headroom:.0f}% above it.")
    print("       The design works and has almost no margin. Set RILIM from")
    print("       the measured limit, not from the requirement (ADR 0004).")
else:
    print(f"\nFAIL - only {i_usable:.1f} mA available above {VBUCKREQ} V, "
          f"against {PASS_MA:.0f} mA required.")
    if not knee_at:
        print("  The curve is still straight, so this is where the sweep")
        print("  stopped, not where the rail did. Fit more resistors if it is")
        print("  safe to (bench-plan 2.2).")
