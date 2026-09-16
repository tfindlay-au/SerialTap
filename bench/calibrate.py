#!/usr/bin/env python
"""Measure the offset between the two analog channels, so it can be subtracted.

Tie BOTH probes to the same point (the bench PSU's +5 V terminal is ideal) and
both grounds to its return, then run this.

Why it is needed: the rig drop in bench-plan 2.2 is AN0 - AN1, and at the first
step that difference is only about 6 mV. A few millivolts of channel-to-channel
offset therefore lands squarely on top of the quantity being measured. With
both probes on one point the true difference is zero by construction, so
whatever is measured IS the offset.

Two modes:

  --record V   measure one point at the voltage now set on the PSU
  --fit        fit offset against voltage over the recorded points

Record at three or more voltages spanning the working range. On the Logic Pro 8
measured here the mismatch is NOT a fixed offset - it moves with the level, so
it is gain as well as offset, and a single-point correction leaves error behind
as the rail droops. With no --record/--fit, a single point is taken at --expect
and stored as a fallback.
"""
import argparse
import json
import pathlib
import tempfile

import numpy as np
from saleae import automation

import saleae_common as sc

CAL_PATH = pathlib.Path(__file__).resolve().parent / "calibration.json"

ap = argparse.ArgumentParser()
ap.add_argument("--channels", type=int, nargs=2, default=[0, 1],
                metavar=("AN_SOURCE", "AN_LOAD"))
ap.add_argument("--seconds", type=float, default=5.0)
ap.add_argument("--rate", type=int, default=781_250)
ap.add_argument("--expect", type=float, default=5.0,
                help="the voltage you have applied, for a sanity check")
ap.add_argument("--record", type=float, default=None, metavar="VOLTS",
                help="record one sweep point at the voltage now set on the PSU. "
                     "Repeat at 3+ voltages, then --fit. Separates a fixed "
                     "offset from a gain mismatch, which matters because the "
                     "rail droops ~200 mV during a real sweep.")
ap.add_argument("--fit", action="store_true",
                help="fit offset against voltage over the recorded points")
args = ap.parse_args()
an_src, an_load = args.channels

print(__doc__)


def grab(manager, tmpdir, dev, cfg):
    """One capture -> (median_src, median_load, diff_array)."""
    capture = manager.start_capture(device_configuration=dev,
                                    capture_configuration=cfg)
    capture.wait()
    capture.export_raw_data_binary(directory=tmpdir,
                                   analog_channels=[an_src, an_load])
    capture.close()
    _, _, a = sc.read_analog_bin(pathlib.Path(tmpdir) / f"analog_{an_src}.bin")
    _, _, b = sc.read_analog_bin(pathlib.Path(tmpdir) / f"analog_{an_load}.bin")
    k = min(a.size, b.size)
    return float(np.median(a[:k])), float(np.median(b[:k])), a[:k] - b[:k]


SWEEP_PATH = CAL_PATH.with_name("calibration-sweep.json")

if args.record is not None or args.fit:
    cfg = automation.CaptureConfiguration(
        capture_mode=automation.TimedCaptureMode(duration_seconds=args.seconds))
    dev = automation.LogicDeviceConfiguration(
        enabled_analog_channels=[an_src, an_load], analog_sample_rate=args.rate)
    pts = json.loads(SWEEP_PATH.read_text()) if SWEEP_PATH.exists() else []

    if args.record is not None:
        with sc.connect() as manager, tempfile.TemporaryDirectory() as tmp:
            m0, m1, _ = grab(manager, tmp, dev, cfg)
        pts = [q for q in pts if abs(q["set"] - args.record) > 1e-6]
        pts.append({"set": args.record, "an_src": m0, "an_load": m1,
                    "offset": m0 - m1})
        pts.sort(key=lambda q: q["set"])
        SWEEP_PATH.write_text(json.dumps(pts, indent=2))
        print(f"{args.record:.3f} V set  ->  AN{an_src}={m0:.5f} V  "
              f"AN{an_load}={m1:.5f} V  offset={(m0-m1)*1000:+.3f} mV")
        print(f"  {len(pts)} point(s) recorded in {SWEEP_PATH.name}")

    if args.fit:
        if len(pts) < 3:
            raise SystemExit(f"Need 3+ points to separate offset from gain; "
                             f"have {len(pts)}.")
        v = np.array([q["an_src"] for q in pts])   # measured level, not the dial
        d = np.array([q["offset"] for q in pts])
        print(f"\n{'PSU set':>9} {'AN'+str(an_src):>10} {'AN'+str(an_load):>10} "
              f"{'offset':>11}")
        print("-" * 44)
        for q in pts:
            print(f"{q['set']:>8.3f}V {q['an_src']:>9.5f}V {q['an_load']:>9.5f}V "
                  f"{q['offset']*1000:>+9.3f} mV")
        gain, const = np.polyfit(v, d, 1)
        resid = d - (gain * v + const)
        # Across the ~200 mV the rail droops, how far does a gain term move it?
        wander = abs(gain) * 0.2 * 1000
        print(f"\n  offset(V) = {const*1000:+.3f} mV  {gain*1000:+.3f} mV/V")
        print(f"  fitted over a {v.max()-v.min():.3f} V span, "
              f"worst residual {np.abs(resid).max()*1000:.3f} mV")
        print(f"  over a 200 mV droop that moves the offset by {wander:.3f} mV")
        fixed = wander < 0.2
        print("  -> effectively a FIXED OFFSET; a single-point correction is fine."
              if fixed else
              f"  *** GAIN-LIKE - a single-point correction leaves up to "
              f"{wander:.2f} mV of error across the sweep.")
        CAL_PATH.write_text(json.dumps({
            "channel_source": an_src, "channel_load": an_load,
            "offset_volts": float(np.interp(5.0, v, d)),
            "calibrated_at_volts": 5.0,
            "offset_fit_const_volts": float(const),
            "offset_fit_gain_per_volt": float(gain),
            "sweep_points": pts, "sample_rate": args.rate,
            "seconds": args.seconds, "stable": bool(fixed),
        }, indent=2))
        print(f"\nwritten to {CAL_PATH}")
    raise SystemExit(0)

cfg = automation.CaptureConfiguration(
    capture_mode=automation.TimedCaptureMode(duration_seconds=args.seconds))
dev = automation.LogicDeviceConfiguration(
    enabled_analog_channels=[an_src, an_load], analog_sample_rate=args.rate)

with sc.connect() as manager, tempfile.TemporaryDirectory() as tmp:
    capture = manager.start_capture(device_configuration=dev,
                                    capture_configuration=cfg)
    capture.wait()
    capture.export_raw_data_binary(directory=tmp,
                                   analog_channels=[an_src, an_load])
    capture.close()
    _, rate, v0 = sc.read_analog_bin(pathlib.Path(tmp) / f"analog_{an_src}.bin")
    _, _, v1 = sc.read_analog_bin(pathlib.Path(tmp) / f"analog_{an_load}.bin")

n = min(v0.size, v1.size)
v0, v1 = v0[:n], v1[:n]
m0, m1 = float(np.median(v0)), float(np.median(v1))
offset = m0 - m1          # add this to AN1 to put it on AN0's scale
diff = v0 - v1

print(f"applied ~{args.expect} V, {args.seconds:g} s, {n:,} samples\n")
print(f"  AN{an_src} (source side): {m0:.5f} V")
print(f"  AN{an_load} (load side)  : {m1:.5f} V")
print(f"  offset (AN{an_src} - AN{an_load}) = {offset*1000:+.3f} mV")

for ch, v, m in ((an_src, v0, m0), (an_load, v1, m1)):
    err = (m - args.expect) * 1000
    print(f"  AN{ch} absolute error vs the {args.expect} V you set: {err:+.1f} mV")
print("  (absolute error does not matter here - droop is a DIFFERENCE. "
      "The offset does.)")

# If the two channels see the same noise, the difference is quieter than either
# channel alone, and the rig-drop number is better than the raw noise suggests.
print(f"\n  noise rms: AN{an_src} {v0.std()*1000:.2f} mV, "
      f"AN{an_load} {v1.std()*1000:.2f} mV, difference {diff.std()*1000:.2f} mV")
if diff.std() < min(v0.std(), v1.std()):
    print("  the difference is quieter than either channel - the noise is")
    print("  largely common-mode, so the rig drop is better resolved than the")
    print("  per-channel figures imply.")
else:
    print("  the noise is largely independent between channels.")

# Drift: split the capture and compare halves. A stable offset is subtractable;
# a drifting one is not, and would need re-checking through the session.
h = n // 2
drift = (float(np.median(diff[:h])) - float(np.median(diff[h:]))) * 1000
print(f"  offset drift across the capture: {drift:+.3f} mV")
stable = abs(drift) < 0.5
print("  stable enough to subtract." if stable else
      "  *** DRIFTING - re-run calibration between steps, do not trust one value.")

CAL_PATH.write_text(json.dumps({
    "channel_source": an_src, "channel_load": an_load,
    "offset_volts": offset, "calibrated_at_volts": args.expect,
    "sample_rate": rate, "seconds": args.seconds,
    "drift_mv": drift, "stable": stable,
    "diff_noise_mv": float(diff.std()) * 1000,
}, indent=2))
print(f"\nwritten to {CAL_PATH}")
print(f"capture_rail.py will add {offset*1000:+.3f} mV to AN{an_load} from now on.")
