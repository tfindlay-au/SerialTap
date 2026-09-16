#!/usr/bin/env python
"""Quick voltmeter: take a short analog capture and print what each channel sees.

  python probe.py                 # AN0 and AN1, 0.5 s
  python probe.py --channels 0 1 2 3 --seconds 2

Use it to sanity-check probe placement before a real run - the wrong clip on
the wrong pin is invisible until the numbers come out wrong.
"""
import argparse
import tempfile
import pathlib

import numpy as np
from saleae import automation

import saleae_common as sc

ap = argparse.ArgumentParser()
ap.add_argument("--channels", type=int, nargs="+", default=[0, 1])
ap.add_argument("--seconds", type=float, default=0.5)
ap.add_argument("--rate", type=int, default=781_250)
args = ap.parse_args()

cfg = automation.CaptureConfiguration(
    capture_mode=automation.TimedCaptureMode(duration_seconds=args.seconds))
dev = automation.LogicDeviceConfiguration(
    enabled_analog_channels=args.channels, analog_sample_rate=args.rate)

with sc.connect() as manager, tempfile.TemporaryDirectory() as tmp:
    capture = manager.start_capture(device_configuration=dev,
                                    capture_configuration=cfg)
    capture.wait()
    capture.export_raw_data_binary(directory=tmp, analog_channels=args.channels)
    capture.close()

    print(f"{args.seconds:g} s at {args.rate:,} S/s\n")
    print(f"{'ch':>4} {'median':>10} {'mean':>10} {'min':>10} {'max':>10} "
          f"{'pk-pk':>10} {'rms noise':>10}")
    print("-" * 68)
    for ch in args.channels:
        _, _, v = sc.read_analog_bin(pathlib.Path(tmp) / f"analog_{ch}.bin")
        pk = float(v.max() - v.min())
        print(f"{ch:>4} {np.median(v):>9.4f}V {v.mean():>9.4f}V "
              f"{v.min():>9.4f}V {v.max():>9.4f}V {pk*1000:>8.1f}mV "
              f"{v.std()*1000:>8.2f}mV")
