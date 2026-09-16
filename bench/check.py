#!/usr/bin/env python
"""Pre-flight: is Logic 2 reachable and is the Logic Pro 8 present?

Run this first. It answers "can the laptop drive the analyser" before
anything is connected to the appliance.
"""
import saleae_common as sc

with sc.connect() as manager:
    print("Connected to the Logic 2 automation server on port %d." % sc.PORT)
    sc.describe_devices(manager)
    print("\nReady. Part 1 -> capture_uart.py, Part 2 -> capture_rail.py")
