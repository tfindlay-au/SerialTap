#!/usr/bin/env python
"""Bench plan Part 2.2 - the V-I curve, one step at a time.

You fit resistors; after each change you enter how many are now fitted and the
script takes a short capture on AN0 (at the appliance connector) and AN1 (at
the breadboard rails), then tells you immediately what the rail is doing.

  python capture_rail.py --resistance 119.4

--resistance is the MEASURED MEAN of the resistors going in, not 120. Parallel
conductances add, so the mean is what sets the array value (bench-plan 2.2).

Why short captures per step, rather than one long recording: the Logic Pro 8's
slowest analog rate is 781.25 kS/s, so a continuous run would make gigabytes of
data for a measurement that is flat by construction. More to the point, the
safety rule is "stop at the first sign of sag" - which requires seeing the sag
at the time, not when analysing afterwards. Each step is read out before you
are asked for the next one.

SAFETY, from docs/bench-plan.md:
  - work upward, never start with the biggest load
  - STOP at the first sign of sag - that is the answer, not a problem to
    push through
  - seconds per step, not minutes; spread the resistors out on the breadboard
  - check polarity twice; never short the rail
"""
import argparse
import datetime
import json
import pathlib
import sys

import numpy as np
from saleae import automation

import saleae_common as sc

PASS_MA = 370.0   # sim/README.md: the appliance must supply 300-370 mA
VBUCKREQ = 4.0    # sim/README.md: the buck's minimum input. A pass needs
                  # BOTH - 370 mA *while the rail stays above 4.0 V*.

ap = argparse.ArgumentParser()
ap.add_argument("--resistance", type=float, required=True,
                help="measured MEAN resistance of the fitted parts, in ohms")
ap.add_argument("--analog-channels", type=int, nargs=2, default=[0, 1],
                metavar=("AN_SOURCE", "AN_LOAD"),
                help="AN0 at the connector, AN1 at the breadboard rails")
ap.add_argument("--seconds", type=float, default=2.0,
                help="capture length per step")
ap.add_argument("--skip-calibration", action="store_true",
                help="run without calibrate.py's channel-offset correction; "
                     "the rig drop column is then unreliable")
ap.add_argument("--rate", type=int, default=781_250,
                help="analog sample rate; 781,250 is the Logic Pro 8 minimum "
                     "for a two-channel analog config")
args = ap.parse_args()

stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
out = sc.outdir(f"rail-{stamp}")
an_src, an_load = args.analog_channels
R = args.resistance

# Channel-to-channel offset, from calibrate.py. The rig drop is AN0 - AN1 and
# is only a few mV at the low steps, so an uncorrected offset of that same size
# would be most of the number. Refuse to run uncalibrated rather than quietly
# report a rig drop that is really an instrument artefact.
cal_path = pathlib.Path(__file__).resolve().parent / "calibration.json"
fit_gain = fit_const = None
if args.skip_calibration:
    offset = 0.0
    print("*** running UNCALIBRATED - the rig drop column is unreliable ***\n")
else:
    if not cal_path.exists():
        sys.exit(
            "No calibration.json. Tie both probes to one point (a bench PSU at\n"
            "5 V is ideal) and run:  python calibrate.py\n"
            "Or pass --skip-calibration to proceed without it, accepting that\n"
            "the rig drop column will be wrong by a few mV.")
    cal = json.loads(cal_path.read_text())
    if [cal["channel_source"], cal["channel_load"]] != [an_src, an_load]:
        sys.exit(f"calibration.json is for channels "
                 f"{cal['channel_source']}/{cal['channel_load']}, but this run "
                 f"uses {an_src}/{an_load}. Re-run calibrate.py.")
    offset = cal["offset_volts"]
    # The mismatch measured on this Logic Pro 8 is not a constant - it moves
    # with the level, so it is gain as well as offset. Where calibrate.py has
    # fitted that, correct against the voltage actually being read rather than
    # against one number taken at 5 V.
    fit_gain = cal.get("offset_fit_gain_per_volt")
    fit_const = cal.get("offset_fit_const_volts")

print(__doc__[__doc__.index("SAFETY"):])
print(f"R (measured mean) = {R} ohm  ->  {5.0/R*1000:.1f} mA per resistor at 5 V")
if fit_gain is not None and fit_const is not None:
    print(f"Channel correction: ({fit_gain*1000:+.3f} mV/V x V) "
          f"{fit_const*1000:+.3f} mV, applied against the measured level")
elif offset:
    print(f"Channel offset correction: {offset*1000:+.3f} mV added to AN{an_load} "
          f"(single point at 5 V)")
print(f"Logging to {out}\n")

device_config = automation.LogicDeviceConfiguration(
    enabled_analog_channels=[an_src, an_load], analog_sample_rate=args.rate)
capture_config = automation.CaptureConfiguration(
    capture_mode=automation.TimedCaptureMode(duration_seconds=args.seconds))


def measure(manager, tag: str) -> dict:
    """One short capture -> the medians, at full float32 precision."""
    step_dir = out / tag
    step_dir.mkdir(parents=True, exist_ok=True)
    capture = manager.start_capture(device_configuration=device_config,
                                    capture_configuration=capture_config)
    capture.wait()
    # Binary, not CSV: the CSV export rounds to 3 decimals (1 mV), and at these
    # currents the rig drop is only a few mV. Verified against the CSV of the
    # same capture - the two agree to exactly the CSV's quantisation.
    capture.export_raw_data_binary(directory=str(step_dir),
                                   analog_channels=[an_src, an_load])
    capture.save_capture(filepath=str(step_dir / "capture.sal"))
    capture.close()
    _, _, s_src = sc.read_analog_bin(step_dir / f"analog_{an_src}.bin")
    _, _, s_load = sc.read_analog_bin(step_dir / f"analog_{an_load}.bin")
    v_src_med = float(np.median(s_src))
    v_load_med = float(np.median(s_load))
    if fit_gain is not None and fit_const is not None:
        correction = fit_gain * v_src_med + fit_const
    else:
        correction = offset
    return {
        "v_src": v_src_med,
        "v_load": v_load_med + correction,
        "correction_mv": correction * 1000,
        "ripple_mv": float(np.std(s_src)) * 1000,
        "v_src_min": float(np.min(s_src)), "samples": int(s_src.size),
    }


steps = []
with sc.connect() as manager:
    sc.describe_devices(manager)

    input("\nFit NOTHING yet. Press Enter to take the open-circuit baseline > ")
    base = measure(manager, "n00-baseline")
    v_oc = base["v_src"]
    print(f"  open circuit: {v_oc:.4f} V  (ripple {base['ripple_mv']:.1f} mV)")
    if v_oc > 5.25:
        print("  *** ABOVE 5.25 V - the TPD4E05U06 ESD array (5.5 V standoff)")
        print("      needs reconsidering. See bench-plan 2.1.")
    else:
        print("  within the ESD array's margin (bench-plan 2.1)")
    steps.append({"n": 0, **base, "i_ma": 0.0})

    print("\nNow add resistors. Enter the number FITTED after each change.")
    print("Enter 'stop' when done, or at the first sign of sag.\n")

    try:
        while True:
            raw = input("resistors fitted now > ").strip().lower()
            if raw in ("stop", "q", "quit", "done"):
                break
            if not raw:
                continue
            try:
                n = int(raw)
            except ValueError:
                print("  enter a whole number, or 'stop'")
                continue
            if n <= 0:
                print("  the baseline is already taken; enter 1 or more")
                continue

            m = measure(manager, f"n{n:02d}")
            i_ma = m["v_load"] * n / R * 1000
            drop_mv = (m["v_src"] - m["v_load"]) * 1000
            sag_mv = (v_oc - m["v_src"]) * 1000
            rec = {"n": n, **m, "i_ma": i_ma}
            steps.append(rec)
            (out / "steps.json").write_text(json.dumps(
                {"resistance_ohm": R, "analog_sample_rate": args.rate,
                 "channel_offset_volts": offset,
                 "seconds_per_step": args.seconds, "v_open_circuit": v_oc,
                 "channel_source": an_src, "channel_load": an_load,
                 "steps": steps}, indent=2))

            print(f"  N={n:<3} I={i_ma:6.1f} mA   AN0={m['v_src']:.4f} V "
                  f"(sag {sag_mv:5.1f} mV)   AN1={m['v_load']:.4f} V "
                  f"(rig {drop_mv:4.1f} mV)   ripple {m['ripple_mv']:.1f} mV")
            print(f"         each part {5.0**2/R:.2f} W, array {5.0**2/R*n:.2f} W")

            # Incremental source impedance. A knee shows up here first, as this
            # number climbing away from the value the early steps established.
            loaded = [s for s in steps if s["n"] > 0]
            if len(loaded) >= 2:
                a, b = loaded[-2], loaded[-1]
                di = (b["i_ma"] - a["i_ma"]) / 1000.0
                if di > 1e-6:
                    r_inc = (a["v_src"] - b["v_src"]) / di
                    r_avg = (v_oc - b["v_src"]) / (b["i_ma"] / 1000.0)
                    print(f"         RAPP: {r_avg:.3f} ohm average, "
                          f"{r_inc:.3f} ohm over this last step")
                    if r_inc > max(3 * r_avg, r_avg + 0.5):
                        print("  *** THE RAIL IS STARTING TO GIVE. That is the")
                        print("      knee - it is the answer, not a problem to")
                        print("      push through. Type 'stop' now.")
            # Current alone is not the pass. A rail that has folded back can
            # still push 370 mA through a resistor while being useless to the
            # buck, so the voltage has to be checked at the same time.
            if m["v_src"] < VBUCKREQ:
                print(f"  *** BELOW {VBUCKREQ} V - the buck's minimum input. "
                      f"This current is not usable.")
                print("      Stop. Whatever the meter says, the rail has given up.")
            elif i_ma >= PASS_MA:
                print(f"  >>> {i_ma:.0f} mA at {m['v_src']:.4f} V, above "
                      f"{VBUCKREQ} V. That is the pass condition met.")
                print("      Confirm with analyse_rail.py - it checks for a knee")
                print("      underneath, which a single step cannot show.")
    except (KeyboardInterrupt, EOFError):
        print("\ninterrupted")

print(f"\nSaved {len(steps)} steps to {out}")
print(f"Next: bench/.venv/bin/python bench/analyse_rail.py {out}")
