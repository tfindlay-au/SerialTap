#!/usr/bin/env python
"""Bench plan Part 1.2 - capture all five service-connector pins.

5 V threshold, heavily oversampled at 9600 baud. Attaches an Async Serial
analyzer to the pin that 1.1 identified as the appliance's TX so the frames
are decoded in the capture itself.

  python capture_uart.py --seconds 30 --tx-channel 0

Predictions this is checked against are in docs/bench-plan.md 1.3:
104.17 us/bit, 11 bits/frame (8E1), idle high, logic high ~5 V.
"""
import argparse
import datetime

from saleae import automation

import saleae_common as sc

ap = argparse.ArgumentParser()
ap.add_argument("--seconds", type=float, default=30.0,
                help="capture duration; poll intervals may be seconds apart")
ap.add_argument("--channels", type=int, nargs="+", default=[0, 1, 2, 3, 4],
                help="digital channels wired to the five connector pins")
ap.add_argument("--tx-channel", type=int, default=None,
                help="channel carrying appliance TX, per test 1.1; adds a decoder")
ap.add_argument("--baud", type=int, default=9600)
ap.add_argument("--threshold", type=float, default=1.2,
                help="COMPARATOR threshold in volts, not the logic family - "
                     "see the note in this file. Logic Pro 8 accepts a limited "
                     "set of values; an invalid one is rejected with a list.")
args = ap.parse_args()

# NOTE on --threshold, because the bench plan's "set it for 5 V" is ambiguous
# and the two readings give opposite settings.
#
# This parameter is the COMPARATOR voltage, not a logic-family label. It must
# land BETWEEN the bus's low and high, so for a 5 V bus the one value that is
# certainly wrong is 5.0 - that sits at the high rail and decodes everything
# as low. 1.2 V is the safe default: it is below even a TTL Voh minimum of
# 2.4 V, so it reads a 5 V bus whether the driver is CMOS or TTL.
#
# Logic Pro 8 does not accept arbitrary values. The real set is confirmed
# against the device on the day - run check.py first, and if a threshold is
# refused the error names what is allowed.

stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
out = sc.outdir(f"uart-{stamp}")


def device_config(rate):
    return automation.LogicDeviceConfiguration(
        enabled_digital_channels=args.channels,
        digital_sample_rate=rate,
        digital_threshold_volts=args.threshold,
    )


device_config.rates = sc.DIGITAL_RATE_CANDIDATES

capture_config = automation.CaptureConfiguration(
    capture_mode=automation.TimedCaptureMode(duration_seconds=args.seconds)
)

with sc.connect() as manager:
    sc.describe_devices(manager)
    print(f"\nThreshold {args.threshold} V, channels {args.channels}, "
          f"{args.seconds:g} s.")
    print("Change the setpoint or the mode NOW so the bus is not merely idling.")

    capture, rate = sc.start_capture(manager, device_config, capture_config,
                                     "UART")
    capture.wait()

    # Save the raw capture FIRST. The decode is a convenience; the samples are
    # the evidence, and a bad analyzer setting must never cost 45 s of traffic
    # from an appliance that is only opened up once.
    capture.export_raw_data_csv(directory=str(out), digital_channels=args.channels)
    capture.save_capture(filepath=str(out / "capture.sal"))
    print(f"raw capture saved -> {out}")

    if args.tx_channel is not None:
        analyzer = capture.add_analyzer(
            "Async Serial",
            label=f"TX ch{args.tx_channel}",
            settings={
                "Input Channel": args.tx_channel,
                "Bit Rate (Bits/s)": args.baud,
                "Bits per Frame": "8 Bits per Transfer (Standard)",
                "Stop Bits": "1 Stop Bit (Standard)",
                "Parity Bit": "Even Parity Bit",
                "Significant Bit": "Least Significant Bit Sent First (Standard)",
                "Signal inversion": "Non Inverted (Standard)",
                "Mode": "Normal",
            },
        )
        capture.export_data_table(
            filepath=str(out / "frames.csv"), analyzers=[analyzer]
        )
        print(f"decoded frames -> {out/'frames.csv'}")

    capture.close()

print(f"\nSaved to {out}")
print("Next: check the bit period against 104.17 us and the frame against "
      "~1.146 ms (docs/bench-plan.md 1.3).")
