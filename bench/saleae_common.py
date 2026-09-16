"""Shared helpers for the AS50QDFHRA bench session.

Talks to Logic 2 (2.4.46) over its automation server on port 10430.
The server is OFF by default: Logic 2 -> Preferences -> Automation ->
"Enable automation server", then restart Logic 2.
"""
from __future__ import annotations

import pathlib
import sys

from saleae import automation

PORT = 10430
CAPTURES = pathlib.Path(__file__).resolve().parent / "captures"

# Verified against Logic Pro 8 id 5701262AE78884C9 on 2026-09-16, for one and
# for two analog channels (the accepted set was identical for both). The
# automation API has no query for this, so these were found by probing.
# Note 25 MS/s is NOT accepted even though 50 and 12.5 are.
#
# Ordered lowest-first: the rail measurement wants the LOWEST rate, because the
# per-step file is proportional to it and 781.25 kS/s already gives ~1.5 M
# samples in 2 s - far more averaging than the measurement needs. Go higher
# only for transients (bench-plan 2.3 and 2.4), where the shape matters and
# not just the average.
ANALOG_RATES = [781_250, 1_562_500, 3_125_000, 6_250_000, 12_500_000, 50_000_000]
ANALOG_RATE_CANDIDATES = list(ANALOG_RATES)
DIGITAL_RATE_CANDIDATES = [  # verified set, lowest-first
    6_250_000, 12_500_000, 25_000_000, 50_000_000, 125_000_000, 500_000_000,
]


def connect() -> automation.Manager:
    """Connect to Logic 2, with an actionable message if the server is off."""
    try:
        return automation.Manager.connect(port=PORT, connect_timeout_seconds=5)
    except Exception as exc:
        if "Connection refused" in str(exc) or "UNAVAILABLE" in str(exc):
            sys.exit(
                "Cannot reach the Logic 2 automation server on port %d.\n"
                "  In Logic 2: Preferences -> Automation -> Enable automation\n"
                "  server, then restart Logic 2 and re-run this.\n"
                "  (Logic 2 must be running, and the Logic Pro 8 plugged in.)" % PORT
            )
        raise


def describe_devices(manager: automation.Manager) -> None:
    devices = manager.get_devices(include_simulation_devices=False)
    if not devices:
        sys.exit("Logic 2 is up but reports no hardware. Check the USB cable.")
    for dev in devices:
        print(f"  device: {dev.device_type}  id={dev.device_id}")


def start_capture(manager, device_config_factory, capture_config, label: str):
    """Start a capture, probing sample rates until the device accepts one.

    `device_config_factory(rate)` returns a LogicDeviceConfiguration.
    Returns (capture, rate_that_worked).
    """
    rates = device_config_factory.rates
    last = None
    for rate in rates:
        try:
            capture = manager.start_capture(
                device_configuration=device_config_factory(rate),
                capture_configuration=capture_config,
            )
        except Exception as exc:  # unsupported rate for this device
            last = exc
            continue
        print(f"{label}: capturing at {rate:,} S/s")
        return capture, rate
    raise SystemExit(f"No candidate sample rate accepted. Last error:\n{last}")


def outdir(name: str) -> pathlib.Path:
    CAPTURES.mkdir(parents=True, exist_ok=True)
    path = CAPTURES / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_analog_bin(path) -> tuple:
    """Read a Saleae analog .bin export -> (begin_time, sample_rate, samples).

    Format, verified against a Logic Pro 8 export on 2026-09-16 and cross-checked
    against the CSV of the same capture: magic '<SALEAE>', then int32 version,
    int32 type (1 = analog), float64 begin_time, uint64 sample_rate,
    uint64 downsample, uint64 num_samples, then num_samples of float32.
    """
    import struct

    import numpy as np

    with open(path, "rb") as fh:
        head = fh.read(8)
        if head != b"<SALEAE>":
            raise ValueError(f"{path}: not a Saleae binary export")
        version, dtype = struct.unpack("<ii", fh.read(8))
        if version != 0 or dtype != 1:
            raise ValueError(
                f"{path}: expected analog v0, got version={version} type={dtype}"
            )
        begin, rate, downsample, count = struct.unpack("<dQQQ", fh.read(32))
        samples = np.fromfile(fh, dtype="<f4", count=count)
    if samples.size != count:
        raise ValueError(f"{path}: expected {count} samples, got {samples.size}")
    return begin, rate / downsample, samples
